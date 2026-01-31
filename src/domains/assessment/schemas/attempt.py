from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator
from decimal import Decimal

from src.shared.schemas.base import (
    BaseSchema,
)

from src.domains.assessment.enums import AttemptStatus

from src.domains.assessment.schemas.answer import AnswerResponse
from src.domains.assessment.schemas.assessment import (
    AssessmentSummaryResponseForAttempt,
)
from pydantic import EmailStr


class UserResponseForAttempt(BaseSchema):
    """user schema for attempt"""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)


class AttemptResponse(BaseSchema):
    """Raw assessment attempt state (with assessment attached)"""

    assessment_id: UUID
    attempt_id: UUID = Field(alias="id")
    assessment: AssessmentSummaryResponseForAttempt
    attempt_number: int
    status: AttemptStatus
    grading_status: Optional[str]
    started_at: Optional[str]
    submitted_at: Optional[str]
    must_submit_by: Optional[str]
    time_spent_seconds: int
    time_remaining_seconds: Optional[int]
    total_questions: int
    questions_attempted: int
    questions_unanswered: int
    questions_flagged: int
    correct_answers: int
    incorrect_answers: int
    partially_correct: int
    score: Decimal
    percentage: Decimal
    points_earned: Decimal
    points_possible: Decimal
    passed: bool
    grade: Optional[str]
    rank: Optional[int]
    percentile: Optional[Decimal]
    proctoring_session_id: Optional[str]
    violation_count: int
    flagged_suspicious: bool
    feedback: Optional[str]
    certificate_issued: bool
    certificate_url: Optional[str]
    user: Optional[UserResponseForAttempt] = None


class AttemptStartRequest(BaseSchema):
    """Request to start an assessment attempt"""

    access_code: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None


class AttemptStartResponse(BaseSchema):
    """Response when starting an attempt"""

    attempt_id: UUID
    assessment_id: UUID
    attempt_number: int
    duration_minutes: int
    must_submit_by: str
    total_questions: int
    instructions: Optional[str] = None
    proctoring_required: bool = False
    proctoring_config: Optional[Dict[str, Any]] = None


class SaveAnswerRequest(BaseSchema):
    """Request to save an answer"""

    question_id: UUID
    selected_option_ids: Optional[List[UUID]] = None
    text_answer: Optional[str] = None
    matching_pairs: Optional[Dict[str, str]] = None
    ordered_items: Optional[List[str]] = None
    flagged_for_review: bool = False

    @field_validator("selected_option_ids", mode="after")
    def convert_uuid_list_to_str(cls, v):
        if v:
            # Convert all UUIDs in the list to strings for JSONB storage
            return [str(uuid_val) for uuid_val in v]
        return v


class SubmitAttemptRequest(BaseSchema):
    """Request to submit an attempt"""

    confirm_submission: bool = True


class AttemptProgressResponse(BaseSchema):
    """Response showing attempt progress"""

    attempt_id: UUID
    status: AttemptStatus
    time_spent_seconds: int
    time_remaining_seconds: Optional[int]
    total_questions: int
    questions_attempted: int
    questions_unanswered: int
    questions_flagged: int
    can_submit: bool


class AttemptResultResponse(BaseSchema):
    """Response showing attempt results"""

    attempt_id: UUID = Field(alias="id")
    assessment_id: UUID
    attempt_number: int
    status: AttemptStatus
    submitted_at: Optional[str]
    score: Decimal
    percentage: Decimal
    points_earned: Decimal
    points_possible: Decimal
    passed: bool
    grade: Optional[str]
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    partially_correct: int
    rank: Optional[int]
    percentile: Optional[Decimal]
    time_spent_seconds: int
    feedback: Optional[str]
    certificate_issued: bool
    certificate_url: Optional[str]


class AttemptDetailResponse(AttemptResultResponse):
    """Detailed attempt response with answers"""

    answers: List["AnswerResponse"] = []
    violations: Optional[List[Dict[str, Any]]] = None


class AttemptListResponse(BaseSchema):
    """Paginated attempt list"""

    items: List[AttemptResultResponse]
    total: int
    page: int
    page_size: int


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


# Forward reference updates
AttemptDetailResponse.model_rebuild()
