from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from src.core.security import hash_password
from src.core.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    SystemException,
)
from src.domains.auth.repositories.user_repository import UserRepository
from src.domains.auth.repositories.role_repository import RoleRepository
from src.domains.auth.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    AssignRolesToUserRequest,
)
from src.shared.events.dispatcher import dispatch_user_registered
from src.domains.auth.enums import UserType


class UserService:
    """Service for user management operations"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_user(
        self, user_data: UserCreate, assign_default_role: bool = True
    ) -> UserResponse:
        """
        Create a new user

        Args:
            user_data: User creation data
            assign_default_role: Whether to assign default role

        Returns:
            UserResponse: Created user

        Raises:
            ResourceAlreadyExistsException: If email or username exists
        """
        # Check if email exists
        if self.user_repo.email_exists(user_data.email):
            raise ResourceAlreadyExistsException("User", f"email '{user_data.email}'")

        # Check if username exists (if provided)
        if user_data.username and self.user_repo.username_exists(user_data.username):
            raise ResourceAlreadyExistsException(
                "User", f"username '{user_data.username}'"
            )

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user
        user_dict = user_dict = user_data.model_dump(
            exclude={
                "password",
                "category",
                "guardian_email",
                "school_name",
                "admin_email",
            }
        )
        user_dict["password_hash"] = password_hash

        user = self.user_repo.create(user_dict)

        # Assign default role based on user type
        if assign_default_role:
            default_role_name = f"{user_data.user_type}_role"
            default_role = self.role_repo.get_by_name(default_role_name)
            if default_role:
                self.user_repo.add_role(user.id, default_role.id)

        dispatch_user_registered(
            user_id=user.id,
            user_type=user_data.user_type,
            registration_data=user_data,
        )

        return UserResponse.model_validate(user)

    async def get_user(self, user_id: UUID) -> UserResponse:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            UserResponse: User details

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)
        return UserResponse.model_validate(user)

    async def get_user_by_email(self, email: str) -> UserResponse:
        """
        Get user by email

        Args:
            email: User email

        Returns:
            UserResponse: User details

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.get_by_email(email)
        if not user:
            raise ResourceNotFoundException("User", f"email '{email}'")
        return UserResponse.model_validate(user)

    async def get_user_by_username(self, username: str) -> UserResponse:
        """
        Get user by username

        Args:
            username: Username

        Returns:
            UserResponse: User details

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.get_by_username(username)
        if not user:
            raise ResourceNotFoundException("User", f"username '{username}'")

        return UserResponse.model_validate(user)

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """
        List all users

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[UserResponse]: List of users
        """
        users = self.user_repo.get_all(skip=skip, limit=limit)
        return [UserResponse.model_validate(u) for u in users]

    async def get_users_by_type(
        self, user_type: UserType, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        Get users by type

        Args:
            user_type: Type of user
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[UserResponse]: List of users
        """
        users = self.user_repo.get_by_user_type(user_type, skip=skip, limit=limit)
        return [UserResponse.model_validate(u) for u in users]

    async def get_active_users(
        self, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        Get active users

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[UserResponse]: List of active users
        """
        users = self.user_repo.get_active_users(skip=skip, limit=limit)
        return [UserResponse.model_validate(u) for u in users]

    async def search_users(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        Search users by name or email

        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[UserResponse]: List of matching users
        """
        users = self.user_repo.search_users(query, skip=skip, limit=limit)
        return [UserResponse.model_validate(u) for u in users]

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> UserResponse:
        """
        Update user

        Args:
            user_id: User ID
            user_data: User update data

        Returns:
            UserResponse: Updated user

        Raises:
            ResourceNotFoundException: If user not found
        """
        # Check if user exists
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        # Update user
        update_dict = user_data.model_dump(exclude_unset=True)
        updated_user = self.user_repo.update(user_id, update_dict)

        return UserResponse.model_validate(updated_user)

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user (soft delete)

        Args:
            user_id: User ID

        Returns:
            bool: True if successful

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        self.user_repo.delete(user)
        return True

    async def activate_user(self, user_id: UUID) -> UserResponse:
        """
        Activate a user

        Args:
            user_id: User ID

        Returns:
            UserResponse: Updated user

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.activate_user(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        return UserResponse.model_validate(user)

    async def deactivate_user(self, user_id: UUID) -> UserResponse:
        """
        Deactivate a user

        Args:
            user_id: User ID

        Returns:
            UserResponse: Updated user

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.deactivate_user(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        return UserResponse.model_validate(user)

    async def verify_email(self, user_id: UUID) -> UserResponse:
        """
        Mark user email as verified

        Args:
            user_id: User ID

        Returns:
            UserResponse: Updated user

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.verify_email(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        return UserResponse.model_validate(user)

    async def assign_roles(
        self, user_id: UUID, roles_data: AssignRolesToUserRequest
    ) -> UserResponse:
        """
        Assign roles to user

        Args:
            user_id: User ID
            roles_data: Role IDs to assign

        Returns:
            UserResponse: Updated user

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        # Verify all roles exist
        for role_id in roles_data.role_ids:
            role = self.role_repo.get_by_id(role_id)
            if not role:
                raise ResourceNotFoundException("Role", role_id)

        # Assign roles
        user = self.user_repo.assign_roles(user_id, roles_data.role_ids)

        return UserResponse.model_validate(user)

    async def add_role(self, user_id: UUID, role_id: UUID) -> UserResponse:
        """
        Add a single role to user

        Args:
            user_id: User ID
            role_id: Role ID

        Returns:
            UserResponse: Updated user

        Raises:
            ResourceNotFoundException: If user or role not found
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        # Add role
        user = self.user_repo.add_role(user_id, role_id)

        return UserResponse.model_validate(user)

    async def remove_role(self, user_id: UUID, role_id: UUID) -> UserResponse:
        """
        Remove a role from user

        Args:
            user_id: User ID
            role_id: Role ID

        Returns:
            UserResponse: Updated user

        Raises:
            ResourceNotFoundException: If user or role not found
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException("Role", role_id)

        # Remove role
        user = self.user_repo.remove_role(user_id, role_id)

        return UserResponse.model_validate(user)
