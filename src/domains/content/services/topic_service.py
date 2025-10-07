from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.core.exceptions import ResourceNotFoundException, ValidationException
from src.domains.content.repositories.topic_repository import TopicRepository
from src.domains.content.repositories.subject_repository import SubjectRepository
from src.domains.content.schemas.subject import (
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    TopicWithSubtopics,
    TopicListResponse,
)


class TopicService:
    """Service for topic operations"""

    def __init__(self, db: Session):
        self.db = db
        self.topic_repo = TopicRepository(db)
        self.subject_repo = SubjectRepository(db)

    async def bulk_create_topics(
        self, topics_data: list[TopicCreate], created_by: UUID
    ) -> list[TopicResponse]:
        """Bulk create multiple topics"""

        created_topics: list[TopicResponse] = []

        for topic_data in topics_data:
            # Validate subject exists
            subject = self.subject_repo.get_by_id(topic_data.subject_id)
            if not subject:
                raise ResourceNotFoundException("Subject", topic_data.subject_id)

            # Check for duplicate code in same subject
            existing_topic = self.topic_repo.get_by_code(
                topic_data.code, topic_data.subject_id
            )
            if existing_topic:
                raise ValidationException(
                    f"Topic with code '{topic_data.code}' already exists in subject '{subject.name}'"
                )

            # Check for duplicate name in same subject
            existing_topic_by_name = self.topic_repo.get_by_name(
                topic_data.name, topic_data.subject_id
            )
            if existing_topic_by_name:
                raise ValidationException(
                    f"Topic with name '{topic_data.name}' already exists in subject '{subject.name}'"
                )

            # Validate parent topic if provided
            if topic_data.parent_id:
                parent = self.topic_repo.get_by_id(topic_data.parent_id)
                if not parent:
                    raise ResourceNotFoundException(
                        "Parent topic", topic_data.parent_id
                    )
                if parent.subject_id != topic_data.subject_id:
                    raise ValidationException(
                        "Parent topic must belong to the same subject"
                    )

            # Create topic
            topic_dict = topic_data.model_dump()
            topic_dict["created_by"] = created_by
            topic = self.topic_repo.create(topic_dict)

            # Retrieve with stats
            stats = self.topic_repo.get_with_stats(topic.id)
            response = TopicResponse.model_validate(stats["topic"])
            response.questions_count = stats["questions_count"]
            created_topics.append(response)

        return created_topics

    async def create_topic(
        self, topic_data: TopicCreate, created_by: UUID
    ) -> TopicResponse:
        """Create a new topic"""
        # Validate subject exists
        subject = self.subject_repo.get_by_id(topic_data.subject_id)
        if not subject:
            raise ResourceNotFoundException("Subject", topic_data.subject_id)

        # Check for duplicate topic by code within the subject

        existing_topic = self.topic_repo.get_by_code(
            topic_data.code, topic_data.subject_id
        )
        if existing_topic:
            raise ValidationException(
                f"Topic with code '{topic_data.code}' already exists in this subject"
            )

        # Check for duplicate topic by name within the subject (optional but recommended)
        existing_topic_by_name = self.topic_repo.get_by_name(
            topic_data.name, topic_data.subject_id
        )
        if existing_topic_by_name:
            raise ValidationException(
                f"Topic with name '{topic_data.name}' already exists in this subject"
            )

        # Validate parent topic if provided
        if topic_data.parent_id:
            parent = self.topic_repo.get_by_id(topic_data.parent_id)
            if not parent:
                raise ResourceNotFoundException("Parent topic", topic_data.parent_id)

            # Ensure parent belongs to same subject
            if parent.subject_id != topic_data.subject_id:
                raise ValidationException(
                    "Parent topic must belong to the same subject"
                )

        # Create topic
        topic_dict = topic_data.model_dump()
        topic_dict["created_by"] = created_by

        topic = self.topic_repo.create(topic_dict)

        # Get with stats
        stats = self.topic_repo.get_with_stats(topic.id)
        response = TopicResponse.model_validate(stats["topic"])
        response.questions_count = stats["questions_count"]

        return response

    async def get_topic(self, topic_id: UUID) -> TopicResponse:
        """Get topic by ID"""
        stats = self.topic_repo.get_with_stats(topic_id)
        if not stats:
            raise ResourceNotFoundException("Topic", topic_id)

        response = TopicResponse.model_validate(stats["topic"])
        response.questions_count = stats["questions_count"]

        return response

    async def get_topics_by_subject(
        self, subject_id: UUID, skip: int = 0, limit: int = 100
    ) -> TopicListResponse:
        """Get topics by subject"""
        topics = self.topic_repo.get_by_subject(subject_id, skip, limit)
        total = self.topic_repo.count({"subject_id": subject_id, "is_deleted": False})

        # Enrich with stats
        items = []
        for topic in topics:
            stats = self.topic_repo.get_with_stats(topic.id)
            response = TopicResponse.model_validate(stats["topic"])
            response.questions_count = stats["questions_count"]
            items.append(response)

        page = (skip // limit) + 1

        return TopicListResponse(items=items, total=total, page=page, page_size=limit)

    async def update_topic(
        self, topic_id: UUID, topic_data: TopicUpdate, updated_by: UUID
    ) -> TopicResponse:
        """Update a topic"""
        topic = self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise ResourceNotFoundException("Topic", topic_id)

        # Validate parent if being updated
        if topic_data.parent_id:
            if topic_data.parent_id == topic_id:
                raise ValidationException("A topic cannot be its own parent")

            parent = self.topic_repo.get_by_id(topic_data.parent_id)
            if not parent:
                raise ResourceNotFoundException("Parent topic", topic_data.parent_id)

            if parent.subject_id != topic.subject_id:
                raise ValidationException(
                    "Parent topic must belong to the same subject"
                )

        # Update
        update_dict = topic_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = updated_by

        self.topic_repo.update(topic_id, update_dict)

        return await self.get_topic(topic_id)

    async def delete_topic(self, topic_id: UUID) -> bool:
        """Soft delete a topic"""
        topic = self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise ResourceNotFoundException("Topic", topic_id)

        # Check if topic has subtopics
        subtopics = self.topic_repo.get_subtopics(topic_id)
        if subtopics:
            raise ValidationException("Cannot delete topic with subtopics")

        return self.topic_repo.soft_delete(topic_id) is not None

    async def search_topics(
        self,
        query: str,
        subject_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TopicResponse]:
        """Search topics"""
        topics = self.topic_repo.search_topics(query, subject_id, skip, limit)

        return [TopicResponse.model_validate(t) for t in topics]
