from typing import Optional, List, Dict
from uuid import UUID
from pydantic import Field, field_validator
from decimal import Decimal
from pydantic_core import PydanticCustomError
from src.shared.schemas.base import (
    BaseSchema,
    ResponseSchema,
)


class AnswerBase(BaseSchema):
    """Base answer schema"""

    question_id: UUID
    selected_option_ids: Optional[List[UUID]] = None
    text_answer: Optional[str] = None
    matching_pairs: Optional[Dict[str, str]] = None
    ordered_items: Optional[List[str]] = None


class AnswerResponse(AnswerBase, ResponseSchema):
    """Schema for answer response"""

    attempt_id: UUID
    section_id: Optional[UUID] = None

    # Grading
    is_correct: Optional[bool] = None
    is_partially_correct: bool = False
    points_earned: Decimal
    points_possible: Decimal

    # Manual grading
    requires_manual_grading: bool
    manually_graded: bool
    manual_feedback: Optional[str] = None

    # Metadata
    time_spent_seconds: int
    flagged_for_review: bool


class AnswerWithSolutionResponse(AnswerResponse):
    """Answer response with correct answer and explanation"""

    correct_option_ids: Optional[List[UUID]] = None
    correct_text_answer: Optional[str] = None
    explanation: Optional[str] = None


class ManualGradeRequest(BaseSchema):
    """Request to manually grade an answer"""

    points_earned: Decimal = Field(..., ge=0)
    feedback: Optional[str] = None

    @field_validator("points_earned")
    @classmethod
    def validate_points(cls, v):
        """Ensure points are not negative"""
        if v < 0:
            raise PydanticCustomError("value_error", "Points earned cannot be negative")
        return v


AnswerResponse.model_rebuild()
AnswerWithSolutionResponse.model_rebuild()
