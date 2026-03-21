from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from src.shared.database.base import FullBaseModel


class QuestionOption(FullBaseModel):
    """Question option model - represents answer options"""

    __tablename__ = "question_option"

    question_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("question.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Option content
    option_text = Column(Text, nullable=False)

    option_content = Column(JSONB, nullable=True)

    option_order = Column(Integer, nullable=False)

    # For matching and ordering questions
    match_pair_id = Column(String(50), nullable=True)
    correct_order = Column(Integer, nullable=True)

    # Additional content
    image_url = Column(String(500), nullable=True)

    # Correctness
    is_correct = Column(Boolean, default=False)

    # Explanation for this option
    explanation = Column(Text, nullable=True)

    # Relationships
    question = relationship("Question", back_populates="options")

    def __repr__(self):
        return f"<QuestionOption {self.id}>"
