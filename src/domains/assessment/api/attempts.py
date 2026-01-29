from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id
from src.domains.assessment.services.attempt_service import AssessmentAttemptService
from src.domains.assessment.schemas.attempt import (
    AttemptStartRequest,
    AttemptStartResponse,
    SaveAnswerRequest,
    AttemptProgressResponse,
    AttemptResultResponse,
    AttemptListResponse,
    AttemptResponse,
)
from src.domains.assessment.schemas.correction import AnswerCorrectionResponse
from src.shared.response import success_response

router = APIRouter()


@router.post(
    "/{assessment_id}/start",
    response_model=AttemptStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an assessment attempt",
)
async def start_attempt(
    assessment_id: UUID,
    request_data: AttemptStartRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Start a new assessment attempt.

    - Validates assessment availability
    - Checks attempt limits
    - Verifies payment for exams
    - Creates or resumes attempt
    """
    service = AssessmentAttemptService(db)
    return await service.start_attempt(assessment_id, current_user_id, request_data)


@router.post("/{attempt_id}/answer", response_model=dict, summary="Save an answer")
async def save_answer(
    attempt_id: UUID,
    answer_data: SaveAnswerRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Save or update an answer for a question.

    - Can be called multiple times for the same question
    - Tracks time spent and edit count
    - Supports flagging for review
    """
    service = AssessmentAttemptService(db)
    return await service.save_answer(attempt_id, current_user_id, answer_data)


@router.post(
    "/{attempt_id}/submit",
    response_model=AttemptResultResponse,
    summary="Submit an attempt",
)
async def submit_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Submit an assessment attempt for grading.

    - Auto-grades objective questions
    - Marks essays for manual grading
    - Calculates scores and ranking
    - Updates assessment statistics
    """
    service = AssessmentAttemptService(db)
    return await service.submit_attempt(attempt_id, current_user_id)


@router.get(
    "/{attempt_id}/progress",
    response_model=AttemptProgressResponse,
    summary="Get attempt progress",
)
async def get_attempt_progress(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Get current progress of an ongoing attempt.

    Returns:
    - Time spent and remaining
    - Questions answered/unanswered
    - Flagged questions count
    - Submission eligibility
    """
    service = AssessmentAttemptService(db)
    return await service.get_attempt_progress(attempt_id, current_user_id)


@router.get(
    "/{attempt_id}/result",
    response_model=AttemptResultResponse,
    summary="Get attempt result",
)
async def get_attempt_result(
    attempt_id: UUID,
    include_answers: bool = Query(False),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Get result of a completed attempt.

    - **include_answers**: Include detailed answer breakdown with correct answers
    """
    service = AssessmentAttemptService(db)
    return await service.get_attempt_result(
        attempt_id, current_user_id, include_answers
    )


@router.get(
    "/{attempt_id}/correction",
    response_model=AnswerCorrectionResponse,
    summary="Get attempt correction",
)
async def get_correction(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    service = AssessmentAttemptService(db)
    return await service.get_attempt_correction(attempt_id=attempt_id, user_id=user_id)


@router.get(
    "/{attempt_id}/attempt",
    response_model=AttemptResponse,
    summary="Get attempt details",
)
async def get_single_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Get attempt details for the current user.
    """
    service = AssessmentAttemptService(db)
    return await service.get_attempt(attempt_id, user_id)


@router.get(
    "/my-attempts", response_model=AttemptListResponse, summary="Get my attempts"
)
async def get_my_attempts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all attempts for the current user."""
    service = AssessmentAttemptService(db)
    return await service.get_user_attempts(current_user_id, skip, limit)


"""Delete attempt for the current user.
    This is for development purpose only"""


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

    return success_response(
        data={"id": str(violation.id)},
        message="Violation logged successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/delete-attempt", summary="Delete attempts")
def delete_attempts(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = AssessmentAttemptService(db)
    return service.delete_attempt(attempt_id)
