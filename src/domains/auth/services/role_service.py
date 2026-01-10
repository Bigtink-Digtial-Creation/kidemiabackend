from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    SystemException,
)
from src.domains.auth.repositories.role_repository import RoleRepository
from src.domains.auth.repositories.permission_repository import PermissionRepository
from src.domains.auth.schemas.user import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    AssignPermissionsToRoleRequest,
)


class RoleService:
    """Service for role operations"""

    def __init__(self, db: Session):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.permission_repo = PermissionRepository(db)

    async def create_role(self, role_data: RoleCreate) -> RoleResponse:
        """
        Create a new role

        Args:
            role_data: Role creation data

        Returns:
            RoleResponse: Created role

        Raises:
            ResourceAlreadyExistsException: If role name already exists
        """
        # Check if role with same name exists
        existing = self.role_repo.get_by_name(role_data.name)
        if existing:
            raise ResourceAlreadyExistsException("Role", f"name '{role_data.name}'")

        # Create role
        role_dict = role_data.model_dump(exclude={"permission_ids"})
        role_dict["is_system"] = False  # Custom roles are not system roles

        role = self.role_repo.create(role_dict)

        # Assign permissions if provided
        if role_data.permission_ids:
            role = self.role_repo.assign_permissions(role.id, role_data.permission_ids)

        return RoleResponse.model_validate(role)

    async def get_role(self, role_id: UUID) -> RoleResponse:
        """
        Get role by ID

        Args:
            role_id: Role ID

        Returns:
            RoleResponse: Role details

        Raises:
            ResourceNotFoundException: If role not found
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        return RoleResponse.model_validate(role)

    async def get_role_by_name(self, name: str) -> RoleResponse:
        """
        Get role by name

        Args:
            name: Role name

        Returns:
            RoleResponse: Role details

        Raises:
            ResourceNotFoundException: If role not found
        """
        role = self.role_repo.get_by_name(name)
        if not role:
            raise ResourceNotFoundException("Role", f"name '{name}'")

        return RoleResponse.model_validate(role)

    async def list_roles(self, skip: int = 0, limit: int = 100) -> List[RoleResponse]:
        """
        List all roles

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[RoleResponse]: List of roles
        """
        roles = self.role_repo.get_all(skip=skip, limit=limit)
        return [RoleResponse.model_validate(r) for r in roles]

    async def get_system_roles(self) -> List[RoleResponse]:
        """
        Get all system roles

        Returns:
            List[RoleResponse]: List of system roles
        """
        roles = self.role_repo.get_system_roles()
        return [RoleResponse.model_validate(r) for r in roles]

    async def get_custom_roles(self) -> List[RoleResponse]:
        """
        Get all custom roles

        Returns:
            List[RoleResponse]: List of custom roles
        """
        roles = self.role_repo.get_custom_roles()
        return [RoleResponse.model_validate(r) for r in roles]

    async def update_role(self, role_id: UUID, role_data: RoleUpdate) -> RoleResponse:
        """
        Update role

        Args:
            role_id: Role ID
            role_data: Role update data

        Returns:
            RoleResponse: Updated role

        Raises:
            ResourceNotFoundException: If role not found
            SystemException: If trying to update system role
        """
        # Check if role exists
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        # Prevent updating system roles
        if role.is_system:
            raise SystemException("Cannot update system roles")

        # Update role
        update_dict = role_data.model_dump(
            exclude_unset=True, exclude={"permission_ids"}
        )

        if update_dict:
            role = self.role_repo.update(role_id, update_dict)

        # Update permissions if provided
        if role_data.permission_ids is not None:
            role = self.role_repo.assign_permissions(role_id, role_data.permission_ids)

        return RoleResponse.model_validate(role)

    async def delete_role(self, role_id: UUID) -> bool:
        """
        Delete role

        Args:
            role_id: Role ID

        Returns:
            bool: True if successful

        Raises:
            ResourceNotFoundException: If role not found
            SystemException: If trying to delete system role
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        # Prevent deleting system roles
        if role.is_system:
            raise SystemException("Cannot delete system roles")

        try:
            self.role_repo.delete(role)
        except Exception as e:
            print(e)
        return True

    async def assign_permissions(
        self, role_id: UUID, permissions_data: AssignPermissionsToRoleRequest
    ) -> RoleResponse:
        """

        Assign permissions to role

        Args:
            role_id: Role ID
            permissions_data: Permission IDs to assign

        Returns:
            RoleResponse: Updated role

        Raises:
            ResourceNotFoundException: If role not found
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        # Verify all permissions exist
        for perm_id in permissions_data.permission_ids:
            permission = self.permission_repo.get_by_id(perm_id)
            if not permission:
                raise ResourceNotFoundException("Permission", perm_id)

        # Assign permissions
        role = self.role_repo.assign_permissions(
            role_id, permissions_data.permission_ids
        )

        return RoleResponse.model_validate(role)

    async def add_permission(self, role_id: UUID, permission_id: UUID) -> RoleResponse:
        """
        Add a single permission to role

        Args:
            role_id: Role ID
            permission_id: Permission ID

        Returns:
            RoleResponse: Updated role

        Raises:
            ResourceNotFoundException: If role or permission not found
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        permission = self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException("Permission", permission_id)

        # Add permission
        role = self.role_repo.add_permission(role_id, permission_id)

        return RoleResponse.model_validate(role)

    async def remove_permission(
        self, role_id: UUID, permission_id: UUID
    ) -> RoleResponse:
        """
        Remove a permission from role

        Args:
            role_id: Role ID
            permission_id: Permission ID

        Returns:
            RoleResponse: Updated role

        Raises:
            ResourceNotFoundException: If role or permission not found
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        permission = self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException("Permission", permission_id)

        # Remove permission
        role = self.role_repo.remove_permission(role_id, permission_id)

        return RoleResponse.model_validate(role)
