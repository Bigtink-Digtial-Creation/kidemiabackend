from pydantic import Field
from typing import Optional
from datetime import datetime
from src.shared.schemas.base import IDSchema, BaseSchema


class PlatformSettingBase(BaseSchema):
    key: str = Field(..., description="Unique setting key")
    value: Optional[str] = Field(None, description="Setting value")
    category: str = Field(..., description="Setting category")
    description: Optional[str] = Field(None, description="Setting description")
    is_secret: bool = Field(False, description="Whether this is sensitive data")
    is_active: bool = Field(True, description="Whether this setting is active")


class PlatformSettingCreate(PlatformSettingBase):
    pass


class PlatformSettingUpdate(BaseSchema):
    value: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PlatformSettingResponse(IDSchema, PlatformSettingBase):
    created_at: datetime
    updated_at: Optional[datetime]


class PlatformSettingPublic(IDSchema):
    """Public response that masks secret values"""

    key: str
    value: Optional[str]  # Will be masked if is_secret=True
    category: str
    description: Optional[str]
    is_secret: bool
    is_active: bool
    created_at: datetime
