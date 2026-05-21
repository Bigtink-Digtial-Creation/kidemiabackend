from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions, require_roles
from src.domains.auth.services.user_service import UserService
from src.domains.auth.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    AssignRolesToUserRequest,
)
from src.domains.auth.enums import UserType
from src.shared.schemas.base import MessageResponse


router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    user_data: UserCreate,
    assign_default_role: bool = Query(
        True, description="Assign default role based on user type"
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("admin:create")),
):
    """
    Create a new user account.

    - **email**: Valid email address
    - **password**: Min 8 characters with uppercase, lowercase, and number
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **middle_name**: User's middle name (optional)
    - **phone_number**: Phone number (optional)
    - **date_of_birth**: Date of birth (optional)
    - **user_type**: Type of user (student, guardian, institution_admin, platform_admin)
    - **username**: Username (optional)
    """
    service = UserService(db)
    user = await service.create_user(user_data, assign_default_role=assign_default_role)
    return user


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List all users",
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    """
    Get list of all users with pagination.
    """
    service = UserService(db)
    users = await service.list_users(skip=skip, limit=limit)
    return users


@router.get(
    "/minimal",
    response_model=List[UserListResponse],
    summary="List users (optimized)",
)
async def list_users_minimal(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|email|last_login)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    service = UserService(db)
    return await service.list_users_minimal(
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
        role=role,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/active",
    response_model=List[UserResponse],
    summary="Get all active users",
)
async def get_active_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    """
    Get all active users with pagination.
    """
    service = UserService(db)
    users = await service.get_active_users(skip=skip, limit=limit)
    return users


@router.get(
    "/type/{user_type}",
    response_model=List[UserResponse],
    summary="Get users by type",
)
async def get_users_by_type(
    user_type: UserType,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    """
    Get users by their type with pagination.

    - **user_type**: student, guardian, institution_admin, or platform_admin
    """
    service = UserService(db)
    users = await service.get_users_by_type(user_type, skip=skip, limit=limit)
    return users


@router.get(
    "/search",
    response_model=List[UserResponse],
    summary="Search users",
)
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    """
    Search users by name, email, or username.

    - **q**: Search query (searches in first_name, last_name, email, username)
    """
    service = UserService(db)
    users = await service.search_users(q, skip=skip, limit=limit)
    return users


@router.get(
    "/email/{email}",
    response_model=UserResponse,
    summary="Get user by email",
)
async def get_user_by_email(
    email: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    """
    Get user by email address.
    """
    service = UserService(db)
    user = await service.get_user_by_email(email)
    return user


@router.get(
    "/username/{username}",
    response_model=UserResponse,
    summary="Get user by username",
)
async def get_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    """
    Get user by username.
    """
    service = UserService(db)
    user = await service.get_user_by_username(username)
    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_roles("admin", "super_admin")),
):
    """
    Get user details by ID.
    """
    service = UserService(db)
    user = await service.get_user(user_id)
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:update")),
):
    """
    Update user details.

    - **first_name**: Updated first name
    - **last_name**: Updated last name
    - **middle_name**: Updated middle name
    - **phone_number**: Updated phone number
    - **date_of_birth**: Updated date of birth
    - **profile_picture_url**: Profile picture URL
    - **bio**: User bio
    - **language**: Preferred language
    - **timezone**: User's timezone
    """
    service = UserService(db)
    user = await service.update_user(user_id, user_data)
    return user


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
)
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:delete")),
):
    """
    Delete (soft delete) a user by ID.
    """
    service = UserService(db)
    deleted = await service.delete_user(user_id)
    if deleted:
        return MessageResponse(message="User deleted successfully")


@router.post(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user",
)
async def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:update")),
):
    """
    Activate a user account.
    """
    service = UserService(db)
    user = await service.activate_user(user_id)
    return user


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user",
)
async def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:update")),
):
    """
    Deactivate a user account.
    """
    service = UserService(db)
    user = await service.deactivate_user(user_id)
    return user


@router.post(
    "/{user_id}/verify-email",
    response_model=UserResponse,
    summary="Verify user email",
)
async def verify_user_email(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:update")),
):
    """
    Mark user's email as verified.
    """
    service = UserService(db)
    user = await service.verify_email(user_id)
    return user


@router.post(
    "/{user_id}/roles",
    response_model=UserResponse,
    summary="Assign roles to user",
)
async def assign_roles_to_user(
    user_id: UUID,
    roles_data: AssignRolesToUserRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:update")),
):
    """
    Assign multiple roles to a user.

    - **role_ids**: List of role IDs to assign
    """
    service = UserService(db)
    user = await service.assign_roles(user_id, roles_data)
    return user


@router.post(
    "/{user_id}/roles/{role_id}",
    response_model=UserResponse,
    summary="Add single role to user",
)
async def add_role_to_user(
    user_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:update")),
):
    """
    Add a single role to a user.
    """
    service = UserService(db)
    user = await service.add_role(user_id, role_id)
    return user


@router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=UserResponse,
    summary="Remove role from user",
)
async def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: None = Depends(require_permissions("users:update")),
):
    """
    Remove a role from a user.
    """
    service = UserService(db)
    user = await service.remove_role(user_id, role_id)
    return user
