from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from src.shared.schemas.base import (
    BaseSchema,
)

from src.domains.assessment.schemas.attempt import AttemptResultResponse


class AssessmentStatistics(BaseSchema):
    """Detailed assessment statistics"""

    assessment_id: UUID

    # Attempt stats
    total_attempts: int
    total_completions: int
    completion_rate: Decimal

    # Pass/Fail stats
    total_passes: int
    total_fails: int
    pass_rate: Decimal

    # Score distribution
    average_score: Decimal
    median_score: Decimal
    highest_score: Decimal
    lowest_score: Decimal
    score_distribution: Dict[str, int]  # Grade ranges

    # Time stats
    average_completion_time: int  # seconds
    median_completion_time: int

    # Question analysis
    most_difficult_questions: List[Dict[str, Any]]
    easiest_questions: List[Dict[str, Any]]


class UserPerformanceStats(BaseSchema):
    """User performance statistics"""

    user_id: UUID

    # Overall
    total_assessments_taken: int
    total_assessments_passed: int
    overall_pass_rate: Decimal
    average_score: Decimal

    # By type
    tests_taken: int
    exams_taken: int

    # By category
    performance_by_category: Dict[str, Dict[str, Any]]

    # By subject
    performance_by_subject: Dict[str, Dict[str, Any]]

    # Streaks
    current_streak: int
    longest_streak: int

    # Recent activity
    recent_attempts: List[AttemptResultResponse]


class LeaderboardEntry(BaseSchema):
    """Leaderboard entry"""

    rank: int
    user_id: UUID
    user_name: str
    score: Decimal
    percentage: Decimal
    time_spent_seconds: int
    submitted_at: str


class LeaderboardResponse(BaseSchema):
    """Leaderboard response"""

    assessment_id: UUID
    assessment_title: str
    entries: List[LeaderboardEntry]
    total_participants: int
    user_rank: Optional[int] = None
