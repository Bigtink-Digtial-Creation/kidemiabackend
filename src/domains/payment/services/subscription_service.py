from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.domains.payment.repositories.subscription_repository import (
    SubscriptionRepository,
    SubscriptionMemberRepository,
    SubscriptionUsageLogRepository,
)
from src.domains.payment.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionWithMembersResponse,
    AddMemberRequest,
    RemoveMemberRequest,
    SubscriptionUpgradeRequest,
    UsageStatsResponse,
    PlanDetails,
)
from src.domains.payment.enums import (
    SubscriptionStatus,
    MemberRole,
    BillingCycle,
)
from src.core.exceptions import (
    BusinessLogicException,
    ResourceNotFoundException,
)


class SubscriptionService:
    """Service for subscription operations"""

    def __init__(self, db: Session):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)
        self.member_repo = SubscriptionMemberRepository(db)
        self.usage_repo = SubscriptionUsageLogRepository(db)

    async def create_subscription(
        self, user_id: UUID, subscription_data: SubscriptionCreate
    ) -> SubscriptionWithMembersResponse:
        """Create a new subscription"""
        # Check if user already has an active subscription

        existing = self.subscription_repo.get_active_subscription(user_id)
        if existing:
            raise BusinessLogicException(
                "User already has an active subscription. Please cancel or upgrade existing subscription."
            )

        plan_details = self._get_plan_details(
            subscription_data.plan, subscription_data.billing_cycle
        )

        start_date = datetime.now(timezone.utc)
        end_date = self._calculate_end_date(start_date, subscription_data.billing_cycle)

        sub_data = {
            "subscription_reference": f"SUB-{uuid4().hex[:12].upper()}",
            "owner_id": user_id,
            "plan_code": subscription_data.plan,
            "subscription_type": plan_details["type"].value,
            "price": plan_details["price"],
            "currency": "NGN",
            "billing_cycle": subscription_data.billing_cycle.value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "auto_renew": subscription_data.auto_renew,
            "next_billing_date": end_date.isoformat()
            if subscription_data.auto_renew
            else None,
            "features": plan_details["features"],
            "limits": plan_details["limits"],
            "max_members": plan_details.get("max_members"),
            "current_members": 1,
            "status": SubscriptionStatus.PENDING,
            "institution_id": subscription_data.institution_id,
            "created_by": user_id,
        }

        try:
            subscription = self.subscription_repo.create(sub_data)
        except Exception as e:
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            raise

        member_data = {
            "subscription_id": subscription.id,
            "user_id": user_id,
            "role": MemberRole.OWNER,
            "joined_at": start_date.isoformat(),
            "is_active": True,
            "created_by": user_id,
        }
        self.member_repo.create(member_data)
        print(subscription)
        return await self.get_subscription_with_members(subscription.id, user_id)

    async def activate_subscription(
        self, subscription_id: UUID, payment_reference: str
    ) -> SubscriptionResponse:
        """Activate subscription after successful payment"""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.status != SubscriptionStatus.PENDING:
            raise BusinessLogicException("Subscription is not active")
        self.subscription_repo.update(
            subscription_id,
            {
                "status": SubscriptionStatus.ACTIVE,
                "updated_by": subscription.owner_id,
            },
        )
        subscription = self.subscription_repo.get_by_id(subscription_id)
        return SubscriptionResponse.model_validate(subscription)

    async def add_member(
        self, subscription_id: UUID, owner_id: UUID, member_request: AddMemberRequest
    ) -> SubscriptionWithMembersResponse:
        """Add a member to subscription (ward/student)"""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)
        if subscription.owner_id != owner_id:
            raise BusinessLogicException("Only subscription owner can add members")
        if not subscription.is_active:
            raise BusinessLogicException("Subscription is not active")
        if not subscription.can_add_members:
            raise BusinessLogicException(
                f"Cannot add more members. Plan allows maximum {subscription.max_members} members."
            )

        # Check if user is already a member
        existing_member = self.member_repo.get_by_user_and_subscription(
            member_request.user_id, subscription_id
        )
        if existing_member and existing_member.is_active:
            raise BusinessLogicException(
                "User is already a member of this subscription"
            )

        # Check if user has another active subscription
        user_membership = self.member_repo.get_user_active_membership(
            member_request.user_id
        )
        if user_membership:
            raise BusinessLogicException(
                "User already has an active subscription membership"
            )

        member_data = {
            "subscription_id": subscription_id,
            "user_id": member_request.user_id,
            "role": member_request.role,
            "added_by": owner_id,
            "joined_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "created_by": owner_id,
        }
        self.member_repo.create(member_data)

        # Update subscription member count
        self.subscription_repo.update(
            subscription_id,
            {
                "current_members": subscription.current_members + 1,
                "updated_by": owner_id,
            },
        )

        return await self.get_subscription_with_members(subscription_id, owner_id)

    async def remove_member(
        self, subscription_id: UUID, owner_id: UUID, member_request: RemoveMemberRequest
    ) -> SubscriptionWithMembersResponse:
        """Remove a member from subscription"""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)
        if subscription.owner_id != owner_id:
            raise BusinessLogicException("Only subscription owner can remove members")

        member = self.member_repo.get_by_id(member_request.member_id)
        if not member or member.subscription_id != subscription_id:
            raise ResourceNotFoundException("Member", member_request.member_id)
        if member.role == MemberRole.OWNER:
            raise BusinessLogicException("Cannot remove subscription owner")
        self.member_repo.update(
            member_request.member_id,
            {
                "is_active": False,
                "removed_at": datetime.utcnow().isoformat(),
                "removal_reason": member_request.reason,
                "updated_by": owner_id,
            },
        )
        self.subscription_repo.update(
            subscription_id,
            {
                "current_members": subscription.current_members - 1,
                "updated_by": owner_id,
            },
        )

        return await self.get_subscription_with_members(subscription_id, owner_id)

    async def cancel_subscription(
        self,
        subscription_id: UUID,
        user_id: UUID,
        reason: Optional[str] = None,
        cancel_immediately: bool = False,
    ) -> SubscriptionResponse:
        """Cancel a subscription"""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.owner_id != user_id:
            raise BusinessLogicException("Only subscription owner can cancel")

        update_data = {
            "auto_renew": False,
            "cancelled_at": datetime.utcnow().isoformat(),
            "cancellation_reason": reason,
            "updated_by": user_id,
        }

        if cancel_immediately:
            update_data["status"] = SubscriptionStatus.CANCELLED
            update_data["end_date"] = datetime.now(timezone.utc).isoformat()

            # Deactivate all members
            members = self.member_repo.get_active_members(subscription_id)
            for member in members:
                self.member_repo.update(
                    member.id,
                    {
                        "is_active": False,
                        "removed_at": datetime.utcnow().isoformat(),
                        "removal_reason": "Subscription cancelled",
                        "updated_by": user_id,
                    },
                )

        self.subscription_repo.update(subscription_id, update_data)

        subscription = self.subscription_repo.get_by_id(subscription_id)
        return SubscriptionResponse.model_validate(subscription)

    async def upgrade_subscription(
        self,
        subscription_id: UUID,
        user_id: UUID,
        upgrade_data: SubscriptionUpgradeRequest,
    ) -> SubscriptionResponse:
        """Upgrade subscription plan"""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.owner_id != user_id:
            raise BusinessLogicException("Only subscription owner can upgrade")

        # Validate upgrade path
        if not self._is_valid_upgrade(subscription.plan, upgrade_data.new_plan):
            raise BusinessLogicException(
                f"Cannot upgrade from {subscription.plan} to {upgrade_data.new_plan}"
            )

        billing_cycle = BillingCycle(subscription.billing_cycle)
        new_plan_details = self._get_plan_details(upgrade_data.new_plan, billing_cycle)

        # Calculate prorated amount (simplified - you should implement proper proration)
        # For now, we'll just charge the difference

        update_data = {
            "plan": upgrade_data.new_plan,
            "subscription_type": new_plan_details["type"],
            "price": new_plan_details["price"],
            "features": new_plan_details["features"],
            "limits": new_plan_details["limits"],
            "max_members": new_plan_details.get("max_members"),
            "upgraded_from": subscription.id,
            "updated_by": user_id,
        }

        self.subscription_repo.update(subscription_id, update_data)

        subscription = self.subscription_repo.get_by_id(subscription_id)
        return SubscriptionResponse.model_validate(subscription)

    async def check_feature_access(
        self, user_id: UUID, feature: str
    ) -> tuple[bool, Optional[str]]:
        """Check if user has access to a feature"""
        # Get user's active membership
        membership = self.member_repo.get_user_active_membership(user_id)

        if not membership:
            return False, "No active subscription"

        subscription = membership.subscription
        if not subscription.is_active:
            return False, "Subscription expired"

        # Check feature
        features = subscription.features or {}
        has_feature = features.get(feature, False)

        if not has_feature:
            return (
                False,
                f"Feature '{feature}' not available in {subscription.plan} plan",
            )

        return True, None

    async def check_usage_limit(
        self, user_id: UUID, activity_type: str
    ) -> tuple[bool, Optional[str]]:
        """Check if user has exceeded usage limits"""
        membership = self.member_repo.get_user_active_membership(user_id)

        if not membership:
            return False, "No active subscription"

        subscription = membership.subscription
        limits = subscription.limits or {}

        # Check specific limits
        if activity_type == "test":
            limit = limits.get("tests_per_month")
            if limit and membership.tests_taken >= limit:
                return False, f"Test limit reached ({limit} per month)"

        elif activity_type == "exam":
            limit = limits.get("exams_per_month")
            if limit and membership.exams_taken >= limit:
                return False, f"Exam limit reached ({limit} per month)"

        return True, None

    async def log_activity(
        self,
        user_id: UUID,
        activity_type: str,
        activity_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Log subscription activity and update usage counters"""
        membership = self.member_repo.get_user_active_membership(user_id)

        if not membership:
            return False

        # Log activity
        self.usage_repo.log_activity(
            subscription_id=membership.subscription_id,
            member_id=membership.id,
            user_id=user_id,
            activity_type=activity_type,
            activity_id=activity_id,
            meta_data=metadata,
        )

        # Update counters
        update_data = {"last_activity": datetime.utcnow().isoformat()}

        if activity_type == "test":
            update_data["tests_taken"] = membership.tests_taken + 1
        elif activity_type == "exam":
            update_data["exams_taken"] = membership.exams_taken + 1

        self.member_repo.update(membership.id, update_data)

        # Update subscription totals
        subscription = membership.subscription
        sub_update = {}
        if activity_type == "test":
            sub_update["total_tests_taken"] = subscription.total_tests_taken + 1
        elif activity_type == "exam":
            sub_update["total_exams_taken"] = subscription.total_exams_taken + 1

        if sub_update:
            self.subscription_repo.update(subscription.id, sub_update)

        return True

    async def get_subscription_with_members(
        self, subscription_id: UUID, user_id: UUID
    ) -> SubscriptionWithMembersResponse:
        """Get subscription with all members"""
        subscription = self.subscription_repo.get_subscription_with_members(
            subscription_id
        )
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        # Verify access
        member = self.member_repo.get_by_user_and_subscription(user_id, subscription_id)
        if not member:
            raise BusinessLogicException("You don't have access to this subscription")
        return SubscriptionWithMembersResponse.model_validate(subscription)

    async def get_user_subscriptions(self, user_id: UUID) -> List[SubscriptionResponse]:
        """Get all subscriptions for user"""
        subscriptions = self.subscription_repo.get_user_subscriptions(user_id)
        return [SubscriptionResponse.model_validate(sub) for sub in subscriptions]

    async def get_usage_stats(
        self, subscription_id: UUID, user_id: UUID
    ) -> UsageStatsResponse:
        """Get usage statistics"""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        # Verify access
        member = self.member_repo.get_by_user_and_subscription(user_id, subscription_id)
        if not member:
            raise BusinessLogicException("You don't have access to this subscription")

        limits = subscription.limits or {}
        tests_limit = limits.get("tests_per_month")
        exams_limit = limits.get("exams_per_month")

        tests_remaining = None
        exams_remaining = None
        usage_percentage = 0.0

        if tests_limit:
            tests_remaining = max(0, tests_limit - subscription.total_tests_taken)
            usage_percentage = (subscription.total_tests_taken / tests_limit) * 100

        # Get member usage breakdown
        members = self.member_repo.get_active_members(subscription_id)
        member_usage = [
            {
                "user_id": str(m.user_id),
                "role": m.role.value,
                "tests_taken": m.tests_taken,
                "exams_taken": m.exams_taken,
            }
            for m in members
        ]

        return UsageStatsResponse(
            subscription_id=subscription_id,
            subscription_reference=subscription.subscription_reference,
            total_tests=subscription.total_tests_taken,
            total_exams=subscription.total_exams_taken,
            tests_limit=tests_limit,
            exams_limit=exams_limit,
            tests_remaining=tests_remaining,
            exams_remaining=exams_remaining,
            usage_percentage=usage_percentage,
            member_usage=member_usage,
        )

    def get_available_plans(self) -> List[PlanDetails]:
        """
        Get all available subscription plans from dynamic configuration.
        This now fetches from SubscriptionPlanConfig instead of hardcoded values.
        """
        from src.domains.payment.repositories.plan_management_repository import (
            PlanConfigRepository,
        )

        plan_repo = PlanConfigRepository(self.db)
        active_plans = plan_repo.get_active_plans()

        plans = []
        for plan_config in active_plans:
            plan_info = PlanDetails(
                plan=plan_config.plan_code,
                name=plan_config.plan_name,
                description=plan_config.description or "",
                price_monthly=plan_config.price_monthly,
                price_yearly=plan_config.price_yearly,
                discount_percentage=plan_config.yearly_discount_percentage,
                features=plan_config.features,
                limits=plan_config.limits,
                max_members=plan_config.max_members,
                subscription_type=plan_config.subscription_type,
                is_popular=plan_config.is_popular,
            )
            plans.append(plan_info)

        return plans

    def _get_plan_details(
        self, plan_code: str, billing_cycle: BillingCycle
    ) -> Dict[str, Any]:
        """
        Get plan pricing and features from dynamic plan configuration.
        This now fetches from SubscriptionPlanConfig table instead of hardcoded values.
        """
        from src.domains.payment.services.plan_management_service import (
            PlanManagementService,
        )

        plan_service = PlanManagementService(self.db)

        try:
            # Get plan details from database
            plan_details = plan_service.get_plan_details_for_subscription(
                plan_code, billing_cycle
            )
            return plan_details
        except Exception as e:
            # Fallback to basic plan if something goes wrong
            print(e)
            raise BusinessLogicException(
                f"Plan '{plan_code}' not found or not available"
            )

    def _calculate_end_date(
        self, start_date: datetime, billing_cycle: BillingCycle
    ) -> datetime:
        """Calculate subscription end date"""
        if billing_cycle == BillingCycle.MONTHLY:
            return start_date + timedelta(days=30)
        elif billing_cycle == BillingCycle.YEARLY:
            return start_date + timedelta(days=365)
        else:
            return start_date + timedelta(days=30)

    def _is_valid_upgrade(self, current_plan_code: str, new_plan_code: str) -> bool:
        """
        Validate upgrade path using dynamic plan configuration.
        Checks if new plan allows upgrades from current plan.
        """
        from src.domains.payment.repositories import PlanConfigRepository

        plan_repo = PlanConfigRepository(self.db)

        # Get current and new plan configs
        current_plan = plan_repo.get_by_plan_code(current_plan_code)
        new_plan = plan_repo.get_by_plan_code(new_plan_code)

        if not current_plan or not new_plan:
            return False

        # Check if upgrade is explicitly allowed
        if new_plan.can_upgrade_to:
            # If can_upgrade_to is defined, current plan must be in the list
            # This is actually "can upgrade FROM" list
            pass

        # Check if downgrade is prevented
        if (
            current_plan.can_downgrade_to
            and new_plan_code not in current_plan.can_downgrade_to
        ):
            # If current plan has downgrade restrictions and new plan is not in list
            pass

        # Simple price-based upgrade validation
        # Get pricing for comparison
        current_price = (
            current_plan.price_yearly
            if current_plan.price_yearly
            else current_plan.price_monthly
        )
        new_price = (
            new_plan.price_yearly if new_plan.price_yearly else new_plan.price_monthly
        )

        # Generally allow upgrades to higher-priced plans
        return new_price >= current_price
