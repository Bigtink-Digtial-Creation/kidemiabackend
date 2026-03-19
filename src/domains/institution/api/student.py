import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.database import get_async_db
from src.core.security import get_current_user

from src.domains.auth.models.user import User
from src.domains.auth.models.student import Student
from src.domains.assessment.models.attempt import AssessmentAttempt

from src.domains.institution.services.institution_analytic_service import (
    InstitutionAnalyticsService,
)

logger = logging.getLogger(__name__)

student_router = APIRouter(prefix="/institution", tags=["Institution"])


@student_router.get("/my-assignments/institution")
async def get_institution_assignments(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all assessments assigned to the student via their institution
    (classroom, group, or individual assignments).
    """

    student_result = await db.execute(
        select(Student)
        .options(selectinload(Student.institution))
        .where(
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

    now = datetime.utcnow()
    results = []

    for assignment in assignments:
        assessment = assignment.assessment
        if not assessment:
            continue

        try:
            subject_name = assessment.subject.name if assessment.subject else None

            # Fetch attempts
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

            # Determine best attempt
            best = next(
                (a for a in attempts if a.status and a.status.value == "graded"),
                None,
            )

            if not best and attempts:
                best = attempts[0]

            # Determine assignment status
            assign_status = "not_started"

            if best:
                if best.status and best.status.value == "graded":
                    assign_status = "completed"
                elif best.status and best.status.value == "in_progress":
                    assign_status = "started"

            if (
                assignment.due_date
                and assignment.due_date < now
                and assign_status != "completed"
            ):
                assign_status = "overdue"

            score = (
                float(best.percentage) if best and best.percentage is not None else None
            )

            # Determine assignment scope
            if assignment.classroom_id:
                assigned_via = "classroom"
            elif assignment.student_group_id:
                assigned_via = "group"
            else:
                assigned_via = "individual"

            item = {
                "id": str(assignment.id),
                "assessment_id": str(assessment.id),
                "assessment_title": assessment.title,
                "subject_name": subject_name,
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
                "score": score,
                "passed": best.passed if best else None,
                "grade": best.grade if best else None,
                "assigned_via": assigned_via,
                "institution_name": student.institution.name
                if student.institution
                else None,
            }

            if not status or item["status"] == status:
                results.append(item)

        except Exception as exc:
            logger.exception(
                "Failed processing assignment %s for user %s",
                assignment.id,
                current_user.id,
            )

    return results
