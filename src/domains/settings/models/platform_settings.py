from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from src.shared.database.base import FullBaseModel


class PlatformSetting(FullBaseModel):
    __tablename__ = "platform_settings"

    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    category = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    is_secret = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
