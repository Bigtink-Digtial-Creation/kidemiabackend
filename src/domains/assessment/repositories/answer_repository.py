from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.shared.repositories.base import BaseRepository
from src.domains.assessment.models.answer import Answer
from datetime import datetime


class AnswerRepository(BaseRepository[Answer, dict, dict]):
    """Repository for Answer model"""

    def __init__(self, db: Session):
        super().__init__(Answer, db)

    def get_by_attempt(self, attempt_id: UUID) -> List[Answer]:
        """Get all answers for an attempt"""
        return (
            self.db.query(Answer)
            .filter(Answer.attempt_id == attempt_id, Answer.is_deleted.is_(False))
            .order_by(Answer.answer_order)
            .all()
        )

    def get_by_question(self, attempt_id: UUID, question_id: UUID) -> Optional[Answer]:
        """Get answer for a specific question in attempt"""
        return (
            self.db.query(Answer)
            .filter(
                Answer.attempt_id == attempt_id,
                Answer.question_id == question_id,
                Answer.is_deleted.is_(False),
            )
            .first()
        )

    def get_unanswered_questions(
        self, attempt_id: UUID, all_question_ids: List[UUID]
    ) -> List[UUID]:
        """Get IDs of unanswered questions"""
        answered_question_ids = (
            self.db.query(Answer.question_id)
            .filter(Answer.attempt_id == attempt_id, Answer.is_deleted.is_(False))
            .all()
        )
        answered_ids = [q[0] for q in answered_question_ids]
        return [qid for qid in all_question_ids if qid not in answered_ids]

    def get_flagged_answers(self, attempt_id: UUID) -> List[Answer]:
        """Get flagged answers for an attempt"""
        return (
            self.db.query(Answer)
            .filter(
                Answer.attempt_id == attempt_id,
                Answer.flagged_for_review.is_(True),
                Answer.is_deleted.is_(False),
            )
            .all()
        )

    def get_pending_manual_grading(
        self, attempt_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Answer]:
        """Get answers pending manual grading"""
        query = self.db.query(Answer).filter(
            Answer.requires_manual_grading.is_(True),
            Answer.manually_graded.is_(False),
            Answer.is_deleted.is_(False),
        )
        if attempt_id:
            query = query.filter(Answer.attempt_id == attempt_id)
        return query.offset(skip).limit(limit).all()

    def bulk_update_grading(self, answer_ids: List[UUID], grader_id: UUID) -> int:
        """Bulk update grading status"""

        updated = (
            self.db.query(Answer)
            .filter(Answer.id.in_(answer_ids))
            .update(
                {
                    "manually_graded": True,
                    "graded_by": grader_id,
                    "graded_at": datetime.utcnow(),
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return updated
