from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from src.config.database import get_db
from src.core.security import get_current_user_id
from src.domains.forum.feed import ForumFeedService
from src.domains.forum.schemas.forum import PostResponse


feed_router = APIRouter(prefix="/feed", tags=["Forum Feed"])


@feed_router.get("/personalized", response_model=dict)
def get_personalized_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get personalized feed based on user's interests and activity

    This feed is algorithmically generated based on:
    - Posts from users you follow
    - Posts in your subjects
    - Posts matching your interests
    - Trending content in your areas
    - Recent activity

    **Requires authentication**
    """
    feed_service = ForumFeedService(db)
    return feed_service.get_personalized_feed(
        user_id=user_id, page=page, page_size=page_size
    )


@feed_router.get("/discover", response_model=dict)
def get_discover_feed(
    feed_type: str = Query(
        "all", pattern="^(all|trending|unanswered|popular|following|subjects)$"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get discovery feed with various filter options

    **Feed Types:**
    - **all**: All recent posts (default)
    - **trending**: Trending posts in the last 7 days
    - **unanswered**: Unanswered questions only
    - **popular**: Most popular posts in the last 30 days
    - **following**: Posts from users you follow (requires auth)
    - **subjects**: Posts in your enrolled subjects (requires auth)

    **Public feed types** (all, trending, unanswered, popular) don't require authentication.
    **Personal feed types** (following, subjects) require authentication.
    """
    feed_service = ForumFeedService(db)
    user_id = user_id if user_id else None

    return feed_service.get_discover_feed(
        user_id=user_id, page=page, page_size=page_size, feed_type=feed_type
    )


@feed_router.get("/subject/{subject_id}", response_model=dict)
def get_subject_feed(
    subject_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get all posts for a specific subject

    This shows all posts tagged with or categorized under the given subject.
    Posts are sorted by most recent activity.

    **Use this for:** Subject-specific discussion pages
    """
    feed_service = ForumFeedService(db)
    user_id = user_id if user_id else None

    return feed_service.get_subject_feed(
        subject_id=subject_id, user_id=user_id, page=page, page_size=page_size
    )


@feed_router.get("/tag/{tag_id}", response_model=dict)
def get_tag_feed(
    tag_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get all posts with a specific tag

    This shows all posts tagged with the given tag.
    Posts are sorted by most recent activity.

    **Use this for:** Tag-specific browsing, topic exploration
    """
    feed_service = ForumFeedService(db)
    user_id = user_id if user_id else None

    return feed_service.get_tag_feed(
        tag_id=tag_id, user_id=user_id, page=page, page_size=page_size
    )


@feed_router.get("/user/{user_id}", response_model=dict)
def get_user_activity_feed(
    user_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get a user's posts and activity

    This shows all posts created by a specific user.
    Posts are sorted by creation date (newest first).

    **Use this for:** User profile pages, viewing someone's contributions
    """
    feed_service = ForumFeedService(db)
    current_user_id = current_user_id if current_user_id else None

    return feed_service.get_user_activity_feed(
        target_user_id=user_id,
        current_user_id=current_user_id,
        page=page,
        page_size=page_size,
    )


@feed_router.get("/recommended", response_model=List[PostResponse])
def get_recommended_posts(
    limit: int = Query(10, ge=1, le=20),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get recommended posts based on your interests

    Uses collaborative filtering to recommend posts:
    - Finds users with similar interaction patterns
    - Recommends posts those users interacted with
    - Falls back to trending posts for new users

    **Use this for:**
    - "Recommended for you" section
    - Sidebar suggestions
    - Homepage widgets

    **Requires authentication**
    """
    feed_service = ForumFeedService(db)
    return feed_service.get_recommended_posts(user_id=user_id, limit=limit)


@feed_router.get("/questions-for-you", response_model=dict)
def get_questions_for_you(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get unanswered questions that match your expertise

    This feed shows questions where you could help:
    - Questions in subjects you've answered before
    - Questions with tags you're familiar with
    - Recent questions with no or few replies

    **Use this for:**
    - Encouraging users to help others
    - Gamification ("Help a student!")
    - Building reputation through expertise

    **Requires authentication**
    """
    feed_service = ForumFeedService(db)
    return feed_service.get_questions_for_you(
        user_id=user_id, page=page, page_size=page_size
    )


@feed_router.get("/home", response_model=dict)
def get_home_feed(
    current_user_id: Optional[UUID] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive home feed with multiple sections

    Returns a curated home feed containing:
    - Personalized posts (if authenticated)
    - Trending posts
    - Unanswered questions
    - Recommended posts (if authenticated)

    **Use this for:** Main forum homepage
    """
    feed_service = ForumFeedService(db)

    response = {"personalized": [], "trending": [], "unanswered": [], "recommended": []}

    # Get trending posts (everyone sees these)
    trending_feed = feed_service.get_discover_feed(
        user_id=None, page=1, page_size=5, feed_type="trending"
    )
    response["trending"] = trending_feed["posts"]

    # Get unanswered questions (everyone sees these)
    unanswered_feed = feed_service.get_discover_feed(
        user_id=None, page=1, page_size=5, feed_type="unanswered"
    )
    response["unanswered"] = unanswered_feed["posts"]

    # If user is authenticated, add personalized content
    if current_user_id:
        user_id = current_user_id

        # Get personalized feed
        personalized_feed = feed_service.get_personalized_feed(
            user_id=user_id, page=1, page_size=10
        )
        response["personalized"] = personalized_feed["posts"]

        # Get recommended posts
        recommended = feed_service.get_recommended_posts(user_id=user_id, limit=5)
        response["recommended"] = recommended

    return response


# Additional Helper Endpoints


@feed_router.get("/latest-activity", response_model=dict)
def get_latest_activity(
    limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)
):
    """
    Get the latest activity across the entire forum

    Shows the most recent posts and replies across all categories.
    Useful for a global activity feed or "What's happening now" section.
    """
    feed_service = ForumFeedService(db)
    return feed_service.get_discover_feed(
        user_id=None, page=1, page_size=limit, feed_type="all"
    )


@feed_router.get("/my-feed", response_model=dict)
def get_my_complete_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get your complete personalized feed

    This is the main feed for authenticated users, combining:
    - Personalized recommendations
    - Posts from followed users
    - Subject-specific content
    - Trending content

    **Requires authentication**
    **Use this for:** Main feed page after login
    """
    feed_service = ForumFeedService(db)
    return feed_service.get_personalized_feed(
        user_id=user_id, page=page, page_size=page_size
    )


# Export the router
__all__ = ["feed_router"]
