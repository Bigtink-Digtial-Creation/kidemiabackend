from typing import Optional, List

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped

from src.shared.database.base import FullBaseModel


class GamificationProfile(FullBaseModel):
    """Gamification profile - tracks student's overall gamification progress"""

    __tablename__ = "gamification_profiles"

    # Foreign keys
    student_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Points & levels
    total_points = Column(Integer, default=0, nullable=False)
    current_level = Column(Integer, default=1, nullable=False)
    experience_points = Column(Integer, default=0, nullable=False)

    # Streaks
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_activity_date = Column(DateTime, nullable=True)

    # Stats
    total_assessments_completed = Column(Integer, default=0, nullable=False)
    total_questions_answered = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)

    # Rank
    rank_title = Column(String(100), nullable=True, default="Beginner")
    leaderboard_position = Column(Integer, nullable=True)

    # Relationships
    student: Mapped[Optional["Student"]] = relationship(
        "Student", back_populates="gamification_profile"
    )
    badges: Mapped[List["StudentBadge"]] = relationship(
        "StudentBadge", back_populates="profile", lazy="selectin"
    )
    achievements: Mapped[List["StudentAchievement"]] = relationship(
        "StudentAchievement", back_populates="profile", lazy="selectin"
    )

    def __repr__(self):
        return f"<GamificationProfile Level {self.current_level}>"
