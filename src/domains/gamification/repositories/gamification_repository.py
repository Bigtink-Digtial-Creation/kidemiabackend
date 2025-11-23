from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.auth.models.student import Student
from src.domains.gamification.models import (
    GamificationProfile,
    Badge,
    StudentBadge,
    Achievement,
    StudentAchievement,
)


class GamificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Profile
    async def get_profile_by_student_id(
        self, student_id: UUID
    ) -> Optional[GamificationProfile]:
        query = (
            select(GamificationProfile)
            .where(GamificationProfile.student_id == student_id)
            .options(
                selectinload(GamificationProfile.badges).selectinload(
                    StudentBadge.badge
                ),
                selectinload(GamificationProfile.achievements).selectinload(
                    StudentAchievement.achievement
                ),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_profile(self, student_id: UUID) -> GamificationProfile:
        profile = GamificationProfile(student_id=student_id)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def update_profile(self, profile: GamificationProfile) -> GamificationProfile:
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def get_or_create_profile(self, student_id: UUID) -> GamificationProfile:
        profile = await self.get_profile_by_student_id(student_id)
        if not profile:
            profile = await self.create_profile(student_id)
        return profile

    # Badges
    async def get_all_active_badges(self) -> List[Badge]:
        query = select(Badge).where(Badge.is_active.is_(True))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_badge_by_id(self, badge_id: UUID) -> Optional[Badge]:
        query = select(Badge).where(Badge.id == badge_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_badge_by_name(self, name: str) -> Optional[Badge]:
        query = select(Badge).where(Badge.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_badge(self, badge_data: dict) -> Badge:
        badge = Badge(**badge_data)
        self.db.add(badge)
        await self.db.flush()
        return badge

    async def get_student_badges(self, profile_id: UUID) -> List[StudentBadge]:
        query = (
            select(StudentBadge)
            .where(StudentBadge.profile_id == profile_id)
            .options(selectinload(StudentBadge.badge))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def has_badge(self, profile_id: UUID, badge_id: UUID) -> bool:
        query = select(StudentBadge).where(
            and_(
                StudentBadge.profile_id == profile_id,
                StudentBadge.badge_id == badge_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def award_badge(self, profile_id: UUID, badge_id: UUID) -> StudentBadge:
        student_badge = StudentBadge(
            profile_id=profile_id,
            badge_id=badge_id,
            earned_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(student_badge)
        await self.db.flush()
        return student_badge

    # ACHIEVEMENTS
    async def get_all_active_achievements(self) -> List[Achievement]:
        query = select(Achievement).where(Achievement.is_active.is_(True))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_achievement_by_id(
        self, achievement_id: UUID
    ) -> Optional[Achievement]:
        query = select(Achievement).where(Achievement.id == achievement_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_achievement(self, achievement_data: dict) -> Achievement:
        achievement = Achievement(**achievement_data)
        self.db.add(achievement)
        await self.db.flush()
        return achievement

    async def get_student_achievements(
        self, profile_id: UUID
    ) -> List[StudentAchievement]:
        query = (
            select(StudentAchievement)
            .where(StudentAchievement.profile_id == profile_id)
            .options(selectinload(StudentAchievement.achievement))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_student_achievement(
        self, profile_id: UUID, achievement_id: UUID
    ) -> Optional[StudentAchievement]:
        query = select(StudentAchievement).where(
            and_(
                StudentAchievement.profile_id == profile_id,
                StudentAchievement.achievement_id == achievement_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_student_achievement(
        self, profile_id: UUID, achievement_id: UUID
    ) -> StudentAchievement:
        student_achievement = StudentAchievement(
            profile_id=profile_id,
            achievement_id=achievement_id,
            current_value=0,
            is_completed=False,
        )
        self.db.add(student_achievement)
        await self.db.flush()
        return student_achievement

    async def update_student_achievement(
        self, student_achievement: StudentAchievement
    ) -> StudentAchievement:
        await self.db.flush()
        await self.db.refresh(student_achievement)
        return student_achievement

    # LEADERBOARD
    async def get_leaderboard(
        self,
        limit: int = 100,
        offset: int = 0,
        category_id: Optional[UUID] = None,
        institution_id: Optional[UUID] = None,
    ) -> List[GamificationProfile]:
        query = (
            select(GamificationProfile)
            .join(GamificationProfile.student)
            .order_by(desc(GamificationProfile.total_points))
            .limit(limit)
            .offset(offset)
        )

        if category_id:
            query = query.where(Student.category_id == category_id)

        if institution_id:
            query = query.where(Student.institution_id == institution_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_student_rank(self, student_id: UUID) -> Optional[int]:
        profile = await self.get_profile_by_student_id(student_id)
        if not profile:
            return None

        query = select(func.count(GamificationProfile.id)).where(
            GamificationProfile.total_points > profile.total_points
        )
        result = await self.db.execute(query)
        rank = result.scalar() + 1
        return rank

    async def update_leaderboard_positions(self) -> None:
        """Batch update all leaderboard positions - run as scheduled job"""
        query = select(GamificationProfile).order_by(
            desc(GamificationProfile.total_points)
        )
        result = await self.db.execute(query)
        profiles = result.scalars().all()

        for i, profile in enumerate(profiles, start=1):
            profile.leaderboard_position = i

        await self.db.flush()

    async def get_total_participants(self) -> int:
        query = select(func.count(GamificationProfile.id))
        result = await self.db.execute(query)
        return result.scalar() or 0
