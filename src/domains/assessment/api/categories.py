from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions

from src.domains.assessment.schemas.category import (
    CategoryConfigCreate,
    CategoryConfigUpdate,
    CategoryConfigResponse,
)
from src.shared.schemas.base import MessageResponse

router = APIRouter()


@router.post(
    "/",
    response_model=CategoryConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category configuration",
)
async def create_category_config(
    config_data: CategoryConfigCreate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("assessment:manage")),
):
    """
    Create a new assessment category configuration.

    Requires `assessment:manage` permission.
    """
    from src.domains.assessment.models.category import AssessmentCategoryConfig
    from src.core.exceptions import ResourceAlreadyExistsException

    # Check if category exists
    existing = (
        db.query(AssessmentCategoryConfig)
        .filter(AssessmentCategoryConfig.category_name == config_data.category_name)
        .first()
    )

    if existing:
        raise ResourceAlreadyExistsException(
            "Category configuration", f"category '{config_data.category_name}'"
        )

    config_dict = config_data.model_dump()
    config_dict["created_by"] = current_user_id

    config = AssessmentCategoryConfig(**config_dict)
    db.add(config)
    db.commit()
    db.refresh(config)

    return CategoryConfigResponse.model_validate(config)


@router.get(
    "/",
    response_model=List[CategoryConfigResponse],
    summary="Get all category configurations",
)
async def get_category_configs(
    active_only: bool = Query(True), db: Session = Depends(get_db)
):
    """Get all assessment category configurations."""
    from src.domains.assessment.models.category import AssessmentCategoryConfig

    query = db.query(AssessmentCategoryConfig)

    if active_only:
        query = query.filter(AssessmentCategoryConfig.is_active.is_(True))

    configs = query.order_by(AssessmentCategoryConfig.order).all()

    return [CategoryConfigResponse.model_validate(c) for c in configs]


@router.get(
    "/{config_id}",
    response_model=CategoryConfigResponse,
    summary="Get category configuration by ID",
)
async def get_category_config(config_id: UUID, db: Session = Depends(get_db)):
    """Get a specific category configuration."""
    from src.domains.assessment.models.category import AssessmentCategoryConfig
    from src.core.exceptions import ResourceNotFoundException

    config = (
        db.query(AssessmentCategoryConfig)
        .filter(AssessmentCategoryConfig.id == config_id)
        .first()
    )

    if not config:
        raise ResourceNotFoundException("Category configuration", config_id)

    return CategoryConfigResponse.model_validate(config)


@router.put(
    "/{config_id}",
    response_model=CategoryConfigResponse,
    summary="Update category configuration",
)
async def update_category_config(
    config_id: UUID,
    config_data: CategoryConfigUpdate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("assessment:manage")),
):
    """Update a category configuration."""
    from src.domains.assessment.models.category import AssessmentCategoryConfig
    from src.core.exceptions import ResourceNotFoundException

    config = (
        db.query(AssessmentCategoryConfig)
        .filter(AssessmentCategoryConfig.id == config_id)
        .first()
    )

    if not config:
        raise ResourceNotFoundException("Category configuration", config_id)

    update_dict = config_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(config, key, value)

    config.updated_by = current_user_id

    db.commit()
    db.refresh(config)

    return CategoryConfigResponse.model_validate(config)


@router.delete(
    "/{config_id}",
    response_model=MessageResponse,
    summary="Delete category configuration",
)
async def delete_category_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("assessment:manage")),
):
    """Delete a category configuration."""
    from src.domains.assessment.models.category import AssessmentCategoryConfig
    from src.core.exceptions import ResourceNotFoundException

    config = (
        db.query(AssessmentCategoryConfig)
        .filter(AssessmentCategoryConfig.id == config_id)
        .first()
    )

    if not config:
        raise ResourceNotFoundException("Category configuration", config_id)

    db.delete(config)
    db.commit()

    return MessageResponse(message="Category configuration deleted successfully")
