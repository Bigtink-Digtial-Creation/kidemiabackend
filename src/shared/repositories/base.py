"""
Base Repository Interface
This provides the abstraction layer for database operations,
allowing us to switch databases without affecting business logic.
"""

from abc import ABC
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository with common CRUD operations"""

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_by_ids(self, ids: List[UUID]) -> List[ModelType]:
        """Get multiple records by IDs"""
        return self.db.query(self.model).filter(self.model.id.in_(ids)).all()

    def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get all records with pagination and optional filters"""
        query = self.db.query(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        if hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())

        return query.offset(skip).limit(limit).all()

    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record"""
        obj_data = obj_in.dict() if hasattr(obj_in, "dict") else obj_in
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def create_many(self, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple records"""
        db_objs = []
        for obj_in in objs_in:
            obj_data = obj_in.dict() if hasattr(obj_in, "dict") else obj_in
            db_obj = self.model(**obj_data)
            db_objs.append(db_obj)

        self.db.add_all(db_objs)
        self.db.commit()
        for db_obj in db_objs:
            self.db.refresh(db_obj)
        return db_objs

    def update(
        self, id: UUID, obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> Optional[ModelType]:
        """Update a record by ID"""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None

        obj_data = (
            obj_in.dict(exclude_unset=True) if hasattr(obj_in, "dict") else obj_in
        )

        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, db_obj):
        try:
            self.db.delete(db_obj)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return True

    def soft_delete(self, id: UUID) -> Optional[ModelType]:
        """Soft delete a record by ID"""

        db_obj = self.get_by_id(id)
        if not db_obj:
            return None

        if hasattr(db_obj, "is_deleted"):
            db_obj.is_deleted = True

        if hasattr(db_obj, "deleted_at"):
            db_obj.deleted_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(db_obj)

        return db_obj

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters"""
        query = self.db.query(func.count(self.model.id))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        return query.scalar()

    def exists(self, id: UUID) -> bool:
        """Check if a record exists"""
        return self.db.query(
            self.db.query(self.model).filter(self.model.id == id).exists()
        ).scalar()

    def get_or_create(
        self, defaults: Optional[Dict[str, Any]] = None, **kwargs
    ) -> tuple[ModelType, bool]:
        """Get a record or create it if it doesn't exist"""
        instance = self.db.query(self.model).filter_by(**kwargs).first()

        if instance:
            return instance, False

        params = dict(kwargs)
        if defaults:
            params.update(defaults)

        instance = self.model(**params)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)

        return instance, True

    def bulk_update(self, updates: List[Dict[str, Any]]) -> bool:
        """Bulk update records"""
        try:
            self.db.bulk_update_mappings(self.model, updates)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False


class ReadOnlyRepository(ABC, Generic[ModelType]):
    """Repository for read-only operations (useful for views or reporting)"""

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        query = self.db.query(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        return query.offset(skip).limit(limit).all()

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        query = self.db.query(func.count(self.model.id))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        return query.scalar()
