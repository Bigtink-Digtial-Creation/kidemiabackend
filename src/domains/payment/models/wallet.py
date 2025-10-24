from sqlalchemy import Column, String, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import FullBaseModel


class Wallet(FullBaseModel):
    """Wallet model - user wallet for platform currency"""

    __tablename__ = "wallet"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Balance
    balance = Column(Numeric(12, 2), default=0.00, nullable=False)
    currency = Column(String(3), default="NGN")

    # Limits
    daily_limit = Column(Numeric(12, 2), nullable=True)
    monthly_limit = Column(Numeric(12, 2), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)

    # PIN/Security
    has_pin = Column(Boolean, default=False)
    pin_hash = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", backref="wallet")

    def __repr__(self):
        return f"<Wallet User:{self.user_id} Balance:{self.balance}>"
