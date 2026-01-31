"""
Enhanced Analytics Schemas - Updated for Topic Analytics and Study Plans
Developed By Samuel Kufre Willie - 31 January 2026
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from src.domains.report.enums import (
    ExportFormat,
    ReportType,
    MasteryLevel,
    RecommendationType,
    RecommendationPriority,
)


class OverviewMetrics(BaseModel):
    total_users: int
    total_students: int
    total_assessments: int
    total_questions: int
    active_subscriptions: int
    total_attempts: int
    completed_attempts: int
    completion_rate: float
    total_revenue: float


class AssessmentPerformanceMetrics(BaseModel):
    average_score: float
    total_completed: int
    total_passed: int
    pass_rate: float
    average_completion_time_minutes: float


class RevenueMetrics(BaseModel):
    total_revenue: float
    monthly_revenue: float
    subscription_revenue: float
    assessment_revenue: float
    wallet_topup: float = 0.0  # NEW
    total_transactions: int
    average_transaction_value: float


class EngagementMetrics(BaseModel):
    daily_active_users: int
    monthly_active_users: int
    forum_posts_this_week: int
    forum_replies_this_week: int
    average_session_minutes: float


class GamificationData(BaseModel):
    level: int
    total_points: int
    current_streak: int
    longest_streak: int


class TopicPerformance(BaseModel):
    """Topic-level performance data"""

    topic_id: str
    topic_name: str
    subject_name: str
    subject_id: str
    questions_attempted: int
    correct_answers: int
    success_rate: float
    mastery_score: float
    mastery_level: MasteryLevel


class TopicTrendDataPoint(BaseModel):
    """Topic performance over time"""

    date: str
    success_rate: float
    questions_attempted: int


class TopicTrendAnalysis(BaseModel):
    """Trend analysis for a specific topic"""

    trend_direction: str  # "improving", "declining", "insufficient_data"
    data_points: List[TopicTrendDataPoint]


class RecommendedTopic(BaseModel):
    """Topic recommendation for practice"""

    topic_id: str
    topic_name: str
    subject_name: str
    current_mastery: float
    mastery_level: MasteryLevel
    reason: str
    suggested_assessments: List[Dict[str, Any]]


class ActivityDetail(BaseModel):
    """Study activity detail"""

    type: str  # "video_lesson", "practice", "review", "assessment"
    duration: int  # minutes
    description: str


class DailySchedule(BaseModel):
    """Daily study schedule"""

    day: int
    focus: str
    activities: List[ActivityDetail]


class WeeklySchedule(BaseModel):
    """Weekly study schedule"""

    week: int
    theme: str
    days: List[DailySchedule]


class FocusArea(BaseModel):
    """Priority focus area in study plan"""

    topic: str
    subject: str
    current_level: MasteryLevel
    target_improvement: str
    daily_minutes: int
    priority: int


class Milestone(BaseModel):
    """Study plan milestone"""

    week: int
    target: str
    metric: str


class PersonalizedStudyPlan(BaseModel):
    """Complete personalized study plan"""

    duration_days: int
    daily_study_minutes: int
    focus_areas: List[FocusArea]
    weekly_schedule: List[WeeklySchedule]
    milestones: List[Milestone]


class RecommendationAction(BaseModel):
    """Action associated with recommendation"""

    type: str
    topic_id: Optional[str] = None
    subject_id: Optional[str] = None
    assessments: Optional[List[Dict[str, Any]]] = None


class PersonalizedRecommendation(BaseModel):
    """Enhanced recommendation with priority and action"""

    type: RecommendationType
    icon: str
    title: str
    description: str
    action: RecommendationAction
    priority: RecommendationPriority


class DataPoint(BaseModel):
    date: str
    count: int


class RevenueDataPoint(BaseModel):
    date: str
    revenue: float
    transactions: int


class ProgressDataPoint(BaseModel):
    date: str
    average_score: float
    attempts: int


class TrendData(BaseModel):
    user_growth: List[DataPoint]
    revenue: List[RevenueDataPoint]


class AssessmentSummary(BaseModel):
    assessment_id: str
    title: str
    category: str
    total_attempts: int
    average_score: float
    pass_rate: Optional[float] = None


class AssessmentsByCategory(BaseModel):
    category: str
    total_attempts: int
    average_score: float
    passed_count: int
    pass_rate: float


class AssessmentInfo(BaseModel):
    id: str
    title: str
    category: str
    total_questions: int
    total_points: int


class AttemptStatistics(BaseModel):
    total: int
    completed: int
    passed: int
    pass_rate: float


class ScoreStatistics(BaseModel):
    average: float
    minimum: float
    maximum: float
    standard_deviation: float


class TimeStatistics(BaseModel):
    average_minutes: float
    minimum_minutes: float
    maximum_minutes: float


class DetailedAssessmentReport(BaseModel):
    assessment: AssessmentInfo
    attempts: AttemptStatistics
    scores: ScoreStatistics
    time: TimeStatistics


class StudentPerformanceSummary(BaseModel):
    total_attempts: int
    completed_attempts: int
    average_score: float
    passed_count: int
    pass_rate: float
    best_score: float
    worst_score: float
    gamification: Optional[GamificationData] = None


class SubjectPerformance(BaseModel):
    subject_id: str
    subject_name: str
    total_attempts: int
    average_score: float
    pass_rate: float


class QuestionAnalysis(BaseModel):
    question_id: str
    question_preview: str
    rated_difficulty: str
    total_answers: int
    success_rate: float
    accuracy_assessment: str


class MissedQuestion(BaseModel):
    question_id: str
    question_preview: str
    difficulty: str
    subject: str
    total_answers: int
    success_rate: float


class SubscriptionBreakdown(BaseModel):
    type: str
    count: int


class SubscriptionAnalytics(BaseModel):
    breakdown: List[SubscriptionBreakdown]
    churn_rate: float
    monthly_recurring_revenue: float


class FinancialInsights(BaseModel):
    insights: List[str]


class StudentPerformanceResponse(BaseModel):
    performance_summary: StudentPerformanceSummary
    subject_breakdown: List[SubjectPerformance]
    topic_breakdown: List[TopicPerformance]
    progress_over_time: List[ProgressDataPoint]
    personalized_recommendations: List[PersonalizedRecommendation]  # ENHANCED
    study_plan: PersonalizedStudyPlan  # NEW
    generated_at: str


class TopicAnalyticsResponse(BaseModel):
    """NEW: Topic analytics response"""

    all_topics: List[TopicPerformance]
    weak_topics: List[TopicPerformance]
    recommended_for_practice: List[RecommendedTopic]
    generated_at: str


class TopicTrendResponse(BaseModel):
    """NEW: Topic trend analysis response"""

    topic_id: str
    trend_analysis: TopicTrendAnalysis
    generated_at: str


class StudyPlanResponse(BaseModel):
    """NEW: Study plan response"""

    study_plan: PersonalizedStudyPlan
    generated_at: str


class DashboardResponse(BaseModel):
    overview: OverviewMetrics
    assessment_performance: AssessmentPerformanceMetrics
    revenue: RevenueMetrics
    engagement: EngagementMetrics
    trends: TrendData
    assessments: Dict[str, List[AssessmentSummary]]
    generated_at: str


class AssessmentAnalyticsResponse(BaseModel):
    report: DetailedAssessmentReport
    generated_at: str


class QuestionQualityResponse(BaseModel):
    total_analyzed: int
    needs_difficulty_adjustment: int
    questions_needing_review: List[QuestionAnalysis]
    most_missed_questions: List[MissedQuestion]
    generated_at: str


class FinancialOverviewResponse(BaseModel):
    overview: RevenueMetrics
    subscriptions: SubscriptionAnalytics
    trend: List[RevenueDataPoint]
    insights: FinancialInsights
    generated_at: str


class ReportGenerationRequest(BaseModel):
    report_type: ReportType
    entity_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: ExportFormat = ExportFormat.JSON
    include_charts: bool = Field(
        default=False, description="Include chart data in report"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional filters"
    )


class PerformancePrediction(BaseModel):
    prediction: str
    current_average: float
    trend_confidence: str
    recommendation: str


class PeerComparison(BaseModel):
    student_performance: StudentPerformanceSummary
    peer_average: Dict[str, Any]
    percentile: int
    generated_at: str


# ==================== ACTIVITY FEED ====================


class ActivityItem(BaseModel):
    id: str
    type: str
    user_id: str
    description: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ActivityFeedResponse(BaseModel):
    activities: List[ActivityItem]
    total: int
    page: int = 1
    limit: int = 20
