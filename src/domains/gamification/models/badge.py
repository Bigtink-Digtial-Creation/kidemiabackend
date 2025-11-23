from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped

from src.shared.database.base import FullBaseModel


class Badge(FullBaseModel):
    """Badge definitions - available badges students can earn"""

    __tablename__ = "badges"

    # Badge info
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Visual
    icon_url = Column(String(500), nullable=True)
    color_code = Column(String(7), nullable=True)

    # Requirements
    points_required = Column(Integer, nullable=True)
    criteria = Column(Text, nullable=True)  # JSON string describing unlock criteria

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_secret = Column(Boolean, default=False, nullable=False)
    rarity = Column(String(50), default="common")  # common, rare, epic, legendary

    # Relationships
    student_badges: Mapped[List["StudentBadge"]] = relationship(
        "StudentBadge", back_populates="badge"
    )

    def __repr__(self):
        return f"<Badge {self.name}>"


class StudentBadge(FullBaseModel):
    """Student badges - tracks badges earned by students"""

    __tablename__ = "student_badges"

    # Foreign keys
    profile_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("gamification_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Earned info
    earned_at = Column(
        DateTime, default=datetime.now(timezone.utc).isoformat(), nullable=False
    )
    is_displayed = Column(Boolean, default=False, nullable=False)  # Featured on profile

    # Relationships
    profile: Mapped[Optional["GamificationProfile"]] = relationship(
        "GamificationProfile", back_populates="badges"
    )
    badge: Mapped[Optional["Badge"]] = relationship(
        "Badge", back_populates="student_badges"
    )

    def __repr__(self):
        return f"<StudentBadge {self.badge_id}>"
