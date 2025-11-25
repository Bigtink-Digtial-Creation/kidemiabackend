from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr

from src.shared.schemas.base import (
    BaseSchema,
    UpdateSchema,
    ResponseSchema,
)
from src.domains.assessment.schemas.category import CategoryConfigBase


class StudentBase(BaseSchema):
    """Shared fields for Student"""

    category_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    guardian_id: Optional[UUID] = None
    guardian_email: Optional[EmailStr] = None
    target_exam_date: Optional[datetime] = None
    preparation_level: Optional[str] = None
    is_active: Optional[bool] = True
    is_suspended: Optional[bool] = False


class StudentUpdate(UpdateSchema):
    """Fields allowed to update a student"""

    student_code: Optional[str] = None
    registration_date: Optional[datetime] = None
    category_id: Optional[UUID] = None


class StudentResponse(StudentBase, ResponseSchema):
    user_id: UUID
    student_code: Optional[str] = None
    registration_date: datetime
    category: Optional[CategoryConfigBase] = None
