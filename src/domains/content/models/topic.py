from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import FullBaseModel
from src.domains.content.enums import DifficultyLevel


class Topic(FullBaseModel):
    """Topic model - represents topics within subjects"""

    __tablename__ = "topic"

    subject_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(200), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)

    # Learning resources
    content = Column(Text, nullable=True)  # Rich text content
    video_url = Column(String(500), nullable=True)
    document_url = Column(String(500), nullable=True)

    # Hierarchy
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey("topic.id"), nullable=True)
    order = Column(Integer, default=0)

    # Metadata
    estimated_time_minutes = Column(Integer, nullable=True)
    difficulty_level = Column(SQLEnum(DifficultyLevel), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    subject = relationship("Subject", back_populates="topics")
    parent = relationship("Topic", remote_side="Topic.id", backref="subtopics")
    questions = relationship(
        "Question", back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Topic {self.name}>"
