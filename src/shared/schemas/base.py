from datetime import datetime
from typing import Optional, Generic, TypeVar, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
        json_schema_extra={"example": {}},
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""

    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema with ID field"""

    id: UUID


class BaseDBSchema(IDSchema, TimestampSchema):
    """Base schema for database models (with ID and timestamps)"""

    pass


class CreateSchema(BaseSchema):
    """Base schema for create operations"""

    pass


class UpdateSchema(BaseSchema):
    """Base schema for update operations"""

    pass


class InDBSchema(BaseDBSchema):
    """Base schema for database representation"""

    pass


class ResponseSchema(BaseDBSchema):
    """Base schema for API responses"""

    pass


DataT = TypeVar("DataT")


class PaginationParams(BaseSchema):
    """Pagination parameters"""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def skip(self) -> int:
        """Calculate skip value for database query"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit value for database query"""
        return self.page_size


class PaginatedResponse(BaseSchema, Generic[DataT]):
    """Generic paginated response"""

    items: List[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def create(
        cls, items: List[DataT], total: int, page: int, page_size: int
    ) -> "PaginatedResponse[DataT]":
        """Create paginated response"""
        total_pages = (total + page_size - 1) // page_size

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class SuccessResponse(BaseSchema):
    """Standard success response"""

    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseSchema):
    """Standard error response"""

    success: bool = False
    error_code: str
    message: str
    details: Optional[dict] = None


class MessageResponse(BaseSchema):
    """Simple message response"""

    message: str


class BaseFilterSchema(BaseSchema):
    """Base schema for filtering"""

    search: Optional[str] = Field(default=None, description="Search query")
    sort_by: Optional[str] = Field(default="created_at", description="Field to sort by")
    sort_order: Optional[str] = Field(
        default="desc", description="Sort order (asc/desc)"
    )


class DateRangeFilter(BaseSchema):
    """Date range filter"""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ==================== BULK OPERATION SCHEMAS ====================


class BulkCreateResponse(BaseSchema):
    """Response for bulk create operations"""

    created_count: int
    failed_count: int
    created_ids: List[UUID]
    errors: Optional[List[dict]] = None


class BulkUpdateResponse(BaseSchema):
    """Response for bulk update operations"""

    updated_count: int
    failed_count: int
    updated_ids: List[UUID]
    errors: Optional[List[dict]] = None


class BulkDeleteResponse(BaseSchema):
    """Response for bulk delete operations"""

    deleted_count: int
    failed_count: int
    deleted_ids: List[UUID]
    errors: Optional[List[dict]] = None


# ==================== FILE UPLOAD SCHEMAS ====================


class FileUploadResponse(BaseSchema):
    """Response for file upload"""

    file_id: UUID
    filename: str
    file_size: int
    file_type: str
    url: str
    uploaded_at: datetime


class HealthCheckResponse(BaseSchema):
    """Health check response"""

    status: str
    version: str
    database: str
    cache: str
    timestamp: datetime
