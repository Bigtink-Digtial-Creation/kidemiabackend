from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.content.services.topic_service import TopicService
from src.domains.content.schemas.subject import (
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    TopicListResponse,
)
from src.shared.schemas.base import MessageResponse

router = APIRouter()


@router.post(
    "/",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new topic",
)
async def create_topic(
    topic_data: TopicCreate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:create")),
):
    """
    Create a new Topic

    Parameters:
    - subject_id (string <uuid>, required): The Subject Id this topic belongs to.
    - name (string, required, 1..200 chars): The name of the topic.
    - code (string, required, 1..20 chars): Short code/identifier for the topic.
    - description (string | null): A description of the topic.
    - content (string | null): Rich content or body text for the topic.
    - video_url (string | null): Optional video resource link.
    - document_url (string | null): Optional document resource link.
    - parent_id (string <uuid> | null): If this topic has a parent topic, supply its id.
    - order (integer >= 0, default=0): The order of the topic in listings.
    - estimated_time_minutes (integer | null): Estimated time (in minutes) to complete this topic.
    - difficulty_level (string | null): Difficulty level of the topic. Enum: "easy", "medium", "hard", "expert".
    - is_active (boolean, default=true): Whether the topic is active.

    Responses:
    - 201 Created: Returns the created Topic object.
    - 400 Bad Request: Invalid input data.
    - 404 Not Found: Subject or parent topic not found.
    """

    service = TopicService(db)
    return await service.create_topic(topic_data, current_user_id)


@router.get(
    "/subject/{subject_id}",
    response_model=TopicListResponse,
    summary="Get topics by subject",
)
async def get_topics_by_subject(
    subject_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get all topics for a specific subject."""
    service = TopicService(db)
    return await service.get_topics_by_subject(subject_id, skip, limit)


@router.get("/search", response_model=List[TopicResponse], summary="Search topics")
async def search_topics(
    q: str = Query(..., min_length=1),
    subject_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search topics by name, code, or description."""
    service = TopicService(db)
    return await service.search_topics(q, subject_id, skip, limit)


@router.get("/{topic_id}", response_model=TopicResponse, summary="Get topic by ID")
async def get_topic(topic_id: UUID, db: Session = Depends(get_db)):
    """Get a specific topic by ID."""
    service = TopicService(db)
    return await service.get_topic(topic_id)


@router.put("/{topic_id}", response_model=TopicResponse, summary="Update a topic")
async def update_topic(
    topic_id: UUID,
    topic_data: TopicUpdate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:update")),
):
    """
    Update a topic.

    Requires `content:update` permission.
    """
    service = TopicService(db)
    return await service.update_topic(topic_id, topic_data, current_user_id)


@router.delete("/{topic_id}", response_model=MessageResponse, summary="Delete a topic")
async def delete_topic(
    topic_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("content:delete")),
):
    """
    Delete a topic (soft delete).

    Requires `content:delete` permission.
    """
    service = TopicService(db)
    await service.delete_topic(topic_id)
    return MessageResponse(message="Topic deleted successfully")
