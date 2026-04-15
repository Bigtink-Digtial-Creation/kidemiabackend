from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class AchievementType(str):
    ASSESSMENTS_COMPLETED = "assessments_completed"
    QUESTIONS_ANSWERED = "questions_answered"
    CORRECT_ANSWERS = "correct_answers"
    STREAK_DAYS = "streak_days"
    POINTS_EARNED = "points_earned"
    PERFECT_SCORES = "perfect_scores"
    CATEGORY_MASTERY = "category_mastery"


class BadgeRarity(str):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class LeaderboardType(str):
    GLOBAL = "global"
    CATEGORY = "category"
    INSTITUTION = "institution"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class GamificationProfileBase(BaseModel):
    total_points: int = 0
    current_level: int = 1
    experience_points: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    rank_title: str = "Beginner"


class GamificationProfileCreate(BaseModel):
    student_id: UUID


class GamificationProfileUpdate(BaseModel):
    total_points: Optional[int] = None
    current_level: Optional[int] = None
    experience_points: Optional[int] = None
    current_streak: Optional[int] = None
    longest_streak: Optional[int] = None
    rank_title: Optional[str] = None
    leaderboard_position: Optional[int] = None


class GamificationProfileResponse(GamificationProfileBase):
    id: UUID
    student_id: UUID
    last_activity_date: Optional[datetime] = None
    total_assessments_completed: int = 0
    total_questions_answered: int = 0
    correct_answers: int = 0
    leaderboard_position: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BadgeBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color_code: Optional[str] = None
    rarity: str = BadgeRarity.COMMON


class BadgeCreate(BadgeBase):
    criteria: dict  # JSON criteria for earning
    points_required: Optional[int] = None
    is_secret: bool = False


class BadgeUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color_code: Optional[str] = None
    is_active: Optional[bool] = None
    criteria: Optional[dict] = None


class BadgeResponse(BadgeBase):
    id: UUID
    is_active: bool
    is_secret: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StudentBadgeResponse(BaseModel):
    id: UUID
    badge: BadgeResponse
    earned_at: datetime
    is_displayed: bool

    class Config:
        from_attributes = True


class AchievementBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color_code: Optional[str] = None
    achievement_type: str
    target_value: int
    points_reward: int = 0


class AchievementCreate(AchievementBase):
    pass


class AchievementUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: Optional[bool] = None
    points_reward: Optional[int] = None


class AchievementResponse(AchievementBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StudentAchievementResponse(BaseModel):
    id: UUID
    achievement: AchievementResponse
    current_value: int
    is_completed: bool
    completed_at: Optional[datetime] = None
    progress_percentage: float = Field(default=0.0)

    class Config:
        from_attributes = True


class LeaderboardEntryResponse(BaseModel):
    rank: int
    student_id: UUID
    student_name: str
    student_avatar: Optional[str] = None
    points: int
    level: int
    streak_days: int
    badges: List[BadgeResponse] = []
    trend: Optional[str] = None  # "up", "down", "same"

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    leaderboard_type: str
    period: Optional[str] = None
    entries: List[LeaderboardEntryResponse]
    total_participants: int
    current_user_rank: Optional[int] = None
    updated_at: datetime


class AssessmentCompletedEvent(BaseModel):
    student_id: UUID
    assessment_id: UUID
    category_id: Optional[UUID] = None
    score: int
    total_questions: int
    time_taken_seconds: int
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class GamificationResult(BaseModel):
    points_earned: int
    total_points: int
    level_up: bool = False
    new_level: Optional[int] = None
    new_rank_title: Optional[str] = None
    current_streak: int
    badges_earned: List[BadgeResponse] = []
    achievements_completed: List[AchievementResponse] = []
    achievements_progressed: List[StudentAchievementResponse] = []


class AssessmentLeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    student_name: str
    student_avatar: Optional[str] = None
    score: float
    points_earned: float
    attempt_number: int
    submitted_at: Optional[str] = None
    is_current_user: bool = False
    percentile: Optional[float] = None

    model_config = {"from_attributes": True}


class AssessmentLeaderboardResponse(BaseModel):
    assessment_id: UUID
    assessment_title: Optional[str] = None
    entries: List[AssessmentLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None
    updated_at: str
