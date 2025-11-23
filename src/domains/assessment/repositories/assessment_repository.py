from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from sqlalchemy import or_, desc
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from src.shared.repositories.base import BaseRepository
from src.domains.assessment.models.assessment import Assessment
from src.domains.assessment.models.category import AssessmentCategoryConfig
from src.domains.payment.models.transaction import Transaction
from src.domains.payment.models.subscription import Subscription
from src.domains.payment.models.refund import Refund
from src.domains.payment.models.wallet import Wallet
from src.domains.payment.models.payout import Payout
from src.domains.institution.models.institution import Institution
from src.domains.auth.models.student import Student
from src.domains.gamification.models import (
    GamificationProfile,
    Badge,
    StudentBadge,
    Achievement,
    StudentAchievement,
)

from src.domains.assessment.enums import (
    AssessmentType,
    AssessmentCategory,
    AssessmentStatus,
)


class AssessmentRepository(BaseRepository[Assessment, dict, dict]):
    """Repository for Assessment model"""

    def __init__(self, db: Session):
        super().__init__(Assessment, db)

    def get_with_questions(self, assessment_id: UUID) -> Optional[Assessment]:
        """Get assessment with questions loaded"""
        return (
            self.db.query(Assessment)
            .options(joinedload(Assessment.questions), joinedload(Assessment.sections))
            .filter(Assessment.id == assessment_id)
            .first()
        )

    def get_by_code(self, code: str) -> Optional[Assessment]:
        """Get assessment by code"""
        return (
            self.db.query(Assessment)
            .filter(Assessment.code == code, Assessment.is_deleted.is_(False))
            .first()
        )

    def code_exists(self, code: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if code exists"""
        query = self.db.query(Assessment).filter(
            Assessment.code == code, Assessment.is_deleted.is_(False)
        )
        if exclude_id:
            query = query.filter(Assessment.id != exclude_id)
        return query.first() is not None

    def get_by_type(
        self, assessment_type: AssessmentType, skip: int = 0, limit: int = 100
    ) -> List[Assessment]:
        """Get assessments by type"""
        return (
            self.db.query(Assessment)
            .filter(
                Assessment.assessment_type == assessment_type,
                Assessment.is_deleted.is_(False),
            )
            .order_by(desc(Assessment.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_category(
        self,
        category: AssessmentCategory,
        status: Optional[AssessmentStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Assessment]:
        """Get assessments by category"""
        query = self.db.query(Assessment).filter(
            Assessment.category == category, Assessment.is_deleted.is_(False)
        )

        if status:
            query = query.filter(Assessment.status == status)

        return (
            query.order_by(desc(Assessment.exam_year), Assessment.title)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_published(
        self,
        assessment_type: Optional[AssessmentType] = None,
        category: Optional[AssessmentCategory] = None,
        subject_id: Optional[UUID] = None,
        exam_year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Assessment]:
        """Get published assessments with filters"""
        query = self.db.query(Assessment).filter(
            Assessment.status == AssessmentStatus.PUBLISHED,
            Assessment.is_public.is_(True),
            Assessment.is_deleted.is_(False),
        )

        if assessment_type:
            query = query.filter(Assessment.assessment_type == assessment_type)
        if category:
            query = query.filter(Assessment.category == category)
        if subject_id:
            query = query.filter(Assessment.subject_id == subject_id)
        if exam_year:
            query = query.filter(Assessment.exam_year == exam_year)

        return (
            query.order_by(desc(Assessment.created_at)).offset(skip).limit(limit).all()
        )

    def get_by_subject(
        self,
        subject_id: UUID,
        status: Optional[AssessmentStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Assessment]:
        """Get assessments by subject"""
        query = self.db.query(Assessment).filter(
            Assessment.subject_id == subject_id, Assessment.is_deleted.is_(False)
        )

        if status:
            query = query.filter(Assessment.status == status)

        return query.offset(skip).limit(limit).all()

    def get_by_institution(
        self, institution_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Assessment]:
        """Get assessments by institution"""
        return (
            self.db.query(Assessment)
            .filter(
                Assessment.institution_id == institution_id,
                Assessment.is_deleted.is_(False),
            )
            .order_by(desc(Assessment.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_available_now(
        self,
        assessment_type: Optional[AssessmentType] = None,
        category: Optional[AssessmentCategory] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Assessment]:
        """Get assessments available now"""
        now = datetime.now(timezone.utc).isoformat()

        query = self.db.query(Assessment).filter(
            Assessment.status == AssessmentStatus.PUBLISHED,
            Assessment.is_public.is_(True),
            Assessment.is_deleted.is_(False),
            or_(Assessment.available_from.is_(None), Assessment.available_from <= now),
            or_(
                Assessment.available_until.is_(None), Assessment.available_until >= now
            ),
        )

        if assessment_type:
            query = query.filter(Assessment.assessment_type == assessment_type)
        if category:
            query = query.filter(Assessment.category == category)

        return query.offset(skip).limit(limit).all()

    def search_assessments(
        self,
        query: str,
        assessment_type: Optional[AssessmentType] = None,
        category: Optional[AssessmentCategory] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Assessment]:
        """Search assessments"""
        search_term = f"%{query}%"
        db_query = self.db.query(Assessment).filter(
            or_(
                Assessment.title.ilike(search_term),
                Assessment.code.ilike(search_term),
                Assessment.description.ilike(search_term),
            ),
            Assessment.is_deleted.is_(False),
        )

        if assessment_type:
            db_query = db_query.filter(Assessment.assessment_type == assessment_type)
        if category:
            db_query = db_query.filter(Assessment.category == category)

        return db_query.offset(skip).limit(limit).all()

    def get_popular(
        self, assessment_type: Optional[AssessmentType] = None, limit: int = 10
    ) -> List[Assessment]:
        """Get popular assessments by attempt count"""
        query = self.db.query(Assessment).filter(
            Assessment.status == AssessmentStatus.PUBLISHED,
            Assessment.is_public.is_(True),
            Assessment.is_deleted.is_(False),
        )

        if assessment_type:
            query = query.filter(Assessment.assessment_type == assessment_type)

        return query.order_by(desc(Assessment.total_attempts)).limit(limit).all()

    def update_statistics(
        self,
        assessment_id: UUID,
        completed: bool = False,
        passed: bool = False,
        score: Optional[float] = None,
        completion_time: Optional[int] = None,
    ) -> Optional[Assessment]:
        """Update assessment statistics"""
        assessment = self.get_by_id(assessment_id)
        if not assessment:
            return None

        assessment.total_attempts += 1

        if completed:
            assessment.total_completions += 1

            if passed:
                assessment.total_passes += 1
            else:
                assessment.total_fails += 1

            # Update average score
            if score is not None:
                # Convert to Decimal for consistent arithmetic
                score_decimal = Decimal(str(score))
                average_score = (
                    Decimal(str(assessment.average_score))
                    if assessment.average_score
                    else Decimal("0")
                )

                total_scores = (
                    average_score * (assessment.total_completions - 1) + score_decimal
                )
                assessment.average_score = float(
                    total_scores / assessment.total_completions
                )

                # Update highest/lowest scores
                if score > float(assessment.highest_score):
                    assessment.highest_score = score
                if assessment.lowest_score == 0 or score < float(
                    assessment.lowest_score
                ):
                    assessment.lowest_score = score

            # Update average completion time
            if completion_time is not None:
                # Convert to Decimal for consistent arithmetic
                avg_time = (
                    Decimal(str(assessment.average_completion_time))
                    if assessment.average_completion_time
                    else Decimal("0")
                )
                completion_time_decimal = Decimal(str(completion_time))

                total_time = (
                    avg_time * (assessment.total_completions - 1)
                    + completion_time_decimal
                )
                assessment.average_completion_time = int(
                    total_time / assessment.total_completions
                )

        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def get_years_available(self, category: AssessmentCategory) -> List[int]:
        """Get list of years with assessments for a category"""
        years = (
            self.db.query(Assessment.exam_year)
            .filter(
                Assessment.category == category,
                Assessment.exam_year.isnot(None),
                Assessment.is_deleted.is_(False),
            )
            .distinct()
            .order_by(desc(Assessment.exam_year))
            .all()
        )
        return [year[0] for year in years if year[0]]
