from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from src.shared.database.base import FullBaseModel


class PaystackSubscription(FullBaseModel):
    __tablename__ = "paystack_subscriptions"

    subscription_id = Column(
        UUID(as_uuid=True), ForeignKey("subscription.id"), nullable=False, unique=True
    )
    paystack_subscription_code = Column(String, nullable=False, unique=True)
    paystack_email_token = Column(String, nullable=False)
    authorization_code = Column(String, nullable=False)
    customer_code = Column(String, nullable=False)
    status = Column(String, default="active")
    next_payment_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class PaystackPlan(FullBaseModel):
    __tablename__ = "paystack_plans"

    internal_plan_code = Column(String(100), unique=True, nullable=False)
    billing_cycle = Column(String(20), nullable=False)
    paystack_plan_code = Column(String(50), unique=True, nullable=False)
    paystack_plan_id = Column(BigInteger, nullable=False)


# charge.success
# subscription.create
# invoice.create
# invoice.update
# invoice.payment_failed
# subscription.disable
# subscription.not_renew
