from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from src.shared.repositories.base import BaseRepository
from src.domains.auth.models.permission import Permission
from src.domains.auth.models.role import Role


class RoleRepository(BaseRepository[Role, dict, dict]):
    """Repository for Role model"""

    def __init__(self, db: Session):
        super().__init__(Role, db)

    def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.db.query(Role).filter(Role.name == name).first()

    def get_system_roles(self) -> List[Role]:
        """Get all system roles"""
        return self.db.query(Role).filter(Role.is_system.is_(True)).all()

    def get_custom_roles(self) -> List[Role]:
        """Get all custom roles"""
        return self.db.query(Role).filter(Role.is_system.is_(False)).all()

    def assign_permissions(
        self, role_id: UUID, permission_ids: List[UUID]
    ) -> Optional[Role]:
        """Assign permissions to role"""
        role = self.get_by_id(role_id)
        if not role:
            return None

        permissions = (
            self.db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        )
        role.permissions = permissions
        self.db.commit()
        self.db.refresh(role)
        return role

    def add_permission(self, role_id: UUID, permission_id: UUID) -> Optional[Role]:
        """Add a single permission to role"""
        role = self.get_by_id(role_id)
        if not role:
            return None

        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if permission and permission not in role.permissions:
            role.permissions.append(permission)
            self.db.commit()
            self.db.refresh(role)
        return role

    def remove_permission(self, role_id: UUID, permission_id: UUID) -> Optional[Role]:
        """Remove a permission from role"""
        role = self.get_by_id(role_id)
        if not role:
            return None

        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if permission and permission in role.permissions:
            role.permissions.remove(permission)
            self.db.commit()
            self.db.refresh(role)
        return role
