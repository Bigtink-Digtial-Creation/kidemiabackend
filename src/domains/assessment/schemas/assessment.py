from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import Field, field_validator, model_validator, model_serializer
from decimal import Decimal
from pydantic_core import PydanticCustomError

from src.shared.schemas.base import (
    BaseSchema,
    CreateSchema,
    UpdateSchema,
    ResponseSchema,
)
from src.domains.assessment.enums import (
    AssessmentType,
    AssessmentCategory,
    AssessmentStatus,
    QuestionSelectionMode,
    ResultDisplayMode,
)
from src.domains.assessment.schemas.section import SectionCreate, SectionResponse

from src.domains.content.schemas.question import QuestionPublicResponse


class AssessmentBase(BaseSchema):
    """Base assessment schema"""

    title: str = Field(..., min_length=1, max_length=300)
    code: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    instructions: Optional[str] = None

    assessment_type: AssessmentType
    category: AssessmentCategory

    subject_id: UUID
    topic_ids: Optional[List[UUID]] = None

    exam_year: Optional[int] = Field(None, ge=1900, le=2100)
    exam_session: Optional[str] = Field(None, max_length=50)

    # Pricing
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = Field(default="NGN", max_length=3)
    discount_price: Optional[Decimal] = Field(None, ge=0)

    # Timing
    duration_minutes: int = Field(..., gt=0, le=600)
    available_from: Optional[str] = None
    available_until: Optional[str] = None

    # Configuration
    question_selection_mode: QuestionSelectionMode = QuestionSelectionMode.MANUAL
    passing_percentage: Decimal = Field(default=Decimal("50.00"), ge=0, le=100)

    # Behavior
    shuffle_questions: bool = True
    shuffle_options: bool = True
    allow_question_navigation: bool = True
    allow_backward_navigation: bool = True
    max_attempts: int = Field(default=3, gt=0, le=10)

    # Results
    result_display_mode: ResultDisplayMode = ResultDisplayMode.IMMEDIATE
    show_correct_answers: bool = True
    show_explanations: bool = True

    # Proctoring
    proctoring_enabled: bool = False
    require_webcam: bool = False
    fullscreen_required: bool = True
    detect_tab_switching: bool = True
    max_tab_switches: int = Field(default=3, ge=0)

    # Access
    is_public: bool = True
    require_enrollment: bool = False


class AssessmentCreate(AssessmentBase, CreateSchema):
    """Schema for creating assessment"""

    category_config_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None

    # Question assignment
    question_ids: Optional[List[UUID]] = Field(default_factory=list)
    sections: Optional[List[SectionCreate]] = Field(default_factory=list)

    @model_serializer(mode="wrap", when_used="json")
    def serialize_model(self, serializer, info):
        """Convert all UUID fields to strings for database insertion"""
        data = serializer(self)

        # Single UUID fields
        uuid_fields = [
            "id",
            "subject_id",
            "category_config_id",
            "certificate_template_id",
            "institution_id",
            "created_by",
            "updated_by",
        ]
        for field in uuid_fields:
            if field in data and data[field] is not None:
                if isinstance(data[field], UUID):
                    data[field] = str(data[field])

        # UUID list fields
        uuid_list_fields = ["topic_ids", "question_ids"]
        for field in uuid_list_fields:
            if field in data and data[field] is not None:
                data[field] = [
                    str(v) if isinstance(v, UUID) else v for v in data[field]
                ]

        return data

    @field_validator("discount_price")
    @classmethod
    def validate_discount(cls, v, info):
        """Validate discount price is less than regular price"""
        if v is not None:
            price = info.data.get("price")
            if price and v >= price:
                raise PydanticCustomError(
                    "price_value", "Discount price must be less than regular price"
                )
        return v

    @model_validator(mode="after")
    def validate_exam_pricing(self):
        """Validate that exams have pricing"""
        if self.assessment_type == AssessmentType.EXAM:
            if self.price == 0:
                raise PydanticCustomError(
                    "price_value", "Exams must have a price greater than 0"
                )
        return self


class AssessmentUpdate(UpdateSchema):
    """Schema for updating assessment"""

    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    instructions: Optional[str] = None
    status: Optional[AssessmentStatus] = None

    exam_year: Optional[int] = Field(None, ge=1900, le=2100)
    exam_session: Optional[str] = Field(None, max_length=50)

    price: Optional[Decimal] = Field(None, ge=0)
    discount_price: Optional[Decimal] = Field(None, ge=0)

    duration_minutes: Optional[int] = Field(None, gt=0, le=600)
    available_from: Optional[str] = None
    available_until: Optional[str] = None

    passing_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    max_attempts: Optional[int] = Field(None, gt=0, le=10)

    result_display_mode: Optional[ResultDisplayMode] = None
    show_correct_answers: Optional[bool] = None
    show_explanations: Optional[bool] = None

    proctoring_enabled: Optional[bool] = None
    is_public: Optional[bool] = None


class AssessmentResponse(AssessmentBase, ResponseSchema):
    """Schema for assessment response"""

    category_config_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    status: AssessmentStatus

    total_questions: int
    total_points: int

    # Statistics
    total_attempts: int
    total_completions: int
    total_passes: int
    total_fails: int
    average_score: Decimal
    highest_score: Decimal
    lowest_score: Decimal

    sections: List[SectionResponse] = []
    questions: Optional[List[QuestionPublicResponse]] = None


class AssessmentSummaryResponse(BaseSchema):
    """Lightweight assessment response for listings"""

    id: UUID
    title: str
    code: str
    assessment_type: AssessmentType
    category: AssessmentCategory
    subject_id: UUID
    price: Decimal
    duration_minutes: int
    total_questions: int
    status: AssessmentStatus
    created_at: datetime

    # Quick stats
    total_attempts: int
    average_score: Decimal


class TopicResponse(BaseSchema):
    """Schema for topic response"""

    name: str
    description: Optional[str] = None
    content: Optional[str] = None
    questions_count: int = 0


class SubjectWithTopics(BaseSchema):
    """Subject response with nested topics"""

    name: str
    topics_count: int = 0
    questions_count: int = 0
    topics: List[TopicResponse] = []


class AssessmentSummaryResponseForAttempt(BaseSchema):
    """Lightweight assessment response for listings"""

    id: UUID
    title: str
    code: str
    assessment_type: AssessmentType
    category: AssessmentCategory
    subject_id: UUID
    price: Decimal
    duration_minutes: int
    total_questions: int
    status: AssessmentStatus
    created_at: datetime
    subject: SubjectWithTopics
    total_attempts: int
    average_score: Decimal


class AssessmentListResponse(BaseSchema):
    """Paginated assessment list"""

    items: List[AssessmentSummaryResponse]
    total: int
    page: int
    page_size: int


class AssessmentFilterParams(BaseSchema):
    """Assessment filter parameters"""

    assessment_type: Optional[AssessmentType] = None
    category: Optional[AssessmentCategory] = None
    subject_id: Optional[UUID] = None
    status: Optional[AssessmentStatus] = None
    exam_year: Optional[int] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    is_public: Optional[bool] = None
    search: Optional[str] = None


class BulkAssessmentPublishRequest(BaseSchema):
    """Bulk publish assessments"""

    assessment_ids: List[UUID] = Field(..., min_items=1)
    publish_date: Optional[str] = None


class BulkAssessmentArchiveRequest(BaseSchema):
    """Bulk archive assessments"""

    assessment_ids: List[UUID] = Field(..., min_items=1)


class BulkGradeRequest(BaseSchema):
    """Bulk grade attempts"""

    attempt_ids: List[UUID] = Field(..., min_items=1)


# Auto Assessment Schemas


class AutoAssessmentRequest(BaseSchema):
    """Schema for auto-generating assessment from topics"""

    subject_id: UUID
    topic_ids: List[UUID] = Field(..., min_items=1, max_items=10)

    # Assessment configuration
    assessment_type: AssessmentType = AssessmentType.TEST
    number_of_questions: int = Field(default=5, ge=5, le=100)
    duration_minutes: int = Field(default=20, ge=10, le=180)

    # Optional filters
    difficulty_level: Optional[str] = None
    question_types: Optional[List[str]] = None

    # Behavior
    shuffle_questions: bool = True
    shuffle_options: bool = True
    allow_review: bool = True

    @field_validator("number_of_questions")
    @classmethod
    def validate_question_count(cls, v, info):
        """Ensure reasonable question count based on duration"""
        duration = info.data.get("duration_minutes", 30)
        max_questions = duration * 2  # Rough estimate: 30 seconds per question

        if v > max_questions:
            raise PydanticCustomError(
                "question_count",
                f"Too many questions ({v}) for duration ({duration} minutes). Maximum recommended: {max_questions}",
            )
        return v


class AutoAssessmentResponse(BaseSchema):
    """Response after auto-generating assessment"""

    assessment_id: UUID
    title: str
    total_questions: int
    duration_minutes: int
    topics_covered: List[str]
    message: str
