from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_async_db as get_db
from src.core.security import get_current_user_id
from src.domains.auth.models.user import User
from src.domains.auth.models.student import Student
from src.domains.gamification.services.gamification_service import GamificationService
from src.domains.gamification.schemas.schemas import (
    AssessmentLeaderboardResponse,
    GamificationProfileResponse,
    BadgeResponse,
    StudentBadgeResponse,
    StudentAchievementResponse,
    LeaderboardResponse,
)
from src.domains.access_control.dependency import RequireAccess
from src.domains.access_control.schema import ACCESS_RESPONSES
from src.domains.access_control.core import AccessResult
from src.domains.gamification.services.ranking_service import (
    AssessmentLeaderboardService,
)

router = APIRouter(prefix="/gamification", tags=["Gamification"])


def get_gamification_service(db: AsyncSession = Depends(get_db)) -> GamificationService:
    return GamificationService(db)


@router.get("/profile", response_model=GamificationProfileResponse)
async def get_my_gamification_profile(
    current_user_id: str = Depends(get_current_user_id),
    service: GamificationService = Depends(get_gamification_service),
):
    """Get current student's gamification profile"""
    student = await service.get_student_profile_from_user(current_user_id)

    if student:
        profile = await service.get_student_profile(student.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gamification profile not found",
            )
        return profile
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Student profile not found",
    )


@router.get("/profile/{student_id}", response_model=GamificationProfileResponse)
async def get_student_gamification_profile(
    student_id: UUID,
    service: GamificationService = Depends(get_gamification_service),
):
    """Get a specific student's gamification profile (public view)"""
    profile = await service.get_student_profile(student_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gamification profile not found",
        )
    return profile


@router.get("/badges/mine", response_model=List[StudentBadgeResponse])
async def get_my_badges(
    current_user_id: str = Depends(get_current_user_id),
    service: GamificationService = Depends(get_gamification_service),
):
    """Get current student's earned badges"""

    student = await service.get_student_profile_from_user(current_user_id)
    if student:
        badges = await service.get_student_badges(student.id)
        return badges


@router.get("/achievements/mine", response_model=List[StudentAchievementResponse])
async def get_my_achievements(
    current_user_id: str = Depends(get_current_user_id),
    service: GamificationService = Depends(get_gamification_service),
):
    """Get current student's achievements with progress"""
    student = await service.get_student_profile_from_user(current_user_id)
    if student:
        achievements = await service.get_student_achievements(student.id)
        return [service._to_student_achievement_response(a) for a in achievements]


@router.get(
    "/leaderboard", response_model=LeaderboardResponse, responses={**ACCESS_RESPONSES}
)
async def get_leaderboard(
    limit: int = Query(default=100, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: Optional[UUID] = Query(default=None),
    institution_id: Optional[UUID] = Query(default=None),
    user_id: Optional[User] = Depends(get_current_user_id),
    service: GamificationService = Depends(get_gamification_service),
    access: AccessResult = Depends(
        RequireAccess(
            resource="leaderboard",
            feature="leaderboard_access",
            feature_only=True,
            auto_charge=False,
        )
    ),
):
    """Get leaderboard with optional filters"""
    current_student_id = None

    if user_id:
        student = await service.get_student_profile_from_user(user_id)
        current_student_id = student.id if student else None

    return await service.get_leaderboard(
        limit=limit,
        offset=offset,
        category_id=category_id,
        institution_id=institution_id,
        current_student_id=current_student_id,
    )


@router.get("/leaderboard/my-rank")
async def get_my_rank(
    current_user_id: str = Depends(get_current_user_id),
    service: GamificationService = Depends(get_gamification_service),
):
    """Get current student's leaderboard rank"""
    student = await service.get_student_profile_from_user(current_user_id)
    rank = await service.repo.get_student_rank(student.id)
    profile = await service.get_student_profile(student.id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return {
        "rank": rank,
        "total_points": profile.total_points,
        "level": profile.current_level,
        "rank_title": profile.rank_title,
    }


@router.get("/stats/summary")
async def get_gamification_summary(
    current_user_id: Student = Depends(get_current_user_id),
    service: GamificationService = Depends(get_gamification_service),
):
    """Get a summary of student's gamification stats"""
    student = await service.get_student_profile_from_user(current_user_id)
    profile = await service.get_student_profile(student.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    badges = await service.get_student_badges(student.id)
    achievements = await service.get_student_achievements(student.id)
    rank = await service.repo.get_student_rank(student.id)

    completed_achievements = [a for a in achievements if a.is_completed]

    return {
        "profile": {
            "total_points": profile.total_points,
            "level": profile.current_level,
            "rank_title": profile.rank_title,
            "experience_points": profile.experience_points,
        },
        "streak": {
            "current": profile.current_streak,
            "longest": profile.longest_streak,
            "last_activity": profile.last_activity_date,
        },
        "stats": {
            "assessments_completed": profile.total_assessments_completed,
            "questions_answered": profile.total_questions_answered,
            "correct_answers": profile.correct_answers,
            "accuracy": round(
                (profile.correct_answers / profile.total_questions_answered) * 100, 2
            )
            if profile.total_questions_answered > 0
            else 0,
        },
        "badges": {
            "total_earned": len(badges),
            "recent": [BadgeResponse.model_validate(b.badge) for b in badges[:5]],
        },
        "achievements": {
            "completed": len(completed_achievements),
            "total": len(achievements),
        },
        "leaderboard": {
            "rank": rank,
        },
    }


@router.get(
    "/{assessment_id}/ranking",
    response_model=AssessmentLeaderboardResponse,
)
async def get_assessment_rankings(
    assessment_id: UUID,
    limit: int = Query(default=100, le=100),
    offset: int = Query(default=0, ge=0),
    current_user_id: Optional[UUID] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Public leaderboard for a specific assessment.
    Shows all submitted attempts ranked by highest score.
    The current user's rank is included even if they're outside the page.
    """
    service = AssessmentLeaderboardService(db)

    return await service.get_assessment_leaderboard(
        assessment_id=assessment_id,
        limit=limit,
        offset=offset,
        current_user_id=current_user_id,
    )
