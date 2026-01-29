from fastapi import APIRouter, Depends, status, Query
from uuid import UUID
from typing import Optional
from fastapi.encoders import jsonable_encoder

from src.core.security import get_db, get_current_user_id
from src.domains.assessment.services.assessment_service import AssessmentService
from src.domains.assessment.services.attempt_service import AssessmentAttemptService
from src.domains.auth.repositories.student_repositoty import StudentRepository
from src.shared.response import success_response

from src.domains.guardian.services.challenge_service import ChallengeAssessmentService


router = APIRouter(prefix="/wards", tags=["Wards"])


@router.get("/assignments", status_code=status.HTTP_200_OK)
async def get_my_assignments(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get all assignments for the current ward (student)"""
    student_repo = StudentRepository(db)
    student = student_repo.get_by_user_id(user_id)

    if not student:
        return success_response(
            data=[],
            message="No student profile found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    challenge_service = ChallengeAssessmentService(db)
    result = await challenge_service.get_ward_assignments_for_student(
        student_id=student.id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )

    return success_response(
        data=jsonable_encoder(result),
        message="Assignments retrieved successfully",
    )


@router.get("/assignments/{assignment_id}", status_code=status.HTTP_200_OK)
async def get_assignment_detail(
    assignment_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get detailed information about a specific assignment"""
    student_repo = StudentRepository(db)
    student = student_repo.get_by_user_id(user_id)

    if not student:
        return success_response(
            data=None,
            message="No student profile found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    challenge_service = ChallengeAssessmentService(db)
    result = await challenge_service.get_assignment_detail_for_student(
        assignment_id=assignment_id,
        student_id=student.id,
    )

    return success_response(
        data=jsonable_encoder(result),
        message="Assignment details retrieved successfully",
    )


@router.get("/assessments/{assessment_id}/config", status_code=status.HTTP_200_OK)
async def get_assessment_config(
    assessment_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get assessment configuration for pre-check screen"""
    assessment_service = AssessmentService(db)
    attempt_service = AssessmentAttemptService(db)
    student_repo = StudentRepository(db)

    student = student_repo.get_by_user_id(user_id)
    if not student:
        return success_response(
            data=None,
            message="No student profile found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Get assessment
    assessment = await assessment_service.get_assessment(assessment_id)

    # Get student's attempts count
    attempts = await attempt_service.get_attempt_by_assessment(
        user_id=user_id, assessment_id=assessment.id
    )

    config = {
        "assessment_id": str(assessment.id),
        "assessment_title": assessment.title,
        "duration_minutes": assessment.duration_minutes,
        "total_questions": assessment.total_questions,
        "max_attempts": assessment.max_attempts,
        "attempts_used": len(attempts),
        "requires_webcam": assessment.require_webcam,
        "requires_fullscreen": assessment.fullscreen_required,
        "detects_tab_switching": assessment.detect_tab_switching,
        "max_tab_switches": assessment.max_tab_switches or 3,
        "due_date": assessment.available_until,
        "instructions": assessment.instructions,
    }

    return success_response(
        data=config,
        message="Assessment configuration retrieved successfully",
    )


@router.post("/attempts/{attempt_id}/violation", status_code=status.HTTP_201_CREATED)
async def log_proctoring_violation(
    attempt_id: UUID,
    violation_data: dict,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Log a proctoring violation"""
    from src.domains.assessment.models.assessment import AssessmentProctoringEvent
    from datetime import datetime

    # Create violation record
    violation = AssessmentProctoringEvent(
        attempt_id=attempt_id,
        event_type=violation_data.get("violation_type", "unknown"),
        occurred_at=datetime.fromisoformat(violation_data.get("occurred_at"))
        if violation_data.get("occurred_at")
        else datetime.utcnow(),
        severity="warning",
        details=violation_data,
    )

    db.add(violation)
    db.commit()
    db.refresh(violation)

    challenge_service = ChallengeAssessmentService(db)
    await challenge_service.notify_guardian_of_violation(
        attempt_id=attempt_id,
        violation_type=violation_data.get("violation_type"),
    )

    return success_response(
        data={"id": str(violation.id)},
        message="Violation logged successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/attempts/{attempt_id}/auto-submit", status_code=status.HTTP_200_OK)
async def auto_submit_attempt(
    attempt_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    challenge_service = ChallengeAssessmentService(db)
    await challenge_service.notify_guardian_of_completion(
        ward_user_id=user_id,
        attempt_id=attempt_id,
        auto_submitted=True,
    )

    return success_response(
        message="Assessment auto-submitted successfully",
    )


@router.get("/dashboard/stats", status_code=status.HTTP_200_OK)
async def get_ward_dashboard_stats(
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get ward dashboard statistics"""
    student_repo = StudentRepository(db)
    student = student_repo.get_by_user_id(user_id)

    if not student:
        return success_response(
            data=None,
            message="No student profile found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    challenge_service = ChallengeAssessmentService(db)

    # Get assignment counts
    assignments = await challenge_service.get_ward_assignments_for_student(
        student_id=student.id,
        status_filter=None,
        skip=0,
        limit=1000,
    )

    stats = {
        "total_assignments": len(assignments),
        "pending": len(
            [a for a in assignments if a["status"] in ["assigned", "started"]]
        ),
        "completed": len([a for a in assignments if a["status"] == "completed"]),
        "overdue": len([a for a in assignments if a["status"] == "overdue"]),
        "average_score": sum([a["score"] for a in assignments if a.get("score")])
        / len([a for a in assignments if a.get("score")])
        if [a for a in assignments if a.get("score")]
        else 0,
        "pass_rate": len([a for a in assignments if a.get("passed")])
        / len([a for a in assignments if a.get("score")])
        if [a for a in assignments if a.get("score")]
        else 0,
    }

    return success_response(
        data=stats,
        message="Dashboard stats retrieved successfully",
    )
