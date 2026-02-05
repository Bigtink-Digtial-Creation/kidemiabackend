from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional


class AssessmentCompletedPayload(BaseModel):
    assessment_id: UUID
    category_id: Optional[UUID]
    score: int
    total_questions: int
    time_taken_seconds: int
    completed_at: datetime


class AssessmentResultPayload(BaseModel):
    """Payload for assessment result event"""

    user_id: UUID
    assessment_title: str
    score: float
    total_questions: int
    passed: bool


class WardRemovePayload(BaseModel):
    email: EmailStr
    relationship_type: str
    guardian_email: str
    date: datetime


class WardAddPayload(WardRemovePayload):
    pass


class CategoryChangePayload(BaseModel):
    guardian_email: EmailStr
    student_name: str
    old_category: str
    new_category: str
    reason: Optional[str]


class CategoryChangeApproved(BaseModel):
    state: str
    ward_email: EmailStr
    old_category: str
    new_category: str


class ChallengeAssigned(BaseModel):
    ward_user_id: UUID
    assessment_id: UUID
    guardian_id: UUID
    due_date: Optional[datetime]
    instructions: Optional[str]


class ChallengeCompleted(BaseModel):
    guardian_user_id: UUID
    ward_user_id: UUID
    assessment_id: UUID
    attempt_id: UUID
    score: float
    percentage: float
    passed: bool = False
    auto_submitted: bool = False


class UserRegisterPayload(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    user_type: str


class EmailVerificationPayload(BaseModel):
    user_email: EmailStr
    verify_token: str
    client_type: str


class SecurityAlertPayload(BaseModel):
    email: EmailStr
    full_name: str
    action_type: str
    details: str
    user_type: str
