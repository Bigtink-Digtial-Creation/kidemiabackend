from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    Boolean,
    Integer,
    Date,
    ForeignKey,
    UniqueConstraint,
)

from typing import List, Optional
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped

from src.domains.institution.models.classroom import Classroom
from src.domains.institution.models.teacher import InstitutionTeacher
from src.shared.database.base import FullBaseModel
from src.domains.auth.models.student import Student


class Institution(FullBaseModel):
    """
    Represents an educational institution (school, academy, university, etc.)
    that owns or manages content and users within Kidemia.
    """

    __tablename__ = "institution"

    name = Column(String(255), nullable=False, unique=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    motto = Column(String(255), nullable=True)
    established_date = Column(Date, nullable=True)

    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)

    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    color_primary = Column(String(20), nullable=True)
    color_secondary = Column(String(20), nullable=True)

    academic_session = Column(String(20), nullable=True)  # e.g. "2024/2025"

    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    is_verified = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    tier = Column(String(50), default="basic")  # e.g., basic, premium, enterprise

    total_users = Column(Integer, default=0)
    total_assessments = Column(Integer, default=0)
    total_courses = Column(Integer, default=0)
    total_students = Column(Integer, default=0)

    # owner = relationship("User", back_populates="institutions_owned", lazy="joined")

    assessments = relationship(
        "Assessment", back_populates="institution", cascade="all, delete-orphan"
    )

    max_students = Column(Integer, nullable=True)

    # Relationships
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="institution", lazy="selectin"
    )

    teachers: Mapped[List["InstitutionTeacher"]] = relationship(
        "InstitutionTeacher", back_populates="institution", cascade="all, delete-orphan"
    )
    classrooms: Mapped[List["Classroom"]] = relationship(
        "Classroom", back_populates="institution", cascade="all, delete-orphan"
    )

    members: Mapped[List["InstitutionMember"]] = relationship(
        "InstitutionMember", back_populates="institution", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Institution {self.name} ({self.code})>"


class InstitutionMember(FullBaseModel):
    """
    Bridge table between User and Institution.

    This is the single source of truth for which users belong to which
    institution and in what capacity. The Institution model retains a
    denormalized `owner_id` FK purely for quick ownership queries, but
    all access-control and dashboard-routing logic must go through this
    table.
    """

    __tablename__ = "institution_members"

    __table_args__ = (
        # A user can only have one role record per institution
        UniqueConstraint("institution_id", "user_id", name="uq_institution_member"),
    )

    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # owner | admin | staff
    role = Column(String(20), nullable=False, default="owner")

    is_active = Column(Boolean, default=True, nullable=False)

    # When was this membership granted / last changed
    joined_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    institution = relationship("Institution", back_populates="members")
    user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self):
        return f"<InstitutionMember user={self.user_id} institution={self.institution_id} role={self.role}>"
