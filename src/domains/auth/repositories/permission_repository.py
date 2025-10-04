from typing import Optional, List

from sqlalchemy.orm import Session

from src.shared.repositories.base import BaseRepository
from src.domains.auth.models.permission import Permission


class PermissionRepository(BaseRepository[Permission, dict, dict]):
    """Repository for Permission model"""

    def __init__(self, db: Session):
        super().__init__(Permission, db)

    def get_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name"""
        return self.db.query(Permission).filter(Permission.name == name).first()

    def get_by_resource(self, resource: str) -> List[Permission]:
        """Get permissions by resource"""
        return self.db.query(Permission).filter(Permission.resource == resource).all()

    def get_by_action(self, action: str) -> List[Permission]:
        """Get permissions by action"""
        return self.db.query(Permission).filter(Permission.action == action).all()
