from uuid import UUID
from typing import List, Optional
from fastapi import Response, status
from fastapi.responses import Response as FastAPIResponse
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.config.database import get_async_db, get_db
from src.core.security import (
    InstitutionContext,
    get_current_institution_user,
)

from src.domains.institution.services.classroom_service import ClassroomService
from src.domains.institution.services.institution_analytic_service import (
    InstitutionAnalyticsService,
)
from src.domains.institution.services.institution_assessment_service import (
    InstitutionAssessmentService,
)
from src.domains.institution.services.student_group_service import StudentGroupService
from src.domains.institution.services.teacher_service import TeacherService
from src.domains.institution.services.onboarding_service import (
    BulkStudentOnboardingService,
)

from src.domains.institution.models.institution import Institution
from src.domains.institution.schemas.institution import (
    ClassroomCreate,
    ClassroomUpdate,
    ClassroomResponse,
    BulkOnboardResult,
    MoveStudentRequest,
    BulkMoveStudentsRequest,
    StudentGroupCreate,
    StudentGroupUpdate,
    StudentGroupResponse,
    TeacherInviteRequest,
    TeacherResponse,
    AssignAssessmentRequest,
    InstitutionDashboardStats,
    StudentWithClassroomResponse,
    InstitutionAssessmentResponse,
    InstitutionAssessmentCreate,
    InstitutionProfileResponse,
    InstitutionUpdateRequest,
    LinkStudent,
)
from src.domains.institution.schemas.analytics import (
    InstitutionAnalytics,
    ClassroomAnalytics,
    BulkReportCardRequest,
    ClassroomComparison,
    ScoreSnapshot,
)
from src.domains.auth.schemas.user import RegisterRequest
from src.shared.utils.Pdf_service_two import (
    generate_report_card_pdf,
    generate_bulk_report_cards_pdf,
)

institution_router = APIRouter(prefix="/institution", tags=["Institution"])


@institution_router.get("/dashboard", response_model=InstitutionDashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = InstitutionAnalyticsService(db)

    return await svc.get_dashboard_stats(ctx.institution_id)


@institution_router.get(
    "/students-detailed",
    response_model=List[StudentWithClassroomResponse],
)
async def get_detailed_students(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """
    Returns students including their Classroom details (Name, Level, Section).
    """
    svc = InstitutionAnalyticsService(db)

    return await svc.list_students_detailed(ctx.institution_id, skip, limit)


@institution_router.get(
    "/classrooms/{classroom_id}/students",
    response_model=List[StudentWithClassroomResponse],
)
async def get_classroom_students(
    classroom_id: UUID,
    skip: int = 0,
    limit: int = 100,
    ctx: InstitutionContext = Depends(get_current_institution_user),
    db: AsyncSession = Depends(get_async_db),
):

    svc = InstitutionAnalyticsService(db)
    return await svc.list_students_by_classroom(
        ctx.institution_id, classroom_id, skip, limit
    )


@institution_router.delete(
    "/{institution_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_student_from_institution(
    institution_id: UUID,
    student_id: UUID,
    ctx: InstitutionContext = Depends(get_current_institution_user),
    db: AsyncSession = Depends(get_async_db),
):

    if ctx.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this institution's records",
        )

    service = BulkStudentOnboardingService(db)  # Initialize your service

    await service.remove_student_from_institution(
        institution_id=institution_id, student_id=student_id
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@institution_router.post(
    "/classrooms", response_model=ClassroomResponse, status_code=201
)
async def create_classroom(
    body: ClassroomCreate,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = ClassroomService(db)
    return await svc.create_classroom(ctx.institution_id, body)


@institution_router.get("/classrooms", response_model=List[ClassroomResponse])
async def list_classrooms(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = ClassroomService(db)
    return await svc.list_classrooms(ctx.institution_id)


@institution_router.patch(
    "/classrooms/{classroom_id}", response_model=ClassroomResponse
)
async def update_classroom(
    classroom_id: UUID,
    body: ClassroomUpdate,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = ClassroomService(db)
    return await svc.update_classroom(classroom_id, ctx.institution_id, body)


@institution_router.post("/classrooms/move-student")
async def move_student_to_classroom(
    body: MoveStudentRequest,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = ClassroomService(db)
    return await svc.move_student(ctx.institution_id, body)


@institution_router.post("/classrooms/bulk-move-students")
async def bulk_move_students(
    body: BulkMoveStudentsRequest,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = ClassroomService(db)
    return await svc.bulk_move_students(ctx.institution_id, body)


@institution_router.get("/{institution_id}/students/lookup")
async def lookup_student(
    q: str = Query(..., description="Email or student code"),
    ctx: InstitutionContext = Depends(get_current_institution_user),
    db: AsyncSession = Depends(get_async_db),
):
    svc = BulkStudentOnboardingService(db)

    return await svc.lookup_student(ctx.institution_id, q)


@institution_router.post("/{institution_id}/students/link")
async def link_student(
    data: LinkStudent,
    ctx: InstitutionContext = Depends(get_current_institution_user),
    db: AsyncSession = Depends(get_async_db),
):
    svc = BulkStudentOnboardingService(db)

    return await svc.link_student(ctx.institution_id, data)


@institution_router.post("/{institution_id}/students")
async def add_single_student(
    institution_id: UUID,
    data: RegisterRequest,
    send_invite: bool = Query(True),
    ctx: InstitutionContext = Depends(get_current_institution_user),
    db: AsyncSession = Depends(get_async_db),
):
    svc = BulkStudentOnboardingService(db)

    return await svc.single_onboard(ctx.institution_id, data, send_invite)


@institution_router.post("/students/bulk-upload", response_model=BulkOnboardResult)
async def bulk_upload_students(
    file: UploadFile = File(..., description="CSV file using the provided template"),
    send_invite: bool = Query(True),
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """
    Upload a CSV to onboard multiple students at once.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    svc = BulkStudentOnboardingService(db)

    return await svc.bulk_onboard(ctx.institution_id, content, send_invite)


@institution_router.post(
    "/classrooms/{classroom_id}/groups",
    response_model=StudentGroupResponse,
    status_code=201,
)
async def create_student_group(
    classroom_id: UUID,
    body: StudentGroupCreate,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    body.classroom_id = classroom_id
    svc = StudentGroupService(db)
    return await svc.create_group(ctx.institution_id, body)


@institution_router.get(
    "/classrooms/{classroom_id}/groups", response_model=List[StudentGroupResponse]
)
async def list_student_groups(
    classroom_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = StudentGroupService(db)
    return await svc.list_groups(classroom_id)


@institution_router.get("/groups", response_model=List[StudentGroupResponse])
async def list_all_groups(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """All groups across the institution — used by AssignAssessmentModal."""
    svc = StudentGroupService(db)
    return await svc.list_groups_by_institution(ctx.institution_id)


@institution_router.patch("/groups/{group_id}")
async def update_student_group(
    group_id: UUID,
    body: StudentGroupUpdate,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = StudentGroupService(db)
    await svc.update_group(group_id, body)
    return {"updated": True}


@institution_router.post(
    "/teachers/invite", response_model=TeacherResponse, status_code=201
)
async def invite_teacher(
    body: TeacherInviteRequest,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = TeacherService(db)
    return await svc.invite_teacher(ctx.institution_id, body)


@institution_router.get("/teachers", response_model=List[TeacherResponse])
async def list_teachers(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = TeacherService(db)
    return await svc.list_teachers(ctx.institution_id)


@institution_router.patch("/teachers/{teacher_id}/suspend")
async def suspend_teacher(
    teacher_id: UUID,
    suspend: bool = Query(...),
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = TeacherService(db)
    await svc.suspend_teacher(teacher_id, suspend)
    return {"teacher_id": str(teacher_id), "suspended": suspend}


@institution_router.patch("/teachers/{teacher_id}/assign")
async def assign_teacher_to_classroom(
    teacher_id: UUID,
    classroom_id: UUID,
    subject: Optional[str],
    is_class_teacher: bool = False,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = TeacherService(db)
    await svc.assign_to_classroom(teacher_id, classroom_id, subject, is_class_teacher)
    return {"teacher_id": str(teacher_id)}


# Assessment--------------------------------


@institution_router.post(
    "/assessments",
    response_model=InstitutionAssessmentResponse,
    status_code=201,
)
async def create_institution_assessment(
    body: InstitutionAssessmentCreate,
    db: Session = Depends(get_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = InstitutionAssessmentService(db)
    return await svc.create_assessment(ctx.institution_id, ctx.user_id, body)


@institution_router.get(
    "/assessments",
    response_model=List[InstitutionAssessmentResponse],
)
def list_institution_assessments(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = InstitutionAssessmentService(db)

    return svc.list_assessments(ctx.institution_id, skip, limit)


@institution_router.get("/assessments/stats")
async def get_assessment_stat(
    assessement_id: str = "952b4c12-8fd5-45f6-8c32-612cdd374515",
    db: Session = Depends(get_db),
):
    svc = InstitutionAssessmentService(db)
    stat = svc.get_statistics(assessement_id)
    return stat


@institution_router.post("/assessments/assign")
async def assign_assessment(
    body: AssignAssessmentRequest,
    db: Session = Depends(get_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """
    Assign an assessment to a classroom, a student group, or individual students.
    Scope is determined by which IDs are provided in the body.
    """
    svc = InstitutionAssessmentService(db)
    return await svc.assign(ctx.institution_id, ctx.user_id, body)


@institution_router.get(
    "/analytics",
    response_model=InstitutionAnalytics,
)
async def get_institution_analytics(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """Full institution-wide analytics — classrooms, groups, trends."""
    svc = InstitutionAnalyticsService(db)
    return await svc.get_institution_analytics(ctx.institution_id)


@institution_router.get(
    "/analytics/classrooms/{classroom_id}",
    response_model=ClassroomAnalytics,
)
async def get_classroom_analytics(
    classroom_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """Per-classroom analytics with student leaderboard and question difficulty."""
    svc = InstitutionAnalyticsService(db)
    return await svc.get_classroom_analytics(ctx.institution_id, classroom_id)


@institution_router.get(
    "/analytics/overview/score-trend",
    response_model=List[ScoreSnapshot],
)
async def get_score_trend(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """Monthly avg score trend for the institution — used by overview charts."""
    svc = InstitutionAnalyticsService(db)
    return await svc._institution_score_trend(ctx.institution_id)


@institution_router.get(
    "/analytics/overview/classroom-performance",
    response_model=List[ClassroomComparison],
)
async def get_classroom_performance_overview(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    """Per-classroom avg scores — used by overview Class vs Class chart."""
    svc = InstitutionAnalyticsService(db)
    classrooms = await svc._get_classrooms(ctx.institution_id)
    return [await svc._classroom_comparison(c, ctx.institution_id) for c in classrooms]


@institution_router.get("/students/{student_id}/report-card")
async def get_student_report_card(
    student_id: UUID,
    format: str = Query("json", regex="^(json|pdf)$"),
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = InstitutionAnalyticsService(db)
    card = await svc.get_student_report_card(ctx.institution_id, student_id)

    if format == "pdf":
        pdf_bytes = generate_report_card_pdf(card)
        return FastAPIResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="report_card_{student_id}.pdf"'
            },
        )
    return card


@institution_router.post("/report-cards/bulk")
async def generate_bulk_report_cards(
    body: BulkReportCardRequest,
    format: str = Query("json", regex="^(json|pdf)$"),
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    svc = InstitutionAnalyticsService(db)
    result = await svc.get_bulk_report_cards(
        institution_id=ctx.institution_id,
        student_ids=body.student_ids,
        classroom_id=body.classroom_id,
        group_id=body.group_id,
    )

    if format == "pdf":
        pdf_bytes = generate_bulk_report_cards_pdf(result.report_cards)
        return FastAPIResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="report_cards.pdf"'},
        )
    return result


@institution_router.get("/profile", response_model=InstitutionProfileResponse)
async def get_institution_profile(
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    result = await db.execute(
        select(Institution).where(Institution.id == ctx.institution_id)
    )
    institution = result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


@institution_router.patch("/profile", response_model=InstitutionProfileResponse)
async def update_institution_profile(
    body: InstitutionUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    ctx: InstitutionContext = Depends(get_current_institution_user),
):
    # Only owner can update profile
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(
        select(Institution).where(Institution.id == ctx.institution_id)
    )
    institution = result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    payload = body.model_dump(exclude_none=True)
    for field, value in payload.items():
        setattr(institution, field, value)

    await db.commit()
    await db.refresh(institution)
    return institution
