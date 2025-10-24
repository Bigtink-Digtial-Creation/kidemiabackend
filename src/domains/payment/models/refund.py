from sqlalchemy import Column, String, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import FullBaseModel
from src.domains.payment.enums import RefundStatus


class Refund(FullBaseModel):
    """Refund model - tracks refund requests"""

    __tablename__ = "refund"

    refund_reference = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(RefundStatus), default=RefundStatus.REQUESTED, index=True)

    transaction_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("transaction.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="NGN")

    reason = Column(Text, nullable=False)
    requested_by = Column(
        PG_UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    approved_by = Column(
        PG_UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(String(50), nullable=True)

    rejected_by = Column(
        PG_UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at = Column(String(50), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    processed_at = Column(String(50), nullable=True)
    completed_at = Column(String(50), nullable=True)

    # Gateway info
    gateway_refund_id = Column(String(200), nullable=True)

    transaction = relationship("Transaction", back_populates="refund")
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<Refund {self.refund_reference} - {self.status}>"
