from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ValidationException,
)
from src.domains.content.repositories.subject_repository import SubjectRepository
from src.domains.content.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SubjectWithTopics,
    SubjectListResponse,
)


class SubjectService:
    """Service for subject operations"""

    def __init__(self, db: Session):
        self.db = db
        self.subject_repo = SubjectRepository(db)

    async def create_subject(
        self, subject_data: SubjectCreate, created_by: UUID
    ) -> SubjectResponse:
        """Create a new subject"""
        # Check if code exists
        if self.subject_repo.code_exists(subject_data.code):
            raise ResourceAlreadyExistsException(
                "Subject", f"code '{subject_data.code}'"
            )

        # Check if name exists
        if self.subject_repo.name_exists(subject_data.name):
            raise ResourceAlreadyExistsException(
                "Subject", f"name '{subject_data.name}'"
            )

        # Validate parent if provided
        if subject_data.parent_id:
            parent = self.subject_repo.get_by_id(subject_data.parent_id)
            if not parent:
                raise ResourceNotFoundException(
                    "Parent subject", subject_data.parent_id
                )

        # Create subject
        subject_dict = subject_data.model_dump()
        subject_dict["created_by"] = created_by

        subject = self.subject_repo.create(subject_dict)

        # Get with stats
        stats = self.subject_repo.get_with_stats(subject.id)
        response = SubjectResponse.model_validate(stats["subject"])
        response.topics_count = stats["topics_count"]
        response.questions_count = stats["questions_count"]

        return response

    async def get_subject(self, subject_id: UUID) -> SubjectResponse:
        """Get subject by ID"""
        stats = self.subject_repo.get_with_stats(subject_id)
        if not stats:
            raise ResourceNotFoundException("Subject", subject_id)

        response = SubjectResponse.model_validate(stats["subject"])
        response.topics_count = stats["topics_count"]
        response.questions_count = stats["questions_count"]

        return response

    async def get_all_subjects(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> SubjectListResponse:
        """Get all subjects with pagination"""
        if active_only:
            subjects = self.subject_repo.get_active_subjects(skip, limit)
            total = self.subject_repo.count({"is_active": True, "is_deleted": False})
        else:
            subjects = self.subject_repo.get_all(skip, limit, {"is_deleted": False})
            total = self.subject_repo.count({"is_deleted": False})

        # Enrich with stats
        items = []
        for subject in subjects:
            stats = self.subject_repo.get_with_stats(subject.id)
            response = SubjectResponse.model_validate(stats["subject"])
            response.topics_count = stats["topics_count"]
            response.questions_count = stats["questions_count"]
            items.append(response)

        page = (skip // limit) + 1

        return SubjectListResponse(items=items, total=total, page=page, page_size=limit)

    async def update_subject(
        self, subject_id: UUID, subject_data: SubjectUpdate, updated_by: UUID
    ) -> SubjectResponse:
        """Update a subject"""
        subject = self.subject_repo.get_by_id(subject_id)
        if not subject:
            raise ResourceNotFoundException("Subject", subject_id)

        # Check code uniqueness if being updated
        if subject_data.code and subject_data.code != subject.code:
            if self.subject_repo.code_exists(subject_data.code, exclude_id=subject_id):
                raise ResourceAlreadyExistsException(
                    "Subject", f"code '{subject_data.code}'"
                )

        # Check name uniqueness if being updated
        if subject_data.name and subject_data.name != subject.name:
            if self.subject_repo.name_exists(subject_data.name, exclude_id=subject_id):
                raise ResourceAlreadyExistsException(
                    "Subject", f"name '{subject_data.name}'"
                )

        # Validate parent if being updated
        if subject_data.parent_id:
            if subject_data.parent_id == subject_id:
                raise ValidationException("A subject cannot be its own parent")

            parent = self.subject_repo.get_by_id(subject_data.parent_id)
            if not parent:
                raise ResourceNotFoundException(
                    "Parent subject", subject_data.parent_id
                )

        # Update
        update_dict = subject_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = updated_by

        updated_subject = self.subject_repo.update(subject_id, update_dict)

        return await self.get_subject(subject_id)

    async def delete_subject(self, subject_id: UUID) -> bool:
        """Soft delete a subject"""
        subject = self.subject_repo.get_by_id(subject_id)
        if not subject:
            raise ResourceNotFoundException("Subject", subject_id)

        # Check if subject has child subjects
        children = self.subject_repo.get_children(subject_id)
        if children:
            raise ValidationException("Cannot delete subject with child subjects")

        return self.subject_repo.soft_delete(subject_id) is not None

    async def get_featured_subjects(self, limit: int = 10) -> List[SubjectResponse]:
        """Get featured subjects"""
        subjects = self.subject_repo.get_featured_subjects(limit)

        items = []
        for subject in subjects:
            stats = self.subject_repo.get_with_stats(subject.id)
            response = SubjectResponse.model_validate(stats["subject"])
            response.topics_count = stats["topics_count"]
            response.questions_count = stats["questions_count"]
            items.append(response)

        return items

    async def search_subjects(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[SubjectResponse]:
        """Search subjects"""
        subjects = self.subject_repo.search_subjects(query, skip, limit)

        return [SubjectResponse.model_validate(s) for s in subjects]
