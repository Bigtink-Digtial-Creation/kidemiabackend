from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from src.domains.forum.models.forum import (
    ForumPost,
    ForumReply,
    ForumTag,
    PostReaction,
    ReplyReaction,
    PostBookmark,
    UserReputation,
    ForumNotification,
    PostStatus,
    post_followers,
)
from src.domains.auth.models.user import User
from src.shared.repositories.base import BaseRepository
from src.domains.forum.schemas.forum import PostFilters
from uuid import UUID
from src.domains.forum.schemas.forum import ReplyCreate


class ForumRepository(BaseRepository[ForumPost, dict, dict]):
    """Repository for forum-related database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_post(self, post_data: Dict[str, Any], author_id: UUID) -> ForumPost:
        """Create a new forum post"""
        post = ForumPost(author_id=author_id, **post_data)
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    # def get_post_by_id(
    #     self, post_id: UUID, increment_view: bool = False
    # ) -> Optional[ForumPost]:
    #     """Get post by ID with related data"""
    #     post = (
    #         self.db.query(ForumPost)
    #         .options(
    #             joinedload(ForumPost.author),
    #             joinedload(ForumPost.tags),
    #             joinedload(ForumPost.subject),
    #             joinedload(ForumPost.replies).joinedload(ForumReply.author),
    #         )
    #         .filter(ForumPost.id == post_id)
    #         .first()
    #     )

    #     if post and increment_view:
    #         post.view_count += 1
    #         self.db.commit()
    #         self.db.refresh(post)

    #     return post

    def get_post_by_id(
        self, post_id: UUID, increment_view: bool = False
    ) -> Optional[ForumPost]:
        post = (
            self.db.query(ForumPost)
            .options(
                joinedload(ForumPost.author),
                joinedload(ForumPost.tags),
                joinedload(ForumPost.replies).joinedload(ForumReply.author),
            )
            .filter(ForumPost.id == post_id)
            .first()
        )

        if not post:
            return None

        if increment_view:
            post.view_count += 1
            self.db.commit()
            self.db.refresh(post)

        replies = post.replies or []

        reply_map = {}
        root_replies = []

        for reply in replies:
            reply.child_replies = []
            reply_map[reply.id] = reply

        for reply in replies:
            if reply.parent_reply_id:
                parent = reply_map.get(reply.parent_reply_id)
                if parent:
                    parent.child_replies.append(reply)
            else:
                root_replies.append(reply)

        post.replies = root_replies
        return post

    def get_posts(self, filters: PostFilters) -> tuple[List[ForumPost], int]:
        """Get filtered and paginated posts"""
        query = self.db.query(ForumPost).options(
            joinedload(ForumPost.author), joinedload(ForumPost.tags)
        )

        # Apply filters
        if filters.post_type:
            query = query.filter(ForumPost.post_type == filters.post_type)

        if filters.status:
            query = query.filter(ForumPost.status == filters.status)
        else:
            query = query.filter(ForumPost.status == PostStatus.ACTIVE)

        if filters.subject_id:
            query = query.filter(ForumPost.subject_id == filters.subject_id)

        if filters.exam_target:
            query = query.filter(ForumPost.exam_target == filters.exam_target)

        if filters.author_id:
            query = query.filter(ForumPost.author_id == filters.author_id)

        if filters.is_answered is not None:
            query = query.filter(ForumPost.is_answered == filters.is_answered)

        if filters.tag_id:
            query = query.join(ForumPost.tags).filter(ForumTag.id == filters.tag_id)

        if filters.search_query:
            search = f"%{filters.search_query}%"
            query = query.filter(
                or_(ForumPost.title.ilike(search), ForumPost.content.ilike(search))
            )

        # Apply sorting
        if filters.sort_by == "popular":
            query = query.order_by(desc(ForumPost.upvote_count))
        elif filters.sort_by == "trending":
            query = query.order_by(desc(ForumPost.view_count))
        elif filters.sort_by == "unanswered":
            query = query.filter(ForumPost.is_answered.is_(False)).order_by(
                desc(ForumPost.created_at)
            )
        else:  # recent
            query = query.order_by(desc(ForumPost.last_activity_at))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        posts = query.offset(offset).limit(filters.page_size).all()

        return posts, total

    def update_post(
        self, post_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[ForumPost]:
        """Update a forum post"""
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if not post:
            return None

        for key, value in update_data.items():
            if value is not None:
                setattr(post, key, value)

        post.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(post)
        return post

    def delete_post(self, post_id: UUID) -> bool:
        """Delete a forum post"""
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if not post:
            return False

        self.db.delete(post)
        self.db.commit()
        return True

    def update_post_activity(self, post_id: UUID):
        """Update last activity timestamp for a post"""
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if post:
            post.last_activity_at = datetime.utcnow()
            self.db.commit()

    #  Reply Operations
    def create_reply(
        self, reply_data: ReplyCreate, author_id: UUID, post_id: UUID
    ) -> ForumReply:
        """Create a new reply"""
        parent_reply_id = reply_data.get("parent_reply_id")

        # DEBUG: Check existing child replies BEFORE creating new one
        if parent_reply_id:
            parent = (
                self.db.query(ForumReply)
                .filter(ForumReply.id == parent_reply_id)
                .first()
            )
            print(
                f"BEFORE: Parent {parent_reply_id} has {len(parent.child_replies)} child replies"
            )

        reply = ForumReply(
            author_id=author_id,
            post_id=post_id,
            content=reply_data.get("content"),
            parent_reply_id=parent_reply_id,
        )
        self.db.add(reply)

        # Update post reply count and activity
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if post:
            post.reply_count += 1
            post.last_activity_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(reply)
        if parent_reply_id:
            parent = (
                self.db.query(ForumReply)
                .filter(ForumReply.id == parent_reply_id)
                .first()
            )
            print(
                f"AFTER: Parent {parent_reply_id} has {len(parent.child_replies)} child replies"
            )

        return reply

    def get_reply_by_id(self, reply_id: UUID) -> Optional[ForumReply]:
        """Get reply by ID"""
        return (
            self.db.query(ForumReply)
            .options(joinedload(ForumReply.author))
            .filter(ForumReply.id == reply_id)
            .first()
        )

    def get_replies_by_post(self, post_id: UUID) -> List[ForumReply]:
        """Get all replies for a post"""
        return (
            self.db.query(ForumReply)
            .options(joinedload(ForumReply.author))
            .filter(ForumReply.post_id == post_id)
            .order_by(ForumReply.created_at)
            .all()
        )

    def update_reply(self, reply_id: UUID, content: str) -> Optional[ForumReply]:
        """Update a reply"""
        reply = self.db.query(ForumReply).filter(ForumReply.id == reply_id).first()
        if not reply:
            return None

        reply.content = content
        reply.is_edited = True
        reply.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(reply)
        return reply

    def delete_reply(self, reply_id: UUID) -> bool:
        """Delete a reply"""
        reply = self.db.query(ForumReply).filter(ForumReply.id == reply_id).first()
        if not reply:
            return False

        # Update post reply count
        post = self.db.query(ForumPost).filter(ForumPost.id == reply.post_id).first()
        if post and post.reply_count > 0:
            post.reply_count -= 1

        self.db.delete(reply)
        self.db.commit()
        return True

    def mark_as_accepted_answer(
        self, reply_id: UUID, post_id: UUID
    ) -> Optional[ForumReply]:
        """Mark a reply as accepted answer"""
        # Remove any existing accepted answer
        self.db.query(ForumReply).filter(
            ForumReply.post_id == post_id, ForumReply.is_accepted_answer.is_(True)
        ).update({"is_accepted_answer": False})

        # Mark new accepted answer
        reply = self.db.query(ForumReply).filter(ForumReply.id == reply_id).first()
        if reply:
            reply.is_accepted_answer = True

            # Update post
            post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
            if post:
                post.is_answered = True
                post.accepted_answer_id = reply_id
                post.is_locked = True

            self.db.commit()
            self.db.refresh(reply)

        return reply

    #  Tag Operations
    def create_tag(self, tag_data: Dict[str, Any]) -> ForumTag:
        """Create a new tag"""
        tag = ForumTag(**tag_data)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def get_tag_by_name(self, name: str) -> Optional[ForumTag]:
        """Get tag by name"""
        return (
            self.db.query(ForumTag)
            .filter(func.lower(ForumTag.name) == func.lower(name))
            .first()
        )

    def get_or_create_tag(self, name: str, **kwargs) -> ForumTag:
        """Get existing tag or create new one"""
        tag = self.get_tag_by_name(name)
        if not tag:
            tag = self.create_tag({"name": name, **kwargs})
        return tag

    def get_all_tags(self, limit: int = 50) -> List[ForumTag]:
        """Get all tags ordered by usage"""
        return (
            self.db.query(ForumTag)
            .order_by(desc(ForumTag.usage_count))
            .limit(limit)
            .all()
        )

    def add_tags_to_post(self, post_id: UUID, tag_names: List[str]):
        """Add tags to a post"""
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if not post:
            return

        # Clear existing tags
        post.tags.clear()

        # Add new tags
        for tag_name in tag_names:
            tag = self.get_or_create_tag(tag_name)
            post.tags.append(tag)
            tag.usage_count += 1

        self.db.commit()

    #  Reaction Operations
    def add_post_reaction(
        self, post_id: UUID, user_id: UUID, reaction_type: str
    ) -> PostReaction:
        """Add or update reaction to a post"""
        # Check if reaction already exists
        existing = (
            self.db.query(PostReaction)
            .filter(PostReaction.post_id == post_id, PostReaction.user_id == user_id)
            .first()
        )

        if existing:
            existing.reaction_type = reaction_type
            self.db.commit()
            return existing

        reaction = PostReaction(
            post_id=post_id, user_id=user_id, reaction_type=reaction_type
        )
        self.db.add(reaction)

        # Update post upvote count
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if post:
            post.upvote_count += 1

        self.db.commit()
        self.db.refresh(reaction)
        return reaction

    def remove_post_reaction(self, post_id: UUID, user_id: UUID) -> bool:
        """Remove reaction from a post"""
        reaction = (
            self.db.query(PostReaction)
            .filter(PostReaction.post_id == post_id, PostReaction.user_id == user_id)
            .first()
        )

        if not reaction:
            return False

        self.db.delete(reaction)

        # Update post upvote count
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if post and post.upvote_count > 0:
            post.upvote_count -= 1

        self.db.commit()
        return True

    def add_reply_reaction(
        self, reply_id: UUID, user_id: UUID, reaction_type: str
    ) -> ReplyReaction:
        """Add or update reaction to a reply"""
        existing = (
            self.db.query(ReplyReaction)
            .filter(
                ReplyReaction.reply_id == reply_id, ReplyReaction.user_id == user_id
            )
            .first()
        )

        if existing:
            existing.reaction_type = reaction_type
            self.db.commit()
            return existing

        reaction = ReplyReaction(
            reply_id=reply_id, user_id=user_id, reaction_type=reaction_type
        )
        self.db.add(reaction)

        # Update reply upvote count
        reply = self.db.query(ForumReply).filter(ForumReply.id == reply_id).first()
        if reply:
            reply.upvote_count += 1

        self.db.commit()
        self.db.refresh(reaction)
        return reaction

    def remove_reply_reaction(self, reply_id: UUID, user_id: UUID) -> bool:
        """Remove reaction from a reply"""
        reaction = (
            self.db.query(ReplyReaction)
            .filter(
                ReplyReaction.reply_id == reply_id, ReplyReaction.user_id == user_id
            )
            .first()
        )

        if not reaction:
            return False

        self.db.delete(reaction)

        # Update reply upvote count
        reply = self.db.query(ForumReply).filter(ForumReply.id == reply_id).first()
        if reply and reply.upvote_count > 0:
            reply.upvote_count -= 1

        self.db.commit()
        return True

    def user_has_reacted_to_post(self, post_id: UUID, user_id: UUID) -> bool:
        """Check if user has reacted to a post"""
        return (
            self.db.query(PostReaction)
            .filter(PostReaction.post_id == post_id, PostReaction.user_id == user_id)
            .first()
            is not None
        )

    def user_has_reacted_to_reply(self, reply_id: UUID, user_id: UUID) -> bool:
        """Check if user has reacted to a reply"""
        return (
            self.db.query(ReplyReaction)
            .filter(
                ReplyReaction.reply_id == reply_id, ReplyReaction.user_id == user_id
            )
            .first()
            is not None
        )

    #  Bookmark Operations
    def add_bookmark(
        self, post_id: UUID, user_id: UUID, notes: Optional[str] = None
    ) -> PostBookmark:
        """Bookmark a post"""
        existing = (
            self.db.query(PostBookmark)
            .filter(PostBookmark.post_id == post_id, PostBookmark.user_id == user_id)
            .first()
        )

        if existing:
            if notes is not None:
                existing.notes = notes
                self.db.commit()
            return existing

        bookmark = PostBookmark(post_id=post_id, user_id=user_id, notes=notes)
        self.db.add(bookmark)
        self.db.commit()
        self.db.refresh(bookmark)
        return bookmark

    def remove_bookmark(self, post_id: UUID, user_id: UUID) -> bool:
        """Remove bookmark from a post"""
        bookmark = (
            self.db.query(PostBookmark)
            .filter(PostBookmark.post_id == post_id, PostBookmark.user_id == user_id)
            .first()
        )

        if not bookmark:
            return False

        self.db.delete(bookmark)
        self.db.commit()
        return True

    def get_user_bookmarks(self, user_id: UUID) -> List[PostBookmark]:
        """Get all bookmarks for a user"""
        return (
            self.db.query(PostBookmark)
            .options(
                joinedload(PostBookmark.post).joinedload(ForumPost.author),
                joinedload(PostBookmark.post).joinedload(ForumPost.tags),
            )
            .filter(PostBookmark.user_id == user_id)
            .order_by(desc(PostBookmark.created_at))
            .all()
        )

    def user_has_bookmarked(self, post_id: UUID, user_id: UUID) -> bool:
        """Check if user has bookmarked a post"""
        return (
            self.db.query(PostBookmark)
            .filter(PostBookmark.post_id == post_id, PostBookmark.user_id == user_id)
            .first()
            is not None
        )

    #  Follow Operations
    def follow_post(self, post_id: UUID, user_id: UUID) -> bool:
        """Follow a post"""
        post = self.db.query(ForumPost).filter(ForumPost.id == post_id).first()
        if not post:
            return False

        # Check if already following
        stmt = post_followers.select().where(
            and_(
                post_followers.c.post_id == post_id, post_followers.c.user_id == user_id
            )
        )
        existing = self.db.execute(stmt).first()

        if existing:
            return True

        # Add follower
        stmt = post_followers.insert().values(post_id=post_id, user_id=user_id)
        self.db.execute(stmt)
        self.db.commit()
        return True

    def unfollow_post(self, post_id: UUID, user_id: UUID) -> bool:
        """Unfollow a post"""
        stmt = post_followers.delete().where(
            and_(
                post_followers.c.post_id == post_id, post_followers.c.user_id == user_id
            )
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def user_is_following_post(self, post_id: UUID, user_id: UUID) -> bool:
        """Check if user is following a post"""
        stmt = post_followers.select().where(
            and_(
                post_followers.c.post_id == post_id, post_followers.c.user_id == user_id
            )
        )
        return self.db.execute(stmt).first() is not None

    # Reputation Operations
    def get_or_create_reputation(self, user_id: UUID) -> UserReputation:
        """Get or create user reputation record"""
        reputation = (
            self.db.query(UserReputation)
            .filter(UserReputation.user_id == user_id)
            .first()
        )

        if not reputation:
            reputation = UserReputation(user_id=user_id)
            self.db.add(reputation)
            self.db.commit()
            self.db.refresh(reputation)

        return reputation

    def update_reputation_for_post(self, user_id: UUID):
        """Update reputation when user creates a post"""
        reputation = self.get_or_create_reputation(user_id)
        reputation.posts_created += 1
        reputation.total_points += 5
        reputation.last_active_at = datetime.utcnow()
        self.db.commit()

    def update_reputation_for_reply(self, user_id: UUID):
        """Update reputation when user creates a reply"""
        reputation = self.get_or_create_reputation(user_id)
        reputation.replies_created += 1
        reputation.total_points += 2
        reputation.last_active_at = datetime.utcnow()
        self.db.commit()

    def update_reputation_for_accepted_answer(self, user_id: UUID):
        """Update reputation when user's answer is accepted"""
        reputation = self.get_or_create_reputation(user_id)
        reputation.answers_accepted += 1
        reputation.total_points += 15
        self.db.commit()

    def update_reputation_for_upvote(self, user_id: UUID):
        """Update reputation when user receives an upvote"""
        reputation = self.get_or_create_reputation(user_id)
        reputation.helpful_votes_received += 1
        reputation.total_points += 1
        self.db.commit()

    #  Notification Operations
    def create_notification(
        self, notification_data: Dict[str, Any]
    ) -> ForumNotification:
        """Create a notification"""
        notification = ForumNotification(**notification_data)
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_user_notifications(
        self, user_id: UUID, unread_only: bool = False
    ) -> List[ForumNotification]:
        """Get notifications for a user"""
        query = self.db.query(ForumNotification).filter(
            ForumNotification.user_id == user_id
        )

        if unread_only:
            query = query.filter(ForumNotification.is_read.is_(False))

        return query.order_by(desc(ForumNotification.created_at)).limit(50).all()

    def mark_notification_as_read(self, notification_id: UUID) -> bool:
        """Mark a notification as read"""
        notification = (
            self.db.query(ForumNotification)
            .filter(ForumNotification.id == notification_id)
            .first()
        )

        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.utcnow()
        self.db.commit()
        return True

    def mark_all_notifications_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user"""
        result = (
            self.db.query(ForumNotification)
            .filter(
                ForumNotification.user_id == user_id,
                ForumNotification.is_read.is_(False),
            )
            .update({"is_read": True, "read_at": datetime.utcnow()})
        )
        self.db.commit()
        return result

    # ============ Statistics Operations ============
    def get_trending_posts(self, limit: int = 10) -> List[ForumPost]:
        """Get trending posts based on recent activity"""
        since = datetime.utcnow() - timedelta(days=7)
        return (
            self.db.query(ForumPost)
            .filter(
                ForumPost.created_at >= since, ForumPost.status == PostStatus.ACTIVE
            )
            .order_by(
                desc(
                    ForumPost.view_count
                    + ForumPost.reply_count * 3
                    + ForumPost.upvote_count * 5
                )
            )
            .limit(limit)
            .all()
        )

    def get_popular_tags(self, limit: int = 20) -> List[ForumTag]:
        """Get most popular tags"""
        return (
            self.db.query(ForumTag)
            .order_by(desc(ForumTag.usage_count))
            .limit(limit)
            .all()
        )

    def get_forum_statistics(self) -> Dict[str, int]:
        """Get overall forum statistics"""
        total_users = self.db.query(func.count(User.id)).scalar()
        total_posts = self.db.query(func.count(ForumPost.id)).scalar()
        total_replies = self.db.query(func.count(ForumReply.id)).scalar()
        active_discussions = (
            self.db.query(func.count(ForumPost.id))
            .filter(
                ForumPost.status == PostStatus.ACTIVE,
                ForumPost.last_activity_at
                >= datetime.now(timezone.utc) - timedelta(days=7),
            )
            .scalar()
        )
        answered_questions = (
            self.db.query(func.count(ForumPost.id))
            .filter(ForumPost.is_answered.is_(True))
            .scalar()
        )

        return {
            "total_users": total_users or 0,
            "total_posts": total_posts or 0,
            "total_replies": total_replies or 0,
            "active_discussions": active_discussions or 0,
            "answered_questions": answered_questions or 0,
        }
