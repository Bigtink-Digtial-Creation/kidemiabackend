from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    Numeric,
    Enum as SQLEnum,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from src.shared.database.base import FullBaseModel
from src.domains.assessment.enums import AttemptStatus, GradingStatus


class AssessmentAttempt(FullBaseModel):
    """Assessment attempt model - tracks user attempts"""

    __tablename__ = "assessment_attempt"

    # REFERENCES
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #  ATTEMPT INFO
    attempt_number = Column(Integer, nullable=False)
    status = Column(
        SQLEnum(AttemptStatus), default=AttemptStatus.NOT_STARTED, index=True
    )

    #  TIMING
    started_at = Column(String(50), nullable=True)
    submitted_at = Column(String(50), nullable=True)
    paused_at = Column(String(50), nullable=True)
    resumed_at = Column(String(50), nullable=True)

    # Time tracking
    time_spent_seconds = Column(Integer, default=0)
    time_remaining_seconds = Column(Integer, nullable=True)
    pause_count = Column(Integer, default=0)

    # Deadlines
    must_submit_by = Column(String(50), nullable=True)

    # SCORING
    total_questions = Column(Integer, default=0)
    questions_attempted = Column(Integer, default=0)
    questions_unanswered = Column(Integer, default=0)
    questions_flagged = Column(Integer, default=0)

    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)
    partially_correct = Column(Integer, default=0)

    score = Column(Numeric(5, 2), default=0.00)
    percentage = Column(Numeric(5, 2), default=0.00)
    points_earned = Column(Numeric(10, 2), default=0.00)
    points_possible = Column(Numeric(10, 2), default=0.00)

    passed = Column(Boolean, default=False)
    grade = Column(String(10), nullable=True)  # A, B, C, D, F

    # GRADING
    grading_status = Column(SQLEnum(GradingStatus), default=GradingStatus.PENDING)
    auto_graded = Column(Boolean, default=False)
    requires_manual_grading = Column(Boolean, default=False)
    graded_at = Column(String(50), nullable=True)
    graded_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)

    # FEEDBACK
    feedback = Column(Text, nullable=True)
    examiner_comments = Column(Text, nullable=True)

    # PROCTORING
    proctoring_session_id = Column(String(100), nullable=True)
    proctoring_data = Column(JSONB, nullable=True)
    violation_count = Column(Integer, default=0)
    violations = Column(JSONB, nullable=True)  # List of violation details
    flagged_suspicious = Column(Boolean, default=False)

    # Browser/device tracking
    tab_switches = Column(Integer, default=0)
    fullscreen_exits = Column(Integer, default=0)
    copy_paste_attempts = Column(Integer, default=0)

    #  RANKING
    rank = Column(Integer, nullable=True)
    percentile = Column(Numeric(5, 2), nullable=True)

    #  CERTIFICATE
    certificate_issued = Column(Boolean, default=False)
    certificate_id = Column(String(100), nullable=True, unique=True)
    certificate_url = Column(String(500), nullable=True)

    #  METADATA
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(JSONB, nullable=True)
    location_data = Column(JSONB, nullable=True)

    # Payment (for paid exams)
    payment_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("transaction.id"), nullable=True
    )

    #  RELATIONSHIPS
    assessment = relationship("Assessment", back_populates="attempts")
    user = relationship("User", foreign_keys=[user_id], backref="assessment_attempts")
    grader = relationship("User", foreign_keys=[graded_by])
    answers = relationship(
        "Answer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="Answer.created_at",
    )

    # CONSTRAINTS
    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="check_attempt_number"),
        CheckConstraint("time_spent_seconds >= 0", name="check_time_spent"),
        CheckConstraint("score >= 0 AND score <= 100", name="check_score_range"),
    )

    def __repr__(self):
        return f"<AssessmentAttempt {self.id} - User: {self.user_id} - Attempt: {self.attempt_number}>"
