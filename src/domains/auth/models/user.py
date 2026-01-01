from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Table,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped
from typing import Optional
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from src.shared.database.base import FullBaseModel
from src.domains.auth.enums import UserType
from src.domains.auth.models.association import user_roles
from src.domains.forum.models.forum import post_followers
from datetime import datetime, timezone


user_following = Table(
    "user_following",
    FullBaseModel.metadata,
    Column(
        "follower_id", PG_UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE")
    ),
    Column(
        "following_id", PG_UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE")
    ),
    Column("created_at", DateTime, default=datetime.now(timezone.utc)),
    UniqueConstraint("follower_id", "following_id", name="unique_follow"),
)


class User(FullBaseModel):
    """
    User model - represents all types of users in the system
    (Students, Guardians, Institution Admins, Platform Admins)
    """

    __tablename__ = "user"

    # Basic Information
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)

    # Personal Information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)

    # User Type
    user_type = Column(SQLEnum(UserType), nullable=False, index=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    email_verification_token = Column(String, nullable=True)
    email_verification_token_expires = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_token_expires = Column(DateTime, nullable=True)

    # Profile
    profile_picture_url = Column(String(500), nullable=True)
    bio = Column(String(1000), nullable=True)

    # Security
    last_login = Column(String(50), nullable=True)
    failed_login_attempts = Column(String(10), default="0")
    locked_until = Column(String(50), nullable=True)

    # Two-Factor Authentication
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255), nullable=True)

    # Preferences
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    notification_preferences = Column(String(1000), nullable=True)

    # Relationships
    roles = relationship(
        "Role", secondary=user_roles, back_populates="users", lazy="selectin"
    )

    # institution_admin_profile: relationship with InstitutionAdmin

    student: Mapped[Optional["Student"]] = relationship(
        "Student", back_populates="user", uselist=False, passive_deletes=True
    )

    guardian: Mapped[Optional["Guardian"]] = relationship(
        "Guardian", back_populates="user", uselist=False, passive_deletes=True
    )

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    forum_posts = relationship(
        "ForumPost", back_populates="author", foreign_keys="ForumPost.author_id"
    )
    forum_replies = relationship(
        "ForumReply", back_populates="author", foreign_keys="ForumReply.author_id"
    )
    post_reactions = relationship("PostReaction", back_populates="user")
    reply_reactions = relationship("ReplyReaction", back_populates="user")
    bookmarks = relationship("PostBookmark", back_populates="user")
    followed_posts = relationship(
        "ForumPost", secondary=post_followers, back_populates="followers"
    )
    reputation = relationship("UserReputation", back_populates="user", uselist=False)
    forum_notifications = relationship("ForumNotification", back_populates="user")

    def __repr__(self):
        return f"<User {self.email} ({self.user_type})>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission"""
        for role in self.roles:
            if any(perm.name == permission_name for perm in role.permissions):
                return True
        return False
