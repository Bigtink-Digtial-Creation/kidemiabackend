from typing import Optional, List
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped
from src.shared.database.base import FullBaseModel
from datetime import datetime
from sqlalchemy import Text, Enum as SQLEnum, Integer
from src.domains.guardian.enums import CategoryChangeStatus, AssignmentStatus

from src.domains.auth.models.user import User


class Guardian(FullBaseModel):
    """Guardian model - represents parents/guardians who monitor students"""

    __tablename__ = "guardians"

    # Foreign keys
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Guardian details
    guardian_code = Column(String(100), nullable=True, unique=True, index=True)
    relationship_type = Column(
        String(50), nullable=True
    )  # e.g., "parent", "guardian", "sponsor"

    # Contact preferences
    receive_progress_reports = Column(Boolean, default=True, nullable=False)
    receive_performance_alerts = Column(Boolean, default=True, nullable=False)
    receive_payment_reminders = Column(Boolean, default=True, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="guardian")
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="guardian", lazy="selectin"
    )

    def __repr__(self):
        return f"<Guardian {self.guardian_code}>"


class CategoryChangeRequest(FullBaseModel):
    """Model for category change requests"""

    __tablename__ = "category_change_requests"

    # Foreign keys
    ward_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    guardian_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("guardians.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_category_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_category_config.id", ondelete="SET NULL"),
        nullable=True,
    )
    new_category_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_category_config.id", ondelete="CASCADE"),
        nullable=False,
    )
    resolved_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Request details
    status = Column(
        SQLEnum(CategoryChangeStatus),
        default=CategoryChangeStatus.PENDING,
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)

    # Timestamps
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    ward: Mapped[Optional["Student"]] = relationship("Student", foreign_keys=[ward_id])
    guardian: Mapped[Optional["Guardian"]] = relationship(
        "Guardian", foreign_keys=[guardian_id]
    )
    old_category: Mapped[Optional["AssessmentCategoryConfig"]] = relationship(
        "AssessmentCategoryConfig", foreign_keys=[old_category_id]
    )
    new_category: Mapped[Optional["AssessmentCategoryConfig"]] = relationship(
        "AssessmentCategoryConfig", foreign_keys=[new_category_id]
    )

    def __repr__(self):
        return f"<CategoryChangeRequest {self.id} - {self.status}>"


class AssessmentAssignment(FullBaseModel):
    """Model for tracking assessment assignments from guardians to wards"""

    __tablename__ = "assessment_assignments"

    # Foreign keys
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ward_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("guardians.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Assignment details
    status = Column(
        SQLEnum(AssignmentStatus),
        default=AssignmentStatus.ASSIGNED,
        nullable=False,
        index=True,
    )
    due_date = Column(DateTime, nullable=True)
    instructions = Column(Text, nullable=True)

    # Tracking
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    # Relationships
    assessment: Mapped[Optional["Assessment"]] = relationship("Assessment")
    ward: Mapped[Optional["Student"]] = relationship("Student", foreign_keys=[ward_id])
    guardian: Mapped[Optional["Guardian"]] = relationship(
        "Guardian", foreign_keys=[assigned_by]
    )

    def __repr__(self):
        return f"<AssessmentAssignment {self.id} - {self.status}>"
