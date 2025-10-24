from sqlalchemy import (
    Boolean,
    Column,
    String,
    Text,
    ForeignKey,
    Numeric,
    Enum as SQLEnum,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from src.shared.database.base import FullBaseModel
from src.domains.payment.enums import (
    TransactionType,
    TransactionStatus,
    PaymentMethod,
    PaymentGateway,
)


class Transaction(FullBaseModel):
    """Transaction model - tracks all financial transactions"""

    __tablename__ = "transaction"

    transaction_reference = Column(String(100), unique=True, nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    status = Column(
        SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, index=True
    )

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # For institutional transactions
    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="NGN", nullable=False)

    # Fees and charges
    platform_fee = Column(Numeric(12, 2), default=0.00)
    gateway_fee = Column(Numeric(12, 2), default=0.00)
    total_amount = Column(Numeric(12, 2), nullable=False)  # amount + fees

    # Net amount (for payouts)
    net_amount = Column(Numeric(12, 2), nullable=True)

    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    payment_gateway = Column(SQLEnum(PaymentGateway), nullable=False)

    # Gateway-specific references
    gateway_reference = Column(String(200), nullable=True, index=True)
    gateway_response = Column(JSONB, nullable=True)

    # Card/Bank details (masked)
    card_last4 = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    bank_name = Column(String(100), nullable=True)
    account_name = Column(String(200), nullable=True)

    # What was purchased
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    subscription_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Parent transaction (for refunds)
    parent_transaction_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("transaction.id", ondelete="SET NULL"),
        nullable=True,
    )

    description = Column(Text, nullable=True)
    meta_data = Column(JSONB, nullable=True)  # Additional data

    # IP and device info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    initiated_at = Column(String(50), nullable=False)
    completed_at = Column(String(50), nullable=True)
    failed_at = Column(String(50), nullable=True)

    is_reconciled = Column(Boolean, default=False)
    reconciled_at = Column(String(50), nullable=True)
    reconciled_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], backref="transactions")
    institution = relationship("Institution", backref="transactions")
    assessment = relationship("Assessment", backref="transactions")
    subscription = relationship("Subscription", backref="transactions")
    parent_transaction = relationship(
        "Transaction", remote_side="Transaction.id", backref="child_transactions"
    )
    refund = relationship("Refund", back_populates="transaction", uselist=False)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_amount_positive"),
        CheckConstraint("total_amount >= 0", name="check_total_positive"),
        CheckConstraint("platform_fee >= 0", name="check_platform_fee_positive"),
        CheckConstraint("gateway_fee >= 0", name="check_gateway_fee_positive"),
    )

    def __repr__(self):
        return f"<Transaction {self.transaction_reference} - {self.status}>"
