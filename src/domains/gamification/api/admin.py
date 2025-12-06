import json
from uuid import UUID

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
)

router = APIRouter(prefix="/admin/gamification", tags=["Admin - Gamification"])


def get_service(db: AsyncSession = Depends(get_db)) -> GamificationService:
    return GamificationService(db)


# ============== BADGE MANAGEMENT ==============
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


# ============== ACHIEVEMENT MANAGEMENT ==============
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


# ============================================================
# SEEDER - Run once to populate initial badges & achievements
# ============================================================
async def seed_gamification_data(db: AsyncSession):
    """
    Seed initial badges and achievements.

    Run this during application startup or via CLI:

        python -m src.domains.gamification.admin seed
    """
    service = GamificationService(db)

    # ============== BADGES ==============
    badges = [
        {
            "name": "first_steps",
            "display_name": "First Steps",
            "description": "Complete your first assessment",
            "icon_url": "/badges/first-steps.svg",
            "color_code": "#10B981",
            "rarity": "common",
            "criteria": json.dumps({"event": "first_assessment"}),
            "is_secret": False,
        },
        {
            "name": "perfectionist",
            "display_name": "Perfectionist",
            "description": "Score 100% on any assessment",
            "icon_url": "/badges/perfectionist.svg",
            "color_code": "#F59E0B",
            "rarity": "rare",
            "criteria": json.dumps({"event": "assessment_100_percent"}),
            "is_secret": False,
        },
        {
            "name": "night_owl",
            "display_name": "Night Owl",
            "description": "Complete an assessment after 10 PM",
            "icon_url": "/badges/night-owl.svg",
            "color_code": "#6366F1",
            "rarity": "rare",
            "criteria": json.dumps({"event": "assessment_after_10pm"}),
            "is_secret": True,
        },
        {
            "name": "early_bird",
            "display_name": "Early Bird",
            "description": "Complete an assessment before 6 AM",
            "icon_url": "/badges/early-bird.svg",
            "color_code": "#F97316",
            "rarity": "rare",
            "criteria": json.dumps({"event": "assessment_before_6am"}),
            "is_secret": True,
        },
        {
            "name": "speed_demon",
            "display_name": "Speed Demon",
            "description": "Complete an assessment in under 5 minutes",
            "icon_url": "/badges/speed-demon.svg",
            "color_code": "#EF4444",
            "rarity": "epic",
            "criteria": json.dumps({"event": "speed_demon"}),
            "is_secret": False,
        },
        {
            "name": "week_warrior",
            "display_name": "Week Warrior",
            "description": "Maintain a 7-day streak",
            "icon_url": "/badges/week-warrior.svg",
            "color_code": "#EC4899",
            "rarity": "rare",
            "criteria": json.dumps({"event": "streak_milestone", "streak_days": 7}),
            "is_secret": False,
        },
        {
            "name": "month_master",
            "display_name": "Month Master",
            "description": "Maintain a 30-day streak",
            "icon_url": "/badges/month-master.svg",
            "color_code": "#8B5CF6",
            "rarity": "epic",
            "criteria": json.dumps({"event": "streak_milestone", "streak_days": 30}),
            "is_secret": False,
        },
        {
            "name": "centurion",
            "display_name": "Centurion",
            "description": "Maintain a 100-day streak",
            "icon_url": "/badges/centurion.svg",
            "color_code": "#FBBF24",
            "rarity": "legendary",
            "criteria": json.dumps({"event": "streak_milestone", "streak_days": 100}),
            "is_secret": False,
        },
    ]

    for badge_data in badges:
        existing = await service.repo.get_badge_by_name(badge_data["name"])
        if not existing:
            await service.repo.create_badge(badge_data)

    achievements = [
        {
            "name": "assessment_starter",
            "display_name": "Assessment Starter",
            "description": "Complete your first assessment",
            "icon_url": "/achievements/starter.svg",
            "color_code": "#10B981",
            "achievement_type": "assessments_completed",
            "target_value": 1,
            "points_reward": 10,
        },
        {
            "name": "dedicated_learner",
            "display_name": "Dedicated Learner",
            "description": "Complete 10 assessments",
            "icon_url": "/achievements/dedicated.svg",
            "color_code": "#3B82F6",
            "achievement_type": "assessments_completed",
            "target_value": 10,
            "points_reward": 50,
        },
        {
            "name": "assessment_veteran",
            "display_name": "Assessment Veteran",
            "description": "Complete 50 assessments",
            "icon_url": "/achievements/veteran.svg",
            "color_code": "#8B5CF6",
            "achievement_type": "assessments_completed",
            "target_value": 50,
            "points_reward": 200,
        },
        {
            "name": "century_club",
            "display_name": "Century Club",
            "description": "Complete 100 assessments",
            "icon_url": "/achievements/century.svg",
            "color_code": "#F59E0B",
            "achievement_type": "assessments_completed",
            "target_value": 100,
            "points_reward": 500,
        },
        {
            "name": "question_crusher",
            "display_name": "Question Crusher",
            "description": "Answer 1,000 questions",
            "icon_url": "/achievements/crusher.svg",
            "color_code": "#EF4444",
            "achievement_type": "questions_answered",
            "target_value": 1000,
            "points_reward": 200,
        },
        {
            "name": "question_master",
            "display_name": "Question Master",
            "description": "Answer 5,000 questions",
            "icon_url": "/achievements/master.svg",
            "color_code": "#EC4899",
            "achievement_type": "questions_answered",
            "target_value": 5000,
            "points_reward": 500,
        },
        {
            "name": "streak_starter",
            "display_name": "Streak Starter",
            "description": "Maintain a 3-day streak",
            "icon_url": "/achievements/streak-3.svg",
            "color_code": "#F97316",
            "achievement_type": "streak_days",
            "target_value": 3,
            "points_reward": 30,
        },
        {
            "name": "week_warrior_achievement",
            "display_name": "Week Warrior",
            "description": "Maintain a 7-day streak",
            "icon_url": "/achievements/streak-7.svg",
            "color_code": "#EC4899",
            "achievement_type": "streak_days",
            "target_value": 7,
            "points_reward": 100,
        },
        {
            "name": "point_collector",
            "display_name": "Point Collector",
            "description": "Earn 1,000 points",
            "icon_url": "/achievements/points-1k.svg",
            "color_code": "#10B981",
            "achievement_type": "points_earned",
            "target_value": 1000,
            "points_reward": 100,
        },
        {
            "name": "point_hoarder",
            "display_name": "Point Hoarder",
            "description": "Earn 10,000 points",
            "icon_url": "/achievements/points-10k.svg",
            "color_code": "#FBBF24",
            "achievement_type": "points_earned",
            "target_value": 10000,
            "points_reward": 500,
        },
    ]

    for achievement_data in achievements:
        existing_achievements = await service.repo.get_all_active_achievements()
        existing_names = [a.name for a in existing_achievements]

        if achievement_data["name"] not in existing_names:
            await service.repo.create_achievement(achievement_data)
    await db.commit()


# CLI entry point
if __name__ == "__main__":
    import asyncio
    import sys
    from src.shared.database.session import async_session_maker

    async def run_seed():
        async with async_session_maker() as db:
            await seed_gamification_data(db)

    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        asyncio.run(run_seed())
