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
    GamificationProfileResponse,
    BadgeResponse,
    StudentBadgeResponse,
    AchievementResponse,
    StudentAchievementResponse,
    LeaderboardResponse,
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


@router.get("/badges", response_model=List[BadgeResponse])
async def get_all_badges(
    service: GamificationService = Depends(get_gamification_service),
):
    """Get all available badges"""
    badges = await service.repo.get_all_active_badges()
    return badges


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


@router.get("/badges/{student_id}", response_model=List[StudentBadgeResponse])
async def get_student_badges(
    student_id: UUID,
    service: GamificationService = Depends(get_gamification_service),
):
    """Get a specific student's earned badges"""
    badges = await service.get_student_badges(student_id)
    return badges


@router.get("/achievements", response_model=List[AchievementResponse])
async def get_all_achievements(
    service: GamificationService = Depends(get_gamification_service),
):
    """Get all available achievements"""
    achievements = await service.repo.get_all_active_achievements()
    return achievements


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
    "/achievements/{student_id}", response_model=List[StudentAchievementResponse]
)
async def get_student_achievements(
    student_id: UUID,
    service: GamificationService = Depends(get_gamification_service),
):
    """Get a specific student's achievements with progress"""
    achievements = await service.get_student_achievements(student_id)
    return [service._to_student_achievement_response(a) for a in achievements]


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(default=100, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: Optional[UUID] = Query(default=None),
    institution_id: Optional[UUID] = Query(default=None),
    user_id: Optional[User] = Depends(get_current_user_id),
    service: GamificationService = Depends(get_gamification_service),
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


# @router.post("/seed-gamification")
# async def seed_gamification(payload: SeedPayload, db: AsyncSession = Depends(get_db)):
#     # Insert badges
#     for b in payload.badges:
#         data = b.dict()
#         if "criteria" in data and isinstance(data["criteria"], dict):
#             data["criteria"] = json.dumps(data["criteria"])  # Convert dict -> str
#         db.add(Badge(**data))

#     # Insert achievements
#     for a in payload.achievements:
#         db.add(Achievement(**a.dict()))

#     await db.commit()

#     return {"success": True, "message": "Gamification data seeded successfully!"}
