from uuid import UUID
from typing import List, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.enums import AttemptStatus


class AssessmentLeaderboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_leaderboard_entries(
        self,
        assessment_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AssessmentAttempt]:

        best_attempt_subq = (
            select(
                AssessmentAttempt.user_id,
                func.max(AssessmentAttempt.percentage).label("max_percentage"),
            )
            .where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
            )
            .group_by(AssessmentAttempt.user_id)
            .subquery()
        )

        query = (
            select(AssessmentAttempt)
            .join(
                best_attempt_subq,
                (AssessmentAttempt.user_id == best_attempt_subq.c.user_id)
                & (AssessmentAttempt.percentage == best_attempt_subq.c.max_percentage)
                & (AssessmentAttempt.assessment_id == assessment_id),
            )
            .options(
                selectinload(AssessmentAttempt.user),
            )
            .order_by(
                desc(AssessmentAttempt.percentage),
                AssessmentAttempt.submitted_at.asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_total_participants(self, assessment_id: UUID) -> int:
        """Count distinct users who have submitted at least one attempt."""
        result = await self.db.execute(
            select(func.count(func.distinct(AssessmentAttempt.user_id))).where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
            )
        )
        return result.scalar_one()

    async def get_user_rank(self, assessment_id: UUID, user_id: UUID) -> Optional[int]:
        best_pct_result = await self.db.execute(
            select(func.max(AssessmentAttempt.percentage)).where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
            )
        )
        best_pct = best_pct_result.scalar_one_or_none()

        if best_pct is None:
            return None
        higher_count_result = await self.db.execute(
            select(func.count(func.distinct(AssessmentAttempt.user_id))).where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                AssessmentAttempt.percentage > best_pct,
            )
        )
        higher_count = higher_count_result.scalar_one()
        return higher_count + 1

    async def get_user_percentile(
        self, assessment_id: UUID, user_id: UUID, total: int
    ) -> Optional[float]:
        """Percentile = percentage of participants this user scored higher than."""
        if total == 0:
            return None

        best_pct_result = await self.db.execute(
            select(func.max(AssessmentAttempt.percentage)).where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
            )
        )
        best_pct = best_pct_result.scalar_one_or_none()
        if best_pct is None:
            return None

        # Count users who scored strictly lower
        lower_count_result = await self.db.execute(
            select(func.count(func.distinct(AssessmentAttempt.user_id))).where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                AssessmentAttempt.percentage < best_pct,
            )
        )
        lower_count = lower_count_result.scalar_one()
        return round((lower_count / total) * 100, 1)
