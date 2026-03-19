from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped
from typing import List, Optional


from src.domains.auth.models.student import Student

from src.shared.database.base import FullBaseModel


class Classroom(FullBaseModel):
    """
    Represents a classroom/class within an institution.
    Students are grouped into classrooms, and assessments can be assigned at this level.
    """

    __tablename__ = "classrooms"

    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)  # e.g. "JSS 1A", "Year 10 Science"
    code = Column(String(50), nullable=True)  # Short code
    description = Column(Text, nullable=True)
    level = Column(String(50), nullable=True)  # e.g. "JSS1", "SS2", "Year 10"
    section = Column(String(20), nullable=True)  # e.g. "A", "B", "Science"
    academic_year = Column(String(20), nullable=True)  # e.g. "2024/2025"
    capacity = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    # Homeroom / class teacher
    class_teacher_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution_teachers.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    institution = relationship("Institution", back_populates="classrooms")
    class_teacher: Mapped[Optional["InstitutionTeacher"]] = relationship(
        "InstitutionTeacher",
        back_populates="homeroom_class",
        foreign_keys=[class_teacher_id],
    )
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="classroom", lazy="selectin"
    )
    student_groups: Mapped[List["StudentGroup"]] = relationship(
        "StudentGroup", back_populates="classroom", cascade="all, delete-orphan"
    )
    assessment_assignments: Mapped[List["ClassroomAssessmentAssignment"]] = (
        relationship(
            "ClassroomAssessmentAssignment",
            back_populates="classroom",
            cascade="all, delete-orphan",
        )
    )

    def __repr__(self):
        return f"<Classroom {self.name} ({self.institution_id})>"
