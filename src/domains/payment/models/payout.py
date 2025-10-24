from sqlalchemy import Column, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from src.shared.database.base import FullBaseModel


class Payout(FullBaseModel):
    """Payout model - for institution/affiliate payouts"""

    __tablename__ = "payout"

    payout_reference = Column(String(100), unique=True, nullable=False, index=True)

    # Recipient
    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amount
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="NGN")

    # Bank details
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(20), nullable=False)
    account_name = Column(String(200), nullable=False)

    # Status
    status = Column(String(20), default="pending", index=True)

    # Processing
    processed_at = Column(String(50), nullable=True)
    processed_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)

    # Gateway
    gateway_reference = Column(String(200), nullable=True)
    gateway_response = Column(JSONB, nullable=True)

    # Relationships
    institution = relationship("Institution", backref="payouts")

    def __repr__(self):
        return f"<Payout {self.payout_reference}>"
