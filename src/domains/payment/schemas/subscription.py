from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from src.shared.schemas.base import IDSchema
from datetime import datetime
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
    promo_code: Optional[str] = None
    callback_url: str


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
    """Schema for upgrading subscription with improved validation"""

    new_plan: str = Field(..., description="New plan code to upgrade to")
    callback_url: str

    @field_validator("new_plan")
    def validate_upgrade(cls, v):
        # Normalize the plan code
        v = v.strip().lower()

        if not v:
            raise ValueError("Plan code cannot be empty")

        if v == "free":
            raise ValueError(
                "Cannot upgrade to FREE plan. Free plan is only for trial users."
            )

        # Add more validation as needed
        if len(v) > 50:
            raise ValueError("Plan code is too long")

        return v


class SubscriptionCancelRequest(BaseModel):
    """Schema for cancelling subscription"""

    reason: Optional[str] = Field(None, description="Reason for cancellation")
    cancel_immediately: bool = Field(
        default=False,
        description="If True, cancel immediately. If False, cancel at end of billing period",
    )


# Response Schemas
class SubscriptionMemberResponse(IDSchema):
    """Response schema for subscription member"""

    subscription_id: UUID
    user_id: UUID
    role: MemberRole
    is_active: bool
    joined_at: str
    removed_at: Optional[str] = None
    tests_taken: int
    exams_taken: int
    last_activity: Optional[str] = None


class SubscriptionResponse(IDSchema):
    """Response schema for subscription"""

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

    created_at: datetime
    updated_at: datetime

    # Computed fields
    is_active: bool
    days_remaining: int
    can_add_members: bool
    available_slots: int


class SubscriptionWithMembersResponse(SubscriptionResponse):
    """Response schema with member details"""

    members: List[SubscriptionMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)


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


class ErrorResponse(BaseModel):
    """Standardized error response"""

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    suggestion: Optional[str] = Field(
        None, description="Suggestion for resolving the error"
    )


# Error messages mapping for better UX
ERROR_MESSAGES = {
    "ALREADY_SUBSCRIBED": {
        "message": "You already have an active subscription",
        "suggestion": "Please upgrade or cancel your existing subscription first",
    },
    "INVALID_PLAN": {
        "message": "The selected plan is not valid",
        "suggestion": "Please choose from our available subscription plans",
    },
    "SAME_PLAN": {
        "message": "You are already subscribed to this plan",
        "suggestion": "Please select a different plan to upgrade or downgrade",
    },
    "CANNOT_UPGRADE": {
        "message": "Cannot upgrade subscription in current status",
        "suggestion": "Please ensure your subscription is active before upgrading",
    },
    "PAYMENT_FAILED": {
        "message": "Payment processing failed",
        "suggestion": "Please check your payment details and try again",
    },
    "PAYSTACK_ERROR": {
        "message": "Payment gateway error",
        "suggestion": "Please try again or contact support if the issue persists",
    },
    "INSUFFICIENT_PERMISSIONS": {
        "message": "You don't have permission to perform this action",
        "suggestion": "Only the subscription owner can make this change",
    },
    "SUBSCRIPTION_NOT_FOUND": {
        "message": "Subscription not found",
        "suggestion": "Please check your subscription status or contact support",
    },
    "INVALID_STATUS": {
        "message": "Operation not allowed in current subscription status",
        "suggestion": "Please check your subscription status before proceeding",
    },
}


def get_error_response(
    error_code: str, custom_message: str = None, details: dict = None
) -> ErrorResponse:
    """Helper function to create standardized error responses"""
    error_info = ERROR_MESSAGES.get(
        error_code,
        {
            "message": custom_message or "An error occurred",
            "suggestion": "Please try again or contact support",
        },
    )

    return ErrorResponse(
        error=error_code,
        message=custom_message or error_info["message"],
        details=details,
        suggestion=error_info.get("suggestion"),
    )
