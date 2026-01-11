from typing import List, Optional
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.shared.repositories.base import BaseRepository
from src.domains.content.models.question import Question, QuestionTag
from src.domains.content.schemas.question import QuestionCreate, QuestionUpdate
from src.domains.content.enums import QuestionType, DifficultyLevel, QuestionStatus


class QuestionRepository(BaseRepository[Question, QuestionCreate, QuestionUpdate]):
    """Repository for Question model"""

    def __init__(self, db: Session):
        super().__init__(Question, db)

    def get_ids_by_topics(
        self,
        topic_ids: List[UUID],
        difficulty: Optional[DifficultyLevel] = None,
        question_types: Optional[List[QuestionType]] = None,
    ) -> List[UUID]:
        """Efficiently fetch only IDs for multiple topics and filters"""
        query = self.db.query(Question.id).filter(
            Question.topic_id.in_(topic_ids),
            Question.status == QuestionStatus.APPROVED,
            Question.is_deleted.is_(False),
        )

        if difficulty:
            query = query.filter(Question.difficulty_level == difficulty)

        if question_types:
            query = query.filter(Question.question_type.in_(question_types))
        return [q_id[0] for q_id in query.all()]

    def get_with_options(self, question_id: UUID) -> Optional[Question]:
        """Get question with all options loaded"""
        return (
            self.db.query(Question)
            .options(joinedload(Question.options))
            .filter(Question.id == question_id)
            .first()
        )

    def get_by_subject(
        self,
        subject_id: UUID,
        status: Optional[QuestionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Get questions by subject"""
        query = self.db.query(Question).filter(
            Question.subject_id == subject_id, Question.is_deleted.is_(False)
        )

        if status:
            query = query.filter(Question.status == status)

        return query.offset(skip).limit(limit).all()

    def get_by_topic(
        self,
        topic_id: UUID,
        status: Optional[QuestionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Get questions by topic"""
        query = self.db.query(Question).filter(
            Question.topic_id == topic_id, Question.is_deleted.is_(False)
        )

        if status:
            query = query.filter(Question.status == status)

        return query.offset(skip).limit(limit).all()

    def get_by_difficulty(
        self,
        difficulty: DifficultyLevel,
        subject_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Get questions by difficulty level"""
        query = self.db.query(Question).filter(
            Question.difficulty_level == difficulty, Question.is_deleted.is_(False)
        )

        if subject_id:
            query = query.filter(Question.subject_id == subject_id)

        return query.offset(skip).limit(limit).all()

    def get_by_type(
        self,
        question_type: QuestionType,
        subject_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Get questions by type"""
        query = self.db.query(Question).filter(
            Question.question_type == question_type, Question.is_deleted.is_(False)
        )

        if subject_id:
            query = query.filter(Question.subject_id == subject_id)

        return query.offset(skip).limit(limit).all()

    def get_approved_questions(
        self,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty: Optional[DifficultyLevel] = None,
        question_type: Optional[QuestionType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Get approved questions with optional filters"""
        query = self.db.query(Question).filter(
            Question.status == QuestionStatus.APPROVED, Question.is_deleted.is_(False)
        )

        if subject_id:
            query = query.filter(Question.subject_id == subject_id)
        if topic_id:
            query = query.filter(Question.topic_id == topic_id)
        if difficulty:
            query = query.filter(Question.difficulty_level == difficulty)
        if question_type:
            query = query.filter(Question.question_type == question_type)

        return query.offset(skip).limit(limit).all()

    def get_random_questions(
        self,
        count: int,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty: Optional[DifficultyLevel] = None,
        question_type: Optional[QuestionType] = None,
    ) -> List[Question]:
        """Get random approved questions"""
        query = (
            self.db.query(Question)
            .options(joinedload(Question.options))
            .filter(
                Question.status == QuestionStatus.APPROVED,
                Question.is_deleted.is_(False),
            )
        )

        if subject_id:
            query = query.filter(Question.subject_id == subject_id)
        if topic_id:
            query = query.filter(Question.topic_id == topic_id)
        if difficulty:
            query = query.filter(Question.difficulty_level == difficulty)
        if question_type:
            query = query.filter(Question.question_type == question_type)

        return query.order_by(func.random()).limit(count).all()

    def update_statistics(
        self, question_id: UUID, is_correct: bool
    ) -> Optional[Question]:
        """Update question statistics"""
        question = self.get_by_id(question_id)
        if not question:
            return None

        question.times_used += 1
        if is_correct:
            question.times_correct += 1
        else:
            question.times_incorrect += 1

        self.db.commit()
        self.db.refresh(question)
        return question

    def approve_question(
        self, question_id: UUID, reviewer_id: UUID
    ) -> Optional[Question]:
        """Approve a question"""
        from datetime import datetime

        question = self.get_by_id(question_id)
        if not question:
            return None

        question.status = QuestionStatus.APPROVED
        question.reviewed_by = reviewer_id
        question.approved_at = str(datetime.utcnow())

        self.db.commit()
        self.db.refresh(question)
        return question

    def reject_question(self, question_id: UUID) -> Optional[Question]:
        """Reject a question"""
        return self.update(question_id, {"status": QuestionStatus.REJECTED})

    def submit_for_review(self, question_id: UUID) -> Optional[Question]:
        """Submit question for review"""
        return self.update(question_id, {"status": QuestionStatus.REVIEW})

    def search_questions(
        self,
        query: str,
        subject_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Search questions by text"""
        search_term = f"%{query}%"
        db_query = self.db.query(Question).filter(
            Question.question_text.ilike(search_term), Question.is_deleted.is_(False)
        )

        if subject_id:
            db_query = db_query.filter(Question.subject_id == subject_id)

        return db_query.offset(skip).limit(limit).all()

    def get_by_tags(
        self, tag_ids: List[UUID], skip: int = 0, limit: int = 100
    ) -> List[Question]:
        """Get questions by tags"""
        return (
            self.db.query(Question)
            .join(Question.tags)
            .filter(QuestionTag.id.in_(tag_ids), Question.is_deleted.is_(False))
            .distinct()
            .offset(skip)
            .limit(limit)
            .all()
        )
