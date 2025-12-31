from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from src.domains.forum.repositories.forum_repository import ForumRepository
from src.domains.forum.schemas.forum import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostDetailResponse,
    PostListResponse,
    ReplyCreate,
    ReplyUpdate,
    ReplyResponse,
    TagCreate,
    TagResponse,
    BookmarkCreate,
    BookmarkResponse,
    ReactionCreate,
    PostFilters,
    ForumStats,
    TrendingPost,
    PopularTag,
    ReputationResponse,
    NotificationResponse,
)
from src.domains.forum.utils import (
    ForumUtils,
    ForumPermissions,
    ForumValidators,
    ForumAnalytics,
    rate_limit_check,
    content_moderation_check,
)


class ForumService:
    """Service layer for community business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ForumRepository(db)

    def _check_post_ownership(self, post_id: UUID, user_id: UUID) -> bool:
        """Check if user owns the post"""
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )
        return post.author_id == user_id

    def _check_reply_ownership(self, reply_id: UUID, user_id: UUID) -> bool:
        """Check if user owns the reply"""
        reply = self.repo.get_reply_by_id(reply_id)
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found"
            )
        return reply.author_id == user_id

    def _enrich_post_with_user_data(
        self, post: Any, user_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """Add user-specific data to post"""
        post_dict = post.__dict__.copy()

        if user_id:
            post_dict["user_has_upvoted"] = self.repo.user_has_reacted_to_post(
                post.id, user_id
            )
            post_dict["user_has_bookmarked"] = self.repo.user_has_bookmarked(
                post.id, user_id
            )
            post_dict["user_is_following"] = self.repo.user_is_following_post(
                post.id, user_id
            )
        else:
            post_dict["user_has_upvoted"] = False
            post_dict["user_has_bookmarked"] = False
            post_dict["user_is_following"] = False

        return post_dict

    def _enrich_reply_with_user_data(
        self, reply: Any, user_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """Add user-specific data to reply"""
        reply_dict = reply.__dict__.copy()

        if user_id:
            reply_dict["user_has_upvoted"] = self.repo.user_has_reacted_to_reply(
                reply.id, user_id
            )
        else:
            reply_dict["user_has_upvoted"] = False

        return reply_dict

    def _create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        post_id: Optional[UUID] = None,
        reply_id: Optional[UUID] = None,
        triggering_user_id: Optional[UUID] = None,
    ):
        """Create a notification for a user"""
        self.repo.create_notification(
            {
                "user_id": user_id,
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "post_id": post_id,
                "reply_id": reply_id,
                "triggering_user_id": triggering_user_id,
            }
        )

    def _check_and_award_badges(self, user_id: UUID):
        """Check if user has earned new badges and update reputation"""
        reputation = self.repo.get_or_create_reputation(user_id)
        new_badge = ForumUtils.get_badge_for_milestone(reputation)

        if new_badge:
            # Add badge to user's collection
            badges = reputation.badges if reputation.badges else []
            if new_badge not in badges:
                badges.append(new_badge)
                reputation.badges = badges
                self.db.commit()

                # Create notification for badge earned
                badge_names = {
                    "century_poster": "Century Poster - 100 Posts!",
                    "prolific_poster": "Prolific Poster - 50 Posts!",
                    "active_poster": "Active Poster - 10 Posts!",
                    "reply_master": "Reply Master - 500 Replies!",
                    "helpful_responder": "Helpful Responder - 100 Replies!",
                    "answer_guru": "Answer Guru - 50 Accepted Answers!",
                    "problem_solver": "Problem Solver - 10 Accepted Answers!",
                    "first_answer": "First Answer - 1 Accepted Answer!",
                    "community_favorite": "Community Favorite - 100 Helpful Votes!",
                }

                self._create_notification(
                    user_id=user_id,
                    notification_type="badge_earned",
                    title="🏆 New Badge Earned!",
                    message=f"Congratulations! You've earned the '{badge_names.get(new_badge, new_badge)}' badge!",
                )

    def create_post(self, post_data: PostCreate, author_id: UUID) -> PostResponse:
        """Create a new forum post with validation and rate limiting"""
        # Rate limit check
        if not rate_limit_check(author_id, "post", self.db):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You've created too many posts recently. Please wait before posting again.",
            )

        # Validate title
        is_valid, error_msg = ForumValidators.validate_post_title(post_data.title)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        # Validate content
        is_valid, error_msg = ForumValidators.validate_content(post_data.content)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        # Content moderation check
        is_allowed, reason = content_moderation_check(post_data.content)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content moderation failed: {reason}",
            )

        # Sanitize content
        sanitized_content = ForumUtils.sanitize_content(post_data.content)

        # Validate tag names
        for tag_name in post_data.tag_names:
            is_valid, error_msg = ForumValidators.validate_tag_name(tag_name)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tag '{tag_name}': {error_msg}",
                )

        # Extract tags and create post
        tag_names = post_data.tag_names
        post_dict = post_data.model_dump(exclude={"tag_names"})
        post_dict["content"] = sanitized_content

        # Create post
        post = self.repo.create_post(post_dict, author_id)

        # Add tags
        if tag_names:
            self.repo.add_tags_to_post(post.id, tag_names)

        # Update reputation
        self.repo.update_reputation_for_post(author_id)

        # Check for badges
        self._check_and_award_badges(author_id)

        # Refresh to get tags
        self.db.refresh(post)

        return PostResponse.model_validate(post)

    def get_post(
        self, post_id: UUID, current_user_id: Optional[UUID] = None
    ) -> PostDetailResponse:
        """Get a single post with replies"""
        post = self.repo.get_post_by_id(post_id, increment_view=True)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        # Enrich with user-specific data
        post_data = self._enrich_post_with_user_data(post, current_user_id)

        # Add calculated fields using utilities
        post_data["time_ago"] = ForumUtils.format_time_ago(post.created_at)
        post_data["trending_score"] = ForumUtils.calculate_trending_score(post)
        post_data["quality_score"] = ForumAnalytics.get_post_quality_score(post)

        # Enrich replies with user data
        enriched_replies = []
        for reply in post.replies:
            reply_data = self._enrich_reply_with_user_data(reply, current_user_id)
            reply_data["time_ago"] = ForumUtils.format_time_ago(reply.created_at)
            enriched_replies.append(reply_data)

        post_data["replies"] = enriched_replies

        return PostDetailResponse(**post_data)

    def get_posts(
        self, filters: PostFilters, current_user_id: Optional[UUID] = None
    ) -> PostListResponse:
        """Get filtered posts"""
        posts, total = self.repo.get_posts(filters)

        # Enrich posts with user-specific data and utilities
        enriched_posts = []
        for post in posts:
            post_data = self._enrich_post_with_user_data(post, current_user_id)
            post_data["time_ago"] = ForumUtils.format_time_ago(post.created_at)
            post_data["excerpt"] = ForumUtils.generate_post_excerpt(post.content)
            enriched_posts.append(PostResponse(**post_data))

        has_more = (filters.page * filters.page_size) < total

        return PostListResponse(
            posts=enriched_posts,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            has_more=has_more,
        )

    def update_post(
        self, post_id: UUID, post_data: PostUpdate, user_id: UUID
    ) -> PostResponse:
        """Update a post with permission checks"""
        # Check ownership using utility
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        if not ForumPermissions.can_edit_post(post, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this post",
            )

        # Validate if title or content is being updated
        if post_data.title:
            is_valid, error_msg = ForumValidators.validate_post_title(post_data.title)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
                )

        if post_data.content:
            is_valid, error_msg = ForumValidators.validate_content(post_data.content)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
                )

            # Sanitize content
            post_data.content = ForumUtils.sanitize_content(post_data.content)

        # Extract tags if provided
        tag_names = post_data.tag_names
        update_dict = post_data.model_dump(exclude={"tag_names"}, exclude_none=True)

        # Update post
        post = self.repo.update_post(post_id, update_dict)

        # Update tags if provided
        if tag_names is not None:
            # Validate tag names
            for tag_name in tag_names:
                is_valid, error_msg = ForumValidators.validate_tag_name(tag_name)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid tag '{tag_name}': {error_msg}",
                    )
            self.repo.add_tags_to_post(post_id, tag_names)

        # Refresh to get updated data
        self.db.refresh(post)

        return PostResponse.model_validate(post)

    def delete_post(
        self, post_id: UUID, user_id: UUID, is_moderator: bool = False
    ) -> Dict[str, str]:
        """Delete a post with permission checks"""
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        if not ForumPermissions.can_delete_post(post, user_id, is_moderator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this post",
            )

        if not self.repo.delete_post(post_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        return {"message": "Post deleted successfully"}

    def create_reply(
        self, post_id: UUID, reply_data: ReplyCreate, author_id: UUID
    ) -> ReplyResponse:
        """Create a reply to a post with validation and rate limiting"""
        # Rate limit check
        if not rate_limit_check(author_id, "reply", self.db):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You've created too many replies recently. Please wait before replying again.",
            )

        # Check if post exists
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        if post.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This post is locked and cannot accept new replies",
            )

        # Validate content
        is_valid, error_msg = ForumValidators.validate_content(
            reply_data.content, min_length=1
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        # Content moderation
        is_allowed, reason = content_moderation_check(reply_data.content)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content moderation failed: {reason}",
            )

        # Sanitize content
        sanitized_content = ForumUtils.sanitize_content(reply_data.content)

        # Extract mentions
        mentions = ForumUtils.extract_mentions(sanitized_content)

        # Create reply
        reply_dict = reply_data.model_dump()
        reply_dict["content"] = sanitized_content
        reply = self.repo.create_reply(reply_dict, author_id, post_id)

        # Update reputation
        self.repo.update_reputation_for_reply(author_id)

        # Check for badges
        self._check_and_award_badges(author_id)

        # Update post activity
        self.repo.update_post_activity(post_id)

        # Create notification for post author
        if post.author_id != author_id:
            excerpt = ForumUtils.generate_post_excerpt(
                sanitized_content, max_length=100
            )
            self._create_notification(
                user_id=post.author_id,
                notification_type="new_reply",
                title="New Reply on Your Post",
                message=f"Someone replied to '{post.title}': {excerpt}",
                post_id=post_id,
                reply_id=reply.id,
                triggering_user_id=author_id,
            )

        # Create notifications for mentioned users
        for mention in mentions:
            # You would fetch user_id from username here
            # For now, we'll skip this implementation detail
            pass

        return ReplyResponse.model_validate(reply)

    def update_reply(
        self, reply_id: UUID, reply_data: ReplyUpdate, user_id: UUID
    ) -> ReplyResponse:
        """Update a reply with permission checks"""
        reply = self.repo.get_reply_by_id(reply_id)
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found"
            )

        if not ForumPermissions.can_edit_reply(reply, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this reply",
            )

        # Validate content
        is_valid, error_msg = ForumValidators.validate_content(
            reply_data.content, min_length=1
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        # Sanitize content
        sanitized_content = ForumUtils.sanitize_content(reply_data.content)

        reply = self.repo.update_reply(reply_id, sanitized_content)
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found"
            )

        return ReplyResponse.model_validate(reply)

    def delete_reply(
        self, reply_id: UUID, user_id: UUID, is_moderator: bool = False
    ) -> Dict[str, str]:
        """Delete a reply with permission checks"""
        reply = self.repo.get_reply_by_id(reply_id)
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found"
            )

        if not ForumPermissions.can_delete_reply(reply, user_id, is_moderator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this reply",
            )

        if not self.repo.delete_reply(reply_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found"
            )

        return {"message": "Reply deleted successfully"}

    def mark_reply_as_accepted(
        self, post_id: UUID, reply_id: str, user_id: UUID
    ) -> ReplyResponse:
        """Mark a reply as accepted answer with permission checks"""
        # Check if user can accept answers
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        if not ForumPermissions.can_accept_answer(post, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post author can accept answers",
            )

        reply = self.repo.mark_as_accepted_answer(reply_id, post_id)
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found"
            )

        # Update reputation for reply author
        self.repo.update_reputation_for_accepted_answer(reply.author_id)

        # Check for badges
        self._check_and_award_badges(reply.author_id)

        # Create notification for reply author
        if reply.author_id != user_id:
            self._create_notification(
                user_id=reply.author_id,
                notification_type="answer_accepted",
                title="🎉 Your Answer Was Accepted!",
                message=f"Your answer on '{post.title}' was marked as the accepted answer. +15 reputation!",
                post_id=post_id,
                reply_id=reply_id,
                triggering_user_id=user_id,
            )

        return ReplyResponse.model_validate(reply)

    def toggle_post_reaction(
        self, post_id: UUID, user_id: UUID, reaction_data: ReactionCreate
    ) -> Dict[str, Any]:
        """Toggle reaction on a post"""
        # Check if post exists
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        # Check if user already reacted
        has_reacted = self.repo.user_has_reacted_to_post(post_id, user_id)

        if has_reacted:
            # Remove reaction
            self.repo.remove_post_reaction(post_id, user_id)
            return {"reacted": False, "message": "Reaction removed"}
        else:
            # Add reaction
            self.repo.add_post_reaction(post_id, user_id, reaction_data.reaction_type)

            # Update reputation for post author
            if post.author_id != user_id:
                self.repo.update_reputation_for_upvote(post.author_id)

                # Check for badges
                self._check_and_award_badges(post.author_id)

            return {"reacted": True, "message": "Reaction added"}

    def toggle_reply_reaction(
        self, reply_id: UUID, user_id: UUID, reaction_data: ReactionCreate
    ) -> Dict[str, Any]:
        """Toggle reaction on a reply"""
        # Check if reply exists
        reply = self.repo.get_reply_by_id(reply_id)
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found"
            )

        # Check if user already reacted
        has_reacted = self.repo.user_has_reacted_to_reply(reply_id, user_id)

        if has_reacted:
            # Remove reaction
            self.repo.remove_reply_reaction(reply_id, user_id)
            return {"reacted": False, "message": "Reaction removed"}
        else:
            # Add reaction
            self.repo.add_reply_reaction(reply_id, user_id, reaction_data.reaction_type)

            # Update reputation for reply author
            if reply.author_id != user_id:
                self.repo.update_reputation_for_upvote(reply.author_id)

                # Check for badges
                self._check_and_award_badges(reply.author_id)

            return {"reacted": True, "message": "Reaction added"}

    def toggle_bookmark(
        self,
        post_id: UUID,
        user_id: UUID,
        bookmark_data: Optional[BookmarkCreate] = None,
    ) -> Dict[str, Any]:
        """Toggle bookmark on a post"""
        # Check if post exists
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        # Check if already bookmarked
        is_bookmarked = self.repo.user_has_bookmarked(post_id, user_id)

        if is_bookmarked:
            # Remove bookmark
            self.repo.remove_bookmark(post_id, user_id)
            return {"bookmarked": False, "message": "Bookmark removed"}
        else:
            # Add bookmark
            notes = bookmark_data.notes if bookmark_data else None
            self.repo.add_bookmark(post_id, user_id, notes)
            return {"bookmarked": True, "message": "Post bookmarked"}

    def get_user_bookmarks(self, user_id: UUID) -> List[BookmarkResponse]:
        """Get all bookmarks for a user"""
        bookmarks = self.repo.get_user_bookmarks(user_id)
        return [BookmarkResponse.model_validate(b) for b in bookmarks]

    def toggle_follow_post(self, post_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Toggle follow status on a post"""
        # Check if post exists
        post = self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
            )

        # Check if already following
        is_following = self.repo.user_is_following_post(post_id, user_id)

        if is_following:
            # Unfollow
            self.repo.unfollow_post(post_id, user_id)
            return {"following": False, "message": "Unfollowed post"}
        else:
            # Follow
            self.repo.follow_post(post_id, user_id)
            return {"following": True, "message": "Following post"}

    def get_all_tags(self) -> List[TagResponse]:
        """Get all tags"""
        tags = self.repo.get_all_tags()
        return [TagResponse.model_validate(t) for t in tags]

    def create_tag(self, tag_data: TagCreate) -> TagResponse:
        """Create a new tag with validation"""
        # Validate tag name
        is_valid, error_msg = ForumValidators.validate_tag_name(tag_data.name)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        # Check if tag already exists
        existing = self.repo.get_tag_by_name(tag_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Tag already exists"
            )

        tag = self.repo.create_tag(tag_data.model_dump())
        return TagResponse.model_validate(tag)

    def get_user_notifications(
        self, user_id: UUID, unread_only: bool = False
    ) -> List[NotificationResponse]:
        """Get notifications for a user"""
        notifications = self.repo.get_user_notifications(user_id, unread_only)
        return [NotificationResponse.model_validate(n) for n in notifications]

    def mark_notification_as_read(
        self, notification_id: UUID, user_id: UUID
    ) -> Dict[str, str]:
        """Mark a notification as read"""
        if not self.repo.mark_notification_as_read(notification_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )
        return {"message": "Notification marked as read"}

    def mark_all_notifications_as_read(self, user_id: UUID) -> Dict[str, str]:
        """Mark all notifications as read"""
        count = self.repo.mark_all_notifications_as_read(user_id)
        return {"message": f"Marked {count} notifications as read"}

    def get_forum_statistics(self) -> ForumStats:
        """Get forum statistics"""
        stats = self.repo.get_forum_statistics()

        return ForumStats(**stats)

    def get_trending_posts(self, limit: int = 10) -> List[TrendingPost]:
        """Get trending posts using utility calculation"""
        posts = self.repo.get_trending_posts(limit)
        trending = []

        for p in posts:
            ForumUtils.calculate_trending_score(p)
            trending.append(
                TrendingPost(
                    id=p.id,
                    title=p.title,
                    post_type=p.post_type,
                    reply_count=p.reply_count,
                    view_count=p.view_count,
                    upvote_count=p.upvote_count,
                    created_at=p.created_at,
                )
            )

        return trending

    def get_popular_tags(self, limit: int = 20) -> List[PopularTag]:
        """Get popular tags"""
        tags = self.repo.get_popular_tags(limit)
        return [
            PopularTag(id=t.id, name=t.name, usage_count=t.usage_count, color=t.color)
            for t in tags
        ]

    def get_user_reputation(self, user_id: UUID) -> Dict[str, Any]:
        """Get user reputation with calculated level and engagement score"""
        reputation = self.repo.get_or_create_reputation(user_id)

        # Calculate level using utility
        level_info = ForumUtils.calculate_reputation_level(reputation.total_points)

        # Calculate engagement score using analytics
        engagement_score = ForumAnalytics.get_user_engagement_score(reputation)

        return {
            **ReputationResponse.model_validate(reputation).model_dump(),
            "level": level_info["level"],
            "rank": level_info["rank"],
            "next_level_points": level_info["next_level_points"],
            "engagement_score": engagement_score,
        }
