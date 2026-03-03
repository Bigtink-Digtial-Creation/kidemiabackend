from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    ForeignKey,
    Numeric,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from datetime import datetime, timezone

from src.shared.database.base import FullBaseModel
from src.domains.payment.enums import (
    SubscriptionStatus,
    MemberRole,
)


class Subscription(FullBaseModel):
    """
    Subscription model - manages user subscriptions.
    """

    __tablename__ = "subscription"

    subscription_reference = Column(
        String(100), unique=True, nullable=False, index=True
    )
    plan_code = Column(
        String(50), nullable=False, index=True
    )  # References SubscriptionPlanConfig.plan_code
    subscription_type = Column(
        String(20), nullable=False, index=True
    )  # 'individual', 'family', 'institution'

    status = Column(
        SQLEnum(
            SubscriptionStatus,
            values_callable=lambda enum: [e.value.upper() for e in enum],
            name="subscriptionstatus",
            native_enum=True,
        ),
        default=SubscriptionStatus.PENDING,
        index=True,
    )
    owner_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="NGN")
    billing_cycle = Column(String(20), nullable=False)  # monthly, quarterly, yearly
    start_date = Column(String(50), nullable=False)
    end_date = Column(String(50), nullable=False)
    trial_end_date = Column(String(50), nullable=True)
    auto_renew = Column(Boolean, default=True)
    next_billing_date = Column(String(50), nullable=True)
    features = Column(JSONB, nullable=True)  # Plan features
    limits = Column(JSONB, nullable=True)  # Usage limits
    max_members = Column(Integer, nullable=True)  # For family/institution plans
    current_members = Column(Integer, default=1)  # Owner counts as member 1

    total_tests_taken = Column(Integer, default=0)
    total_exams_taken = Column(Integer, default=0)

    # Cancellation tracking
    cancelled_at = Column(String(50), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    renewed_at = Column(String(50), nullable=True)
    upgraded_from = Column(
        PG_UUID(as_uuid=True), nullable=True
    )  # Previous subscription ID

    applied_promo_code = Column(String(50), nullable=True)  # Which promo was used
    promo_discount_amount = Column(Numeric(10, 2), nullable=True)

    # CHANGED: Relationships
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_subscriptions")
    institution = relationship("Institution", backref="subscriptions")
    members = relationship(
        "SubscriptionMember",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    meta_data = Column(JSONB, nullable=True)

    def __repr__(self):
        return f"<Subscription {self.subscription_reference} - {self.plan_code}>"

    @property
    def days_remaining(self) -> int:
        """Calculate days remaining in subscription"""
        if not self.end_date:
            return 0

        end = datetime.fromisoformat(self.end_date)
        now = datetime.now(timezone.utc)
        remaining = (end - now).days
        return max(0, remaining)

    @property
    def can_add_members(self) -> bool:
        """Check if more members can be added"""
        if not self.max_members:
            return False
        return self.current_members < self.max_members

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.status != SubscriptionStatus.ACTIVE:
            return False

        if self.end_date:
            end = datetime.fromisoformat(self.end_date)
            now = datetime.now(timezone.utc)
            return now <= end

        return True

    @property
    def available_slots(self) -> int:
        """Get number of available member slots"""
        if not self.max_members:
            return 0
        return max(0, self.max_members - self.current_members)

    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period"""
        if not self.trial_end_date:
            return False

        trial_end = datetime.fromisoformat(self.trial_end_date)
        now = datetime.now(timezone.utc)
        return now <= trial_end

    @property
    def plan_display_name(self) -> str:
        """Get the plan display name from config (requires DB query)"""
        # This would need to be populated by the service layer
        # Or you can add a denormalized plan_name column
        return self.plan_code.replace("_", " ").title()


class SubscriptionMember(FullBaseModel):
    """Tracks members/beneficiaries of a subscription"""

    __tablename__ = "subscription_member"

    subscription_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(
        SQLEnum(MemberRole), default=MemberRole.MEMBER, nullable=False
    )  # OWNER, MEMBER, WARD, STUDENT

    added_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active = Column(Boolean, default=True)
    joined_at = Column(String(50), nullable=False)
    removed_at = Column(String(50), nullable=True)
    removal_reason = Column(Text, nullable=True)

    # Usage tracking per member
    tests_taken = Column(Integer, default=0)
    exams_taken = Column(Integer, default=0)
    last_activity = Column(String(50), nullable=True)

    # Preferences per member
    preferences = Column(JSONB, nullable=True)

    subscription = relationship("Subscription", back_populates="members")
    user = relationship(
        "User", foreign_keys=[user_id], backref="subscription_memberships"
    )
    added_by_user = relationship("User", foreign_keys=[added_by])

    def __repr__(self):
        return f"<SubscriptionMember {self.user_id} - {self.subscription_id}>"

    @property
    def has_reached_limit(self) -> bool:
        """Check if member has reached usage limits"""
        if not self.subscription or not self.subscription.limits:
            return False

        limits = self.subscription.limits

        # Check test limit
        test_limit = limits.get("tests_per_month")
        if test_limit and self.tests_taken >= test_limit:
            return True

        # Check exam limit
        exam_limit = limits.get("exams_per_month")
        if exam_limit and self.exams_taken >= exam_limit:
            return True

        return False


class SubscriptionUsageLog(FullBaseModel):
    """Logs subscription usage for auditing and analytics"""

    __tablename__ = "subscription_usage_log"

    subscription_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    member_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription_member.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    activity_type = Column(String(50), nullable=False)
    activity_id = Column(PG_UUID(as_uuid=True), nullable=True)

    timestamp = Column(String(50), nullable=False)
    meta_data = Column(JSONB, nullable=True)

    subscription = relationship("Subscription")
    member = relationship("SubscriptionMember")
    user = relationship("User")

    def __repr__(self):
        return f"<SubscriptionUsageLog {self.activity_type} - {self.user_id}>"
