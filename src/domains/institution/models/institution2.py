from typing import List

from sqlalchemy import Column, String, Text, Boolean, Integer
from sqlalchemy.orm import relationship

from src.shared.database.base import FullBaseModel

from src.domains.auth.models.student import Student


class Institution(FullBaseModel):
    """Institution model - represents schools/organizations linked to students"""

    __tablename__ = "institutions"

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), nullable=True, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Contact info
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)

    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="Nigeria")

    # Visual
    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    max_students = Column(Integer, nullable=True)

    # Relationships
    students: List["Student"] = relationship(
        "Student", back_populates="institution", lazy="selectin"
    )

    def __repr__(self):
        return f"<Institution {self.name}>"
