from sqlalchemy import (
    Column,
    Table,
    String,
    Text,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import FullBaseModel, SimpleBaseModel
from src.domains.content.enums import DifficultyLevel, QuestionType, QuestionStatus

question_tags_association = Table(
    "question_tags",
    FullBaseModel.metadata,
    Column(
        "question_id",
        PG_UUID(as_uuid=True),
        ForeignKey("question.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        PG_UUID(as_uuid=True),
        ForeignKey("question_tag.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Question(FullBaseModel):
    """Question model - represents exam/test questions"""

    __tablename__ = "question"

    subject_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("topic.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Question content
    question_text = Column(Text, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False, index=True)

    # Additional content
    image_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    explanation = Column(Text, nullable=True)

    # Metadata
    difficulty_level = Column(SQLEnum(DifficultyLevel), nullable=False, index=True)
    points = Column(Integer, default=1)
    time_limit_seconds = Column(Integer, nullable=True)

    # Status and review
    status = Column(SQLEnum(QuestionStatus), default=QuestionStatus.DRAFT, index=True)
    reviewed_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    approved_at = Column(String(50), nullable=True)

    # Analytics
    times_used = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    times_incorrect = Column(Integer, default=0)

    # Tags for better organization
    tags = relationship(
        "QuestionTag", secondary=question_tags_association, back_populates="questions"
    )  # Comma-separated tags

    # Relationships
    subject = relationship("Subject", back_populates="questions")
    topic = relationship("Topic", back_populates="questions")
    options = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.option_order",
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.times_correct + self.times_incorrect
        if total == 0:
            return 0.0
        return (self.times_correct / total) * 100

    def __repr__(self):
        return f"<Question {self.id} - {self.question_type}>"


class QuestionTag(SimpleBaseModel):
    """Tag model for categorizing questions"""

    __tablename__ = "question_tag"

    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color

    # Relationships
    questions = relationship(
        "Question", secondary=question_tags_association, back_populates="tags"
    )

    def __repr__(self):
        return f"<QuestionTag {self.name}>"
