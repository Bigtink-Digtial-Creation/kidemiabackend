from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.shared.repositories.base import BaseRepository

from src.domains.assessment.models.section import AssessmentSection


class SectionRepository(BaseRepository[AssessmentSection, dict, dict]):
    """Repository for assessment section operations"""

    def __init__(self, db: Session):
        super().__init__(AssessmentSection, db)

    def get_by_assessment(
        self, assessment_id: UUID, include_deleted: bool = False
    ) -> List[AssessmentSection]:
        """Get all sections for an assessment, ordered by order field"""
        query = self.db.query(self.model).filter(
            self.model.assessment_id == assessment_id
        )

        if not include_deleted:
            query = query.filter(self.model.is_deleted.is_(False))

        return query.order_by(self.model.order).all()

    def get_by_assessment_and_order(
        self, assessment_id: UUID, order: int
    ) -> Optional[AssessmentSection]:
        """Get section by assessment and order"""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.assessment_id == assessment_id,
                    self.model.order == order,
                    self.model.is_deleted.is_(False),
                )
            )
            .first()
        )

    def get_with_questions(self, section_id: UUID) -> Optional[AssessmentSection]:
        """Get section with its questions eagerly loaded"""
        from sqlalchemy.orm import joinedload

        return (
            self.db.query(self.model)
            .filter(and_(self.model.id == section_id, self.model.is_deleted.is_(False)))
            .options(joinedload(self.model.questions))
            .first()
        )

    def count_by_assessment(self, assessment_id: UUID) -> int:
        """Count sections in an assessment"""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.assessment_id == assessment_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .count()
        )

    def get_max_order(self, assessment_id: UUID) -> int:
        """Get the maximum order value for sections in an assessment"""
        from sqlalchemy import func

        result = (
            self.db.query(func.max(self.model.order))
            .filter(
                and_(
                    self.model.assessment_id == assessment_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .scalar()
        )

        return result if result is not None else -1

    def reorder_sections(
        self, assessment_id: UUID, section_orders: Dict[UUID, int]
    ) -> None:
        """Reorder multiple sections at once"""
        for section_id, new_order in section_orders.items():
            self.db.query(self.model).filter(
                and_(
                    self.model.id == section_id,
                    self.model.assessment_id == assessment_id,
                    self.model.is_deleted.is_(False),
                )
            ).update({"order": new_order})

        self.db.commit()

    def get_optional_sections(self, assessment_id: UUID) -> List[AssessmentSection]:
        """Get all optional sections for an assessment"""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.assessment_id == assessment_id,
                    self.model.is_optional.is_(False),
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(self.model.order)
            .all()
        )

    def get_required_sections(self, assessment_id: UUID) -> List[AssessmentSection]:
        """Get all required sections for an assessment"""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.assessment_id == assessment_id,
                    self.model.is_optional.is_(False),
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(self.model.order)
            .all()
        )
