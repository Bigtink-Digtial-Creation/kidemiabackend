from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from uuid import UUID
from src.domains.forum.models.forum import (
    ForumPost,
    ForumTag,
    PostStatus,
    PostType,
    post_tags,
)
from src.domains.forum.repositories.forum_repository import ForumRepository
from src.domains.forum.schemas.forum import PostResponse
from src.domains.forum.models.forum import PostReaction, PostBookmark, ForumReply


class ForumFeedService:
    """Service for generating personalized content feeds"""

    def __init__(self, db: Session):
        self.db = db

    def get_personalized_feed(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Generate personalized feed based on user's interests and activity

        Algorithm:
        1. Posts from followed users (high priority)
        2. Posts in user's subjects (medium priority)
        3. Posts in user's exam target (medium priority)
        4. Posts with tags user interacts with (medium priority)
        5. Trending posts (low priority)
        6. Recent posts (fallback)
        """
        # Get user's interests and activity
        user_profile = self._get_user_profile(user_id)

        # Build weighted query
        posts_query = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .filter(ForumPost.status == PostStatus.ACTIVE)
        )

        # Score posts based on relevance
        scored_posts = []
        all_posts = posts_query.all()

        for post in all_posts:
            score = self._calculate_relevance_score(post, user_profile)
            scored_posts.append((score, post))

        # Sort by score (descending) and then by recency
        scored_posts.sort(key=lambda x: (x[0], x[1].last_activity_at), reverse=True)

        # Paginate
        offset = (page - 1) * page_size
        paginated_posts = scored_posts[offset : offset + page_size]

        # Extract posts
        posts = [post for _, post in paginated_posts]
        total = len(scored_posts)

        # Enrich with user-specific data
        enriched_posts = []
        for post in posts:
            post_dict = self._enrich_post_with_user_data(post, user_id)
            enriched_posts.append(PostResponse(**post_dict))

        return {
            "posts": enriched_posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    def get_discover_feed(
        self,
        user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
        feed_type: str = "all",
    ) -> Dict[str, Any]:
        """
        Get discovery feed with various filters

        Feed types:
        - all: All recent posts
        - trending: Trending posts
        - unanswered: Unanswered questions
        - popular: Most popular posts
        - following: Posts from followed users
        - subjects: Posts in user's subjects
        """
        query = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .filter(ForumPost.status == PostStatus.ACTIVE)
        )

        if feed_type == "trending":
            # Trending in last 7 days
            since = datetime.now(timezone.utc) - timedelta(days=7)
            query = query.filter(ForumPost.created_at >= since)
            # Calculate trending score: views + (replies * 3) + (upvotes * 5)
            posts = query.all()
            posts = sorted(
                posts,
                key=lambda p: p.view_count + (p.reply_count * 3) + (p.upvote_count * 5),
                reverse=True,
            )

        elif feed_type == "unanswered":
            query = query.filter(
                ForumPost.post_type == PostType.QUESTION,
                ForumPost.is_answered.is_(False),
            ).order_by(desc(ForumPost.created_at))
            posts = query.all()

        elif feed_type == "popular":
            # Popular in last 30 days
            since = datetime.now(timezone.utc) - timedelta(days=30)
            query = query.filter(ForumPost.created_at >= since)
            query = query.order_by(desc(ForumPost.upvote_count))
            posts = query.all()

        elif feed_type == "following" and user_id:
            # Posts from followed users
            following_ids = self._get_following_user_ids(user_id)
            query = query.filter(ForumPost.author_id.in_(following_ids))
            query = query.order_by(desc(ForumPost.last_activity_at))
            posts = query.all()

        elif feed_type == "subjects" and user_id:
            # Posts in user's subjects
            user_subjects = self._get_user_subjects(user_id)
            query = query.filter(ForumPost.subject_id.in_(user_subjects))
            query = query.order_by(desc(ForumPost.last_activity_at))
            posts = query.all()

        else:  # all
            query = query.order_by(desc(ForumPost.last_activity_at))
            posts = query.all()

        # Paginate
        total = len(posts)
        offset = (page - 1) * page_size
        paginated_posts = posts[offset : offset + page_size]

        # Enrich with user data
        enriched_posts = []
        for post in paginated_posts:
            post_dict = self._enrich_post_with_user_data(post, user_id)
            enriched_posts.append(PostResponse(**post_dict))

        return {
            "posts": enriched_posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
            "feed_type": feed_type,
        }

    def get_subject_feed(
        self,
        subject_id: UUID,
        user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get feed for a specific subject"""
        query = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .filter(
                ForumPost.status == PostStatus.ACTIVE,
                ForumPost.subject_id == subject_id,
            )
            .order_by(desc(ForumPost.last_activity_at))
        )

        total = query.count()
        offset = (page - 1) * page_size
        posts = query.offset(offset).limit(page_size).all()

        # Enrich posts
        enriched_posts = []
        for post in posts:
            post_dict = self._enrich_post_with_user_data(post, user_id)
            enriched_posts.append(PostResponse(**post_dict))

        return {
            "posts": enriched_posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    def get_tag_feed(
        self,
        tag_id: UUID,
        user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get feed for a specific tag"""
        query = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .join(ForumPost.tags)
            .filter(ForumPost.status == PostStatus.ACTIVE, ForumTag.id == tag_id)
            .order_by(desc(ForumPost.last_activity_at))
        )

        total = query.count()
        offset = (page - 1) * page_size
        posts = query.offset(offset).limit(page_size).all()

        enriched_posts = []
        for post in posts:
            post_dict = self._enrich_post_with_user_data(post, user_id)
            enriched_posts.append(PostResponse(**post_dict))

        return {
            "posts": enriched_posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    def get_user_activity_feed(
        self,
        target_user_id: UUID,
        current_user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get a user's posts and activity"""
        query = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .filter(
                ForumPost.status == PostStatus.ACTIVE,
                ForumPost.author_id == target_user_id,
            )
            .order_by(desc(ForumPost.created_at))
        )

        total = query.count()
        offset = (page - 1) * page_size
        posts = query.offset(offset).limit(page_size).all()

        enriched_posts = []
        for post in posts:
            post_dict = self._enrich_post_with_user_data(post, current_user_id)
            enriched_posts.append(PostResponse(**post_dict))

        return {
            "posts": enriched_posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    def get_recommended_posts(
        self, user_id: UUID, limit: int = 10
    ) -> List[PostResponse]:
        """
        Get recommended posts based on user's interests
        Uses collaborative filtering approach
        """
        # Get user's interacted posts
        user_interactions = self._get_user_interactions(user_id)

        if not user_interactions:
            # New user - return trending posts
            return self._get_trending_posts(limit)

        # Find similar users based on interactions
        similar_users = self._find_similar_users(user_id, user_interactions)

        # Get posts interacted with by similar users
        recommended_post_ids = self._get_posts_from_similar_users(
            similar_users, user_interactions, limit
        )

        # Fetch and return posts
        posts = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .filter(
                ForumPost.id.in_(recommended_post_ids),
                ForumPost.status == PostStatus.ACTIVE,
            )
            .all()
        )

        # Enrich posts
        enriched_posts = []
        for post in posts:
            post_dict = self._enrich_post_with_user_data(post, user_id)
            enriched_posts.append(PostResponse(**post_dict))

        return enriched_posts

    def get_questions_for_you(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get unanswered questions that match user's expertise
        Based on subjects and tags user has answered before
        """
        # Get user's areas of expertise
        expertise = self._get_user_expertise(user_id)

        query = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .filter(
                ForumPost.status == PostStatus.ACTIVE,
                ForumPost.post_type == PostType.QUESTION,
                ForumPost.is_answered.is_(False),
            )
        )

        # Filter by expertise
        if expertise["subjects"]:
            query = query.filter(ForumPost.subject_id.in_(expertise["subjects"]))

        # Score by relevance
        posts = query.all()
        scored_posts = []

        for post in posts:
            score = 0
            # Score by matching tags
            post_tag_names = {tag.name for tag in post.tags}
            matching_tags = post_tag_names.intersection(expertise["tags"])
            score += len(matching_tags) * 5

            # Boost recent questions
            created_at = post.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            days_old = (datetime.now(timezone.utc) - created_at).days
            if days_old < 1:
                score += 10
            elif days_old < 3:
                score += 5

            # Boost questions with no replies
            if post.reply_count == 0:
                score += 3

            scored_posts.append((score, post))

        # Sort by score
        scored_posts.sort(key=lambda x: x[0], reverse=True)

        # Paginate
        total = len(scored_posts)
        offset = (page - 1) * page_size
        paginated_posts = scored_posts[offset : offset + page_size]

        posts = [post for _, post in paginated_posts]

        enriched_posts = []
        for post in posts:
            post_dict = self._enrich_post_with_user_data(post, user_id)
            enriched_posts.append(PostResponse(**post_dict))

        return {
            "posts": enriched_posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    #  Helper Methods

    def _get_user_profile(self, user_id: UUID) -> Dict[str, Any]:
        """Get user's profile including interests and activity"""
        # Get user's subjects
        subjects = self._get_user_subjects(user_id)

        # Get user's frequently interacted tags
        tags = self._get_user_frequent_tags(user_id)

        # Get user's exam target
        exam_target = self._get_user_exam_target(user_id)

        # Get users the person follows
        following_ids = self._get_following_user_ids(user_id)

        return {
            "subjects": subjects,
            "tags": tags,
            "exam_target": exam_target,
            "following_ids": following_ids,
        }

    def _calculate_relevance_score(
        self, post: ForumPost, user_profile: Dict[str, Any]
    ) -> float:
        """Calculate how relevant a post is to the user"""
        score = 0

        # Author is followed (+20 points)
        if post.author_id in user_profile["following_ids"]:
            score += 20

        # Same subject (+15 points)
        if post.subject_id in user_profile["subjects"]:
            score += 15

        # Same exam target (+10 points)
        if post.exam_target == user_profile["exam_target"]:
            score += 10

        # Matching tags (+5 points per tag)
        post_tag_names = {tag.name for tag in post.tags}
        matching_tags = post_tag_names.intersection(user_profile["tags"])
        score += len(matching_tags) * 5

        # Engagement boost (popular posts are more relevant)
        engagement_score = (post.upvote_count * 2) + (post.reply_count * 1.5)
        score += min(engagement_score, 20)  # Cap at 20 points

        # Recency boost (newer posts get slight boost)

        created_at = post.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        hours_old = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
        if hours_old < 24:
            score += 10
        elif hours_old < 72:
            score += 5

        return score

    def _get_user_subjects(self, user_id: UUID) -> List[str]:
        """Get subjects the user is interested in"""
        # This would come from user's enrolled courses or preferences
        # For now, return subjects from user's posts
        subjects = (
            self.db.query(ForumPost.subject_id)
            .filter(ForumPost.author_id == user_id, ForumPost.subject_id.isnot(None))
            .distinct()
            .all()
        )

        return [s[0] for s in subjects]

    def _get_user_frequent_tags(self, user_id: UUID, limit: int = 10) -> set:
        """Get tags the user frequently interacts with"""
        # Get tags from user's posts
        _post_tags = (
            self.db.query(ForumTag.name)
            .join(post_tags)
            .join(ForumPost)
            .filter(ForumPost.author_id == user_id)
            .all()
        )

        return {tag[0] for tag in _post_tags}

    def _get_user_exam_target(self, user_id: UUID) -> Optional[str]:
        """Get user's exam target"""
        # This would come from user profile
        # For now, return most common  exam target from user's posts
        result = (
            self.db.query(ForumPost.exam_target)
            .filter(ForumPost.author_id == user_id, ForumPost.exam_target.isnot(None))
            .first()
        )

        return result[0] if result else None

    def _get_following_user_ids(self, user_id: UUID) -> List[str]:
        """Get IDs of users that this user follows"""
        # This would come from a user following system
        # For now, return empty list (implement if you have user following)
        return []

    def _get_user_interactions(self, user_id: UUID) -> set:
        """Get post IDs the user has interacted with"""

        interactions = set()

        # Posts user created
        posts = self.db.query(ForumPost.id).filter(ForumPost.author_id == user_id).all()
        interactions.update([p[0] for p in posts])

        # Posts user reacted to
        reactions = (
            self.db.query(PostReaction.post_id)
            .filter(PostReaction.user_id == user_id)
            .all()
        )
        interactions.update([r[0] for r in reactions])

        # Posts user bookmarked
        bookmarks = (
            self.db.query(PostBookmark.post_id)
            .filter(PostBookmark.user_id == user_id)
            .all()
        )
        interactions.update([b[0] for b in bookmarks])

        # Posts user replied to
        replies = (
            self.db.query(ForumReply.post_id)
            .filter(ForumReply.author_id == user_id)
            .distinct()
            .all()
        )
        interactions.update([r[0] for r in replies])

        return interactions

    def _find_similar_users(
        self, user_id: UUID, user_interactions: set, limit: int = 10
    ) -> List[UUID]:
        """Find users with similar interaction patterns"""

        # Find users who interacted with the same posts
        similar_users = (
            self.db.query(
                PostReaction.user_id,
                func.count(PostReaction.id).label("common_interactions"),
            )
            .filter(
                PostReaction.post_id.in_(user_interactions),
                PostReaction.user_id != user_id,
            )
            .group_by(PostReaction.user_id)
            .order_by(desc("common_interactions"))
            .limit(limit)
            .all()
        )

        return [u[0] for u in similar_users]

    def _get_posts_from_similar_users(
        self, similar_users: List[str], exclude_posts: set, limit: int
    ) -> List[str]:
        """Get posts interacted with by similar users"""

        if not similar_users:
            return []

        # Get posts these users interacted with
        posts = (
            self.db.query(
                PostReaction.post_id,
                func.count(PostReaction.id).label("interaction_count"),
            )
            .filter(
                PostReaction.user_id.in_(similar_users),
                PostReaction.post_id.notin_(exclude_posts),
            )
            .group_by(PostReaction.post_id)
            .order_by(desc("interaction_count"))
            .limit(limit)
            .all()
        )

        return [p[0] for p in posts]

    def _get_trending_posts(self, limit: int) -> List[PostResponse]:
        """Get trending posts for new users"""
        since = datetime.now(timezone.utc) - timedelta(days=7)
        posts = (
            self.db.query(ForumPost)
            .options(joinedload(ForumPost.author), joinedload(ForumPost.tags))
            .filter(
                ForumPost.created_at >= since, ForumPost.status == PostStatus.ACTIVE
            )
            .all()
        )

        # Sort by trending score
        posts = sorted(
            posts,
            key=lambda p: p.view_count + (p.reply_count * 3) + (p.upvote_count * 5),
            reverse=True,
        )[:limit]

        return [PostResponse.model_validate(p) for p in posts]

    def _get_user_expertise(self, user_id: UUID) -> Dict[str, Any]:
        """Get areas where user has expertise (has answered questions)"""

        # Get subjects where user has accepted answers
        expertise_subjects = (
            self.db.query(ForumPost.subject_id)
            .join(ForumReply)
            .filter(
                ForumReply.author_id == user_id,
                ForumReply.is_accepted_answer.is_(True),
                ForumPost.subject_id.isnot(None),
            )
            .distinct()
            .all()
        )

        # Get tags from posts where user has accepted answers
        expertise_tags = (
            self.db.query(ForumTag.name)
            .join(post_tags)
            .join(ForumPost)
            .join(ForumReply)
            .filter(
                ForumReply.author_id == user_id, ForumReply.is_accepted_answeris_(True)
            )
            .distinct()
            .all()
        )

        return {
            "subjects": [s[0] for s in expertise_subjects],
            "tags": {t[0] for t in expertise_tags},
        }

    def _enrich_post_with_user_data(
        self, post: Any, user_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """Add user-specific data to post"""

        repo = ForumRepository(self.db)
        post_dict = post.__dict__.copy()

        if user_id:
            post_dict["user_has_upvoted"] = repo.user_has_reacted_to_post(
                post.id, user_id
            )
            post_dict["user_has_bookmarked"] = repo.user_has_bookmarked(
                post.id, user_id
            )
            post_dict["user_is_following"] = repo.user_is_following_post(
                post.id, user_id
            )
        else:
            post_dict["user_has_upvoted"] = False
            post_dict["user_has_bookmarked"] = False
            post_dict["user_is_following"] = False

        return post_dict
