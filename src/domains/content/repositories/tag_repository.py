from typing import List, Optional
from sqlalchemy.orm import Session

from src.shared.repositories.base import BaseRepository
from src.domains.content.models.question import QuestionTag
from sqlalchemy import func
from src.domains.content.models.question import question_tags_association


class QuestionTagRepository(BaseRepository[QuestionTag, dict, dict]):
    """Repository for QuestionTag model"""

    def __init__(self, db: Session):
        super().__init__(QuestionTag, db)

    def get_by_name(self, name: str) -> Optional[QuestionTag]:
        """Get tag by name"""
        return self.db.query(QuestionTag).filter(QuestionTag.name == name).first()

    def get_or_create_by_name(self, name: str) -> QuestionTag:
        """Get or create tag by name"""
        tag = self.get_by_name(name)
        if not tag:
            tag = QuestionTag(name=name)
            self.db.add(tag)
            self.db.commit()
            self.db.refresh(tag)
        return tag

    def get_popular_tags(self, limit: int = 20) -> List[QuestionTag]:
        """Get most used tags"""

        return (
            self.db.query(QuestionTag)
            .join(question_tags_association)
            .group_by(QuestionTag.id)
            .order_by(func.count(question_tags_association.c.question_id).desc())
            .limit(limit)
            .all()
        )
