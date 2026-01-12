from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DashboardStatsResponse(BaseModel):
    total_students: int = Field(..., description="Total number of students")
    total_subjects: int = Field(..., description="Total number of subjects")
    total_topics: int = Field(..., description="Total number of topics")
    total_questions: int = Field(..., description="Total number of questions")


class ChartSeriesData(BaseModel):
    name: str = Field(..., description="Series name")
    data: List[int] = Field(..., description="Data points")


class ChartData(BaseModel):
    categories: List[str] = Field(..., description="Chart categories (months)")
    series: List[ChartSeriesData] = Field(..., description="Chart series data")


class DashboardAnalyticsResponse(BaseModel):
    exams_by_month: ChartData = Field(..., description="Exams data by month")
    tests_by_month: ChartData = Field(..., description="Tests data by month")


class ActivityItem(BaseModel):
    type: str = Field(..., description="Activity type")
    timestamp: datetime = Field(..., description="Activity timestamp")
    user_name: str = Field(..., description="User name")
    description: str = Field(..., description="Activity description")
    score: Optional[float] = Field(None, description="Score if applicable")


class PerformanceOverview(BaseModel):
    average_score: float = Field(..., description="Average score across assessments")
    total_attempts: int = Field(..., description="Total assessment attempts")
    active_students: int = Field(..., description="Number of active students")
    completion_rate: float = Field(..., description="Assessment completion rate")
