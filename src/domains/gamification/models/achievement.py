from typing import Optional, List

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped

from src.shared.database.base import FullBaseModel


class Achievement(FullBaseModel):
    """Achievement definitions - milestones students can reach"""

    __tablename__ = "achievements"

    # Achievement info
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Visual
    icon_url = Column(String(500), nullable=True)
    color_code = Column(String(7), nullable=True)

    # Requirements
    target_value = Column(
        Integer, nullable=False
    )  # e.g., 100 for "Complete 100 assessments"
    achievement_type = Column(
        String(50), nullable=False
    )  # e.g., "assessments_completed", "streak_days"
    points_reward = Column(Integer, default=0, nullable=False)

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    student_achievements: Mapped[List["StudentAchievement"]] = relationship(
        "StudentAchievement", back_populates="achievement"
    )

    def __repr__(self):
        return f"<Achievement {self.name}>"


class StudentAchievement(FullBaseModel):
    """Student achievements - tracks achievements unlocked by students"""

    __tablename__ = "student_achievements"

    # Foreign keys
    profile_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("gamification_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    achievement_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Progress
    current_value = Column(Integer, default=0, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    profile: Mapped[Optional["GamificationProfile"]] = relationship(
        "GamificationProfile", back_populates="achievements"
    )
    achievement: Mapped[Optional["Achievement"]] = relationship(
        "Achievement", back_populates="student_achievements"
    )

    def __repr__(self):
        return f"<StudentAchievement {self.achievement_id}>"
