from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.auth.services.permission_service import PermissionService
from src.domains.auth.schemas.user import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
)
from src.shared.schemas.base import MessageResponse


router = APIRouter()


@router.post(
    "/",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new permission",
)
async def create_permission(
    permission_data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:create")),
):
    """
    Create a new permission.

    - **name**: Unique permission name (e.g., 'users:create')
    - **display_name**: Human-readable permission name
    - **description**: Permission description
    - **resource**: Resource name (e.g., 'users', 'roles')
    - **action**: Action name (e.g., 'create', 'read', 'update', 'delete')
    """
    service = PermissionService(db)
    permission = await service.create_permission(permission_data)
    return permission


@router.get(
    "/",
    response_model=List[PermissionResponse],
    summary="List all permissions",
)
async def list_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get list of all permissions with pagination.
    """
    service = PermissionService(db)
    permissions = await service.list_permissions(skip=skip, limit=limit)
    return permissions


@router.get(
    "/resource/{resource}",
    response_model=List[PermissionResponse],
    summary="Get permissions by resource",
)
async def get_permissions_by_resource(
    resource: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get all permissions for a specific resource.

    - **resource**: Resource name (e.g., 'users', 'roles')
    """
    service = PermissionService(db)
    permissions = await service.get_permissions_by_resource(resource)
    return permissions


@router.get(
    "/action/{action}",
    response_model=List[PermissionResponse],
    summary="Get permissions by action",
)
async def get_permissions_by_action(
    action: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get all permissions for a specific action.

    - **action**: Action name (e.g., 'create', 'read', 'update', 'delete')
    """
    service = PermissionService(db)
    permissions = await service.get_permissions_by_action(action)
    return permissions


@router.get(
    "/name/{name}",
    response_model=PermissionResponse,
    summary="Get permission by name",
)
async def get_permission_by_name(
    name: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get permission by its unique name.

    - **name**: Permission name
    """
    service = PermissionService(db)
    permission = await service.get_permission_by_name(name)
    return permission


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
    summary="Get permission by ID",
)
async def get_permission(
    permission_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get permission details by ID.
    """
    service = PermissionService(db)
    permission = await service.get_permission(permission_id)
    return permission


@router.patch(
    "/{permission_id}",
    response_model=PermissionResponse,
    summary="Update permission",
)
async def update_permission(
    permission_id: UUID,
    permission_data: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:update")),
):
    """
    Update permission details.

    - **display_name**: Updated display name
    - **description**: Updated description
    """
    service = PermissionService(db)
    permission = await service.update_permission(permission_id, permission_data)
    return permission


@router.delete(
    "/{permission_id}",
    response_model=MessageResponse,
    summary="Delete permission",
)
async def delete_permission(
    permission_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:delete")),
):
    """
    Delete a permission by ID.
    """
    service = PermissionService(db)
    await service.delete_permission(permission_id)
    return MessageResponse(message="Permission deleted successfully")
