from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.core.security import get_current_user
from typing import Optional
from src.domains.report.services.dashboard_service import DashboardService
from src.domains.report.schemas.dashboard import (
    DashboardStatsResponse,
    DashboardAnalyticsResponse,
    ActivityItem,
    PerformanceOverview,
)

router = APIRouter(prefix="/admin/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get dashboard statistics

    Returns counts for students, subjects, topics, and questions.
    Optionally filter by category.
    """
    stats = DashboardService.get_dashboard_stats(db, category_id)
    return stats


@router.get("/analytics", response_model=DashboardAnalyticsResponse)
def get_dashboard_analytics(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    months: int = Query(6, ge=1, le=12, description="Number of months to include"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get dashboard analytics data for charts

    Returns data for exams and tests completion over time.
    """
    analytics = DashboardService.get_dashboard_analytics(db, category_id, months)
    return analytics


@router.get("/activities", response_model=list[ActivityItem])
def get_recent_activities(
    limit: int = Query(10, ge=1, le=50, description="Number of activities to return"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get recent platform activities

    Returns a list of recent user activities on the platform.
    """
    activities = DashboardService.get_recent_activities(db, limit)
    return activities


@router.get("/performance", response_model=PerformanceOverview)
def get_performance_overview(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get overall performance metrics

    Returns average scores, completion rates, and active student counts.
    """
    performance = DashboardService.get_performance_overview(db, category_id)
    return performance


# Register router in main.py
# from app.api.endpoints import dashboard
