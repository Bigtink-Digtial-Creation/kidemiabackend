"""
Content Domain - Question Schemas
src/domains/content/schemas/question.py
"""

from typing import Optional, List
from uuid import UUID
from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from src.shared.schemas.base import (
    BaseSchema,
    CreateSchema,
    UpdateSchema,
    ResponseSchema,
)
from src.domains.content.enums import QuestionType, DifficultyLevel, QuestionStatus


class QuestionTagBase(BaseSchema):
    """Base question tag schema"""

    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class QuestionTagCreate(QuestionTagBase, CreateSchema):
    """Schema for creating question tag"""

    pass


class QuestionTagUpdate(UpdateSchema):
    """Schema for updating question tag"""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class QuestionTagResponse(QuestionTagBase, ResponseSchema):
    """Schema for question tag response"""

    questions_count: int = 0


class QuestionOptionBase(BaseSchema):
    """Base question option schema"""

    option_text: str = Field(..., min_length=1)
    option_order: int = Field(..., ge=0)
    is_correct: bool = False
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    match_pair_id: Optional[str] = Field(None, max_length=50)
    correct_order: Optional[int] = Field(None, ge=0)


class QuestionOptionCreate(QuestionOptionBase, CreateSchema):
    """Schema for creating question option"""

    pass


class QuestionOptionUpdate(UpdateSchema):
    """Schema for updating question option"""

    option_text: Optional[str] = Field(None, min_length=1)
    option_order: Optional[int] = Field(None, ge=0)
    is_correct: Optional[bool] = None
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    match_pair_id: Optional[str] = Field(None, max_length=50)
    correct_order: Optional[int] = Field(None, ge=0)


class QuestionOptionResponse(QuestionOptionBase, ResponseSchema):
    """Schema for question option response"""

    question_id: UUID


class QuestionOptionPublicResponse(BaseSchema):
    """Public question option response (without correct answers)"""

    id: UUID
    option_text: str
    option_order: int
    image_url: Optional[str] = None
    match_pair_id: Optional[str] = None


class QuestionBase(BaseSchema):
    """Base question schema"""

    subject_id: UUID
    topic_id: UUID
    question_text: str = Field(..., min_length=1)
    question_type: QuestionType
    difficulty_level: DifficultyLevel
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    points: int = Field(default=1, ge=1, le=100)
    time_limit_seconds: Optional[int] = Field(None, ge=0, le=3600)


class QuestionCreate(QuestionBase, CreateSchema):
    """Schema for creating question"""

    options: List[QuestionOptionCreate] = Field(..., min_items=2)
    tag_ids: Optional[List[UUID]] = Field(default_factory=list)

    @field_validator("options")
    @classmethod
    def validate_options(cls, v, info):
        """Validate options based on question type"""
        question_type = info.data.get("question_type")

        # At least one correct answer
        if not any(opt.is_correct for opt in v):
            raise PydanticCustomError(
                "option_count", "At least one option must be marked as correct"
            )

        # Type-specific validation
        if question_type == QuestionType.TRUE_FALSE:
            if len(v) != 2:
                raise PydanticCustomError(
                    "option_count", "True/False questions must have exactly 2 options"
                )

        elif question_type == QuestionType.MULTIPLE_CHOICE:
            if len(v) < 2:
                raise PydanticCustomError(
                    "option_count",
                    "Multiple choice questions must have at least 2 options",
                )
            if len(v) > 5:
                raise PydanticCustomError(
                    "option_count",
                    "Multiple choice questions cannot have more than 5 options",
                )

        elif question_type == QuestionType.MATCHING:
            # All options should have match_pair_id
            if not all(opt.match_pair_id for opt in v):
                raise PydanticCustomError(
                    "option_count",
                    "All matching question options must have match_pair_id",
                )

        elif question_type == QuestionType.ORDERING:
            # All options should have correct_order
            if not all(opt.correct_order is not None for opt in v):
                raise PydanticCustomError(
                    "order_error",
                    "All ordering question options must have correct_order",
                )

        return v


class QuestionUpdate(UpdateSchema):
    """Schema for updating question"""

    question_text: Optional[str] = Field(None, min_length=1)
    question_type: Optional[QuestionType] = None
    difficulty_level: Optional[DifficultyLevel] = None
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    points: Optional[int] = Field(None, ge=1, le=100)
    time_limit_seconds: Optional[int] = Field(None, ge=0, le=3600)
    status: Optional[QuestionStatus] = None
    tag_ids: Optional[List[UUID]] = None


class QuestionResponse(QuestionBase, ResponseSchema):
    """Schema for full question response (with answers)"""

    status: QuestionStatus
    times_used: int
    times_correct: int
    times_incorrect: int
    success_rate: float
    reviewed_by: Optional[UUID] = None
    approved_at: Optional[str] = None
    options: List[QuestionOptionResponse] = []
    tags: List[QuestionTagResponse] = []


class QuestionPublicResponse(BaseSchema):
    """Public question response (without answers for students taking exams)"""

    id: UUID
    subject_id: UUID
    topic_id: UUID
    question_text: str
    question_type: QuestionType
    difficulty_level: DifficultyLevel
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    points: int
    time_limit_seconds: Optional[int] = None
    options: List[QuestionOptionPublicResponse] = []
    tags: List[QuestionTagResponse] = []


class QuestionListResponse(BaseSchema):
    """Paginated question list response"""

    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int


class QuestionStatistics(BaseSchema):
    """Question statistics schema"""

    question_id: UUID
    times_used: int
    times_correct: int
    times_incorrect: int
    success_rate: float
    average_time_seconds: Optional[float] = None


class QuestionFilterParams(BaseSchema):
    """Question filter parameters"""

    subject_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None
    difficulty_level: Optional[DifficultyLevel] = None
    question_type: Optional[QuestionType] = None
    status: Optional[QuestionStatus] = None
    tag_ids: Optional[List[UUID]] = None
    search: Optional[str] = None


class BulkQuestionImportRequest(BaseSchema):
    """Bulk question import request"""

    subject_id: UUID
    topic_id: UUID
    questions: List[QuestionCreate]


class BulkQuestionImportResponse(BaseSchema):
    """Bulk question import response"""

    total: int
    success: int
    failed: int
    errors: List[dict] = []


class QuestionReviewRequest(BaseSchema):
    """Question review request"""

    approved: bool
    feedback: Optional[str] = None


# Forward reference updates
QuestionResponse.model_rebuild()
QuestionPublicResponse.model_rebuild()
