from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    Date,
    ForeignKey,
)

from typing import List
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped

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

    def __repr__(self):
        return f"<Institution {self.name} ({self.code})>"
