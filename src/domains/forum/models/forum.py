from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Table,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from src.shared.database.base import FullBaseModel
from src.domains.forum.enums import PostType, PostStatus, ReactionType


# Association tables
post_tags = Table(
    "post_tags",
    FullBaseModel.metadata,
    Column(
        "post_id",
        PG_UUID(as_uuid=True),
        ForeignKey("forum_posts.id", ondelete="CASCADE"),
    ),
    Column(
        "tag_id", PG_UUID(as_uuid=True), ForeignKey("forum_tags.id", ondelete="CASCADE")
    ),
)

post_followers = Table(
    "post_followers",
    FullBaseModel.metadata,
    Column(
        "post_id",
        PG_UUID(as_uuid=True),
        ForeignKey("forum_posts.id", ondelete="CASCADE"),
    ),
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE")),
)


class ForumPost(FullBaseModel):
    __tablename__ = "forum_posts"

    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(String, default=PostType.QUESTION)
    status = Column(String, default=PostStatus.ACTIVE)

    # Author information
    author_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Categorization
    subject_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subject.id", ondelete="SET NULL"),
        nullable=True,
    )
    exam_target = Column(String, nullable=True)
    view_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    upvote_count = Column(Integer, default=0)
    is_answered = Column(Boolean, default=False)
    accepted_answer_id = Column(String, nullable=True)

    # Moderation
    is_pinned = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    flagged_count = Column(Integer, default=0)
    last_activity_at = Column(DateTime, default=datetime.now(timezone.utc))

    # Relationships
    author = relationship(
        "User", back_populates="forum_posts", foreign_keys=[author_id]
    )
    subject = relationship("Subject", back_populates="forum_posts")
    replies = relationship(
        "ForumReply", back_populates="post", cascade="all, delete-orphan"
    )
    tags = relationship("ForumTag", secondary=post_tags, back_populates="posts")
    reactions = relationship(
        "PostReaction", back_populates="post", cascade="all, delete-orphan"
    )
    bookmarks = relationship(
        "PostBookmark", back_populates="post", cascade="all, delete-orphan"
    )
    followers = relationship(
        "User", secondary=post_followers, back_populates="followed_posts"
    )


class ForumReply(FullBaseModel):
    __tablename__ = "forum_replies"

    content = Column(Text, nullable=False)
    post_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("forum_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_reply_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("forum_replies.id", ondelete="CASCADE"),
        nullable=True,
    )
    upvote_count = Column(Integer, default=0)
    is_accepted_answer = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    flagged_count = Column(Integer, default=0)
    post = relationship("ForumPost", back_populates="replies")
    author = relationship(
        "User", back_populates="forum_replies", foreign_keys=[author_id]
    )
    parent_reply = relationship(
        "ForumReply", remote_side=lambda: [ForumReply.id], backref="child_replies"
    )
    reactions = relationship(
        "ReplyReaction", back_populates="reply", cascade="all, delete-orphan"
    )


class ForumTag(FullBaseModel):
    __tablename__ = "forum_tags"

    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    color = Column(String(7), default="#3B82F6")  # Hex color
    usage_count = Column(Integer, default=0)
    posts = relationship("ForumPost", secondary=post_tags, back_populates="tags")


class PostReaction(FullBaseModel):
    __tablename__ = "post_reactions"

    post_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("forum_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    reaction_type = Column(String, default=ReactionType.LIKE)
    post = relationship("ForumPost", back_populates="reactions")
    user = relationship("User", back_populates="post_reactions")


class ReplyReaction(FullBaseModel):
    __tablename__ = "reply_reactions"

    reply_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("forum_replies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    reaction_type = Column(String, default=ReactionType.LIKE)
    reply = relationship("ForumReply", back_populates="reactions")
    user = relationship("User", back_populates="reply_reactions")


class PostBookmark(FullBaseModel):
    __tablename__ = "post_bookmarks"

    post_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("forum_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    notes = Column(Text, nullable=True)
    post = relationship("ForumPost", back_populates="bookmarks")
    user = relationship("User", back_populates="bookmarks")


class UserReputation(FullBaseModel):
    __tablename__ = "user_reputations"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    total_points = Column(Integer, default=0)
    posts_created = Column(Integer, default=0)
    replies_created = Column(Integer, default=0)
    answers_accepted = Column(Integer, default=0)
    helpful_votes_received = Column(Integer, default=0)
    badges = Column(JSON, default=list)
    last_active_at = Column(DateTime, default=datetime.now(timezone.utc))
    user = relationship("User", back_populates="reputation")


class ForumNotification(FullBaseModel):
    __tablename__ = "forum_notifications"
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type = Column(
        String, nullable=False
    )  # reply, mention, answer_accepted, etc.

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    post_id = Column(PG_UUID(as_uuid=True), nullable=True)
    reply_id = Column(PG_UUID(as_uuid=True), nullable=True)
    triggering_user_id = Column(PG_UUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="forum_notifications")
