from typing import List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
)
from src.domains.assessment.repositories.section_repository import SectionRepository
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.assessment.schemas.section import (
    SectionCreate,
    SectionUpdate,
    SectionResponse,
)
from src.domains.assessment.enums import AssessmentStatus


class SectionService:
    """Service for assessment section operations"""

    def __init__(self, db: Session):
        self.db = db
        self.section_repo = SectionRepository(db)
        self.assessment_repo = AssessmentRepository(db)
        self.question_repo = QuestionRepository(db)

    async def create_section(
        self, assessment_id: UUID, section_data: SectionCreate, created_by: UUID
    ) -> SectionResponse:
        """Create a new section for an assessment"""
        # Validate assessment exists
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        # Prevent adding sections to published assessments
        if assessment.status == AssessmentStatus.PUBLISHED:
            raise BusinessLogicException(
                "Cannot add sections to published assessment. Archive it first to make changes."
            )

        # Validate questions if provided
        if section_data.question_ids:
            await self._validate_questions(section_data.question_ids)

        # Check for order conflicts
        existing_section = self.section_repo.get_by_assessment_and_order(
            assessment_id, section_data.order
        )
        if existing_section:
            raise ValidationException(
                f"A section with order {section_data.order} already exists"
            )

        # Create section
        section_dict = section_data.model_dump(exclude={"question_ids"})
        section_dict["assessment_id"] = assessment_id
        section_dict["created_by"] = created_by

        section = self.section_repo.create(section_dict)

        # Add questions
        if section_data.question_ids:
            await self._add_questions_to_section(section.id, section_data.question_ids)

        # Update section totals
        await self._update_section_totals(section.id)

        return await self.get_section(section.id)

    async def get_section(self, section_id: UUID) -> SectionResponse:
        """Get section by ID"""
        section = self.section_repo.get_by_id(section_id)
        if not section:
            raise ResourceNotFoundException("Section", section_id)

        return SectionResponse.model_validate(section)

    async def get_assessment_sections(
        self, assessment_id: UUID
    ) -> List[SectionResponse]:
        """Get all sections for an assessment"""
        sections = self.section_repo.get_by_assessment(assessment_id)
        return [SectionResponse.model_validate(s) for s in sections]

    async def update_section(
        self, section_id: UUID, section_data: SectionUpdate, updated_by: UUID
    ) -> SectionResponse:
        """Update a section"""
        section = self.section_repo.get_by_id(section_id)
        if not section:
            raise ResourceNotFoundException("Section", section_id)

        # Check if assessment is published
        assessment = self.assessment_repo.get_by_id(section.assessment_id)
        if assessment.status == AssessmentStatus.PUBLISHED:
            raise BusinessLogicException(
                "Cannot modify sections in published assessment. Archive it first to make changes."
            )

        # Validate order change if provided
        if section_data.order is not None and section_data.order != section.order:
            existing_section = self.section_repo.get_by_assessment_and_order(
                section.assessment_id, section_data.order
            )
            if existing_section and existing_section.id != section_id:
                raise ValidationException(
                    f"A section with order {section_data.order} already exists"
                )

        # Update section
        update_dict = section_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = updated_by

        self.section_repo.update(section_id, update_dict)

        return await self.get_section(section_id)

    async def delete_section(self, section_id: UUID) -> bool:
        """Soft delete a section"""
        section = self.section_repo.get_by_id(section_id)
        if not section:
            raise ResourceNotFoundException("Section", section_id)

        # Check if assessment is published
        assessment = self.assessment_repo.get_by_id(section.assessment_id)
        if assessment.status == AssessmentStatus.PUBLISHED:
            raise BusinessLogicException(
                "Cannot delete sections from published assessment. Archive it first to make changes."
            )

        return self.section_repo.soft_delete(section_id) is not None

    async def reorder_sections(
        self, assessment_id: UUID, section_orders: Dict[UUID, int]
    ) -> List[SectionResponse]:
        """Reorder sections in an assessment"""
        # Validate assessment exists
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        # Check if assessment is published
        if assessment.status == AssessmentStatus.PUBLISHED:
            raise BusinessLogicException(
                "Cannot reorder sections in published assessment. Archive it first to make changes."
            )

        # Validate all sections belong to this assessment
        for section_id in section_orders.keys():
            section = self.section_repo.get_by_id(section_id)
            if not section:
                raise ResourceNotFoundException("Section", section_id)
            if section.assessment_id != assessment_id:
                raise ValidationException(
                    f"Section {section_id} does not belong to assessment {assessment_id}"
                )

        # Validate no duplicate orders
        orders = list(section_orders.values())
        if len(orders) != len(set(orders)):
            raise ValidationException("Duplicate order values are not allowed")

        # Perform reordering
        self.section_repo.reorder_sections(assessment_id, section_orders)

        # Return updated sections
        return await self.get_assessment_sections(assessment_id)

    async def add_questions_to_section(
        self, section_id: UUID, question_ids: List[UUID]
    ) -> SectionResponse:
        """Add questions to a section"""
        section = self.section_repo.get_by_id(section_id)
        if not section:
            raise ResourceNotFoundException("Section", section_id)

        # Check if assessment is published
        assessment = self.assessment_repo.get_by_id(section.assessment_id)
        if assessment.status == AssessmentStatus.PUBLISHED:
            raise BusinessLogicException(
                "Cannot modify questions in published assessment. Archive it first to make changes."
            )

        # Validate questions
        await self._validate_questions(question_ids)

        # Add questions
        await self._add_questions_to_section(section_id, question_ids)

        # Update section totals
        await self._update_section_totals(section_id)

        return await self.get_section(section_id)

    async def remove_questions_from_section(
        self, section_id: UUID, question_ids: List[UUID]
    ) -> SectionResponse:
        """Remove questions from a section"""
        section = self.section_repo.get_with_questions(section_id)
        if not section:
            raise ResourceNotFoundException("Section", section_id)

        # Check if assessment is published
        assessment = self.assessment_repo.get_by_id(section.assessment_id)
        if assessment.status == AssessmentStatus.PUBLISHED:
            raise BusinessLogicException(
                "Cannot modify questions in published assessment. Archive it first to make changes."
            )

        # Remove questions
        section.questions = [q for q in section.questions if q.id not in question_ids]
        self.db.commit()

        # Update section totals
        await self._update_section_totals(section_id)

        return await self.get_section(section_id)

    async def _validate_questions(self, question_ids: List[UUID]) -> None:
        """Validate questions exist and are approved"""
        for question_id in question_ids:
            question = self.question_repo.get_by_id(question_id)
            if not question:
                raise ResourceNotFoundException("Question", question_id)

            from src.domains.content.enums import QuestionStatus

            if question.status != QuestionStatus.APPROVED:
                raise ValidationException(
                    f"Question {question_id} is not approved for use"
                )

    async def _add_questions_to_section(
        self, section_id: UUID, question_ids: List[UUID]
    ) -> None:
        """Add questions to section"""
        section = self.section_repo.get_with_questions(section_id)

        for question_id in question_ids:
            question = self.question_repo.get_by_id(question_id)
            if question and question not in section.questions:
                section.questions.append(question)

        self.db.commit()

    async def _update_section_totals(self, section_id: UUID) -> None:
        """Update total questions and points for a section"""
        section = self.section_repo.get_with_questions(section_id)

        total_questions = len(section.questions)
        total_points = sum(q.points for q in section.questions)

        self.section_repo.update(
            section_id,
            {"total_questions": total_questions, "total_points": total_points},
        )
