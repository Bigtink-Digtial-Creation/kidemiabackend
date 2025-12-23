from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from src.shared.schemas.base import TimestampSchema, ResponseSchema
from src.domains.payment.enums import (
    SubscriptionPlanType,
    SubscriptionType,
    BillingCycle,
)


# Admin Plan Management Schemas
class PlanConfigCreate(BaseModel):
    """Schema for creating a new plan"""

    plan_code: str = Field(..., max_length=50, description="Unique plan identifier")
    plan_name: str = Field(..., max_length=100)
    plan_type: SubscriptionPlanType
    subscription_type: SubscriptionType

    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=200)
    tagline: Optional[str] = Field(None, max_length=100)

    price_monthly: Decimal
    price_quarterly: Optional[Decimal] = None
    price_yearly: Decimal

    monthly_discount_percentage: int = 0
    quarterly_discount_percentage: int = 0
    yearly_discount_percentage: int = 0

    currency: str = "NGN"
    max_members: Optional[int] = None
    trial_days: int = 0

    features: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, Any] = Field(default_factory=dict)

    is_active: bool = True
    is_featured: bool = False
    is_popular: bool = False
    display_order: int = 0

    is_visible: bool = True
    show_for_individuals: bool = True
    show_for_guardians: bool = False
    show_for_institutions: bool = False

    can_upgrade_to: Optional[List[str]] = None
    can_downgrade_to: Optional[List[str]] = None

    meta_data: Optional[Dict[str, Any]] = None
    terms_url: Optional[str] = None
    benefits_list: Optional[List[str]] = None

    @field_validator("plan_code", mode="before")
    def validate_plan_code(cls, v):
        if not v.isalnum() and "_" not in v:
            raise ValueError("Plan code must be alphanumeric with underscores only")
        return v.lower()


class PlanConfigUpdate(BaseModel):
    """Schema for updating a plan"""

    plan_name: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    tagline: Optional[str] = None

    price_monthly: Optional[Decimal] = None
    price_quarterly: Optional[Decimal] = None
    price_yearly: Optional[Decimal] = None

    monthly_discount_percentage: Optional[int] = None
    quarterly_discount_percentage: Optional[int] = None
    yearly_discount_percentage: Optional[int] = None

    max_members: Optional[int] = None
    trial_days: Optional[int] = None

    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None

    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_popular: Optional[bool] = None
    display_order: Optional[int] = None

    is_visible: Optional[bool] = None
    show_for_individuals: Optional[bool] = None
    show_for_guardians: Optional[bool] = None
    show_for_institutions: Optional[bool] = None

    can_upgrade_to: Optional[List[str]] = None
    can_downgrade_to: Optional[List[str]] = None

    meta_data: Optional[Dict[str, Any]] = None
    terms_url: Optional[str] = None
    benefits_list: Optional[List[str]] = None


class PlanConfigResponse(TimestampSchema):
    """Response schema for plan configuration"""

    id: UUID
    plan_code: str
    plan_name: str
    plan_type: SubscriptionPlanType
    subscription_type: SubscriptionType

    description: Optional[str] = None
    short_description: Optional[str] = None
    tagline: Optional[str] = None

    price_monthly: Decimal
    price_quarterly: Optional[Decimal] = None
    price_yearly: Decimal

    monthly_discount_percentage: int
    quarterly_discount_percentage: int
    yearly_discount_percentage: int

    currency: str
    max_members: Optional[int] = None
    trial_days: int

    features: Dict[str, Any]
    limits: Dict[str, Any]

    is_active: bool
    is_featured: bool
    is_popular: bool
    display_order: int

    is_visible: bool
    show_for_individuals: bool
    show_for_guardians: bool
    show_for_institutions: bool

    can_upgrade_to: Optional[List[str]] = None
    can_downgrade_to: Optional[List[str]] = None

    meta_data: Optional[Dict[str, Any]] = None
    terms_url: Optional[str] = None
    benefits_list: Optional[List[str]] = None

    # Computed fields
    monthly_savings: float
    yearly_savings: float
    effective_monthly_price_yearly: float


class PublicPlanDisplay(BaseModel):
    """Public-facing plan display for pricing page"""

    plan_code: str
    plan_name: str
    plan_type: SubscriptionPlanType
    subscription_type: SubscriptionType

    tagline: Optional[str] = None
    short_description: Optional[str] = None

    price_monthly: Decimal
    price_yearly: Decimal

    yearly_discount_percentage: int
    yearly_savings: float
    effective_monthly_price_yearly: float

    max_members: Optional[int] = None
    trial_days: int

    features: Dict[str, Any]
    benefits_list: Optional[List[str]] = None

    is_featured: bool
    is_popular: bool

    currency: str


# Feature Management
class PlanFeatureCreate(BaseModel):
    """Schema for creating a feature"""

    feature_code: str = Field(..., max_length=50)
    feature_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True
    display_order: int = 0
    requires_value: bool = False
    default_value: Optional[Dict[str, Any]] = None


class PlanFeatureResponse(ResponseSchema):
    """Response schema for feature"""

    feature_code: str
    feature_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    is_active: bool
    display_order: int
    requires_value: bool
    default_value: Optional[Dict[str, Any]] = None
    created_at: datetime


# Promotion Management
class PromotionCreate(BaseModel):
    """Schema for creating a promotion"""

    promo_code: str = Field(..., max_length=50)
    promo_name: str = Field(..., max_length=100)
    description: Optional[str] = None

    applicable_plan_codes: Optional[List[str]] = None

    discount_type: str = Field(
        ..., description="percentage, fixed_amount, trial_extension"
    )
    discount_value: Decimal

    start_date: str
    end_date: Optional[str] = None

    max_uses: Optional[int] = None
    max_uses_per_user: int = 1

    min_billing_cycle: Optional[BillingCycle] = None
    new_users_only: bool = False
    first_time_subscribers_only: bool = False

    is_active: bool = True

    @field_validator("discount_type")
    def validate_discount_type(cls, v):
        allowed = ["percentage", "fixed_amount", "trial_extension"]
        if v not in allowed:
            raise ValueError(f"discount_type must be one of {allowed}")
        return v

    @field_validator("promo_code")
    def validate_promo_code(cls, v):
        return v.upper()


class PromotionResponse(BaseModel):
    """Response schema for promotion"""

    id: UUID
    promo_code: str
    promo_name: str
    description: Optional[str] = None

    applicable_plan_codes: Optional[List[str]] = None

    discount_type: str
    discount_value: Decimal

    start_date: str
    end_date: Optional[str] = None

    max_uses: Optional[int] = None
    max_uses_per_user: int
    current_uses: int

    min_billing_cycle: Optional[BillingCycle] = None
    new_users_only: bool
    first_time_subscribers_only: bool

    is_active: bool
    is_valid: bool

    created_at: str

    class Config:
        from_attributes = True


class ApplyPromotionRequest(BaseModel):
    """Request to apply a promotion code"""

    promo_code: str
    plan_code: str
    billing_cycle: BillingCycle


class PromotionCalculationResponse(BaseModel):
    """Response showing promotion calculation"""

    promo_code: str
    plan_code: str
    original_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
    discount_percentage: Optional[float] = None
    trial_extension_days: Optional[int] = None
    is_valid: bool
    message: Optional[str] = None
