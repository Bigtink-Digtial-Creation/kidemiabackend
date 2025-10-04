from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.shared.repositories.base import BaseRepository
from src.domains.auth.models.user import User
from src.domains.auth.models.role import Role

from src.domains.auth.schemas.user import UserCreate, UserUpdate
from src.domains.auth.enums import UserType


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for User model"""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email_or_username(self, identifier: str) -> Optional[User]:
        """Get user by email or username"""
        return (
            self.db.query(User)
            .filter(or_(User.email == identifier, User.username == identifier))
            .first()
        )

    def email_exists(self, email: str, exclude_user_id: Optional[UUID] = None) -> bool:
        """Check if email already exists"""
        query = self.db.query(User).filter(User.email == email)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    def username_exists(
        self, username: str, exclude_user_id: Optional[UUID] = None
    ) -> bool:
        """Check if username already exists"""
        query = self.db.query(User).filter(User.username == username)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    def get_by_user_type(
        self, user_type: UserType, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get users by type"""
        return (
            self.db.query(User)
            .filter(User.user_type == user_type)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users"""
        return (
            self.db.query(User)
            .filter(User.is_active, User.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def activate_user(self, user_id: UUID) -> Optional[User]:
        """Activate a user"""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self.db.commit()
            self.db.refresh(user)
        return user

    def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Deactivate a user"""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()
            self.db.refresh(user)
        return user

    def verify_email(self, user_id: UUID) -> Optional[User]:
        """Mark user email as verified"""
        user = self.get_by_id(user_id)
        if user:
            user.is_email_verified = True
            user.email_verified_at = str(datetime.now(timezone.utc))
            self.db.commit()
            self.db.refresh(user)
        return user

    def update_last_login(self, user_id: UUID) -> Optional[User]:
        """Update user's last login timestamp"""
        user = self.get_by_id(user_id)
        if user:
            user.last_login = str(datetime.now(timezone.utc))
            user.failed_login_attempts = "0"
            self.db.commit()
            self.db.refresh(user)
        return user

    def increment_failed_login(self, user_id: UUID) -> Optional[User]:
        """Increment failed login attempts"""
        user = self.get_by_id(user_id)
        if user:
            attempts = int(user.failed_login_attempts or "0")
            user.failed_login_attempts = str(attempts + 1)

            # Lock account after 5 failed attempts
            if attempts + 1 >= 5:
                from datetime import timedelta

                lock_duration = timedelta(minutes=30)
                user.locked_until = str(datetime.now(timezone.utc) + lock_duration)

            self.db.commit()
            self.db.refresh(user)
        return user

    def reset_failed_login(self, user_id: UUID) -> Optional[User]:
        """Reset failed login attempts"""
        user = self.get_by_id(user_id)
        if user:
            user.failed_login_attempts = "0"
            user.locked_until = None
            self.db.commit()
            self.db.refresh(user)
        return user

    def assign_roles(self, user_id: UUID, role_ids: List[UUID]) -> Optional[User]:
        """Assign roles to user"""
        user = self.get_by_id(user_id)
        if not user:
            return None

        roles = self.db.query(Role).filter(Role.id.in_(role_ids)).all()
        user.roles = roles
        self.db.commit()
        self.db.refresh(user)
        return user

    def add_role(self, user_id: UUID, role_id: UUID) -> Optional[User]:
        """Add a single role to user"""
        user = self.get_by_id(user_id)
        if not user:
            return None

        role = self.db.query(Role).filter(Role.id == role_id).first()
        if role and role not in user.roles:
            user.roles.append(role)
            self.db.commit()
            self.db.refresh(user)
        return user

    def remove_role(self, user_id: UUID, role_id: UUID) -> Optional[User]:
        """Remove a role from user"""
        user = self.get_by_id(user_id)
        if not user:
            return None

        role = self.db.query(Role).filter(Role.id == role_id).first()
        if role and role in user.roles:
            user.roles.remove(role)
            self.db.commit()
            self.db.refresh(user)
        return user

    def search_users(self, query: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by name or email"""
        search_term = f"%{query}%"
        return (
            self.db.query(User)
            .filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.username.ilike(search_term),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
