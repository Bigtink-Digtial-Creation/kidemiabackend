from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from src.shared.repositories.base import BaseRepository
from src.domains.content.models.topic import Topic
from src.domains.content.schemas.subject import TopicCreate, TopicUpdate


class TopicRepository(BaseRepository[Topic, TopicCreate, TopicUpdate]):
    """Repository for Topic model"""

    def __init__(self, db: Session):
        super().__init__(Topic, db)

    def get_by_code(self, code: str, subject_id: UUID) -> Optional[Topic]:
        """Get topic by code within a subject"""
        return (
            self.db.query(Topic)
            .filter(Topic.code == code, Topic.subject_id == subject_id)
            .first()
        )

    def get_by_name(self, name: str, subject_id: UUID) -> Optional[Topic]:
        """Get topic by name within a subject (case-insensitive)"""
        return (
            self.db.query(Topic)
            .filter(
                func.lower(Topic.name) == name.lower(),
                Topic.subject_id == subject_id,
                Topic.is_deleted.is_(False),
            )
            .first()
        )

    def get_by_subject(
        self, subject_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Topic]:
        """Get topics by subject"""
        return (
            self.db.query(Topic)
            .filter(Topic.subject_id == subject_id, Topic.is_deleted.is_(False))
            .order_by(Topic.order, Topic.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_topics(
        self, subject_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Topic]:
        """Get active topics, optionally filtered by subject"""
        query = self.db.query(Topic).filter(
            Topic.is_active.is_(True), Topic.is_deleted.is_(False)
        )

        if subject_id:
            query = query.filter(Topic.subject_id == subject_id)

        return query.order_by(Topic.order, Topic.name).offset(skip).limit(limit).all()

    def get_root_topics(
        self, subject_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Topic]:
        """Get topics with no parent (root level) for a subject"""
        return (
            self.db.query(Topic)
            .filter(
                Topic.subject_id == subject_id,
                Topic.parent_id.is_(None),
                Topic.is_deleted.is_(False),
            )
            .order_by(Topic.order, Topic.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_subtopics(self, parent_id: UUID) -> List[Topic]:
        """Get subtopics of a parent topic"""
        return (
            self.db.query(Topic)
            .filter(Topic.parent_id == parent_id, Topic.is_deleted.is_(False))
            .order_by(Topic.order, Topic.name)
            .all()
        )

    def search_topics(
        self,
        query: str,
        subject_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Topic]:
        """Search topics by name, code, or description"""
        search_term = f"%{query}%"
        db_query = self.db.query(Topic).filter(
            or_(
                Topic.name.ilike(search_term),
                Topic.code.ilike(search_term),
                Topic.description.ilike(search_term),
            ),
            Topic.is_deleted.is_(False),
        )

        if subject_id:
            db_query = db_query.filter(Topic.subject_id == subject_id)

        return db_query.offset(skip).limit(limit).all()

    def get_with_stats(self, topic_id: UUID) -> Optional[dict]:
        """Get topic with statistics"""
        from src.domains.content.models.question import Question

        topic = self.get_by_id(topic_id)
        if not topic:
            return None

        questions_count = (
            self.db.query(func.count(Question.id))
            .filter(Question.topic_id == topic_id, Question.is_deleted.is_(False))
            .scalar()
        )

        return {"topic": topic, "questions_count": questions_count or 0}
