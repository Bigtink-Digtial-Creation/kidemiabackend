from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.content.repositories.tag_repository import QuestionTagRepository
from src.domains.content.schemas.question import (
    QuestionTagCreate,
    QuestionTagUpdate,
    QuestionTagResponse,
)
from src.shared.schemas.base import MessageResponse

router = APIRouter()


@router.post(
    "/",
    response_model=QuestionTagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a question tag",
)
async def create_tag(
    tag_data: QuestionTagCreate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:create")),
):
    """Create a new question tag."""
    tag_repo = QuestionTagRepository(db)

    # Check if tag exists
    existing = tag_repo.get_by_name(tag_data.name)
    if existing:
        from src.core.exceptions import ResourceAlreadyExistsException

        raise ResourceAlreadyExistsException("Tag", f"name '{tag_data.name}'")

    tag_dict = tag_data.model_dump()
    # tag_dict["created_by"] = current_user_id

    tag = tag_repo.create(tag_dict)
    return QuestionTagResponse.model_validate(tag)


@router.get("/", response_model=List[QuestionTagResponse], summary="Get all tags")
async def get_tags(db: Session = Depends(get_db)):
    """Get all question tags."""
    tag_repo = QuestionTagRepository(db)
    tags = tag_repo.get_all()
    return [QuestionTagResponse.model_validate(t) for t in tags]


@router.get(
    "/popular", response_model=List[QuestionTagResponse], summary="Get popular tags"
)
async def get_popular_tags(limit: int = 20, db: Session = Depends(get_db)):
    """Get most used tags."""
    tag_repo = QuestionTagRepository(db)
    tags = tag_repo.get_popular_tags(limit)
    return [QuestionTagResponse.model_validate(t) for t in tags]


@router.get("/{tag_id}", response_model=QuestionTagResponse, summary="Get tag by ID")
async def get_tag(tag_id: UUID, db: Session = Depends(get_db)):
    """Get a specific tag by ID."""
    tag_repo = QuestionTagRepository(db)
    tag = tag_repo.get_by_id(tag_id)

    if not tag:
        from src.core.exceptions import ResourceNotFoundException

        raise ResourceNotFoundException("Tag", tag_id)

    return QuestionTagResponse.model_validate(tag)


@router.put("/{tag_id}", response_model=QuestionTagResponse, summary="Update a tag")
async def update_tag(
    tag_id: UUID,
    tag_data: QuestionTagUpdate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:update")),
):
    """Update a question tag."""
    tag_repo = QuestionTagRepository(db)

    tag = tag_repo.get_by_id(tag_id)
    if not tag:
        from src.core.exceptions import ResourceNotFoundException

        raise ResourceNotFoundException("Tag", tag_id)

    update_dict = tag_data.model_dump(exclude_unset=True)
    update_dict["updated_by"] = current_user_id

    updated_tag = tag_repo.update(tag_id, update_dict)
    return QuestionTagResponse.model_validate(updated_tag)


@router.delete("/{tag_id}", response_model=MessageResponse, summary="Delete a tag")
async def delete_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("content:delete")),
):
    """Delete a question tag."""
    tag_repo = QuestionTagRepository(db)

    success = tag_repo.delete(tag_id)
    if not success:
        from src.core.exceptions import ResourceNotFoundException

        raise ResourceNotFoundException("Tag", tag_id)

    return MessageResponse(message="Tag deleted successfully")
