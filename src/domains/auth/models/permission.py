from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from src.shared.database.base import SimpleBaseModel
from src.domains.auth.models.association import role_permissions


class Permission(SimpleBaseModel):
    """Permission model - defines granular permissions"""

    __tablename__ = "permission"

    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # Resource and action
    resource = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # create, read, update, delete, etc.

    # Relationships
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self):
        return f"<Permission {self.name}>"
