from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped

from src.shared.database.base import FullBaseModel


from src.domains.auth.models.user import User
from src.domains.gamification.models.leaderboard import GamificationProfile
from src.domains.assessment.models.category import AssessmentCategoryConfig
from src.domains.guardian.models.guardian import Guardian


class Student(FullBaseModel):
    """Student model - represents users preparing for assessments/exams"""

    __tablename__ = "students"

    # Foreign keys
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_category_config.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    guardian_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("guardians.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Student details
    guardian_email = Column(String(255), nullable=True, index=True)
    student_code = Column(String(100), nullable=True, unique=True, index=True)
    registration_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Target exam info
    target_exam_date = Column(DateTime, nullable=True)
    preparation_level = Column(String(50), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="student")
    category: Mapped[Optional["Config"]] = relationship(
        "AssessmentCategoryConfig", back_populates="students"
    )
    institution: Mapped[Optional["Institution"]] = relationship(
        "Institution", back_populates="students"
    )
    guardian: Mapped[Optional["Guardian"]] = relationship(
        "Guardian", back_populates="students"
    )
    gamification_profile: Mapped[Optional["GamificationProfile"]] = relationship(
        "GamificationProfile", back_populates="student", lazy="selectin"
    )

    def __repr__(self):
        return f"<Student {self.student_code}>"
