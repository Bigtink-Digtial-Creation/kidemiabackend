from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.shared.database.base import SimpleBaseModel
from src.domains.auth.enums import RoleType
from src.domains.auth.models.association import user_roles, role_permissions


class Role(SimpleBaseModel):
    """Role model - defines user roles and their permissions"""

    __tablename__ = "role"

    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # Role type for categorization
    role_type = Column(SQLEnum(RoleType), nullable=False, index=True)

    # System role (cannot be deleted)
    is_system = Column(Boolean, default=False)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Role {self.name}>"
