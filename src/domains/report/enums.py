from enum import Enum


class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ReportType(str, Enum):
    PLATFORM_OVERVIEW = "platform_overview"
    STUDENT_PERFORMANCE = "student_performance"
    ASSESSMENT_ANALYSIS = "assessment_analysis"
    FINANCIAL = "financial"
    QUESTION_QUALITY = "question_quality"


class MasteryLevel(str, Enum):
    MASTERED = "MASTERED"
    GOOD = "GOOD"
    DEVELOPING = "DEVELOPING"
    NEEDS_WORK = "NEEDS_WORK"


class RecommendationType(str, Enum):
    TOPIC_FOCUS = "topic_focus"
    TOPIC_PRACTICE = "topic_practice"
    STREAK_MOTIVATION = "streak_motivation"
    STREAK_START = "streak_start"
    LEVEL_UP = "level_up"
    FOUNDATION = "foundation"
    STUDY_PLAN = "study_plan"


class RecommendationPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
