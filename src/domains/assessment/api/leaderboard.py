from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id
from src.domains.assessment.services.leaderboard_service import LeaderboardService
from src.domains.assessment.schemas.statistics import LeaderboardResponse

router = APIRouter()


@router.get(
    "/assessments/{assessment_id}",
    response_model=LeaderboardResponse,
    summary="Get assessment leaderboard",
)
async def get_assessment_leaderboard(
    assessment_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Get leaderboard for a specific assessment.

    Shows top performers ranked by:
    1. Score (highest first)
    2. Time taken (fastest first for ties)

    If authenticated, includes current user's rank.
    """
    service = LeaderboardService(db)
    return await service.get_assessment_leaderboard(
        assessment_id, limit, current_user_id
    )


@router.get(
    "/subjects/{subject_id}",
    response_model=List[Dict[str, Any]],
    summary="Get subject leaderboard",
)
async def get_subject_leaderboard(
    subject_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Get leaderboard for a specific subject.

    Aggregates performance across all assessments in the subject.
    Ranks by average score and total points earned.
    """
    service = LeaderboardService(db)
    return await service.get_subject_leaderboard(subject_id, limit)


@router.get(
    "/users/{user_id}/statistics",
    response_model=Dict[str, Any],
    summary="Get user statistics",
)
async def get_user_statistics(user_id: UUID, db: Session = Depends(get_db)):
    """
    Get comprehensive statistics for a user.

    Includes:
    - Total attempts and completions
    - Pass rate and average score
    - Recent performance
    - Subject-wise breakdown
    """
    service = LeaderboardService(db)
    return await service.get_user_statistics(user_id)


@router.get(
    "/me/statistics", response_model=Dict[str, Any], summary="Get my statistics"
)
async def get_my_statistics(
    db: Session = Depends(get_db), current_user_id: UUID = Depends(get_current_user_id)
):
    """Get statistics for the current user."""
    service = LeaderboardService(db)
    return await service.get_user_statistics(current_user_id)


@router.get(
    "/me/stat/dashboard",
    response_model=Dict[str, Any],
    summary="Get dashboard statistics",
)
async def get_dashboard_stat(
    db: Session = Depends(get_db), current_user_id: UUID = Depends(get_current_user_id)
):
    """Get dashboard data for the current user."""
    service = LeaderboardService(db)
    return await service.dashboard_stats(current_user_id)
