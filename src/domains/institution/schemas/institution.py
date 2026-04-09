import re
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List
from pydantic import (
    BaseModel,
    EmailStr,
    field_validator,
    model_validator,
    ConfigDict,
    Field,
)
from src.domains.auth.schemas.student import StudentResponse

from src.domains.assessment.enums import ResultDisplayMode


class InstitutionStatusUpdate(BaseModel):
    """System admin toggles institution access on/off."""

    is_public: bool
    reason: Optional[str] = None


class InstitutionTierUpdate(BaseModel):
    tier: str  # basic | premium | enterprise
    max_students: Optional[int] = None


class InstitutionOnboardRequest(BaseModel):
    """
    Full payload for manually onboarding one institution.
    The admin fills this form in the system dashboard.
    """

    # Core identity
    name: str
    code: str
    description: Optional[str] = None
    motto: Optional[str] = None
    established_date: Optional[date] = None

    # Contact
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Nigeria"

    # Branding
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    # Owner / admin account
    owner_email: EmailStr
    owner_first_name: str
    owner_last_name: str
    owner_phone: Optional[str] = None

    # Access settings (admin-controlled)
    tier: str = "basic"
    max_students: Optional[int] = None
    is_verified: bool = False
    is_public: bool = True

    # Whether to email the owner their credentials immediately
    send_welcome_email: bool = True

    @field_validator("code")
    @classmethod
    def code_format(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9\-]{3,20}$", v):
            raise ValueError("Code must be 3–20 chars, letters/digits/hyphens only")
        return v

    @field_validator("tier")
    @classmethod
    def tier_valid(cls, v: str) -> str:
        if v not in {"basic", "premium", "enterprise"}:
            raise ValueError("Tier must be one of: basic, premium, enterprise")
        return v


class InstitutionOnboardResponse(BaseModel):
    institution_id: UUID
    name: str
    code: str
    owner_user_id: UUID
    owner_email: str
    tier: str
    is_public: bool
    temp_password_sent: bool  # True if welcome email was dispatched
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
#  Bulk Institution Onboarding (CSV)
# ─────────────────────────────────────────────


class BulkInstitutionRow(BaseModel):
    """One row from the institution bulk-upload CSV."""

    name: str
    code: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Nigeria"
    tier: str = "basic"
    max_students: Optional[int] = None
    owner_email: str
    owner_first_name: str
    owner_last_name: str
    owner_phone: Optional[str] = None


class BulkInstitutionOnboardResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[dict]  # [{row, name, code, reason}]
    created_institution_ids: List[UUID]


# ─────────────────────────────────────────────
#  Institution List / Detail (Admin view)
# ─────────────────────────────────────────────


class InstitutionAdminListItem(BaseModel):
    id: UUID
    name: str
    code: str
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    tier: str
    is_public: bool
    is_verified: bool
    total_students: int
    total_teachers: int = 0
    owner_email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class InstitutionAdminDetail(InstitutionAdminListItem):
    description: Optional[str]
    motto: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    address: Optional[str]
    logo_url: Optional[str]
    max_students: Optional[int]
    total_classrooms: int = 0
    total_assessments: int
    established_date: Optional[date]

    class Config:
        from_attributes = True


class UserRead(BaseModel):
    id: UUID
    full_name: str
    email: str
    model_config = ConfigDict(from_attributes=True)


class TeacherRead(BaseModel):
    id: UUID
    teacher_code: Optional[str]
    specialization: Optional[str]
    user: UserRead

    class Config:
        from_attributes = True


class ClassroomCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    capacity: Optional[int] = None


class ClassroomUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    capacity: Optional[int] = None
    class_teacher_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class ClassroomResponse(BaseModel):
    id: UUID
    institution_id: UUID
    name: str
    code: Optional[str]
    level: Optional[str]
    section: Optional[str]
    academic_year: Optional[str]
    capacity: Optional[int]
    is_active: bool
    student_count: int = 0
    class_teacher_id: Optional[UUID]
    class_teacher: Optional[TeacherRead]
    created_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def set_student_count(cls, data):
        if hasattr(data, "students"):
            data.student_count = len(data.students)
        return data


class SingleStudentCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str | None = None
    date_of_birth: str | None = None
    guardian_email: EmailStr | None = None
    classroom_code: str | None = None
    send_invite: bool = True


class BulkStudentRow(BaseModel):
    """One row from the CSV upload."""

    first_name: str
    last_name: str
    email: EmailStr
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    guardian_email: Optional[str] = None
    classroom_code: Optional[str] = None  # matched to existing classroom
    student_code: Optional[str] = None


class BulkOnboardRequest(BaseModel):
    students: List[BulkStudentRow]
    send_invite_email: bool = True
    default_classroom_id: Optional[UUID] = None


class BulkOnboardResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[dict]  # [{row: int, email: str, reason: str}]
    created_student_ids: List[UUID]


class LinkStudent(BaseModel):
    student_id: UUID
    classroom_id: UUID


class MoveStudentRequest(BaseModel):
    student_id: UUID
    target_classroom_id: UUID


class BulkMoveStudentsRequest(BaseModel):
    student_ids: List[UUID]
    target_classroom_id: UUID


class StudentMember(BaseModel):
    id: UUID
    student_code: str | None = None
    user_id: UUID

    class Config:
        from_attributes = True


class StudentGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    classroom_id: UUID
    student_ids: Optional[List[UUID]] = []


class StudentGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    student_ids: Optional[List[UUID]] = None


class StudentGroupResponse(BaseModel):
    id: UUID
    classroom_id: UUID
    institution_id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    student_count: int = 0
    students: List[StudentMember] = []
    created_at: datetime

    @classmethod
    def from_orm_with_count(cls, group: "StudentGroup") -> "StudentGroupResponse":
        return cls(
            id=group.id,
            classroom_id=group.classroom_id,
            institution_id=group.institution_id,
            name=group.name,
            description=group.description,
            is_active=group.is_active,
            student_count=len(group.students),
            students=[StudentMember.model_validate(s) for s in group.students],
            created_at=group.created_at,
        )

    class Config:
        from_attributes = True


class ClassroomMinimal(BaseModel):
    id: UUID
    name: str
    level: Optional[str]
    section: Optional[str]

    class Config:
        from_attributes = True


class StudentWithClassroomResponse(StudentResponse):
    """
    Extends the rich StudentResponse to include details
    about the classroom they belong to.
    """

    path: Optional[str] = None
    user: UserRead
    classroom: Optional[ClassroomMinimal] = None


class TeacherInviteRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    specialization: Optional[str] = None
    bio: Optional[str] = None
    classroom_ids: Optional[List[UUID]] = []
    subject: Optional[str] = None


# schemas/institution.py


class TeacherResponse(BaseModel):
    id: UUID
    user_id: UUID
    institution_id: UUID
    teacher_code: Optional[str]
    full_name: Optional[str] = None
    email: Optional[str] = None
    specialization: Optional[str] = None
    is_active: bool
    is_suspended: bool
    joined_date: Optional[datetime] = None
    taught_classes_count: int = 0
    taught_classrooms: list[ClassroomMinimal] = []
    homeroom_class: Optional[ClassroomMinimal] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_full(cls, t: "InstitutionTeacher") -> "TeacherResponse":
        return cls(
            id=t.id,
            user_id=t.user_id,
            institution_id=t.institution_id,
            teacher_code=t.teacher_code,
            full_name=f"{t.user.first_name} {t.user.last_name}".strip()
            if t.user
            else None,
            email=t.user.email if t.user else None,
            specialization=t.specialization,
            is_active=t.is_active,
            is_suspended=t.is_suspended,
            joined_date=t.joined_date,
            taught_classrooms=[
                ClassroomMinimal.model_validate(c) for c in (t.taught_classrooms or [])
            ],
            taught_classes_count=len(t.taught_classrooms or []),
            homeroom_class=ClassroomMinimal.model_validate(t.homeroom_class)
            if t.homeroom_class
            else None,
        )


class ClassroomMinimal(BaseModel):
    id: UUID
    name: str
    level: Optional[str] = None
    section: Optional[str] = None
    is_active: bool = True
    student_count: int = 0

    class Config:
        from_attributes = True


class AssignAssessmentRequest(BaseModel):
    assessment_id: UUID
    # Scope — at least one must be set
    classroom_id: Optional[UUID] = None
    student_group_id: Optional[UUID] = None
    student_ids: Optional[List[UUID]] = None  # individual students

    due_date: Optional[datetime] = None
    available_from: Optional[datetime] = None
    instructions: Optional[str] = None


class ClassroomAnalytics(BaseModel):
    classroom_id: UUID
    classroom_name: str
    total_students: int
    active_students: int
    assessments_assigned: int
    avg_score: Optional[float]
    completion_rate: Optional[float]


class InstitutionDashboardStats(BaseModel):
    total_students: int
    active_students: int
    total_teachers: int
    total_classrooms: int
    total_assessments_assigned: int
    avg_score_across_institution: Optional[float]
    recent_activity: List[dict]
    recent_students: List[dict]


class InstitutionAssessmentCreate(BaseModel):
    # Content
    subject_id: UUID
    topic_ids: List[UUID]
    number_of_questions: int = Field(ge=5, le=100)
    instructions: Optional[str] = None

    # Timing
    duration_minutes: int = Field(ge=10, le=300)
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None

    # Behavior
    passing_percentage: Decimal = Decimal("50.00")
    max_attempts: int = Field(default=1, ge=1, le=5)
    shuffle_questions: bool = True
    shuffle_options: bool = True
    allow_question_navigation: bool = True
    allow_backward_navigation: bool = True
    result_display_mode: ResultDisplayMode = ResultDisplayMode.IMMEDIATE
    show_correct_answers: bool = True
    show_explanations: bool = True

    # Proctoring
    proctoring_enabled: bool = False
    require_webcam: bool = False
    fullscreen_required: bool = True
    detect_tab_switching: bool = True
    max_tab_switches: int = 3

    # Auto-submit
    auto_submit_on_time_up: bool = True

    # Draft or publish immediately
    publish: bool = True


class InstitutionAssessmentResponse(BaseModel):
    id: UUID
    title: str
    subject_name: str
    total_questions: int
    duration_minutes: int
    status: str
    created_at: datetime
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    assignment_count: int = 0

    class Config:
        from_attributes = True


class InstitutionProfileResponse(BaseModel):
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    motto: Optional[str] = None
    established_date: Optional[date] = None
    academic_session: Optional[str] = None

    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None

    is_verified: bool = False
    is_public: bool = True
    tier: Optional[str] = None

    total_students: int = 0
    total_assessments: int = 0
    max_students: Optional[int] = None

    created_at: datetime

    class Config:
        from_attributes = True


class InstitutionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    motto: Optional[str] = None
    established_date: Optional[date] = None
    academic_session: Optional[str] = None  # ← added

    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None

    is_public: Optional[bool] = None


# Add to institution/schemas/institution.py


class StudentAttemptStatus(BaseModel):
    student_id: UUID
    student_name: str
    student_code: Optional[str]
    classroom_name: Optional[str]
    status: str  # "not_started" | "in_progress" | "submitted" | "graded" | "overdue"
    attempt_count: int
    best_score: Optional[float]
    best_percentage: Optional[float]
    passed: Optional[bool]
    grade: Optional[str]
    started_at: Optional[datetime]
    submitted_at: Optional[datetime]
    time_spent_seconds: Optional[int]
    assigned_via: str  # "classroom" | "group" | "individual"


class AssessmentDetailResponse(BaseModel):
    # Assessment info
    assessment_id: UUID
    title: str
    subject_name: Optional[str]
    total_questions: int
    duration_minutes: int
    status: str
    created_at: datetime
    available_from: Optional[datetime]
    available_until: Optional[datetime]

    # Aggregate stats (from existing get_statistics)
    total_assigned: int
    total_started: int
    total_submitted: int
    total_graded: int
    completion_rate: float
    pass_rate: float
    average_score: float
    highest_score: float
    lowest_score: float
    score_distribution: dict

    # Per-student breakdown
    students: list[StudentAttemptStatus]
