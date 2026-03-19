from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from src.config.database import get_async_db
from src.core.security import get_current_user
from typing import Optional
from sqlalchemy import select
from datetime import datetime, timezone

from src.domains.auth.models.user import User
from src.domains.auth.models.student import Student
from src.domains.assessment.models.attempt import AssessmentAttempt

from src.domains.institution.services.institution_analytic_service import (
    InstitutionAnalyticsService,
)

student_router = APIRouter(prefix="/institution", tags=["Institution"])


@student_router.get("/my-assignments/institution")
async def get_institution_assignments(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all assessments assigned to this student via their institution
    (classroom, group, or individual assignments).
    """
    # Get student record
    student_result = await db.execute(
        select(Student).where(
            Student.user_id == current_user.id,
            Student.is_active.is_(True),
        )
    )
    student = student_result.scalar_one_or_none()
    if not student or not student.institution_id:
        return []

    svc = InstitutionAnalyticsService(db)
    assignments = await svc._get_student_assignment_ids(
        student_id=student.id,
        classroom_id=student.classroom_id,
        institution_id=student.institution_id,
    )

    now = datetime.now(timezone.utc)
    result = []

    for assignment in assignments:
        assessment = assignment.assessment
        if not assessment:
            continue

        # Find best attempt
        attempt_result = await db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.user_id == current_user.id,
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(AssessmentAttempt.started_at.desc())
        )
        attempts = attempt_result.scalars().all()
        best = next((a for a in attempts if a.status.value == "graded"), None) or (
            attempts[0] if attempts else None
        )

        # Determine status
        assign_status = "not_started"
        if best:
            if best.status.value == "graded":
                assign_status = "completed"
            elif best.status.value == "in_progress":
                assign_status = "started"

        if (
            assignment.due_date
            and assignment.due_date < now
            and assign_status != "completed"
        ):
            assign_status = "overdue"

        item = {
            "id": str(assignment.id),
            "assessment_id": str(assessment.id),
            "assessment_title": assessment.title,
            "subject_name": assessment.subject.name if assessment.subject else None,
            "total_questions": assessment.total_questions,
            "duration_minutes": assessment.duration_minutes,
            "assigned_at": assignment.created_at.isoformat(),
            "due_date": assignment.due_date.isoformat()
            if assignment.due_date
            else None,
            "available_from": assignment.available_from.isoformat()
            if assignment.available_from
            else None,
            "instructions": assignment.instructions,
            "status": assign_status,
            "attempt_count": len(attempts),
            "max_attempts": assessment.max_attempts,
            "requires_webcam": assessment.require_webcam,
            "requires_fullscreen": assessment.fullscreen_required,
            "detects_tab_switching": assessment.detect_tab_switching,
            "score": float(best.percentage) if best and best.percentage else None,
            "passed": best.passed if best else None,
            "grade": best.grade if best else None,
            # Scope — so student knows how they were assigned
            "assigned_via": "classroom"
            if assignment.classroom_id
            else "group"
            if assignment.student_group_id
            else "individual",
            "institution_name": student.institution.name
            if hasattr(student, "institution") and student.institution
            else None,
        }

        if not status or item["status"] == status:
            result.append(item)

    return result
