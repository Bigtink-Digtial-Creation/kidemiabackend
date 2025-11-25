from sqlalchemy import Column, String, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import FullBaseModel


class Wallet(FullBaseModel):
    __tablename__ = "wallet"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    balance = Column(Numeric(12, 2), default=0.00, nullable=False)
    currency = Column(String(3), default="KID")

    daily_limit = Column(Numeric(12, 2), nullable=True)
    monthly_limit = Column(Numeric(12, 2), nullable=True)

    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)

    has_pin = Column(Boolean, default=False)
    pin_hash = Column(String(255), nullable=True)

    # Relationship
    user = relationship("User", passive_deletes=True)

    def __repr__(self):
        return f"<Wallet User:{self.user_id} Balance:{self.balance}>"
