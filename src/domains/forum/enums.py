from enum import Enum


class PostType(str, Enum):
    QUESTION = "question"
    DISCUSSION = "discussion"
    STUDY_GROUP = "study_group"
    RESOURCE_SHARE = "resource_share"
    ANNOUNCEMENT = "announcement"


class PostStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"
    FLAGGED = "flagged"


class ReactionType(str, Enum):
    LIKE = "like"
    HELPFUL = "helpful"
    INSIGHTFUL = "insightful"
    CELEBRATE = "celebrate"
