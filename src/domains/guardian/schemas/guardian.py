from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class GuardianBase(BaseModel):
    relationship_type: Optional[str] = Field(None, max_length=50)
    receive_progress_reports: bool = True
    receive_performance_alerts: bool = True
    receive_payment_reminders: bool = True

    model_config = ConfigDict(from_attributes=True)


class GuardianCreate(GuardianBase):
    """Schema for creating a guardian"""

    pass


class GuardianUpdate(BaseModel):
    """Schema for updating guardian"""

    relationship_type: Optional[str] = None
    receive_progress_reports: Optional[bool] = None
    receive_performance_alerts: Optional[bool] = None
    receive_payment_reminders: Optional[bool] = None
    is_verified: Optional[bool] = None


class AddWardRequest(BaseModel):
    """Request to add a ward via email"""

    ward_email: EmailStr = Field(..., description="Email of the student to add as ward")
    relationship_type: Optional[str] = Field(
        None, description="Relationship to ward (parent, guardian, etc.)"
    )


class WardResponse(BaseModel):
    """Response for a ward"""

    id: UUID
    user_id: UUID
    student_code: Optional[str]
    full_name: str
    email: str
    category_name: Optional[str] = None
    category_id: Optional[UUID] = None
    is_active: bool
    is_suspended: bool
    avg_exam_score: Optional[float] = None
    avg_test_score: Optional[float] = None
    total_assessments: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class RemoveWardRequest(BaseModel):
    """Request to remove a ward"""

    ward_id: UUID = Field(..., description="ID of the student to remove")
    reason: Optional[str] = Field(None, description="Reason for removal")


class CategoryChangeRequest(BaseModel):
    """Request to change ward category"""

    ward_id: UUID
    new_category_id: UUID
    reason: Optional[str] = None


class CategoryChangeResponse(BaseModel):
    """Response for category change request"""

    id: UUID
    ward_id: UUID
    guardian_id: UUID
    old_category_id: Optional[UUID]
    new_category_id: UUID
    status: str  # pending, approved, rejected, cancelled
    reason: Optional[str]
    requested_at: datetime
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]

    # Additional display fields
    ward_name: Optional[str] = None
    old_category_name: Optional[str] = None
    new_category_name: Optional[str] = None

    class Config:
        from_attributes = True


class ApproveCategoryChangeRequest(BaseModel):
    """Request to approve/reject category change"""

    request_id: UUID
    approve: bool
    admin_notes: Optional[str] = None


class GuardianResponse(GuardianBase):
    """Response schema for guardian"""

    id: UUID
    user_id: UUID
    guardian_code: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    # User details
    full_name: Optional[str] = None
    email: Optional[str] = None

    # Aggregated stats
    total_wards: int = 0
    active_wards: int = 0

    class Config:
        from_attributes = True


class GuardianDetailResponse(GuardianResponse):
    """Detailed guardian response with wards"""

    wards: List[WardResponse] = []


# ============= Ward Reports =============


class WardSubjectPerformance(BaseModel):
    """Performance in a specific subject"""

    subject_id: UUID
    subject_name: str
    total_assessments: int
    avg_score: float
    highest_score: float
    lowest_score: float
    completion_rate: float


class WardPerformanceReport(BaseModel):
    """Comprehensive performance report for a ward"""

    ward_id: UUID
    ward_name: str
    category_name: Optional[str]

    # Overall stats
    total_assessments: int
    completed_assessments: int
    pending_assessments: int
    avg_overall_score: float

    # Subject breakdown
    subject_performance: List[WardSubjectPerformance]

    # Trends
    performance_trend: str  # improving, declining, stable
    strengths: List[str]
    weaknesses: List[str]

    # Time-based
    last_assessment_date: Optional[datetime]
    generated_at: datetime


class ComprehensiveGuardianReport(BaseModel):
    """Comprehensive report for all wards"""

    guardian_id: UUID
    total_wards: int
    active_wards: int

    # Aggregated performance
    overall_avg_score: float
    total_assessments_assigned: int
    total_assessments_completed: int

    # Individual ward summaries
    ward_summaries: List[WardPerformanceReport]

    # Comparative insights
    top_performing_ward: Optional[str]
    needs_attention: List[str]

    generated_at: datetime


# ============= Assessment Assignment =============


class AssignAssessmentRequest(BaseModel):
    """Request to assign assessment to ward(s)"""

    assessment_id: UUID
    ward_ids: List[UUID] = Field(..., min_items=1)
    due_date: Optional[datetime] = None
    instructions: Optional[str] = None


class AssignmentResponse(BaseModel):
    """Response for assessment assignment"""

    id: UUID
    assessment_id: UUID
    assessment_title: str
    ward_id: UUID
    ward_name: str
    assigned_by: UUID
    due_date: Optional[datetime]
    status: str  # assigned, started, completed
    assigned_at: datetime

    class Config:
        from_attributes = True


class GuardianListResponse(BaseModel):
    """Paginated list of guardians"""

    items: List[GuardianResponse]
    total: int
    page: int
    page_size: int


class WardListResponse(BaseModel):
    """Paginated list of wards"""

    items: List[WardResponse]
    total: int
    page: int
    page_size: int


class CategoryChangeListResponse(BaseModel):
    """Paginated list of category change requests"""

    items: List[CategoryChangeResponse]
    total: int
    page: int
    page_size: int


class AssessmentAssignmentResponse(BaseModel):
    """Response after creating and assigning assessment"""

    assessment_id: UUID
    assessment_title: str
    total_questions: int
    duration_minutes: int
    assigned_to: List[UUID]
    assignments: List[AssignmentResponse]
    message: str


# Enhanced version of CreateAssessmentForWardsRequest with ALL options


class CreateAssessmentForWardsRequest(BaseModel):
    """Request to create fully-featured assessment and assign to wards"""

    # Content Selection
    subject_id: UUID
    topic_ids: List[UUID] = Field(..., min_items=1, max_items=20)
    number_of_questions: int = Field(10, ge=5, le=100)

    # Timing
    duration_minutes: int = Field(30, ge=10, le=300)
    due_date: Optional[datetime] = None
    available_from: Optional[datetime] = None

    # Assignment Details
    ward_ids: List[UUID] = Field(..., min_items=1, description="Wards to assign to")
    instructions: Optional[str] = Field(None, max_length=1000)

    # Assessment Configuration
    passing_percentage: Optional[float] = Field(50.0, ge=0, le=100)
    max_attempts: Optional[int] = Field(1, ge=1, le=5)

    # Question Behavior
    shuffle_questions: bool = True
    shuffle_options: bool = True
    allow_question_navigation: bool = True
    allow_review: bool = True  # Allow backward navigation

    # Results Display
    result_display_mode: Optional[str] = Field(
        "after_due_date", description="immediate, after_submission, after_due_date"
    )
    show_correct_answers: Optional[bool] = False
    show_explanations: Optional[bool] = False

    # Proctoring Features (IMPORTANT!)
    enable_proctoring: Optional[bool] = True
    require_webcam: Optional[bool] = True
    fullscreen_required: Optional[bool] = True
    detect_tab_switching: Optional[bool] = True
    max_tab_switches: Optional[int] = Field(3, ge=0, le=10)

    # Auto-submit
    auto_submit_on_time_up: Optional[bool] = Field(
        True, description="Automatically submit when time expires"
    )


class WardAssignmentResponse(BaseModel):
    """Ward's view of assigned assessment"""

    id: UUID
    assessment_id: UUID
    assessment_title: str
    subject_name: str
    topic_count: int
    total_questions: int
    duration_minutes: int

    # Assignment details
    assigned_by_name: str  # Guardian's name
    assigned_at: datetime
    due_date: Optional[datetime]
    instructions: Optional[str]

    # Status
    status: str  # assigned, started, completed, overdue
    attempt_count: int
    max_attempts: int

    # Proctoring info
    requires_webcam: bool
    requires_fullscreen: bool
    detects_tab_switching: bool

    # Progress
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    score: Optional[float]
    passed: Optional[bool]


class GuardianAssignmentMonitorResponse(BaseModel):
    """Guardian's view of assignment with monitoring data"""

    id: UUID
    assessment_id: UUID
    assessment_title: str
    ward_id: UUID
    ward_name: str

    # Assignment details
    assigned_at: datetime
    due_date: Optional[datetime]
    status: str

    # Attempt tracking
    attempt_count: int
    max_attempts: int
    attempts_remaining: int

    # Latest attempt info
    last_attempt_date: Optional[datetime]
    last_attempt_score: Optional[float]
    last_attempt_time_spent: Optional[int]  # seconds

    # Proctoring violations (if any)
    tab_switches: Optional[int]
    webcam_violations: Optional[int]
    fullscreen_exits: Optional[int]

    # Performance
    score: Optional[float]
    percentage: Optional[float]
    passed: Optional[bool]
    completed_at: Optional[datetime]


class AssignmentNotificationData(BaseModel):
    """Data for assignment notifications"""

    notification_type: str  # assigned, completed, overdue
    assessment_title: str
    ward_name: Optional[str]
    guardian_name: Optional[str]
    due_date: Optional[datetime]
    score: Optional[float]
    passed: Optional[bool]
