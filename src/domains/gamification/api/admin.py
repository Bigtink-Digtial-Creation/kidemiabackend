import json
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_async_db as get_db
from src.core.security import require_permissions
from src.domains.gamification.services.gamification_service import GamificationService
from src.domains.gamification.schemas.schemas import (
    BadgeCreate,
    BadgeUpdate,
    BadgeResponse,
    AchievementCreate,
    AchievementUpdate,
    AchievementResponse,
    StudentBadgeResponse,
    StudentAchievementResponse,
)


router = APIRouter(prefix="/admin/gamification", tags=["Admin - Gamification"])


def get_service(db: AsyncSession = Depends(get_db)) -> GamificationService:
    return GamificationService(db)


@router.get("/badges", response_model=List[BadgeResponse])
async def get_all_badges(
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Get all available badges"""
    badges = await service.repo.get_all_active_badges()
    return badges


@router.get("/badges/{student_id}", response_model=List[StudentBadgeResponse])
async def get_student_badges(
    student_id: UUID,
    service: GamificationService = Depends(get_service),
):
    """Get a specific student's earned badges"""
    badges = await service.get_student_badges(student_id)
    return badges


@router.post(
    "/badges", response_model=BadgeResponse, status_code=status.HTTP_201_CREATED
)
async def create_badge(
    data: BadgeCreate,
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Create a new badge"""
    existing = await service.repo.get_badge_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Badge with this name already exists",
        )

    badge_data = data.model_dump()
    badge_data["criteria"] = json.dumps(data.criteria)
    badge = await service.repo.create_badge(badge_data)
    await service.db.commit()
    return badge


@router.put("/badges/{badge_id}", response_model=BadgeResponse)
async def update_badge(
    badge_id: UUID,
    data: BadgeUpdate,
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Update an existing badge"""
    badge = await service.repo.get_badge_by_id(badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "criteria" and value:
            value = json.dumps(value)
        setattr(badge, key, value)

    await service.db.commit()
    return badge


@router.delete("/badges/{badge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_badge(
    badge_id: UUID,
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Soft delete a badge (deactivate)"""
    badge = await service.repo.get_badge_by_id(badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    badge.is_active = False
    await service.db.commit()


@router.get("/achievements", response_model=List[AchievementResponse])
async def get_all_achievements(
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Get all available achievements"""
    achievements = await service.repo.get_all_active_achievements()
    return achievements


@router.get(
    "/achievements/{student_id}", response_model=List[StudentAchievementResponse]
)
async def get_student_achievements(
    student_id: UUID,
    service: GamificationService = Depends(get_service),
    _: None = Depends(require_permissions("content:create")),
):
    """Get a specific student's achievements with progress"""
    achievements = await service.get_student_achievements(student_id)
    return [service._to_student_achievement_response(a) for a in achievements]


@router.post(
    "/achievements",
    response_model=AchievementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_achievement(
    data: AchievementCreate,
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Create a new achievement"""
    achievement = await service.repo.create_achievement(data.model_dump())
    await service.db.commit()
    return achievement


@router.put("/achievements/{achievement_id}", response_model=AchievementResponse)
async def update_achievement(
    achievement_id: UUID,
    data: AchievementUpdate,
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Update an existing achievement"""
    achievement = await service.repo.get_achievement_by_id(achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(achievement, key, value)

    await service.db.commit()
    return achievement


@router.delete("/achievements/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(
    achievement_id: UUID,
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Soft delete an achievement (deactivate)"""
    achievement = await service.repo.get_achievement_by_id(achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    achievement.is_active = False
    await service.db.commit()


@router.post("/leaderboard/refresh", status_code=status.HTTP_200_OK)
async def refresh_leaderboard(
    _: None = Depends(require_permissions("content:create")),
    service: GamificationService = Depends(get_service),
):
    """Manually refresh leaderboard positions"""
    await service.repo.update_leaderboard_positions()
    await service.db.commit()
    return {"message": "Leaderboard positions updated"}
