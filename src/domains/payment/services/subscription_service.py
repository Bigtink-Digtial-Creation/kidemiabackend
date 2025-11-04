from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any
from src.core.exceptions import ResourceNotFoundException, BusinessLogicException
from src.domains.payment.repositories.subscription_repository import (
    SubscriptionRepository,
)
from src.domains.payment.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpgradeRequest,
)
from src.domains.payment.enums import SubscriptionPlan, SubscriptionStatus


class SubscriptionService:
    """Service for subscription operations"""

    def __init__(self, db: Session):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)

    async def create_subscription(
        self, user_id: UUID, subscription_data: SubscriptionCreate
    ) -> SubscriptionResponse:
        """Create a new subscription"""
        # Check if user has active subscription
        existing = self.subscription_repo.get_active_subscription(user_id)
        if existing:
            raise BusinessLogicException("User already has an active subscription")

        # Get plan pricing
        plan_details = self._get_plan_details(subscription_data.plan)

        # Calculate dates
        start_date = datetime.utcnow()
        end_date = self._calculate_end_date(start_date, subscription_data.billing_cycle)

        # Create subscription
        sub_data = {
            "subscription_reference": f"SUB-{uuid4().hex[:12].upper()}",
            "user_id": user_id,
            "plan": subscription_data.plan,
            "price": plan_details["price"],
            "billing_cycle": subscription_data.billing_cycle,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "auto_renew": subscription_data.auto_renew,
            "features": plan_details["features"],
            "limits": plan_details["limits"],
            "exams_limit": plan_details.get("exams_limit"),
            "status": SubscriptionStatus.ACTIVE,
            "created_by": user_id,
        }

        subscription = self.subscription_repo.create(sub_data)

        return SubscriptionResponse.model_validate(subscription)

    async def cancel_subscription(
        self, subscription_id: UUID, user_id: UUID, reason: Optional[str] = None
    ) -> SubscriptionResponse:
        """Cancel a subscription"""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription", subscription_id)

        if subscription.user_id != user_id:
            raise BusinessLogicException("Not authorized to cancel this subscription")

        # Update subscription
        self.subscription_repo.update(
            subscription_id,
            {
                "status": SubscriptionStatus.CANCELLED,
                "auto_renew": False,
                "cancelled_at": datetime.utcnow().isoformat(),
                "cancellation_reason": reason,
            },
        )

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

        if subscription.user_id != user_id:
            raise BusinessLogicException("Not authorized to upgrade this subscription")

        # Get new plan details
        new_plan_details = self._get_plan_details(upgrade_data.new_plan)

        # Calculate prorated amount (simplified)
        # TODO: Implement proper proration logic

        # Update subscription
        self.subscription_repo.update(
            subscription_id,
            {
                "plan": upgrade_data.new_plan,
                "price": new_plan_details["price"],
                "features": new_plan_details["features"],
                "limits": new_plan_details["limits"],
                "exams_limit": new_plan_details.get("exams_limit"),
            },
        )

        subscription = self.subscription_repo.get_by_id(subscription_id)
        return SubscriptionResponse.model_validate(subscription)

    def _get_plan_details(self, plan: SubscriptionPlan) -> Dict[str, Any]:
        """Get plan pricing and features"""
        plans = {
            SubscriptionPlan.FREE: {
                "price": Decimal("0.00"),
                "exams_limit": 3,
                "features": {"basic_tests": True},
                "limits": {"exams_per_month": 3},
            },
            SubscriptionPlan.BASIC: {
                "price": Decimal("2000.00"),
                "exams_limit": 10,
                "features": {"all_tests": True, "past_questions": True},
                "limits": {"exams_per_month": 10},
            },
            SubscriptionPlan.PREMIUM: {
                "price": Decimal("5000.00"),
                "exams_limit": None,  # Unlimited
                "features": {
                    "all_tests": True,
                    "past_questions": True,
                    "ai_assistance": True,
                    "detailed_analytics": True,
                },
                "limits": {},
            },
            SubscriptionPlan.INSTITUTION: {
                "price": Decimal("50000.00"),
                "exams_limit": None,
                "features": {
                    "custom_exams": True,
                    "student_management": True,
                    "bulk_enrollment": True,
                    "analytics_dashboard": True,
                },
                "limits": {},
            },
        }

        return plans.get(plan, plans[SubscriptionPlan.FREE])

    def _calculate_end_date(self, start_date: datetime, billing_cycle: str) -> datetime:
        """Calculate subscription end date"""
        if billing_cycle == "monthly":
            return start_date + timedelta(days=30)
        elif billing_cycle == "quarterly":
            return start_date + timedelta(days=90)
        elif billing_cycle == "yearly":
            return start_date + timedelta(days=365)
        else:
            return start_date + timedelta(days=30)
