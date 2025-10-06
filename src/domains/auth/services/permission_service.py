from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
)
from src.domains.auth.repositories.permission_repository import PermissionRepository
from src.domains.auth.schemas.user import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
)


class PermissionService:
    """Service for permission operations"""

    def __init__(self, db: Session):
        self.db = db
        self.permission_repo = PermissionRepository(db)

    async def create_permission(
        self, permission_data: PermissionCreate
    ) -> PermissionResponse:
        """
        Create a new permission

        Args:
            permission_data: Permission creation data

        Returns:
            PermissionResponse: Created permission

        Raises:
            ResourceAlreadyExistsException: If permission name already exists
        """
        # Check if permission with same name exists
        existing = self.permission_repo.get_by_name(permission_data.name)
        if existing:
            raise ResourceAlreadyExistsException(
                "Permission", f"name '{permission_data.name}'"
            )

        # Create permission
        permission_dict = permission_data.model_dump()
        permission = self.permission_repo.create(permission_dict)

        return PermissionResponse.model_validate(permission)

    async def get_permission(self, permission_id: UUID) -> PermissionResponse:
        """
        Get permission by ID

        Args:
            permission_id: Permission ID

        Returns:
            PermissionResponse: Permission details

        Raises:
            ResourceNotFoundException: If permission not found
        """
        permission = self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException("Permission", permission_id)

        return PermissionResponse.model_validate(permission)

    async def get_permission_by_name(self, name: str) -> PermissionResponse:
        """
        Get permission by name

        Args:
            name: Permission name

        Returns:
            PermissionResponse: Permission details

        Raises:
            ResourceNotFoundException: If permission not found
        """
        permission = self.permission_repo.get_by_name(name)
        if not permission:
            raise ResourceNotFoundException("Permission", f"name '{name}'")

        return PermissionResponse.model_validate(permission)

    async def list_permissions(
        self, skip: int = 0, limit: int = 100
    ) -> List[PermissionResponse]:
        """
        List all permissions

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[PermissionResponse]: List of permissions
        """
        permissions = self.permission_repo.get_all(skip=skip, limit=limit)
        return [PermissionResponse.model_validate(p) for p in permissions]

    async def get_permissions_by_resource(
        self, resource: str
    ) -> List[PermissionResponse]:
        """
        Get all permissions for a specific resource

        Args:
            resource: Resource name

        Returns:
            List[PermissionResponse]: List of permissions for the resource
        """
        permissions = self.permission_repo.get_by_resource(resource)
        return [PermissionResponse.model_validate(p) for p in permissions]

    async def get_permissions_by_action(self, action: str) -> List[PermissionResponse]:
        """
        Get all permissions for a specific action

        Args:
            action: Action name

        Returns:
            List[PermissionResponse]: List of permissions for the action
        """
        permissions = self.permission_repo.get_by_action(action)
        return [PermissionResponse.model_validate(p) for p in permissions]

    async def update_permission(
        self, permission_id: UUID, permission_data: PermissionUpdate
    ) -> PermissionResponse:
        """
        Update permission

        Args:
            permission_id: Permission ID
            permission_data: Permission update data

        Returns:
            PermissionResponse: Updated permission

        Raises:
            ResourceNotFoundException: If permission not found
        """
        # Check if permission exists
        permission = self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException("Permission", permission_id)

        # Update permission
        update_dict = permission_data.model_dump(exclude_unset=True)
        updated_permission = self.permission_repo.update(permission_id, update_dict)

        return PermissionResponse.model_validate(updated_permission)

    async def delete_permission(self, permission_id: UUID) -> bool:
        """
        Delete permission

        Args:
            permission_id: Permission ID

        Returns:
            bool: True if successful

        Raises:
            ResourceNotFoundException: If permission not found
        """
        permission = self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException("Permission", permission_id)

        self.permission_repo.delete(permission_id)
        return True
