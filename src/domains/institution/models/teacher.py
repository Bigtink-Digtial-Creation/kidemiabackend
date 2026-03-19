from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped
from typing import Optional
from datetime import datetime, timezone

from src.domains.auth.models.user import User
from src.shared.database.base import FullBaseModel


class InstitutionTeacher(FullBaseModel):
    """
    Represents a teacher within an institution.
    A teacher is linked to a User account and belongs to one institution.
    """

    __tablename__ = "institution_teachers"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    teacher_code = Column(String(100), nullable=True, unique=True, index=True)
    specialization = Column(String(255), nullable=True)  # Subject area
    bio = Column(Text, nullable=True)
    joined_date = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")
    institution = relationship("Institution", back_populates="teachers")

    # Classes this teacher is assigned to teach (not homeroom)
    taught_classes = relationship(
        "ClassroomTeacherAssignment",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )

    taught_classrooms = relationship(
        "Classroom", secondary="classroom_teacher_assignments", viewonly=True
    )
    homeroom_class: Mapped[Optional["Classroom"]] = relationship(
        "Classroom",
        back_populates="class_teacher",
        foreign_keys="Classroom.class_teacher_id",
    )

    def __repr__(self):
        return f"<InstitutionTeacher {self.teacher_code}>"
