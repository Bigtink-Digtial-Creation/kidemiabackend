from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from src.shared.database.base import FullBaseModel


from sqlalchemy import UniqueConstraint


class Subject(FullBaseModel):
    """Subject model - represents academic subjects"""

    __tablename__ = "subject"

    name = Column(String(200), nullable=False, index=True)
    code = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(500), nullable=True)
    color_code = Column(String(7), nullable=True)

    category_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_category_config.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Hierarchy
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey("subject.id"), nullable=True)
    order = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    category = relationship("AssessmentCategoryConfig", backref="subjects")
    parent = relationship("Subject", remote_side="Subject.id", backref="children")

    topics = relationship(
        "Topic", back_populates="subject", cascade="all, delete-orphan"
    )
    questions = relationship("Question", back_populates="subject")
    forum_posts = relationship("ForumPost", back_populates="subject")

    # 3. CONSTRAINTS
    __table_args__ = (
        UniqueConstraint("name", "category_id", name="_subject_name_category_uc"),
    )

    (
        Index(
            "uq_subject_code_active",
            "code",
            unique=True,
            postgresql_where=(FullBaseModel.deleted_at.is_(None)),
        ),
    )

    def __repr__(self):
        cat = self.category_config.display_name if self.category else "General"
        return f"<Subject {self.name} [{cat}]>"
