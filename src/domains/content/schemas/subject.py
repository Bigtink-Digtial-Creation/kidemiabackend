from typing import Optional, List
from uuid import UUID
from pydantic import Field

from src.shared.schemas.base import (
    BaseSchema,
    CreateSchema,
    UpdateSchema,
    ResponseSchema,
)


class CategoryMinimalResponse(BaseSchema):
    category_name: str
    display_name: str
    color_code: Optional[str] = None


class SubjectBase(BaseSchema):
    """Base subject schema"""

    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color_code: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    parent_id: Optional[UUID] = None
    category_id: Optional[UUID] = Field(
        None, description="Linked assessment category configuration"
    )
    order: int = Field(default=0, ge=0)
    is_active: bool = True
    is_featured: bool = False


class SubjectCreate(SubjectBase, CreateSchema):
    """Schema for creating a subject"""

    pass


class SubjectUpdate(UpdateSchema):
    """Schema for updating a subject"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color_code: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    parent_id: Optional[UUID] = None

    category_id: Optional[UUID] = None
    order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class SubjectResponse(SubjectBase, ResponseSchema):
    """Schema for subject response"""

    topics_count: int = 0
    questions_count: int = 0
    category: Optional[CategoryMinimalResponse] = None


class SubjectWithTopics(SubjectResponse):
    """Subject response with nested topics"""

    topics: List["TopicResponse"] = []


class SubjectListResponse(BaseSchema):
    """Paginated subject list response"""

    items: List[SubjectResponse]
    total: int
    page: int
    page_size: int


class TopicBase(BaseSchema):
    """Base topic schema"""

    subject_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    document_url: Optional[str] = None
    parent_id: Optional[UUID] = None
    order: int = Field(default=0, ge=0)
    estimated_time_minutes: Optional[int] = Field(None, ge=0)
    difficulty_level: Optional[str] = None
    is_active: bool = True


class TopicCreate(TopicBase, CreateSchema):
    """Schema for creating a topic"""

    pass


class TopicUpdate(UpdateSchema):
    """Schema for updating a topic"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    document_url: Optional[str] = None
    parent_id: Optional[UUID] = None
    order: Optional[int] = Field(None, ge=0)
    estimated_time_minutes: Optional[int] = Field(None, ge=0)
    difficulty_level: Optional[str] = None
    is_active: Optional[bool] = None


class TopicResponse(TopicBase, ResponseSchema):
    """Schema for topic response"""

    questions_count: int = 0


class TopicWithSubtopics(TopicResponse):
    """Topic response with nested subtopics"""

    subtopics: List["TopicResponse"] = []


class TopicListResponse(BaseSchema):
    """Paginated topic list response"""

    items: List[TopicResponse]
    total: int
    page: int
    page_size: int


# Forward reference updates
SubjectWithTopics.model_rebuild()
TopicWithSubtopics.model_rebuild()
