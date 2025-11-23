from typing import Optional, List

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped

from src.shared.database.base import FullBaseModel

from src.domains.auth.models.user import User


class Guardian(FullBaseModel):
    """Guardian model - represents parents/guardians who monitor students"""

    __tablename__ = "guardians"

    # Foreign keys
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Guardian details
    guardian_code = Column(String(100), nullable=True, unique=True, index=True)
    relationship_type = Column(
        String(50), nullable=True
    )  # e.g., "parent", "guardian", "sponsor"

    # Contact preferences
    receive_progress_reports = Column(Boolean, default=True, nullable=False)
    receive_performance_alerts = Column(Boolean, default=True, nullable=False)
    receive_payment_reminders = Column(Boolean, default=True, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="guardian")
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="guardian", lazy="selectin"
    )

    def __repr__(self):
        return f"<Guardian {self.guardian_code}>"
