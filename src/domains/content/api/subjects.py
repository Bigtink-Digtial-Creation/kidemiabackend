from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.content.services.subject_service import SubjectService
from src.domains.content.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SubjectListResponse,
)


from src.shared.schemas.base import MessageResponse

router = APIRouter()


@router.post(
    "/",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subject",
)
async def create_subject(
    subject_data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:create")),
):
    """
    Create a new subject.

    Requires `content:create` permission.
    """
    service = SubjectService(db)
    return await service.create_subject(subject_data, current_user_id)


@router.get("/", response_model=SubjectListResponse, summary="Get All subjects")
async def get_subjects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Get all subjects with pagination.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **active_only**: Return only active subjects
    """
    service = SubjectService(db)
    return await service.get_all_subjects(skip, limit, active_only)


@router.get(
    "/featured", response_model=List[SubjectResponse], summary="Get featured subjects"
)
async def get_featured_subjects(
    limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)
):
    """Get featured subjects."""
    service = SubjectService(db)
    return await service.get_featured_subjects(limit)


@router.get("/search", response_model=List[SubjectResponse], summary="Search subjects")
async def search_subjects(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search subjects by name, code, or description."""
    service = SubjectService(db)
    return await service.search_subjects(q, skip, limit)


@router.get(
    "/{subject_id}", response_model=SubjectResponse, summary="Get subject by ID"
)
async def get_subject(subject_id: UUID, db: Session = Depends(get_db)):
    """Get a specific subject by ID."""
    service = SubjectService(db)
    return await service.get_subject(subject_id)


@router.put("/{subject_id}", response_model=SubjectResponse, summary="Update a subject")
async def update_subject(
    subject_id: UUID,
    subject_data: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:update")),
):
    """
    Update a subject.

    Requires `content:update` permission.
    """
    service = SubjectService(db)
    return await service.update_subject(subject_id, subject_data, current_user_id)


@router.delete(
    "/{subject_id}", response_model=MessageResponse, summary="Delete a subject"
)
async def delete_subject(
    subject_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("content:delete")),
):
    """
    Delete a subject (soft delete).

    Requires `content:delete` permission.
    """
    service = SubjectService(db)
    await service.delete_subject(subject_id)
    return MessageResponse(message="Subject deleted successfully")
