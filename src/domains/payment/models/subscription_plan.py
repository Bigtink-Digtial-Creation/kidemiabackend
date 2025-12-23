from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    Numeric,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.database.base import FullBaseModel
from src.domains.payment.enums import (
    SubscriptionPlanType,
    SubscriptionType,
    BillingCycle,
)


class SubscriptionPlanConfig(FullBaseModel):
    """
    Admin-managed subscription plans configuration.
    This allows admins to dynamically create and update plans.
    """

    __tablename__ = "subscription_plan_config"

    # Plan identification
    plan_code = Column(
        String(50), unique=True, nullable=False, index=True
    )  # e.g., 'student', 'family'
    plan_name = Column(String(100), nullable=False)  # Display name: "Family Plan"
    plan_type = Column(
        SQLEnum(SubscriptionPlanType), nullable=False, index=True
    )  # STUDENT, SIBLING, FAMILY, etc.
    subscription_type = Column(
        SQLEnum(SubscriptionType), nullable=False
    )  # INDIVIDUAL, FAMILY, INSTITUTION

    description = Column(Text, nullable=True)
    short_description = Column(String(200), nullable=True)
    tagline = Column(String(100), nullable=True)  # e.g., "Best for families"

    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_quarterly = Column(Numeric(10, 2), nullable=True)
    price_yearly = Column(Numeric(10, 2), nullable=False)

    monthly_discount_percentage = Column(Integer, default=0)
    quarterly_discount_percentage = Column(Integer, default=0)
    yearly_discount_percentage = Column(Integer, default=0)

    currency = Column(String(3), default="NGN")

    # Plan configuration
    max_members = Column(Integer, nullable=True)  # Null = unlimited or N/A
    trial_days = Column(Integer, default=0)  # Free trial period

    # Features and limits (flexible JSON structure)
    features = Column(JSONB, nullable=False, default=dict)
    # Example: {"unlimited_subjects": true, "leaderboard_access": true}

    limits = Column(JSONB, nullable=False, default=dict)
    # Example: {"tests_per_month": 10, "exams_per_month": 5}

    # Display settings
    is_active = Column(Boolean, default=True, index=True)
    is_featured = Column(Boolean, default=False)
    is_popular = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)  # For sorting on frontend

    # Visibility
    is_visible = Column(Boolean, default=True)  # Show on pricing page
    show_for_individuals = Column(Boolean, default=True)
    show_for_guardians = Column(Boolean, default=False)
    show_for_institutions = Column(Boolean, default=False)

    # Upgrade/downgrade rules
    can_upgrade_to = Column(JSONB, nullable=True)  # List of plan_codes
    can_downgrade_to = Column(JSONB, nullable=True)  # List of plan_codes

    meta_data = Column(JSONB, nullable=True)
    #  icon, color, custom fields, etc.

    terms_url = Column(String(500), nullable=True)
    benefits_list = Column(JSONB, nullable=True)

    def __repr__(self):
        return f"<SubscriptionPlanConfig {self.plan_code} - {self.plan_name}>"

    @property
    def monthly_savings(self) -> float:
        """Calculate monthly savings compared to no discount"""
        if self.monthly_discount_percentage:
            original = float(self.price_monthly) / (
                1 - self.monthly_discount_percentage / 100
            )
            return original - float(self.price_monthly)
        return 0.0

    @property
    def yearly_savings(self) -> float:
        """Calculate yearly savings compared to monthly * 12"""
        monthly_total = float(self.price_monthly) * 12
        yearly_price = float(self.price_yearly)
        return monthly_total - yearly_price

    @property
    def effective_monthly_price_yearly(self) -> float:
        """Calculate effective monthly price when paying yearly"""
        return float(self.price_yearly) / 12


class SubscriptionPlanFeature(FullBaseModel):
    """
    Reusable features that can be assigned to plans.
    Makes it easier to manage features across multiple plans.
    """

    __tablename__ = "subscription_plan_feature"

    feature_code = Column(
        String(50), unique=True, nullable=False, index=True
    )  # e.g., 'unlimited_tests'
    feature_name = Column(String(100), nullable=False)  # "Unlimited Tests"
    description = Column(Text, nullable=True)

    # Display
    icon = Column(String(50), nullable=True)  # Icon name or emoji
    category = Column(String(50), nullable=True)  # "core", "premium", "analytics"

    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    # Feature configuration
    requires_value = Column(Boolean, default=False)  # Does it need a limit value?
    default_value = Column(JSONB, nullable=True)  # Default configuration

    def __repr__(self):
        return f"<SubscriptionPlanFeature {self.feature_code} - {self.feature_name}>"


class PlanComparison(FullBaseModel):
    """
    For creating comparison tables between plans.
    Helps display "Plan A vs Plan B" type comparisons.
    """

    __tablename__ = "plan_comparison"

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Plans to compare (array of plan_codes)
    plan_codes = Column(JSONB, nullable=False)

    # Comparison criteria
    comparison_features = Column(JSONB, nullable=False)
    # Example: [
    #   {"feature": "tests_per_month", "label": "Monthly Tests"},
    #   {"feature": "subjects", "label": "Subjects Available"}
    # ]

    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    def __repr__(self):
        return f"<PlanComparison {self.title}>"


class SubscriptionPromotion(FullBaseModel):
    """
    Promotional campaigns for subscriptions (discounts, special offers).
    """

    __tablename__ = "subscription_promotion"

    promo_code = Column(String(50), unique=True, nullable=False, index=True)
    promo_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Applicable plans (null = all plans)
    applicable_plan_codes = Column(JSONB, nullable=True)

    # Discount configuration
    discount_type = Column(
        String(20), nullable=False
    )  # 'percentage', 'fixed_amount', 'trial_extension'
    discount_value = Column(Numeric(10, 2), nullable=False)

    # Validity
    start_date = Column(String(50), nullable=False)
    end_date = Column(String(50), nullable=True)

    # Usage limits
    max_uses = Column(Integer, nullable=True)  # Total uses allowed
    max_uses_per_user = Column(Integer, default=1)
    current_uses = Column(Integer, default=0)

    # Conditions
    min_billing_cycle = Column(
        SQLEnum(BillingCycle), nullable=True
    )  # e.g., must be yearly
    new_users_only = Column(Boolean, default=False)
    first_time_subscribers_only = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True, index=True)

    def __repr__(self):
        return f"<SubscriptionPromotion {self.promo_code}>"

    @property
    def is_valid(self) -> bool:
        """Check if promotion is currently valid"""
        from datetime import datetime

        if not self.is_active:
            return False

        now = datetime.utcnow()

        # Check start date
        start = datetime.fromisoformat(self.start_date)
        if now < start:
            return False

        # Check end date
        if self.end_date:
            end = datetime.fromisoformat(self.end_date)
            if now > end:
                return False

        # Check usage limit
        if self.max_uses and self.current_uses >= self.max_uses:
            return False

        return True
