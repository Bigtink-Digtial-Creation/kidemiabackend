from sqlalchemy.orm import as_declarative
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from src.shared.database.mixins import (
    UUIDMixin,
    AuditMixin,
    TimestampMixin,
    SoftDeleteMixin,
)


# Base class for all models
Base = declarative_base()


@as_declarative()
class BaseModel:
    """Base model class that all models inherit from"""

    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        return cls.__name__.lower()

    def dict(self):
        """Convert model to dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def update(self, **kwargs):
        """Update model attributes"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class FullBaseModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """
    Complete base model with all mixins.
    Use this for most domain models.
    """

    __abstract__ = True


class SimpleBaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Simple base model with only ID and timestamps.
    Use for simple lookup tables or junction tables.
    """

    __abstract__ = True


class ReadOnlyBaseModel(Base, UUIDMixin):
    """
    Read-only base model.
    Use for database views or read-only tables.
    """

    __abstract__ = True
