from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from src.domains.forum.models.forum import PostType, PostStatus, ReactionType
from src.shared.schemas.base import (
    BaseSchema,
    IDSchema,
    BaseDBSchema,
    ResponseSchema,
)


class TagBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field("#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")


class TagCreate(TagBase):
    pass


class TagResponse(TagBase, ResponseSchema):
    usage_count: int


class AuthorInfo(IDSchema):
    full_name: str
    email: str
    profile_picture_url: Optional[str] = None
    reputation_points: Optional[int] = 0


#  Reply Schemas
class ReplyBase(BaseSchema):
    content: str = Field(..., min_length=1, max_length=5000)
    parent_reply_id: Optional[UUID] = None


class ReplyCreate(ReplyBase):
    pass


class ReplyUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class ReplyResponse(ReplyBase, BaseDBSchema):
    post_id: UUID
    author_id: UUID
    author: Optional[AuthorInfo] = None
    upvote_count: int
    is_accepted_answer: bool
    is_edited: bool
    flagged_count: int
    child_replies: List["ReplyResponse"] = []
    user_has_upvoted: Optional[bool] = False


#  Post Schemas
class PostBase(BaseSchema):
    title: str = Field(..., min_length=5, max_length=500)
    content: str = Field(..., min_length=10, max_length=10000)
    post_type: PostType = PostType.DISCUSSION
    subject_id: Optional[UUID] = None
    exam_target: Optional[str] = None
    tag_names: List[str] = Field(default_factory=list, max_items=5)


class PostCreate(PostBase):
    pass


class PostUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    content: Optional[str] = Field(None, min_length=10, max_length=10000)
    status: Optional[PostStatus] = None
    tag_names: Optional[List[str]] = Field(None, max_items=5)


class PostResponse(PostBase, BaseDBSchema):
    status: PostStatus
    author_id: UUID
    author: Optional[AuthorInfo] = None
    view_count: int
    reply_count: int
    upvote_count: int
    is_answered: bool
    accepted_answer_id: Optional[str] = None
    is_pinned: bool
    is_locked: bool
    flagged_count: int
    last_activity_at: datetime
    tags: List[TagResponse] = []
    user_has_upvoted: Optional[bool] = False
    user_has_bookmarked: Optional[bool] = False
    user_is_following: Optional[bool] = False


class PostDetailResponse(PostResponse):
    replies: List[ReplyResponse] = []


class PostListResponse(BaseSchema):
    posts: List[PostResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Reaction Schemas
class ReactionCreate(BaseSchema):
    reaction_type: ReactionType = ReactionType.LIKE


class ReactionResponse(IDSchema):
    user_id: UUID
    reaction_type: ReactionType
    created_at: datetime


#  Bookmark Schemas
class BookmarkCreate(BaseSchema):
    notes: Optional[str] = Field(None, max_length=500)


class BookmarkUpdate(BaseSchema):
    notes: Optional[str] = Field(None, max_length=500)


class BookmarkResponse(IDSchema):
    post_id: UUID
    user_id: UUID
    notes: Optional[str] = None
    created_at: datetime
    post: Optional[PostResponse] = None


#  Reputation Schemas
class ReputationResponse(IDSchema):
    user_id: UUID
    total_points: int
    posts_created: int
    replies_created: int
    answers_accepted: int
    helpful_votes_received: int
    badges: List[str] = []
    last_active_at: datetime


# Notification Schemas
class NotificationResponse(IDSchema):
    notification_type: str
    title: str
    message: str
    post_id: Optional[UUID] = None
    reply_id: Optional[UUID] = None
    triggering_user_id: Optional[UUID] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None


#  Statistics Schemas
class ForumStats(BaseModel):
    total_posts: int
    total_replies: int
    total_users: int
    active_discussions: int
    answered_questions: int


class TrendingPost(IDSchema):
    title: str
    post_type: PostType
    reply_count: int
    view_count: int
    upvote_count: int
    created_at: datetime


class PopularTag(IDSchema):
    name: str
    usage_count: int
    color: str


#  Search/Filter Schemas
class PostFilters(BaseModel):
    post_type: Optional[PostType] = None
    status: Optional[PostStatus] = None
    subject_id: Optional[UUID] = None
    exam_target: Optional[str] = None
    tag_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
    is_answered: Optional[bool] = None
    search_query: Optional[str] = None
    sort_by: Optional[str] = "recent"  # recent, popular, trending, unanswered
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class UserProfile(IDSchema):
    full_name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    reputation_points: int
    created_at: datetime


class UserStatsResponse(BaseSchema):
    posts_created: int
    replies_created: int
    answers_accepted: int
    helpful_votes_received: int
    questions_asked: int
    questions_answered: int


class UserReputationResponse(BaseSchema):
    total_points: int
    level: str
    rank: int
    next_level_points: int
    engagement_score: float
    badges: list[str] = []


class UserProfileResponse(BaseSchema):
    user: UserProfile
    stats: UserStatsResponse
    reputation_meta: UserReputationResponse


ReplyResponse.model_rebuild()
