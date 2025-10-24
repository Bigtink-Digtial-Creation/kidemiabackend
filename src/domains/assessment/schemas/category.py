from typing import Optional
from pydantic import Field

from src.shared.schemas.base import (
    BaseSchema,
    CreateSchema,
    UpdateSchema,
    ResponseSchema,
)


class CategoryConfigBase(BaseSchema):
    """Base category configuration schema"""

    category_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color_code: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    banner_url: Optional[str] = None
    is_active: bool = True
    requires_payment: bool = False
    order: int = Field(default=0, ge=0)
    exam_body: Optional[str] = Field(None, max_length=200)
    target_level: Optional[str] = Field(None, max_length=100)


class CategoryConfigCreate(CategoryConfigBase, CreateSchema):
    """Schema for creating category configuration"""

    pass


class CategoryConfigUpdate(UpdateSchema):
    """Schema for updating category configuration"""

    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color_code: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    banner_url: Optional[str] = None
    is_active: Optional[bool] = None
    requires_payment: Optional[bool] = None
    order: Optional[int] = Field(None, ge=0)
    exam_body: Optional[str] = Field(None, max_length=200)
    target_level: Optional[str] = Field(None, max_length=100)


class CategoryConfigResponse(CategoryConfigBase, ResponseSchema):
    """Schema for category configuration response"""

    assessments_count: int = 0
