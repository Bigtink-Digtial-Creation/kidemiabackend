from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped
from typing import List

from src.shared.database.base import FullBaseModel
from src.domains.auth.models.student import Student


student_group_members = Table(
    "student_group_members",
    FullBaseModel.metadata,
    Column(
        "student_id",
        PG_UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
    ),
    Column(
        "group_id",
        PG_UUID(as_uuid=True),
        ForeignKey("student_groups.id", ondelete="CASCADE"),
    ),
)


class StudentGroup(FullBaseModel):
    """Named group of students within a classroom for targeted assessment assignment."""

    __tablename__ = "student_groups"

    classroom_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    classroom = relationship("Classroom", back_populates="student_groups")
    students: Mapped[List["Student"]] = relationship(
        "Student", secondary=student_group_members, lazy="selectin"
    )
    assessment_assignments = relationship(
        "ClassroomAssessmentAssignment", back_populates="student_group"
    )

    def __repr__(self):
        return f"<StudentGroup {self.name}>"


class ClassroomTeacherAssignment(FullBaseModel):
    """Links a teacher to a classroom for a specific subject."""

    __tablename__ = "classroom_teacher_assignments"

    classroom_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution_teachers.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    classroom = relationship("Classroom")
    teacher = relationship("InstitutionTeacher", back_populates="taught_classes")

    def __repr__(self):
        return f"<ClassroomTeacherAssignment classroom={self.classroom_id} teacher={self.teacher_id}>"


class ClassroomAssessmentAssignment(FullBaseModel):
    """
    Central assignment record linking an Assessment to a scope within an institution.

    Populated via two paths:s
      1. Directly from the institution dashboard (InstitutionAssessmentService.assign).
      2. Automatically by the SQLAlchemy after_insert event listener below, which
         fires whenever the main assessment domain creates an AssessmentAssignment
         for a student who belongs to an institution. This keeps the institution
         dashboard in sync regardless of where the assignment originated.

    Scope:
      classroom_id set      → whole class assignment
      student_group_id set  → named group assignment
      both None             → individual student (bridged from assessment domain)
    """

    __tablename__ = "classroom_assessment_assignments"

    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scope selectors
    classroom_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    student_group_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("student_groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    student_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    assigned_by_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    due_date = Column(DateTime, nullable=True)
    available_from = Column(DateTime, nullable=True)
    instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    classroom = relationship("Classroom", back_populates="assessment_assignments")
    student_group = relationship(
        "StudentGroup", back_populates="assessment_assignments"
    )
    assessment = relationship("Assessment")
    assigned_by = relationship("User")

    def __repr__(self):
        scope = (
            "classroom"
            if self.classroom_id
            else ("group" if self.student_group_id else "individual")
        )
        return f"<ClassroomAssessmentAssignment assessment={self.assessment_id} scope={scope}>"
