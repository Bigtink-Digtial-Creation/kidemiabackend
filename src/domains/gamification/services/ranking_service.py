# src/domains/assessment/services/leaderboard_service.py

from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.gamification.repositories.ranking_repo import (
    AssessmentLeaderboardRepository,
)
from src.domains.gamification.schemas.schemas import (
    AssessmentLeaderboardEntry,
    AssessmentLeaderboardResponse,
)


class AssessmentLeaderboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssessmentLeaderboardRepository(db)

    async def get_assessment_leaderboard(
        self,
        assessment_id: UUID,
        limit: int = 100,
        offset: int = 0,
        current_user_id: Optional[UUID] = None,
        assessment_title: Optional[str] = None,
    ) -> AssessmentLeaderboardResponse:

        attempts = await self.repo.get_leaderboard_entries(
            assessment_id=assessment_id,
            limit=limit,
            offset=offset,
        )
        total = await self.repo.get_total_participants(assessment_id)

        entries = []
        for i, attempt in enumerate(attempts, start=offset + 1):
            user = attempt.user
            percentile = round(((total - i) / total) * 100, 1) if total > 0 else None
            entries.append(
                AssessmentLeaderboardEntry(
                    rank=i,
                    user_id=attempt.user_id,
                    student_name=user.full_name if user else "Unknown",
                    student_avatar=user.profile_picture_url if user else None,
                    score=float(attempt.percentage),
                    points_earned=float(attempt.points_earned),
                    attempt_number=attempt.attempt_number,
                    submitted_at=attempt.submitted_at,
                    is_current_user=(
                        current_user_id is not None
                        and attempt.user_id == current_user_id
                    ),
                    percentile=percentile,
                )
            )

        current_user_rank = None
        if current_user_id:
            current_user_rank = await self.repo.get_user_rank(
                assessment_id=assessment_id,
                user_id=current_user_id,
            )

        return AssessmentLeaderboardResponse(
            assessment_id=assessment_id,
            assessment_title=assessment_title,
            entries=entries,
            total_participants=total,
            current_user_rank=current_user_rank,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
