from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
    Numeric,
    Enum as SQLEnum,
    Table,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from src.shared.database.base import FullBaseModel
from src.domains.assessment.enums import (
    AssessmentType,
    AssessmentCategory,
    AssessmentStatus,
    QuestionSelectionMode,
    ResultDisplayMode,
)

# Association table for assessment questions with metadata
assessment_questions = Table(
    "assessment_questions",
    FullBaseModel.metadata,
    Column(
        "assessment_id",
        PG_UUID(as_uuid=True),
        ForeignKey("assessment.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "question_id",
        PG_UUID(as_uuid=True),
        ForeignKey("question.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("order", Integer, nullable=False),
    Column("points", Integer, default=1),
    Column("section_id", PG_UUID(as_uuid=True), nullable=True),  # For sectioned exams
)


class Assessment(FullBaseModel):
    """Assessment model - represents tests and exams"""

    __tablename__ = "assessment"

    # ==================== BASIC INFO ====================
    title = Column(String(300), nullable=False, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)

    assessment_type = Column(SQLEnum(AssessmentType), nullable=False, index=True)
    category = Column(SQLEnum(AssessmentCategory), nullable=False, index=True)

    category_config_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_category_config.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        SQLEnum(AssessmentStatus), default=AssessmentStatus.DRAFT, index=True
    )

    subject_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_ids = Column(JSONB, nullable=True)  # Multiple topics can be covered

    # Year and session (for exam categories)
    exam_year = Column(Integer, nullable=True, index=True)
    exam_session = Column(String(50), nullable=True)  # e.g., "May/June", "Nov/Dec"

    price = Column(Numeric(10, 2), default=0.00)
    currency = Column(String(3), default="NGN")
    discount_price = Column(Numeric(10, 2), nullable=True)

    duration_minutes = Column(Integer, nullable=False)

    available_from = Column(String(50), nullable=True)
    available_until = Column(String(50), nullable=True)

    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)

    late_submission_minutes = Column(Integer, default=0)
    early_start_minutes = Column(Integer, default=0)

    total_questions = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    question_selection_mode = Column(
        SQLEnum(QuestionSelectionMode), default=QuestionSelectionMode.MANUAL
    )
    questions_per_subject = Column(JSONB, nullable=True)

    passing_score = Column(Integer, default=50)
    passing_percentage = Column(Numeric(5, 2), default=50.00)

    shuffle_questions = Column(Boolean, default=True)
    shuffle_options = Column(Boolean, default=True)
    allow_question_navigation = Column(Boolean, default=True)
    allow_backward_navigation = Column(Boolean, default=True)
    show_question_numbers = Column(Boolean, default=True)

    # Review settings
    allow_review_before_submit = Column(Boolean, default=True)
    allow_flag_questions = Column(Boolean, default=True)

    # Attempt settings
    max_attempts = Column(Integer, default=3)
    attempts_interval_hours = Column(Integer, default=24)
    retry_same_questions = Column(Boolean, default=False)

    result_display_mode = Column(
        SQLEnum(ResultDisplayMode), default=ResultDisplayMode.IMMEDIATE
    )
    result_release_date = Column(String(50), nullable=True)
    show_correct_answers = Column(Boolean, default=True)
    show_explanations = Column(Boolean, default=True)
    show_score = Column(Boolean, default=True)
    show_percentage = Column(Boolean, default=True)
    show_ranking = Column(Boolean, default=False)

    # Certificate
    generate_certificate = Column(Boolean, default=False)
    certificate_template_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # PROCTORING
    proctoring_enabled = Column(Boolean, default=False)
    proctoring_config = Column(JSONB, nullable=True)  # Detailed proctoring settings
    require_webcam = Column(Boolean, default=False)
    require_screen_share = Column(Boolean, default=False)
    detect_tab_switching = Column(Boolean, default=True)
    max_tab_switches = Column(Integer, default=3)
    fullscreen_required = Column(Boolean, default=True)

    # ACCESS CONTROL
    # Institution specific
    institution_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_public = Column(Boolean, default=True)

    # Access restrictions
    require_enrollment = Column(Boolean, default=False)
    allowed_user_types = Column(JSONB, nullable=True)  # List of allowed user types
    access_code = Column(String(50), nullable=True)  # Optional access code
    ip_whitelist = Column(JSONB, nullable=True)  # IP restrictions

    # STATISTICS
    total_attempts = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    total_passes = Column(Integer, default=0)
    total_fails = Column(Integer, default=0)
    average_score = Column(Numeric(5, 2), default=0.00)
    average_completion_time = Column(Integer, default=0)  # in seconds
    highest_score = Column(Numeric(5, 2), default=0.00)
    lowest_score = Column(Numeric(5, 2), default=0.00)

    # METADATA
    tags = Column(JSONB, nullable=True)
    difficulty_rating = Column(Numeric(3, 2), nullable=True)  # 1.0 to 5.0
    estimated_difficulty = Column(String(20), nullable=True)

    # SEO
    meta_title = Column(String(200), nullable=True)
    meta_description = Column(Text, nullable=True)
    slug = Column(String(200), unique=True, nullable=True, index=True)

    # RELATIONSHIPS
    subject = relationship("Subject", backref="assessments")
    category_config = relationship(
        "AssessmentCategoryConfig", back_populates="assessments"
    )
    institution = relationship("Institution", backref="assessments")
    questions = relationship(
        "Question", secondary=assessment_questions, backref="assessments"
    )
    sections = relationship(
        "AssessmentSection",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentSection.order",
    )
    attempts = relationship(
        "AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan"
    )

    #  CONSTRAINTS
    __table_args__ = (
        CheckConstraint(
            "passing_score >= 0 AND passing_score <= 100", name="check_passing_score"
        ),
        CheckConstraint("duration_minutes > 0", name="check_duration"),
        CheckConstraint("max_attempts > 0", name="check_max_attempts"),
        CheckConstraint("price >= 0", name="check_price"),
    )

    def __repr__(self):
        return f"<Assessment {self.title} ({self.category})>"
