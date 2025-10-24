from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.assessment.services.grading_service import GradingService
from src.domains.assessment.schemas.answer import ManualGradeRequest

router = APIRouter()


@router.post(
    "/attempts/{attempt_id}/auto-grade",
    response_model=dict,
    summary="Auto-grade an attempt",
)
async def auto_grade_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("grading:auto")),
):
    """
    Auto-grade an assessment attempt.

    - Grades objective questions automatically
    - Identifies essays requiring manual grading
    - Calculates scores and pass/fail status
    """
    service = GradingService(db)
    return await service.auto_grade_attempt(attempt_id)


@router.post(
    "/answers/{answer_id}/manual-grade",
    response_model=dict,
    summary="Manually grade an answer",
)
async def manual_grade_answer(
    answer_id: UUID,
    grade_data: ManualGradeRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("grading:manual")),
):
    """
    Manually grade an answer (typically for essays).

    Requires `grading:manual` permission.
    """
    service = GradingService(db)
    return await service.manual_grade_answer(
        answer_id=answer_id,
        grader_id=current_user_id,
        points_earned=grade_data.points_earned,
        feedback=grade_data.feedback,
    )


@router.post(
    "/answers/bulk-grade", response_model=dict, summary="Bulk grade multiple answers"
)
async def bulk_grade_answers(
    grading_data: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("grading:manual")),
):
    """
    Bulk grade multiple answers at once.

    Requires `grading:manual` permission.

    Expected format:
    ```json
    [
        {
            "answer_id": "uuid",
            "points_earned": 8.5,
            "feedback": "Good work"
        }
    ]
    ```
    """
    service = GradingService(db)
    return await service.bulk_grade_answers(grading_data, current_user_id)


@router.get(
    "/pending", response_model=List[dict], summary="Get attempts pending grading"
)
async def get_pending_grading(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("grading:read")),
):
    """
    Get list of attempts pending manual grading.

    Returns attempts with essays or subjective questions awaiting grading.
    """
    service = GradingService(db)
    return await service.get_pending_grading(skip, limit)
