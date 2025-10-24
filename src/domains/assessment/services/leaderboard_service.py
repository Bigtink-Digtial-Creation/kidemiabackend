from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from src.domains.assessment.repositories.attempt_repository import (
    AssessmentAttemptRepository,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.auth.repositories.user_repository import UserRepository
from src.domains.assessment.schemas.statistics import (
    LeaderboardEntry,
    LeaderboardResponse,
)
from src.domains.assessment.enums import AttemptStatus


class LeaderboardService:
    """Service for leaderboard operations"""

    def __init__(self, db: Session):
        self.db = db
        self.attempt_repo = AssessmentAttemptRepository(db)
        self.assessment_repo = AssessmentRepository(db)
        self.user_repo = UserRepository(db)

    async def get_assessment_leaderboard(
        self,
        assessment_id: UUID,
        limit: int = 100,
        current_user_id: Optional[UUID] = None,
    ) -> LeaderboardResponse:
        """Get leaderboard for a specific assessment"""
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            from src.core.exceptions import ResourceNotFoundException

            raise ResourceNotFoundException("Assessment", assessment_id)

        # Get top attempts
        attempts = self.attempt_repo.get_leaderboard(assessment_id, limit)

        # Build leaderboard entries
        entries = []
        for rank, attempt in enumerate(attempts, 1):
            user = self.user_repo.get_by_id(attempt.user_id)

            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    user_id=attempt.user_id,
                    user_name=user.full_name if user else "Unknown",
                    score=attempt.score,
                    percentage=attempt.percentage,
                    time_spent_seconds=attempt.time_spent_seconds,
                    submitted_at=attempt.submitted_at,
                )
            )

        # Get user's rank if provided
        user_rank = None
        if current_user_id:
            user_attempt = self.attempt_repo.get_latest_attempt(
                current_user_id, assessment_id
            )
            if user_attempt and user_attempt.status == AttemptStatus.GRADED:
                user_rank = self.attempt_repo.calculate_rank(user_attempt.id)

        # Count total participants
        total_participants = self.attempt_repo.count(
            {
                "assessment_id": assessment_id,
                "status": AttemptStatus.GRADED,
                "is_deleted": False,
            }
        )

        return LeaderboardResponse(
            assessment_id=assessment_id,
            assessment_title=assessment.title,
            entries=entries,
            total_participants=total_participants,
            user_rank=user_rank,
        )

    async def get_global_leaderboard(
        self,
        limit: int = 100,
        assessment_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get global leaderboard across all assessments"""
        # TODO: Implement global leaderboard with aggregation
        # This would aggregate scores across multiple assessments
        pass

    async def get_subject_leaderboard(
        self, subject_id: UUID, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific subject"""
        # Get all assessments for subject
        assessments = self.assessment_repo.get_by_subject(subject_id)
        assessment_ids = [a.id for a in assessments]

        # Aggregate user scores
        from sqlalchemy import and_
        from src.domains.assessment.models.attempt import AssessmentAttempt

        user_scores = (
            self.db.query(
                AssessmentAttempt.user_id,
                func.count(AssessmentAttempt.id).label("total_attempts"),
                func.avg(AssessmentAttempt.score).label("average_score"),
                func.sum(AssessmentAttempt.points_earned).label("total_points"),
            )
            .filter(
                and_(
                    AssessmentAttempt.assessment_id.in_(assessment_ids),
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                )
            )
            .group_by(AssessmentAttempt.user_id)
            .order_by(desc("average_score"), desc("total_points"))
            .limit(limit)
            .all()
        )

        # Build leaderboard
        leaderboard = []
        for rank, (user_id, attempts, avg_score, total_points) in enumerate(
            user_scores, 1
        ):
            user = self.user_repo.get_by_id(user_id)

            leaderboard.append(
                {
                    "rank": rank,
                    "user_id": str(user_id),
                    "user_name": user.full_name if user else "Unknown",
                    "total_attempts": attempts,
                    "average_score": float(avg_score) if avg_score else 0.0,
                    "total_points": float(total_points) if total_points else 0.0,
                }
            )

        return leaderboard

    async def get_user_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """Get comprehensive statistics for a user"""
        from src.domains.assessment.models.attempt import AssessmentAttempt
        from sqlalchemy import and_

        # Overall stats
        total_attempts = self.attempt_repo.count(
            {"user_id": user_id, "is_deleted": False}
        )

        graded_attempts = self.attempt_repo.count(
            {"user_id": user_id, "status": AttemptStatus.GRADED, "is_deleted": False}
        )

        passed_attempts = self.attempt_repo.count(
            {
                "user_id": user_id,
                "status": AttemptStatus.GRADED,
                "passed": True,
                "is_deleted": False,
            }
        )

        # Average score
        avg_result = (
            self.db.query(func.avg(AssessmentAttempt.score))
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                )
            )
            .scalar()
        )

        average_score = float(avg_result) if avg_result else 0.0
        pass_rate = (
            (passed_attempts / graded_attempts * 100) if graded_attempts > 0 else 0.0
        )

        # Recent attempts
        recent_attempts = self.attempt_repo.get_user_attempts(
            user_id, status=AttemptStatus.GRADED, skip=0, limit=10
        )

        return {
            "user_id": str(user_id),
            "total_attempts": total_attempts,
            "graded_attempts": graded_attempts,
            "passed_attempts": passed_attempts,
            "pass_rate": pass_rate,
            "average_score": average_score,
            "recent_attempts": [
                {
                    "assessment_id": str(a.assessment_id),
                    "score": float(a.score),
                    "percentage": float(a.percentage),
                    "passed": a.passed,
                    "submitted_at": a.submitted_at,
                }
                for a in recent_attempts
            ],
        }
