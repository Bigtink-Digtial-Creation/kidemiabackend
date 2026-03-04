from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.shared.repositories.base import BaseRepository
from src.domains.content.models.subject import Subject
from src.domains.content.schemas.subject import SubjectCreate, SubjectUpdate


class SubjectRepository(BaseRepository[Subject, SubjectCreate, SubjectUpdate]):
    """Repository for Subject model"""

    def __init__(self, db: Session):
        super().__init__(Subject, db)

    def get_by_code(self, code: str) -> Optional[Subject]:
        """Get subject by code"""
        return self.db.query(Subject).filter(Subject.code == code).first()

    def get_by_name(
        self, name: str, category_id: Optional[UUID] = None
    ) -> Optional[Subject]:
        """Get subject by name, optionally scoped by category"""
        query = self.db.query(Subject).filter(Subject.name == name)
        if category_id:
            query = query.filter(Subject.category_id == category_id)
        return query.first()

    def code_exists(self, code: str, exclude_id: Optional[UUID] = None) -> bool:
        filters = [
            Subject.code == code,
            Subject.is_deleted.is_(False),
        ]

        if exclude_id:
            filters.append(Subject.id != exclude_id)

        return self.db.query(self.db.query(Subject).filter(*filters).exists()).scalar()

    def name_exists(
        self,
        name: str,
        category_id: Optional[UUID] = None,
        exclude_id: Optional[UUID] = None,
    ) -> bool:
        """
        Check if subject name exists.
        Now scoped to category_id to allow the same name across different systems.
        """
        query = self.db.query(Subject).filter(
            Subject.name == name,
            Subject.category_id == category_id,
            Subject.is_deleted.is_(False),
        )
        if exclude_id:
            query = query.filter(Subject.id != exclude_id)
        return query.first() is not None

    def get_active_subjects(
        self, skip: int = 0, limit: int = 100, category_id: UUID = None
    ) -> List[Subject]:
        """Get all active subjects with optional category filtering"""
        query = self.db.query(Subject).filter(
            Subject.is_active.is_(True), Subject.is_deleted.is_(False)
        )

        if category_id:
            query = query.filter(Subject.category_id == category_id)

        return (
            query.order_by(Subject.order, Subject.name).offset(skip).limit(limit).all()
        )

    def get_featured_subjects(self, limit: int = 10) -> List[Subject]:
        """Get featured subjects"""
        return (
            self.db.query(Subject)
            .filter(
                Subject.is_featured.is_(True),
                Subject.is_active.is_(True),
                Subject.is_deleted.is_(False),
            )
            .order_by(Subject.order)
            .limit(limit)
            .all()
        )

    def get_root_subjects(self, skip: int = 0, limit: int = 100) -> List[Subject]:
        """Get subjects with no parent (root level)"""
        return (
            self.db.query(Subject)
            .filter(Subject.parent_id.is_(None), Subject.is_deleted.is_(False))
            .order_by(Subject.order, Subject.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_children(self, parent_id: UUID) -> List[Subject]:
        """Get child subjects of a parent"""
        return (
            self.db.query(Subject)
            .filter(Subject.parent_id == parent_id, Subject.is_deleted.is_(False))
            .order_by(Subject.order, Subject.name)
            .all()
        )

    def search_subjects(
        self,
        query: Optional[str] = None,  # Made Optional
        category_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Subject]:
        """Search subjects with dynamic filters."""
        stmt = self.db.query(Subject).filter(Subject.is_deleted.is_(False))
        if query and query.strip():
            search_term = f"%{query}%"
            stmt = stmt.filter(
                or_(
                    Subject.name.ilike(search_term),
                    Subject.code.ilike(search_term),
                    Subject.description.ilike(search_term),
                )
            )

        if category_id:
            stmt = stmt.filter(Subject.category_id == category_id)

        return stmt.offset(skip).limit(limit).all()

    def count_search_results(
        self, query: Optional[str] = None, category_id: Optional[UUID] = None
    ) -> int:
        """Counts matching subjects using the same logic as search."""
        stmt = self.db.query(Subject).filter(Subject.is_deleted.is_(False))

        if query and query.strip():
            search_term = f"%{query}%"
            stmt = stmt.filter(
                or_(
                    Subject.name.ilike(search_term),
                    Subject.code.ilike(search_term),
                    Subject.description.ilike(search_term),
                )
            )

        if category_id:
            stmt = stmt.filter(Subject.category_id == category_id)

        return stmt.count()

    def get_with_stats(self, subject_id: UUID) -> Optional[dict]:
        """Get subject with statistics"""
        from src.domains.content.models.topic import Topic
        from src.domains.content.models.question import Question

        subject = self.get_by_id(subject_id)
        if not subject:
            return None

        topics_count = (
            self.db.query(func.count(Topic.id))
            .filter(Topic.subject_id == subject_id, Topic.is_deleted.is_(False))
            .scalar()
        )

        questions_count = (
            self.db.query(func.count(Question.id))
            .filter(Question.subject_id == subject_id, Question.is_deleted.is_(False))
            .scalar()
        )

        return {
            "subject": subject,
            "topics_count": topics_count or 0,
            "questions_count": questions_count or 0,
        }
