from typing import Dict, Any
from uuid import UUID
from decimal import Decimal
import asyncio
from functools import partial
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.core.db_lock import acquire_db_lock
from src.core.exceptions import (
    BusinessLogicException,
    ResourceNotFoundException,
)
from src.domains.payment.gateways.paystack import PaystackGateway
from src.domains.payment.enums import SubscriptionStatus, BillingCycle
from src.domains.payment.services.plan_management_service import PlanManagementService
from src.domains.payment.services.subscription_service import SubscriptionService
from src.domains.payment.repositories.paystack_subscription_repository import (
    PaystackSubscriptionRepository,
)
from src.domains.payment.repositories.subscription_repository import (
    SubscriptionRepository,
)
from src.domains.payment.repositories.paystack_plan_repository import (
    PaystackPlanRepository,
)
from src.domains.payment.schemas.subscription import SubscriptionCreate
from src.domains.payment.schemas.subscription import SubscriptionUpgradeRequest
from src.domains.auth.services.user_service import UserService


class SubscriptionBillingService:
    """Service to handle subscription billing with Paystack"""

    def __init__(self, db: Session):
        self.db = db
        self.paystack = PaystackGateway()
        self.plan_service = PlanManagementService(db)
        self.subscription_service = SubscriptionService(db)
        self.ps_repo = PaystackSubscriptionRepository(db)
        self.sub_repo = SubscriptionRepository(db)
        self.psl_repo = PaystackPlanRepository(db)
        self.user_service = UserService(db)

    async def ensure_paystack_plan_exists(
        self, plan_code: str, billing_cycle: BillingCycle
    ) -> str:
        internal_plan_code = f"{plan_code}_{billing_cycle.value}"

        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            None,
            partial(acquire_db_lock, self.db, f"paystack_plan:{internal_plan_code}"),
        )

        local_plan = await loop.run_in_executor(
            None, partial(self.psl_repo.get_by_internal_code, internal_plan_code)
        )

        if local_plan:
            return local_plan.paystack_plan_code

        plan_config = await self.plan_service.get_plan_by_code(plan_code)

        interval_map = {
            BillingCycle.MONTHLY: "monthly",
            BillingCycle.QUARTERLY: "quarterly",
            BillingCycle.YEARLY: "annually",
        }
        interval = interval_map.get(billing_cycle, "monthly")
        price, _ = await self.plan_service.get_plan_pricing(plan_code, billing_cycle)

        created_plan = await self.paystack.create_plan(
            plan_code=internal_plan_code,
            name=plan_config.plan_name,
            amount=price,
            interval=interval,
            description=plan_config.description,
        )

        plan_local = {
            "internal_plan_code": internal_plan_code,
            "billing_cycle": billing_cycle.value,
            "paystack_plan_code": created_plan["plan_code"],
            "paystack_plan_id": created_plan["id"],
        }

        await loop.run_in_executor(None, partial(self.psl_repo.create, plan_local))

        return created_plan.get("plan_code")

    async def ensure_paystack_plan_exists_old(
        self, plan_code: str, billing_cycle: BillingCycle
    ) -> str:
        """Ensure plan exists on Paystack and return Paystack's plan code"""
        internal_plan_code = f"{plan_code}_{billing_cycle.value}"

        acquire_db_lock(self.db, f"paystack_plan:{internal_plan_code}")

        local_plan = self.psl_repo.get_by_internal_code(internal_plan_code)
        if local_plan:
            return local_plan.paystack_plan_code

        # Create plan on Paystack
        plan_config = await self.plan_service.get_plan_by_code(plan_code)

        interval_map = {
            BillingCycle.MONTHLY: "monthly",
            BillingCycle.QUARTERLY: "quarterly",
            BillingCycle.YEARLY: "annually",
        }

        interval = interval_map.get(billing_cycle, "monthly")

        price, _ = await self.plan_service.get_plan_pricing(plan_code, billing_cycle)

        created_plan = await self.paystack.create_plan(
            plan_code=internal_plan_code,
            name=plan_config.plan_name,
            amount=price,
            interval=interval,
            description=plan_config.description,
        )

        plan_local = {
            "internal_plan_code": internal_plan_code,
            "billing_cycle": billing_cycle.value,
            "paystack_plan_code": created_plan["plan_code"],
            "paystack_plan_id": created_plan["id"],
        }
        self.psl_repo.create(plan_local)

        paystack_plan_code = created_plan.get("plan_code")
        return paystack_plan_code

    async def start_checkout(
        self, user_id: UUID, user_email: str, subscription_data: SubscriptionCreate
    ) -> Dict[str, Any]:
        """
        Step 1: Initialize subscription checkout
        - Create internal subscription (PENDING)
        - Initialize Paystack payment
        - Return payment URL for user
        """
        # Check if user already has active subscription
        existing = self.sub_repo.get_active_subscription(user_id)
        if existing:
            raise BusinessLogicException(
                "You already have an active subscription. Please cancel or upgrade it first."
            )

        # Get plan pricing
        price, plan_meta = await self.plan_service.get_plan_pricing(
            subscription_data.plan, subscription_data.billing_cycle
        )

        # Create internal subscription (PENDING status)
        subscription = await self.subscription_service.create_subscription(
            user_id, subscription_data
        )

        # Initialize Paystack payment
        payment = await self.paystack.initialize_payment(
            email=user_email,
            amount=price,
            # transaction_ref=subscription.subscription_reference,
            callback_url=subscription_data.callback_url,
            metadata={
                "subscription_id": str(subscription.id),
                "plan_code": subscription_data.plan,
                "billing_cycle": subscription_data.billing_cycle.value,
                "user_id": str(user_id),
            },
        )

        return {
            "subscription_id": subscription.id,
            "subscription_reference": subscription.subscription_reference,
            "authorization_url": payment["authorization_url"],
            "access_code": payment["access_code"],
            "reference": payment["reference"],
        }

    async def confirm_payment_and_activate(self, reference: str) -> Dict[str, Any]:
        """
        Step 2: Confirm payment and activate subscription
        Called after user completes payment on Paystack
        - Verify payment with Paystack
        - Create Paystack subscription
        - Activate internal subscription
        - Store Paystack subscription details
        """

        # Verify payment
        payment = await self.paystack.verify_payment(reference)

        if payment["status"] != "success":
            raise BusinessLogicException("Payment verification failed")
        customer_code = payment["customer"]["customer_code"]

        payment_type = payment.get("metadata", {}).get("type")

        if payment_type == "upgrade_proration":
            subscription_id = UUID(payment["metadata"]["subscription_id"])
            success = await self.complete_upgrade_after_payment(
                subscription_id, customer_code, reference
            )

            if not success:
                raise BusinessLogicException("Failed to complete subscription upgrade")

            subscription = self.sub_repo.get_by_id(subscription_id)
            ps_sub = self.ps_repo.get_by_subscription_id(subscription_id)

            return {
                "status": "success",
                "subscription_reference": subscription.subscription_reference,
                "next_payment_date": ps_sub.next_payment_date if ps_sub else None,
                "message": "Subscription upgraded successfully",
            }
        # Get subscription from metadata
        subscription_id = UUID(payment["metadata"]["subscription_id"])
        subscription = self.sub_repo.get_by_id(subscription_id)

        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.status == SubscriptionStatus.ACTIVE:
            existing_ps = self.ps_repo.get_by_subscription_id(subscription.id)
            return {
                "status": "success",
                "subscription_id": str(subscription.id),
                "subscription_reference": subscription.subscription_reference,
                "next_payment_date": existing_ps.next_payment_date
                if existing_ps
                else None,
                "message": "Subscription already active",
            }
        try:
            # Get authorization code and customer code from payment
            authorization_code = payment["authorization"]["authorization_code"]

            # Ensure Paystack plan exists
            paystack_plan_code = await self.ensure_paystack_plan_exists(
                subscription.plan_code, BillingCycle(subscription.billing_cycle)
            )

            if not paystack_plan_code:
                raise BusinessLogicException("Failed to resolve Paystack plan code")

            paystack_subscription = await self.paystack.create_subscription(
                customer=customer_code,
                plan=paystack_plan_code,
                authorization=authorization_code,
            )

        except Exception as e:
            raise BusinessLogicException(f"Failed to create subscription: {str(e)}")

        # Store Paystack subscription details
        self.ps_repo.create(
            {
                "subscription_id": subscription.id,
                "paystack_subscription_code": paystack_subscription[
                    "subscription_code"
                ],
                "paystack_email_token": paystack_subscription["email_token"],
                "authorization_code": authorization_code,
                "customer_code": customer_code,
                "next_payment_date": paystack_subscription.get("next_payment_date"),
                "status": "active",
                "created_by": subscription.owner_id,
            }
        )

        # Activate internal subscription
        await self.subscription_service.activate_subscription(
            subscription.id, reference
        )

        return {
            "status": "success",
            "subscription_id": subscription.id,
            "subscription_reference": subscription.subscription_reference,
            "next_payment_date": paystack_subscription.get("next_payment_date"),
            "message": "Subscription activated successfully",
        }

    async def pause_subscription(self, subscription_id: UUID, user_id: UUID) -> bool:
        """Pause a subscription (stop charging but keep data)"""
        subscription = self.sub_repo.get_by_id(subscription_id)

        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.owner_id != user_id:
            raise BusinessLogicException("Only subscription owner can pause")

        if subscription.status != SubscriptionStatus.ACTIVE:
            raise BusinessLogicException(
                f"Cannot pause subscription in {subscription.status} status"
            )

        # Get Paystack subscription details
        ps_sub = self.ps_repo.get_by_subscription_id(subscription_id)

        if not ps_sub:
            raise BusinessLogicException("Paystack subscription not found")

        # Disable on Paystack
        success = await self.paystack.disable_subscription(
            ps_sub.paystack_subscription_code,
            ps_sub.paystack_email_token,
        )

        if success:
            # Update internal status
            self.sub_repo.update(
                subscription_id,
                {"status": SubscriptionStatus.SUSPENDED, "updated_by": user_id},
            )

            # Update Paystack subscription status
            self.ps_repo.update(ps_sub.id, {"status": "paused"})

            return True

        raise BusinessLogicException("Failed to pause subscription on Paystack")

    async def resume_subscription(self, subscription_id: UUID, user_id: UUID) -> bool:
        """Resume a paused subscription"""
        subscription = self.sub_repo.get_by_id(subscription_id)

        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.owner_id != user_id:
            raise BusinessLogicException("Only subscription owner can resume")

        if subscription.status != SubscriptionStatus.SUSPENDED:
            raise BusinessLogicException(
                f"Cannot resume subscription in {subscription.status} status"
            )

        # Get Paystack subscription details
        ps_sub = self.ps_repo.get_by_subscription_id(subscription_id)

        if not ps_sub:
            raise BusinessLogicException("Paystack subscription not found")

        # Fetch current status from Paystack
        try:
            ps_details = await self.paystack.fetch_subscription(
                ps_sub.paystack_subscription_code
            )
            ps_status = ps_details["status"]

            if ps_status == "active":
                # Already active, just update our records
                self.sub_repo.update(
                    subscription_id,
                    {"status": SubscriptionStatus.ACTIVE, "updated_by": user_id},
                )
                self.ps_repo.update(ps_sub.id, {"status": "active"})
                return True

            if ps_status not in ["inactive", "non-renewing"]:
                raise BusinessLogicException(
                    f"Subscription cannot be resumed. Current status: {ps_status}"
                )
        except Exception as e:
            raise BusinessLogicException(
                f"Failed to fetch subscription status: {str(e)}"
            )

        # Enable on Paystack
        success = await self.paystack.enable_subscription(
            ps_sub.paystack_subscription_code,
            ps_sub.paystack_email_token,
        )

        if success:
            # Update internal status
            self.sub_repo.update(
                subscription_id,
                {"status": SubscriptionStatus.ACTIVE, "updated_by": user_id},
            )

            # Update Paystack subscription status
            self.ps_repo.update(ps_sub.id, {"status": "active"})

            return True

        raise BusinessLogicException("Failed to resume subscription on Paystack")

    async def cancel_subscription(
        self, subscription_id: UUID, user_id: UUID, reason: str = None
    ) -> bool:
        """
        Cancel subscription completely
        This will stop future charges on Paystack
        """
        subscription = self.sub_repo.get_by_id(subscription_id)

        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.owner_id != user_id:
            raise BusinessLogicException("Only subscription owner can cancel")

        if subscription.status in [
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.EXPIRED,
        ]:
            raise BusinessLogicException(
                f"Subscription is already {subscription.status.lower()}"
            )

        # Get Paystack subscription details
        ps_sub = self.ps_repo.get_by_subscription_id(subscription_id)

        if ps_sub:
            try:
                # Disable on Paystack (this cancels future charges)
                await self.paystack.disable_subscription(
                    ps_sub.paystack_subscription_code,
                    ps_sub.paystack_email_token,
                )

                # Update Paystack subscription status
                self.ps_repo.update(ps_sub.id, {"status": "cancelled"})
            except Exception as e:
                print(f"Warning: Failed to cancel on Paystack: {e}")

        # Cancel internal subscription (keeps active until end date)
        await self.subscription_service.cancel_subscription(
            subscription_id, user_id, reason, cancel_immediately=False
        )

        return True

    async def upgrade_subscription(
        self,
        subscription_id: UUID,
        user_id: UUID,
        upgrade_data: SubscriptionUpgradeRequest,
    ) -> Dict[str, Any]:
        """
        Upgrade or downgrade subscription with proration.

        Steps:
        1. Validate the upgrade
        2. Calculate prorated amount
        3. If upgrade with payment needed: Return payment URL
        4. If downgrade or no payment: Update immediately
        """

        subscription = self.sub_repo.get_by_id(subscription_id)

        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.owner_id != user_id:
            raise BusinessLogicException("Only subscription owner can upgrade")

        if subscription.status not in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.SUSPENDED,
        ]:
            raise BusinessLogicException(
                f"Cannot upgrade subscription in {subscription.status} status"
            )

        # Validate new plan
        if upgrade_data.new_plan == subscription.plan_code:
            raise BusinessLogicException("You are already on this plan")

        # Get current and new plan details
        # Get billing cycle
        billing_cycle = BillingCycle(subscription.billing_cycle)

        # Get current and new pricing
        current_price, _ = await self.plan_service.get_plan_pricing(
            subscription.plan_code, billing_cycle
        )
        new_price, _ = await self.plan_service.get_plan_pricing(
            upgrade_data.new_plan, billing_cycle
        )

        # Calculate proration
        now = datetime.now(timezone.utc)
        start_date = datetime.fromisoformat(subscription.start_date)
        end_date = datetime.fromisoformat(subscription.end_date)

        cycle_days = (end_date - start_date).days
        used_days = (now - start_date).days
        remaining_days = max(0, (end_date - now).days)

        # Only prorate if there are remaining days
        if remaining_days > 0:
            prorated_amount = self.calculate_proration(
                current_price, new_price, used_days, cycle_days
            )
        else:
            # If at end of cycle, just use full new price
            prorated_amount = Decimal("0")

        is_upgrade = new_price > current_price

        result = {
            "subscription_id": str(subscription_id),
            "old_plan": subscription.plan_code,
            "new_plan": upgrade_data.new_plan,
            "old_price": float(current_price),
            "new_price": float(new_price),
            "prorated_amount": float(prorated_amount),
            "is_upgrade": is_upgrade,
            "remaining_days": remaining_days,
        }

        # Get Paystack subscription
        ps_sub = self.ps_repo.get_by_subscription_id(subscription_id)

        if not ps_sub:
            raise BusinessLogicException("Paystack subscription not found")

        # Ensure new plan exists on Paystack
        paystack_plan_code = await self.ensure_paystack_plan_exists(
            upgrade_data.new_plan, billing_cycle
        )

        # If upgrade and prorated amount > minimum charge (e.g., 100 NGN)
        MIN_CHARGE = Decimal("100")
        if is_upgrade and prorated_amount >= MIN_CHARGE:
            # Initialize payment for prorated amount
            user = await self.user_service.get_user(user_id)

            try:
                payment = await self.paystack.initialize_payment(
                    email=user.email,
                    amount=prorated_amount,
                    # transaction_ref=f"UPGRADE-{subscription.subscription_reference}-{int(now.timestamp())}",
                    callback_url=upgrade_data.callback_url,
                    metadata={
                        "subscription_id": str(subscription_id),
                        "upgrade_from": subscription.plan_code,
                        "upgrade_to": upgrade_data.new_plan,
                        "type": "upgrade_proration",
                        "user_id": str(user_id),
                    },
                )

                result["payment_required"] = True
                result["payment_url"] = payment["authorization_url"]
                result["payment_reference"] = payment["reference"]

                # Store upgrade intent in metadata
                current_meta = subscription.meta_data or {}
                current_meta["pending_upgrade"] = {
                    "new_plan": upgrade_data.new_plan,
                    "paystack_plan_code": paystack_plan_code,
                    "payment_reference": payment["reference"],
                    "prorated_amount": float(prorated_amount),
                    "timestamp": now.isoformat(),
                }

                self.sub_repo.update_with_meta(
                    subscription_id,
                    {"meta_data": current_meta},
                )

                return result

            except Exception as e:
                raise BusinessLogicException(
                    f"Failed to initialize upgrade payment: {str(e)}"
                )

        # If downgrade or no significant charge needed, update immediately
        try:
            # For downgrades, we switch at next billing cycle
            # For upgrades with minimal/no proration, switch immediately

            # Cancel current Paystack subscription
            await self.paystack.disable_subscription(
                ps_sub.paystack_subscription_code,
                ps_sub.paystack_email_token,
            )

            # Create new Paystack subscription with new plan

            new_paystack_sub = await self.paystack.create_subscription(
                customer=ps_sub.customer_code,
                plan=paystack_plan_code,
                authorization=ps_sub.authorization_code,
            )

            # Update Paystack subscription record
            self.ps_repo.update(
                ps_sub.id,
                {
                    "paystack_subscription_code": new_paystack_sub["subscription_code"],
                    "paystack_email_token": new_paystack_sub["email_token"],
                    "next_payment_date": new_paystack_sub.get("next_payment_date"),
                    "status": "active",
                },
            )

            # Update internal subscription
            plan_details = self.plan_service.get_plan_details_for_subscription(
                upgrade_data.new_plan, billing_cycle
            )

            update_data = {
                "plan_code": upgrade_data.new_plan,
                "subscription_type": plan_details["type"],
                "price": new_price,
                "features": plan_details["features"],
                "limits": plan_details["limits"],
                "max_members": plan_details.get("max_members"),
                "upgraded_from": subscription.id,
                "updated_by": user_id,
                "status": SubscriptionStatus.ACTIVE,  # Reactivate if was suspended
            }

            # Clear any pending upgrade metadata
            current_meta = subscription.meta_data or {}
            current_meta.pop("pending_upgrade", None)
            update_data["meta_data"] = current_meta

            self.sub_repo.update(subscription_id, update_data)

            result["payment_required"] = False
            result["status"] = "completed"
            result["message"] = (
                "Subscription upgraded successfully"
                if is_upgrade
                else "Subscription will be updated at next billing cycle"
            )

            return result

        except Exception as e:
            raise BusinessLogicException(f"Failed to update subscription: {str(e)}")

    async def complete_upgrade_after_payment(
        self, subscription_id: UUID, customer_code: str, payment_reference: str
    ) -> bool:
        """
        Complete upgrade after proration payment is confirmed.
        Called from webhook or manual verification.
        """

        subscription = self.sub_repo.get_by_id(subscription_id)

        if not subscription:
            return False

        # Check if there's a pending upgrade
        pending_upgrade = (
            subscription.meta_data.get("pending_upgrade")
            if subscription.meta_data
            else None
        )
        if not pending_upgrade:
            return False

        if pending_upgrade.get("payment_reference") != payment_reference:
            return False

        # Get Paystack subscription
        ps_sub = self.ps_repo.get_by_subscription_id(subscription_id)

        if not ps_sub:
            return False

        try:
            # Cancel current Paystack subscription

            await self.paystack.disable_subscription(
                ps_sub.paystack_subscription_code,
                ps_sub.paystack_email_token,
            )

            # Create new Paystack subscription with new plan
            new_paystack_sub = await self.paystack.create_subscription(
                customer=customer_code,
                plan=pending_upgrade["paystack_plan_code"],
                authorization=ps_sub.authorization_code,
            )

            # Update Paystack subscription record
            self.ps_repo.update(
                ps_sub.id,
                {
                    "paystack_subscription_code": new_paystack_sub["subscription_code"],
                    "paystack_email_token": new_paystack_sub["email_token"],
                    "next_payment_date": new_paystack_sub.get("next_payment_date"),
                    "status": "active",
                },
            )

            # Get new plan details
            billing_cycle = BillingCycle(subscription.billing_cycle)
            plan_details = self.plan_service.get_plan_details_for_subscription(
                pending_upgrade["new_plan"], billing_cycle
            )

            new_price, _ = await self.plan_service.get_plan_pricing(
                pending_upgrade["new_plan"], billing_cycle
            )

            # Update internal subscription
            meta_data = subscription.meta_data or {}
            meta_data.pop("pending_upgrade", None)

            self.sub_repo.update(
                subscription_id,
                {
                    "plan_code": pending_upgrade["new_plan"],
                    "subscription_type": plan_details["type"],
                    "price": new_price,
                    "features": plan_details["features"],
                    "limits": plan_details["limits"],
                    "max_members": plan_details.get("max_members"),
                    "upgraded_from": subscription.id,
                    "meta_data": meta_data,
                    "updated_by": subscription.owner_id,
                    "status": SubscriptionStatus.ACTIVE,
                },
            )

            return True

        except Exception as e:
            print(f"Error completing upgrade: {e}")
            return False

    def calculate_proration(
        self,
        old_price: Decimal,
        new_price: Decimal,
        used_days: int,
        cycle_days: int,
    ) -> Decimal:
        """
        Calculate prorated amount for upgrades/downgrades.

        For upgrades: Calculate credit from unused time and charge difference
        For downgrades: Return 0 (switch at next billing cycle)
        """
        if cycle_days <= 0 or used_days >= cycle_days:
            return Decimal("0")

        # Calculate unused portion of current subscription
        unused_ratio = Decimal(cycle_days - used_days) / Decimal(cycle_days)

        # Credit from unused time on old plan
        credit = old_price * unused_ratio

        # Cost for remaining time on new plan
        new_cost = new_price * unused_ratio

        # Difference to charge (can be negative for downgrades)
        difference = new_cost - credit

        # For upgrades, charge the difference
        # For downgrades, return 0 (switch at next billing)
        return max(Decimal("0"), difference).quantize(Decimal("0.01"))

    async def handle_webhook_event(self, event: str, data: Dict[str, Any]) -> bool:
        """
        Handle Paystack webhook events for subscriptions
        """
        if event == "subscription.create":
            return await self._handle_subscription_created(data)

        elif event == "invoice.create":
            return await self._handle_invoice_created(data)

        elif event == "invoice.update":
            return await self._handle_invoice_updated(data)

        elif event == "invoice.payment_failed":
            return await self._handle_payment_failed(data)

        elif event == "subscription.disable":
            return await self._handle_subscription_disabled(data)

        elif event == "subscription.not_renew":
            return await self._handle_subscription_not_renewing(data)

        return False

    async def _handle_subscription_created(self, data: Dict[str, Any]) -> bool:
        """Handle subscription.create webhook"""
        return True

    async def _handle_invoice_created(self, data: Dict[str, Any]) -> bool:
        """Handle invoice.create webhook (upcoming charge notification)"""
        subscription_code = data.get("subscription", {}).get("subscription_code")

        if not subscription_code:
            return False

        ps_sub = self.ps_repo.get_by_paystack_code(subscription_code)

        if not ps_sub:
            return False

        # Update next payment date
        next_payment = data.get("period_end")
        if next_payment:
            self.ps_repo.update(ps_sub.id, {"next_payment_date": next_payment})

        return True

    async def _handle_invoice_updated(self, data: Dict[str, Any]) -> bool:
        """Handle invoice.update webhook (successful payment)"""
        subscription_code = data.get("subscription", {}).get("subscription_code")

        if not subscription_code:
            return False

        ps_sub = self.ps_repo.get_by_paystack_code(subscription_code)

        if not ps_sub:
            return False

        # Check if payment was successful
        if data.get("paid"):
            subscription = self.sub_repo.get_by_id(ps_sub.subscription_id)

            # Extend subscription period
            current_end = datetime.fromisoformat(subscription.end_date)

            # Add billing cycle period
            if subscription.billing_cycle == BillingCycle.MONTHLY.value:
                from dateutil.relativedelta import relativedelta

                new_end = current_end + relativedelta(months=1)
            elif subscription.billing_cycle == BillingCycle.YEARLY.value:
                from dateutil.relativedelta import relativedelta

                new_end = current_end + relativedelta(years=1)
            else:
                from datetime import timedelta

                new_end = current_end + timedelta(days=30)

            self.sub_repo.update(
                subscription.id,
                {
                    "end_date": new_end.isoformat(),
                    "next_billing_date": new_end.isoformat(),
                    "renewed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Update next payment date
            next_payment = data.get("period_end")
            if next_payment:
                self.ps_repo.update(ps_sub.id, {"next_payment_date": next_payment})

            return True

        return False

    async def _handle_payment_failed(self, data: Dict[str, Any]) -> bool:
        """Handle invoice.payment_failed webhook"""
        subscription_code = data.get("subscription", {}).get("subscription_code")

        if not subscription_code:
            return False

        ps_sub = self.ps_repo.get_by_paystack_code(subscription_code)

        if not ps_sub:
            return False

        # Mark subscription as payment failed (but keep active for grace period)
        self.sub_repo.update(
            ps_sub.subscription_id, {"status": SubscriptionStatus.FAILED}
        )

        return True

    async def _handle_subscription_disabled(self, data: Dict[str, Any]) -> bool:
        """Handle subscription.disable webhook"""
        subscription_code = data.get("subscription_code")

        if not subscription_code:
            return False

        ps_sub = self.ps_repo.get_by_paystack_code(subscription_code)

        if not ps_sub:
            return False

        # Cancel subscription
        self.sub_repo.update(
            ps_sub.subscription_id,
            {
                "status": SubscriptionStatus.CANCELLED,
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        self.ps_repo.update(ps_sub.id, {"status": "cancelled"})

        return True

    async def _handle_subscription_not_renewing(self, data: Dict[str, Any]) -> bool:
        """Handle subscription.not_renew webhook"""
        subscription_code = data.get("subscription_code")

        if not subscription_code:
            return False

        ps_sub = self.ps_repo.get_by_paystack_code(subscription_code)

        if not ps_sub:
            return False

        # Mark as not renewing (will expire at end date)
        self.sub_repo.update(ps_sub.subscription_id, {"auto_renew": False})

        return True
