from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from uuid import UUID
from src.config.database import get_db
from src.core.security import get_current_user, get_current_user_id
from src.domains.forum.services.forum_service import ForumService
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
    UserStatsResponse,
    UserProfile,
    UserProfileResponse,
    UserReputationResponse,
)
from src.domains.forum.models.forum import PostType, PostStatus
from src.domains.auth.models.user import User, user_following
from src.domains.forum.models.forum import ForumPost, ForumReply

router = APIRouter(prefix="/forum", tags=["Community"])


#  Post Endpoints
@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a new forum post

    - **title**: Post title (5-500 characters)
    - **content**: Post content (10-10000 characters)
    - **post_type**: Type of post (question, discussion, study_group, resource_share, announcement)
    - **subject_id**: Optional subject ID
    - **exam_target**: Optional exam target
    - **tag_names**: List of tag names (max 5)
    """
    service = ForumService(db)
    return service.create_post(post_data, user_id)


@router.get("/posts", response_model=PostListResponse)
def get_posts(
    post_type: Optional[PostType] = None,
    status_filter: Optional[PostStatus] = Query(None, alias="status"),
    subject_id: Optional[str] = None,
    exam_target: Optional[str] = None,
    tag_id: Optional[str] = None,
    author_id: Optional[str] = None,
    is_answered: Optional[bool] = None,
    search_query: Optional[str] = Query(None, alias="search"),
    sort_by: str = Query("recent", regex="^(recent|popular|trending|unanswered)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get filtered and paginated posts

    **Filters:**
    - **post_type**: Filter by post type
    - **status**: Filter by status (active, closed, archived, flagged)
    - **subject_id**: Filter by subject
    - **exam target**: Filter by exam target
    - **tag_id**: Filter by tag
    - **author_id**: Filter by author
    - **is_answered**: Filter by answered status (for questions)
    - **search**: Search in title and content

    **Sorting:**
    - **recent**: Most recently active posts (default)
    - **popular**: Most upvoted posts
    - **trending**: Most viewed posts
    - **unanswered**: Unanswered questions only

    **Pagination:**
    - **page**: Page number (starts at 1)
    - **page_size**: Number of posts per page (1-100)
    """
    filters = PostFilters(
        post_type=post_type,
        status=status_filter,
        subject_id=subject_id,
        exam_target=exam_target,
        tag_id=tag_id,
        author_id=author_id,
        is_answered=is_answered,
        search_query=search_query,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    service = ForumService(db)
    user_id = user_id if user_id else None
    return service.get_posts(filters, user_id)


@router.get("/posts/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: UUID,
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get a single post with all replies

    This endpoint increments the view count for the post.
    """
    service = ForumService(db)
    user_id = user_id if user_id else None
    return service.get_post(post_id, user_id)


@router.patch("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Update a post

    Only the post author can update their post.
    """
    service = ForumService(db)
    return service.update_post(post_id, post_data, user_id)


@router.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
def delete_post(
    post_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Delete a post

    Only the post author can delete their post.
    This will also delete all associated replies and reactions.
    """
    service = ForumService(db)
    return service.delete_post(post_id, user_id)


# ============ Reply Endpoints ============
@router.post(
    "/posts/{post_id}/replies",
    response_model=ReplyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reply(
    post_id: UUID,
    reply_data: ReplyCreate,
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a reply to a post

    - **content**: Reply content (1-5000 characters)
    - **parent_reply_id**: Optional parent reply ID for threading
    """
    service = ForumService(db)
    return service.create_reply(post_id, reply_data, user_id)


@router.patch("/replies/{reply_id}", response_model=ReplyResponse)
def update_reply(
    reply_id: UUID,
    reply_data: ReplyUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Update a reply

    Only the reply author can update their reply.
    """
    service = ForumService(db)
    return service.update_reply(reply_id, reply_data, user_id)


@router.delete("/replies/{reply_id}", status_code=status.HTTP_200_OK)
def delete_reply(
    reply_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Delete a reply

    Only the reply author can delete their reply.
    """
    service = ForumService(db)
    return service.delete_reply(reply_id, user_id)


@router.post("/posts/{post_id}/replies/{reply_id}/accept", response_model=ReplyResponse)
def accept_answer(
    post_id: UUID,
    reply_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Mark a reply as the accepted answer

    Only the post author can accept answers.
    This awards reputation points to the reply author.
    """
    service = ForumService(db)
    return service.mark_reply_as_accepted(post_id, reply_id, user_id)


#  Reaction Endpoints
@router.post("/posts/{post_id}/reactions")
def toggle_post_reaction(
    post_id: UUID,
    reaction_data: ReactionCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Toggle reaction on a post

    - **reaction_type**: Type of reaction (like, helpful, insightful, celebrate)

    If the user has already reacted, this will remove the reaction.
    Otherwise, it will add the reaction.
    """
    service = ForumService(db)
    return service.toggle_post_reaction(post_id, user_id, reaction_data)


@router.post("/replies/{reply_id}/reactions")
def toggle_reply_reaction(
    reply_id: UUID,
    reaction_data: ReactionCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Toggle reaction on a reply

    - **reaction_type**: Type of reaction (like, helpful, insightful, celebrate)

    If the user has already reacted, this will remove the reaction.
    Otherwise, it will add the reaction.
    """
    service = ForumService(db)
    return service.toggle_reply_reaction(reply_id, user_id, reaction_data)


#  Bookmark Endpoints
@router.post("/posts/{post_id}/bookmark")
def toggle_bookmark(
    post_id: UUID,
    bookmark_data: Optional[BookmarkCreate] = None,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Toggle bookmark on a post

    - **notes**: Optional notes about the bookmark

    If the post is already bookmarked, this will remove the bookmark.
    Otherwise, it will add the bookmark.
    """
    service = ForumService(db)
    return service.toggle_bookmark(post_id, user_id, bookmark_data)


@router.get("/bookmarks", response_model=List[BookmarkResponse])
def get_my_bookmarks(
    user_id: UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Get all bookmarks for the current user
    """
    service = ForumService(db)
    return service.get_user_bookmarks(user_id)


#  Follow Endpoints
@router.post("/posts/{post_id}/follow")
def toggle_follow_post(
    post_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Toggle follow status on a post

    Following a post means you'll receive notifications when:
    - Someone replies to the post
    - The post is updated
    - An answer is accepted

    If already following, this will unfollow.
    Otherwise, it will follow the post.
    """
    service = ForumService(db)
    return service.toggle_follow_post(post_id, user_id)


#  Tag Endpoints
@router.get("/tags", response_model=List[TagResponse])
def get_all_tags(db: Session = Depends(get_db)):
    """
    Get all forum tags ordered by usage count
    """
    service = ForumService(db)
    return service.get_all_tags()


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag_data: TagCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new tag

    - **name**: Tag name (1-50 characters, unique)
    - **description**: Optional tag description (max 200 characters)
    - **color**: Hex color code (default: #3B82F6)
    """
    service = ForumService(db)
    return service.create_tag(tag_data)


# Notification Endpoints
@router.get("/notifications", response_model=List[NotificationResponse])
def get_my_notifications(
    unread_only: bool = Query(False),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get notifications for the current user

    - **unread_only**: If true, only return unread notifications
    """
    service = ForumService(db)
    return service.get_user_notifications(user_id, unread_only)


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Mark a notification as read
    """
    service = ForumService(db)
    return service.mark_notification_as_read(notification_id, user_id)


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    user_id: UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Mark all notifications as read
    """
    service = ForumService(db)
    return service.mark_all_notifications_as_read(user_id)


#  Statistics Endpoints
@router.get("/stats", response_model=ForumStats)
def get_forum_statistics(db: Session = Depends(get_db)):
    """
    Get overall forum statistics

    Returns counts for:
    - Total posts
    - Total replies
    - Active discussions (last 7 days)
    - Answered questions
    """
    service = ForumService(db)
    return service.get_forum_statistics()


@router.get("/trending", response_model=List[TrendingPost])
def get_trending_posts(
    limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)
):
    """
    Get trending posts

    Trending is calculated based on a combination of:
    - View count
    - Reply count (weighted 3x)
    - Upvote count (weighted 5x)

    Only includes posts from the last 7 days.
    """
    service = ForumService(db)
    return service.get_trending_posts(limit)


@router.get("/tags/popular", response_model=List[PopularTag])
def get_popular_tags(
    limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)
):
    """
    Get most popular tags by usage count
    """
    service = ForumService(db)
    return service.get_popular_tags(limit)


@router.get("/users/{user_id}/reputation", response_model=ReputationResponse)
def get_user_reputation(user_id: UUID, db: Session = Depends(get_db)):
    """
    Get reputation and achievements for a user

    Returns:
    - Total reputation points
    - Activity counts (posts, replies, accepted answers)
    - Badges and achievements
    """
    service = ForumService(db)
    return service.get_user_reputation(user_id)


@router.get("/my-reputation", response_model=ReputationResponse)
def get_my_reputation(
    user_id: UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Get reputation and achievements for the current user
    """
    service = ForumService(db)
    return service.get_user_reputation(user_id)


@router.get(
    "/users/{user_id}/profile",
    response_model=UserProfileResponse,
)
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    service = ForumService(db)
    reputation = service.get_user_reputation(user_id)

    stats = UserStatsResponse(
        posts_created=reputation["posts_created"] if reputation else 0,
        replies_created=reputation["replies_created"] if reputation else 0,
        answers_accepted=reputation["answers_accepted"] if reputation else 0,
        helpful_votes_received=reputation["helpful_votes_received"]
        if reputation
        else 0,
        questions_asked=db.query(ForumPost)
        .filter(
            ForumPost.author_id == user_id,
            ForumPost.post_type == "question",
        )
        .count(),
        questions_answered=db.query(ForumReply)
        .filter(
            ForumReply.author_id == user_id,
            ForumReply.is_accepted_answer.is_(True),
        )
        .count(),
    )

    profile = UserProfile(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        avatar_url=getattr(user, "profile_picture_url", None),
        bio=getattr(user, "bio", None),
        location=getattr(user, "location", None),
        website=getattr(user, "website", None),
        reputation_points=reputation["total_points"] if reputation else 0,
        created_at=user.created_at,
    )

    reputation_meta = UserReputationResponse(
        total_points=reputation["total_points"],
        level=reputation["level"],
        rank=reputation["rank"],
        next_level_points=reputation["next_level_points"],
        engagement_score=reputation["engagement_score"],
        badges=reputation["badges"],
    )

    return UserProfileResponse(
        user=profile, stats=stats, reputation_meta=reputation_meta
    )


@router.post("/users/{user_id}/follow")
def toggle_follow_user(
    user_id: str,
    current_user_id: dict = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Follow or unfollow a user"""
    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    # Check if already following
    stmt = user_following.select().where(
        and_(
            user_following.c.follower_id == current_user_id,
            user_following.c.following_id == user_id,
        )
    )
    existing = db.execute(stmt).first()

    if existing:
        # Unfollow
        stmt = user_following.delete().where(
            and_(
                user_following.c.follower_id == current_user_id,
                user_following.c.following_id == user_id,
            )
        )
        db.execute(stmt)
        db.commit()
        return {"following": False, "message": "Unfollowed successfully"}
    else:
        # Follow
        stmt = user_following.insert().values(
            follower_id=current_user_id, following_id=user_id
        )
        db.execute(stmt)
        db.commit()
        return {"following": True, "message": "Following successfully"}


@router.get("/following")
def get_following(
    current_user_id: dict = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """Get list of users current user is following"""
    stmt = (
        select(User)
        .join(user_following, User.id == user_following.c.following_id)
        .where(user_following.c.follower_id == current_user_id)
    )

    following = db.execute(stmt).scalars().all()
    return [
        {"id": u.id, "full_name": u.full_name, "avatar_url": u.avatar_url}
        for u in following
    ]


@router.get("/users/{user_id}/followers")
def get_user_followers(user_id: str, db: Session = Depends(get_db)):
    """Get user's followers"""
    stmt = (
        select(User)
        .join(user_following, User.id == user_following.c.follower_id)
        .where(user_following.c.following_id == user_id)
    )

    followers = db.execute(stmt).scalars().all()
    return [
        {"id": u.id, "full_name": u.full_name, "avatar_url": u.avatar_url}
        for u in followers
    ]
