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

from src.shared.database.base import FullBaseModel
from src.domains.payment.enums import SubscriptionPlan, SubscriptionStatus


class Subscription(FullBaseModel):
    """Subscription model - manages user subscriptions"""

    __tablename__ = "subscription"

    subscription_reference = Column(
        String(100), unique=True, nullable=False, index=True
    )
    plan = Column(SQLEnum(SubscriptionPlan), nullable=False, index=True)
    status = Column(
        SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, index=True
    )

    user_id = Column(
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

    # Usage tracking
    exams_taken = Column(Integer, default=0)
    exams_limit = Column(Integer, nullable=True)

    cancelled_at = Column(String(50), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    user = relationship("User", backref="subscriptions")
    institution = relationship("Institution", backref="subscriptions")

    def __repr__(self):
        return f"<Subscription {self.subscription_reference} - {self.plan}>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        from datetime import datetime

        if self.status != SubscriptionStatus.ACTIVE:
            return False

        if self.end_date:
            end = datetime.fromisoformat(self.end_date)
            return datetime.utcnow() <= end

        return True

    @property
    def days_remaining(self) -> int:
        """Calculate days remaining in subscription"""
        from datetime import datetime

        if not self.end_date:
            return 0

        end = datetime.fromisoformat(self.end_date)
        remaining = (end - datetime.utcnow()).days
        return max(0, remaining)
