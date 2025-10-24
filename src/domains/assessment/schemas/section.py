from typing import Optional, List
from uuid import UUID
from pydantic import Field

from src.shared.schemas.base import (
    BaseSchema,
    CreateSchema,
    UpdateSchema,
    ResponseSchema,
)


class SectionBase(BaseSchema):
    """Base section schema"""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    order: int = Field(..., ge=0)
    time_limit_minutes: Optional[int] = Field(None, ge=0)
    shuffle_questions: bool = True
    is_optional: bool = False


class SectionCreate(SectionBase, CreateSchema):
    """Schema for creating section"""

    question_ids: List[UUID] = Field(default_factory=list)


class SectionUpdate(UpdateSchema):
    """Schema for updating section"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    order: Optional[int] = Field(None, ge=0)
    time_limit_minutes: Optional[int] = Field(None, ge=0)
    shuffle_questions: Optional[bool] = None
    is_optional: Optional[bool] = None


class SectionResponse(SectionBase, ResponseSchema):
    """Schema for section response"""

    assessment_id: UUID
    total_questions: int
    total_points: int
