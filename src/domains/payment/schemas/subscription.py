from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from src.domains.payment.enums import (
    SubscriptionStatus,
    SubscriptionType,
    MemberRole,
    BillingCycle,
)


# Request Schemas
class SubscriptionCreate(BaseModel):
    """Schema for creating a subscription"""

    plan: str = Field(..., description="Plan code (e.g., 'student', 'family')")
    billing_cycle: BillingCycle
    auto_renew: bool = True
    institution_id: Optional[UUID] = None
    promo_code: Optional[str] = None  # Optional promotion code


class AddMemberRequest(BaseModel):
    """Schema for adding a member to subscription"""

    user_id: UUID
    role: MemberRole = MemberRole.WARD

    @field_validator("role")
    def validate_role(cls, v):
        if v == MemberRole.OWNER:
            raise ValueError("Cannot manually add owner role")
        return v


class RemoveMemberRequest(BaseModel):
    """Schema for removing a member"""

    member_id: UUID
    reason: Optional[str] = None


class SubscriptionUpgradeRequest(BaseModel):
    """Schema for upgrading subscription"""

    new_plan: str = Field(..., description="New plan code to upgrade to")

    @field_validator("new_plan")
    def validate_upgrade(cls, v):
        if v == "free":
            raise ValueError("Cannot upgrade to FREE plan")
        return v


class SubscriptionCancelRequest(BaseModel):
    """Schema for cancelling subscription"""

    reason: Optional[str] = None
    cancel_immediately: bool = (
        False  # If False, subscription remains active until end_date
    )


# Response Schemas
class SubscriptionMemberResponse(BaseModel):
    """Response schema for subscription member"""

    id: UUID
    subscription_id: UUID
    user_id: UUID
    role: MemberRole
    is_active: bool
    joined_at: str
    removed_at: Optional[str] = None
    tests_taken: int
    exams_taken: int
    last_activity: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Response schema for subscription"""

    id: UUID
    subscription_reference: str
    plan_code: str
    subscription_type: str
    status: SubscriptionStatus

    owner_id: UUID
    institution_id: Optional[UUID] = None

    price: Decimal
    currency: str
    billing_cycle: str

    start_date: str
    end_date: str
    trial_end_date: Optional[str] = None

    auto_renew: bool
    next_billing_date: Optional[str] = None

    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None

    max_members: Optional[int] = None
    current_members: int

    total_tests_taken: int
    total_exams_taken: int

    cancelled_at: Optional[str] = None
    cancellation_reason: Optional[str] = None

    # Promotion tracking
    applied_promo_code: Optional[str] = None
    promo_discount_amount: Optional[Decimal] = None

    # Upgrade tracking
    renewed_at: Optional[str] = None
    upgraded_from: Optional[UUID] = None

    created_at: str
    updated_at: str

    # Computed fields
    is_active: bool
    days_remaining: int
    can_add_members: bool
    available_slots: int

    class Config:
        from_attributes = True


class SubscriptionWithMembersResponse(SubscriptionResponse):
    """Response schema with member details"""

    members: List[SubscriptionMemberResponse] = []


class SubscriptionSummary(BaseModel):
    """Summary of subscription for quick display"""

    subscription_reference: str
    plan_code: str  # Changed from plan enum
    status: SubscriptionStatus
    is_active: bool
    days_remaining: int
    current_members: int
    available_slots: int
    has_unlimited_tests: bool
    has_leaderboard_access: bool


class UsageStatsResponse(BaseModel):
    """Usage statistics for subscription"""

    subscription_id: UUID
    subscription_reference: str

    total_tests: int
    total_exams: int

    tests_limit: Optional[int] = None
    exams_limit: Optional[int] = None

    tests_remaining: Optional[int] = None
    exams_remaining: Optional[int] = None

    usage_percentage: float

    member_usage: List[Dict[str, Any]] = []


class PlanDetails(BaseModel):
    """Details of a subscription plan"""

    plan: str  # Changed from enum to string (plan_code)
    name: str
    description: str
    price_monthly: Decimal
    price_yearly: Decimal
    discount_percentage: Optional[int] = None

    features: Dict[str, Any]
    limits: Dict[str, Any]

    max_members: Optional[int] = None
    subscription_type: SubscriptionType

    is_popular: bool = False
