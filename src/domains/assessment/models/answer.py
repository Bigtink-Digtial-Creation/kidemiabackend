from sqlalchemy import (
    Column,
    Text,
    Boolean,
    Integer,
    String,
    ForeignKey,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from src.shared.database.base import FullBaseModel


class Answer(FullBaseModel):
    """Answer model - stores user answers to questions"""

    __tablename__ = "answer"

    attempt_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_attempt.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("question.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_section.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Different answer types based on question type
    selected_option_ids = Column(JSONB, nullable=True)
    text_answer = Column(Text, nullable=True)
    matching_pairs = Column(JSONB, nullable=True)
    ordered_items = Column(JSONB, nullable=True)

    # Original question data snapshot (in case question changes)
    question_snapshot = Column(JSONB, nullable=True)

    is_correct = Column(Boolean, nullable=True)
    is_partially_correct = Column(Boolean, default=False)
    points_earned = Column(Numeric(10, 2), default=0.00)
    points_possible = Column(Numeric(10, 2), default=0.00)

    # Manual grading (for essays and subjective questions)
    requires_manual_grading = Column(Boolean, default=False)
    manually_graded = Column(Boolean, default=False)
    manual_feedback = Column(Text, nullable=True)
    graded_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    graded_at = Column(String(50), nullable=True)

    # AI-assisted grading (for essays)
    ai_suggested_score = Column(Numeric(10, 2), nullable=True)
    ai_feedback = Column(Text, nullable=True)

    time_spent_seconds = Column(Integer, default=0)
    flagged_for_review = Column(Boolean, default=False)
    answer_order = Column(Integer, nullable=True)

    # Interaction tracking
    view_count = Column(Integer, default=0)
    edit_count = Column(Integer, default=0)
    first_answered_at = Column(String(50), nullable=True)
    last_modified_at = Column(String(50), nullable=True)

    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("Question")
    section = relationship("AssessmentSection")
    grader = relationship("User", foreign_keys=[graded_by])

    __table_args__ = (
        CheckConstraint("points_earned >= 0", name="check_points_earned"),
        CheckConstraint("points_earned <= points_possible", name="check_points_valid"),
        CheckConstraint("time_spent_seconds >= 0", name="check_time_spent"),
    )

    def __repr__(self):
        return f"<Answer {self.id} - Question: {self.question_id}>"
