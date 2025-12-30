from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import FullBaseModel


class Subject(FullBaseModel):
    """Subject model - represents academic subjects"""

    __tablename__ = "subject"

    name = Column(String(200), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(500), nullable=True)
    color_code = Column(String(7), nullable=True)  # Hex color

    # Hierarchy
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey("subject.id"), nullable=True)
    order = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    # Relationships
    parent = relationship("Subject", remote_side="Subject.id", backref="children")
    topics = relationship(
        "Topic", back_populates="subject", cascade="all, delete-orphan"
    )
    questions = relationship("Question", back_populates="subject")

    forum_posts = relationship("ForumPost", back_populates="subject")

    def __repr__(self):
        return f"<Subject {self.name}>"
