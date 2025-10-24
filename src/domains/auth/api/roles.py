from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.auth.services.role_service import RoleService
from src.domains.auth.schemas.user import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    AssignPermissionsToRoleRequest,
)
from src.shared.schemas.base import MessageResponse


router = APIRouter()


@router.post(
    "/",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role",
)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:create")),
):
    """
    Create a new custom role.

    - **name**: Unique role name
    - **display_name**: Human-readable role name
    - **description**: Role description
    - **role_type**: Type of role (system, custom)
    - **permission_ids**: List of permission IDs to assign
    """
    service = RoleService(db)
    role = await service.create_role(role_data)
    return role


@router.get(
    "/",
    response_model=List[RoleResponse],
    summary="List all roles",
)
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get list of all roles with pagination.
    """
    service = RoleService(db)
    roles = await service.list_roles(skip=skip, limit=limit)
    return roles


@router.get(
    "/system",
    response_model=List[RoleResponse],
    summary="Get all system roles",
)
async def get_system_roles(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get all system-defined roles.
    """
    service = RoleService(db)
    roles = await service.get_system_roles()
    return roles


@router.get(
    "/custom",
    response_model=List[RoleResponse],
    summary="Get all custom roles",
)
async def get_custom_roles(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get all custom/user-created roles.
    """
    service = RoleService(db)
    roles = await service.get_custom_roles()
    return roles


@router.get(
    "/name/{name}",
    response_model=RoleResponse,
    summary="Get role by name",
)
async def get_role_by_name(
    name: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get role by its unique name.

    - **name**: Role name
    """
    service = RoleService(db)
    role = await service.get_role_by_name(name)
    return role


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get role by ID",
)
async def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:read")),
):
    """
    Get role details by ID.
    """
    service = RoleService(db)
    role = await service.get_role(role_id)
    return role


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:update")),
):
    """
    Update role details. Cannot update system roles.

    - **display_name**: Updated display name
    - **description**: Updated description
    - **permission_ids**: Updated list of permission IDs
    """
    service = RoleService(db)
    role = await service.update_role(role_id, role_data)
    return role


@router.delete(
    "/{role_id}",
    response_model=MessageResponse,
    summary="Delete role",
)
async def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:delete")),
):
    """
    Delete a custom role by ID. Cannot delete system roles.
    """
    service = RoleService(db)
    await service.delete_role(role_id)
    return MessageResponse(message="Role deleted successfully")


@router.post(
    "/{role_id}/permissions",
    response_model=RoleResponse,
    summary="Assign permissions to role",
)
async def assign_permissions_to_role(
    role_id: UUID,
    permissions_data: AssignPermissionsToRoleRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:create")),
):
    """
    Assign multiple permissions to a role.

    - **permission_ids**: List of permission IDs to assign
    """
    service = RoleService(db)
    role = await service.assign_permissions(role_id, permissions_data)
    return role


@router.post(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleResponse,
    summary="Add single permission to role",
)
async def add_permission_to_role(
    role_id: UUID,
    permission_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:create")),
):
    """
    Add a single permission to a role.
    """
    service = RoleService(db)
    role = await service.add_permission(role_id, permission_id)
    return role


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleResponse,
    summary="Remove permission from role",
)
async def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:delete")),
):
    """
    Remove a permission from a role.
    """
    service = RoleService(db)
    role = await service.remove_permission(role_id, permission_id)
    return role
