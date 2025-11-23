from sqlalchemy import Column, String, Text, Boolean, Integer
from sqlalchemy.orm import relationship

from src.shared.database.base import FullBaseModel


class AssessmentCategoryConfig(FullBaseModel):
    """Configuration for assessment categories"""

    __tablename__ = "assessment_category_config"

    # Category info
    category_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Visual
    icon_url = Column(String(500), nullable=True)
    color_code = Column(String(7), nullable=True)
    banner_url = Column(String(500), nullable=True)

    # Configuration
    is_active = Column(Boolean, default=True)
    requires_payment = Column(Boolean, default=False)
    order = Column(Integer, default=0)

    # Metadata
    exam_body = Column(String(200), nullable=True)
    target_level = Column(String(100), nullable=True)

    # Relationships
    assessments = relationship("Assessment", back_populates="category_config")

    students = relationship("Student", back_populates="category")

    def __repr__(self):
        return f"<AssessmentCategoryConfig {self.display_name}>"
