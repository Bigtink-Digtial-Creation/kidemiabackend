from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload

from src.shared.repositories.base import BaseRepository
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.enums import AttemptStatus, GradingStatus


class AssessmentAttemptRepository(BaseRepository[AssessmentAttempt, dict, dict]):
    """Repository for AssessmentAttempt model"""

    def __init__(self, db: Session):
        super().__init__(AssessmentAttempt, db)

    def get_with_assessment(self, attempt_id: UUID):
        return (
            self.db.query(AssessmentAttempt)
            .join(AssessmentAttempt.assessment)
            .filter(AssessmentAttempt.id == attempt_id)
            .first()
        )

    def get_with_answers(self, attempt_id: UUID) -> Optional[AssessmentAttempt]:
        """Get attempt with answers loaded"""
        return (
            self.db.query(AssessmentAttempt)
            .options(joinedload(AssessmentAttempt.answers))
            .filter(AssessmentAttempt.id == attempt_id)
            .first()
        )

    def get_by_user_and_assessment(
        self, user_id: UUID, assessment_id: UUID
    ) -> List[AssessmentAttempt]:
        """Get all attempts for a user on specific assessment"""
        return (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(AssessmentAttempt.attempt_number)
            .all()
        )

    def get_assessment_attempts(
        self,
        assessment_id: UUID,
        status: Optional[AttemptStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AssessmentAttempt]:
        """Get all attempts for an assessment"""
        query = (
            self.db.query(AssessmentAttempt)
            .options(joinedload(AssessmentAttempt.user))
            .filter(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.is_deleted.is_(False),
            )
        )

        if status:
            query = query.filter(AssessmentAttempt.status == status)

        return (
            query.order_by(desc(AssessmentAttempt.started_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_attempt(
        self, user_id: UUID, assessment_id: UUID
    ) -> Optional[AssessmentAttempt]:
        """Get latest attempt for user"""
        return (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(desc(AssessmentAttempt.attempt_number))
            .first()
        )

    def get_active_attempt(
        self, user_id: UUID, assessment_id: UUID
    ) -> Optional[AssessmentAttempt]:
        """Get active (in-progress) attempt"""
        return (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.IN_PROGRESS,
                AssessmentAttempt.is_deleted.is_(False),
            )
            .first()
        )

    def count_user_attempts(
        self,
        user_id: UUID,
        assessment_id: UUID,
        exclude_status: Optional[List[AttemptStatus]] = None,
    ) -> int:
        """Count user attempts for an assessment"""
        query = self.db.query(func.count(AssessmentAttempt.id)).filter(
            AssessmentAttempt.user_id == user_id,
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.is_deleted.is_(False),
        )

        if exclude_status:
            query = query.filter(AssessmentAttempt.status.notin_(exclude_status))

        return query.scalar() or 0

    def get_user_attempts(
        self,
        user_id: UUID,
        status: Optional[AttemptStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AssessmentAttempt]:
        """Get all attempts for a user"""
        query = self.db.query(AssessmentAttempt).filter(
            AssessmentAttempt.user_id == user_id,
            AssessmentAttempt.is_deleted.is_(False),
        )

        if status:
            query = query.filter(AssessmentAttempt.status == status)

        return (
            query.order_by(desc(AssessmentAttempt.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_best_attempt(
        self, user_id: UUID, assessment_id: UUID
    ) -> Optional[AssessmentAttempt]:
        """Get user's best attempt for an assessment"""
        return (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                AssessmentAttempt.is_(False),
            )
            .order_by(desc(AssessmentAttempt.score_percentage))
            .first()
        )

    def get_pending_grading(
        self, skip: int = 0, limit: int = 100
    ) -> List[AssessmentAttempt]:
        """Get attempts pending manual grading"""
        return (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.status == AttemptStatus.SUBMITTED,
                AssessmentAttempt.requires_manual_grading.is_(True),
                AssessmentAttempt.grading_status.in_(
                    [GradingStatus.PENDING, GradingStatus.MANUAL_GRADING]
                ),
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(AssessmentAttempt.submitted_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_leaderboard(
        self, assessment_id: UUID, limit: int = 100
    ) -> List[AssessmentAttempt]:
        """Get leaderboard for an assessment"""
        return (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(
                desc(AssessmentAttempt.score), AssessmentAttempt.time_spent_seconds
            )
            .limit(limit)
            .all()
        )

    def calculate_rank(self, attempt_id: UUID) -> Optional[int]:
        """Calculate rank for an attempt"""
        attempt = self.get_by_id(attempt_id)
        if not attempt or attempt.status != AttemptStatus.GRADED:
            return None

        rank = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(
                AssessmentAttempt.assessment_id == attempt.assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                or_(
                    AssessmentAttempt.score > attempt.score,
                    and_(
                        AssessmentAttempt.score == attempt.score,
                        AssessmentAttempt.time_spent_seconds
                        < attempt.time_spent_seconds,
                    ),
                ),
                AssessmentAttempt.is_deleted.is_(False),
            )
            .scalar()
        )

        return (rank or 0) + 1

    def update_rank(self, attempt_id: UUID) -> Optional[AssessmentAttempt]:
        """Update rank for an attempt"""
        attempt = self.get_by_id(attempt_id)
        if not attempt:
            return None

        attempt.rank = self.calculate_rank(attempt_id)

        # Calculate percentile
        total_graded = self.count(
            {
                "assessment_id": attempt.assessment_id,
                "status": AttemptStatus.GRADED,
                "is_deleted": False,
            }
        )

        if total_graded > 0 and attempt.rank:
            attempt.percentile = (
                (total_graded - attempt.rank + 1) / total_graded
            ) * 100

        self.db.commit()
        self.db.refresh(attempt)
        return attempt
