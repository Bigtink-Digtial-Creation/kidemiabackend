from src.domains.payment.enums import SubscriptionPlan, SubscriptionStatus
from src.shared.schemas.base import BaseSchema, CreateSchema, ResponseSchema
from pydantic import Field
from decimal import Decimal
from typing import Optional
from uuid import UUID


class SubscriptionBase(BaseSchema):
    """Base subscription schema"""

    plan: SubscriptionPlan
    billing_cycle: str = Field(..., pattern="^(monthly|quarterly|yearly)$")
    auto_renew: bool = True


class SubscriptionCreate(SubscriptionBase, CreateSchema):
    """Schema for creating subscription"""

    pass


class SubscriptionResponse(SubscriptionBase, ResponseSchema):
    """Schema for subscription response"""

    subscription_reference: str
    status: SubscriptionStatus
    user_id: UUID
    institution_id: Optional[UUID]

    price: Decimal
    currency: str

    start_date: str
    end_date: str
    trial_end_date: Optional[str]
    next_billing_date: Optional[str]

    exams_taken: int
    exams_limit: Optional[int]

    is_active: bool
    days_remaining: int


class SubscriptionUpgradeRequest(BaseSchema):
    """Request to upgrade subscription"""

    new_plan: SubscriptionPlan
