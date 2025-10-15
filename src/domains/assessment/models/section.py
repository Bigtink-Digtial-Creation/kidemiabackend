from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import FullBaseModel


class AssessmentSection(FullBaseModel):
    """Sections within an assessment (for organized exams)"""

    __tablename__ = "assessment_section"

    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Section info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)

    # Ordering
    order = Column(Integer, nullable=False)

    # Configuration
    time_limit_minutes = Column(Integer, nullable=True)  # Section-specific time limit
    total_questions = Column(Integer, default=0)
    total_points = Column(Integer, default=0)

    # Behavior
    shuffle_questions = Column(Boolean, default=True)
    is_optional = Column(Boolean, default=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="sections")

    def __repr__(self):
        return f"<AssessmentSection {self.title}>"
