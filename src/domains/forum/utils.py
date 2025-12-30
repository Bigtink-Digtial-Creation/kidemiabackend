from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from uuid import UUID
from src.domains.forum.models.forum import ForumPost, ForumReply, UserReputation
import bleach


class ForumUtils:
    """Utility functions for forum operations"""

    @staticmethod
    def calculate_trending_score(post: ForumPost) -> float:
        """
        Calculate trending score for a post
        Formula: views + (replies * 3) + (upvotes * 5)
        """
        return post.view_count + (post.reply_count * 3) + (post.upvote_count * 5)

    @staticmethod
    def is_post_recent(post: ForumPost, days: int = 7) -> bool:
        """Check if a post was created within the last N days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return post.created_at >= cutoff

    @staticmethod
    def calculate_reputation_level(total_points: int) -> Dict[str, Any]:
        """
        Calculate user reputation level based on points

        Levels:
        - Novice: 0-49 points
        - Learner: 50-199 points
        - Contributor: 200-499 points
        - Expert: 500-999 points
        - Master: 1000+ points
        """
        if total_points >= 1000:
            return {"level": "Master", "rank": 5, "next_level_points": None}
        elif total_points >= 500:
            return {
                "level": "Expert",
                "rank": 4,
                "next_level_points": 1000 - total_points,
            }
        elif total_points >= 200:
            return {
                "level": "Contributor",
                "rank": 3,
                "next_level_points": 500 - total_points,
            }
        elif total_points >= 50:
            return {
                "level": "Learner",
                "rank": 2,
                "next_level_points": 200 - total_points,
            }
        else:
            return {
                "level": "Novice",
                "rank": 1,
                "next_level_points": 50 - total_points,
            }

    @staticmethod
    def get_badge_for_milestone(reputation: UserReputation) -> Optional[str]:
        """
        Check if user has achieved a new badge milestone
        Returns badge name if milestone reached, None otherwise
        """
        badges = set(reputation.badges) if reputation.badges else set()

        # Post milestones
        if reputation.posts_created >= 100 and "century_poster" not in badges:
            return "century_poster"
        elif reputation.posts_created >= 50 and "prolific_poster" not in badges:
            return "prolific_poster"
        elif reputation.posts_created >= 10 and "active_poster" not in badges:
            return "active_poster"

        # Reply milestones
        if reputation.replies_created >= 500 and "reply_master" not in badges:
            return "reply_master"
        elif reputation.replies_created >= 100 and "helpful_responder" not in badges:
            return "helpful_responder"

        # Answer milestones
        if reputation.answers_accepted >= 50 and "answer_guru" not in badges:
            return "answer_guru"
        elif reputation.answers_accepted >= 10 and "problem_solver" not in badges:
            return "problem_solver"
        elif reputation.answers_accepted >= 1 and "first_answer" not in badges:
            return "first_answer"

        # Vote milestones
        if (
            reputation.helpful_votes_received >= 100
            and "community_favorite" not in badges
        ):
            return "community_favorite"

        return None

    @staticmethod
    def sanitize_content(content: str) -> str:
        """
        Safely sanitize user content while preserving formatting
        """

        allowed_tags = [
            "p",
            "br",
            "b",
            "strong",
            "i",
            "em",
            "u",
            "ul",
            "ol",
            "li",
            "blockquote",
            "a",
            "code",
            "pre",
            "span",
        ]

        allowed_attributes = {
            "a": ["href", "title", "target"],
            "span": ["style"],
        }

        allowed_protocols = ["http", "https", "mailto"]

        return bleach.clean(
            content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=allowed_protocols,
            strip=True,
        )

    @staticmethod
    def extract_mentions(content: str) -> List[str]:
        """
        Extract @mentions from content
        Returns list of usernames
        """
        import re

        pattern = r"@([a-zA-Z0-9_]+)"
        mentions = re.findall(pattern, content)
        return list(set(mentions))

    @staticmethod
    def generate_post_excerpt(content: str, max_length: int = 150) -> str:
        """
        Generate an excerpt from post content
        Useful for previews and notifications
        """
        if len(content) <= max_length:
            return content

        excerpt = content[:max_length]
        last_space = excerpt.rfind(" ")

        if last_space > 0:
            excerpt = excerpt[:last_space]

        return excerpt + "..."

    @staticmethod
    def format_time_ago(dt: datetime) -> str:
        """
        Format datetime as relative time (e.g., "2 hours ago")
        """
        now = datetime.utcnow()
        diff = now - dt

        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif seconds < 31536000:
            months = int(seconds / 2592000)
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = int(seconds / 31536000)
            return f"{years} year{'s' if years != 1 else ''} ago"


class ForumPermissions:
    """Permission checking utilities"""

    @staticmethod
    def can_edit_post(post: ForumPost, user_id: UUID) -> bool:
        """Check if user can edit a post"""
        return post.author_id == user_id

    @staticmethod
    def can_delete_post(
        post: ForumPost, user_id: UUID, is_moderator: bool = False
    ) -> bool:
        """Check if user can delete a post"""
        return post.author_id == user_id or is_moderator

    @staticmethod
    def can_accept_answer(
        post: ForumPost, user_id: UUID, is_moderator: bool = False
    ) -> bool:
        """Check if user can accept answers on a post"""
        return post.author_id == user_id or is_moderator

    @staticmethod
    def can_edit_reply(reply: ForumReply, user_id: UUID) -> bool:
        """Check if user can edit a reply"""
        return reply.author_id == user_id

    @staticmethod
    def can_delete_reply(
        reply: ForumReply, user_id: UUID, is_moderator: bool = False
    ) -> bool:
        """Check if user can delete a reply"""
        return reply.author_id == user_id or is_moderator

    @staticmethod
    def can_lock_post(
        user_id: UUID, is_moderator: bool = False, is_admin: bool = False
    ) -> bool:
        """Check if user can lock/unlock posts"""
        return is_moderator or is_admin

    @staticmethod
    def can_pin_post(
        user_id: UUID, is_moderator: bool = False, is_admin: bool = False
    ) -> bool:
        """Check if user can pin posts"""
        return is_moderator or is_admin


class ForumValidators:
    """Validation utilities for forum data"""

    @staticmethod
    def validate_post_title(title: str) -> tuple[bool, Optional[str]]:
        """
        Validate post title
        Returns (is_valid, error_message)
        """
        if not title or len(title.strip()) < 5:
            return False, "Title must be at least 5 characters long"

        if len(title) > 500:
            return False, "Title must not exceed 500 characters"

        # Check for spam-like patterns (all caps, excessive punctuation)
        if title.isupper() and len(title) > 20:
            return False, "Title should not be in all caps"

        return True, None

    @staticmethod
    def validate_content(
        content: str, min_length: int = 10
    ) -> tuple[bool, Optional[str]]:
        """
        Validate post/reply content
        Returns (is_valid, error_message)
        """
        if not content or len(content.strip()) < min_length:
            return False, f"Content must be at least {min_length} characters long"

        if len(content) > 10000:
            return False, "Content must not exceed 10000 characters"

        return True, None

    @staticmethod
    def validate_tag_name(name: str) -> tuple[bool, Optional[str]]:
        """
        Validate tag name
        Returns (is_valid, error_message)
        """
        if not name or len(name.strip()) < 1:
            return False, "Tag name cannot be empty"

        if len(name) > 50:
            return False, "Tag name must not exceed 50 characters"

        # Only allow alphanumeric, hyphens, and underscores
        import re

        if not re.match(r"^[a-zA-Z0-9\-_]+$", name):
            return (
                False,
                "Tag name can only contain letters, numbers, hyphens, and underscores",
            )

        return True, None


class ForumAnalytics:
    """Analytics and metrics utilities"""

    @staticmethod
    def get_user_engagement_score(reputation: UserReputation) -> float:
        """
        Calculate user engagement score (0-100)
        Based on various activities weighted differently
        """
        score = 0

        # Post creation (max 20 points)
        score += min(reputation.posts_created * 0.5, 20)

        # Reply creation (max 30 points)
        score += min(reputation.replies_created * 0.3, 30)

        # Accepted answers (max 30 points)
        score += min(reputation.answers_accepted * 3, 30)

        # Helpful votes received (max 20 points)
        score += min(reputation.helpful_votes_received * 0.2, 20)

        return min(score, 100)

    @staticmethod
    def get_post_quality_score(post: ForumPost) -> float:
        """
        Calculate post quality score (0-100)
        Based on engagement metrics
        """
        score = 0

        # Upvotes (max 40 points)
        score += min(post.upvote_count * 4, 40)

        # Replies (max 30 points)
        score += min(post.reply_count * 3, 30)

        # Views relative to age (max 30 points)

        created_at = post.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        days_old = (datetime.now(timezone.utc) - created_at).days + 1
        views_per_day = post.view_count / days_old
        score += min(views_per_day * 3, 30)

        return min(score, 100)

    @staticmethod
    def should_feature_post(post: ForumPost, db: Session) -> bool:
        """
        Determine if a post should be featured
        Based on quality score and recency
        """
        quality_score = ForumAnalytics.get_post_quality_score(post)
        is_recent = ForumUtils.is_post_recent(post, days=3)

        return quality_score >= 70 and is_recent


# Middleware functions
def rate_limit_check(user_id: UUID, action: str, db: Session) -> bool:
    """
    Check if user has exceeded rate limits

    Limits:
    - Posts: 10 per hour
    - Replies: 30 per hour
    - Reactions: 100 per hour
    """
    # This is a simplified version
    # In production, use Redis or similar for rate limiting
    from datetime import datetime, timedelta

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    if action == "post":
        recent_posts = (
            db.query(ForumPost)
            .filter(
                ForumPost.author_id == user_id, ForumPost.created_at >= one_hour_ago
            )
            .count()
        )
        return recent_posts < 10

    elif action == "reply":
        recent_replies = (
            db.query(ForumReply)
            .filter(
                ForumReply.author_id == user_id, ForumReply.created_at >= one_hour_ago
            )
            .count()
        )
        return recent_replies < 30

    return True


def content_moderation_check(content: str) -> tuple[bool, Optional[str]]:
    """
    Basic content moderation
    Check for prohibited content

    Returns (is_allowed, reason)
    """
    # List of prohibited words/phrases (expand as needed)
    prohibited_words = [
        # ── Spam & Fraud ──
        "spam",
        "scam",
        "fraud",
        "phishing",
        "spoof",
        "fake",
        "impersonate",
        "clickbait",
        # ── Hacking / Cybercrime ──
        "hack",
        "hacking",
        "crack",
        "cracking",
        "exploit",
        "breach",
        "ddos",
        "malware",
        "ransomware",
        "trojan",
        "keylogger",
        # ── Exam Malpractice / Cheating ──
        "cheat",
        "cheating",
        "exam leak",
        "question leak",
        "answer leak",
        "runz",
        "expo",
        "mercenary",
        "impersonation",
        "exam fraud",
        # ── Illegal / Unethical Activities ──
        "bribe",
        "bribery",
        "corruption",
        "forgery",
        "illegal",
        "piracy",
        "plagiarism",
        "plagiarize",
        # ── Harassment / Abuse ──
        "abuse",
        "harass",
        "harassment",
        "threat",
        "threaten",
        "bully",
        "bullying",
        "blackmail",
        "extort",
        # ── Explicit / Unsafe Content ──
        "porn",
        "pornography",
        "nude",
        "nudity",
        "sex",
        "sexual",
        "explicit",
        "xxx",
        # ── Hate / Offensive Speech ──
        "hate",
        "racist",
        "racism",
        "sexist",
        "discrimination",
        "slur",
        "bigot",
        # ── Platform Abuse ──
        "bot",
        "automation abuse",
        "fake account",
        "account selling",
        "account hacking",
    ]

    content_lower = content.lower()

    for word in prohibited_words:
        if word in content_lower:
            return False, f"Content contains prohibited term: {word}"

    # Check for excessive links (potential spam)
    import re

    links = re.findall(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        content,
    )
    if len(links) > 3:
        return False, "Too many links in content"

    return True, None


# Export all utilities
__all__ = [
    "ForumUtils",
    "ForumPermissions",
    "ForumValidators",
    "ForumAnalytics",
    "rate_limit_check",
    "content_moderation_check",
]
