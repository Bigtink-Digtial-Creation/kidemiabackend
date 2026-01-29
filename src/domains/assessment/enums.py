from enum import Enum


class SeverityLevel(str, Enum):
    """Enum for violation severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    """Enum for common violation types"""

    MULTIPLE_FACES = "multiple_faces"
    NO_FACE = "no_face"
    PHONE_DETECTED = "phone_detected"
    TAB_SWITCH = "tab_switch"
    WINDOW_BLUR = "window_blur"
    COPY_PASTE = "copy_paste"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNKNOWN = "unknown"


class AssessmentType(str, Enum):
    """Type of assessment"""

    TEST = "test"
    EXAM = "exam"


class AssessmentCategory(str, Enum):
    """Assessment categories - Nigerian examination systems"""

    # Primary Level
    COMMON_ENTRANCE = "common_entrance"
    PRIMARY_SCHOOL = "primary_school"

    # Junior Secondary
    JUNIOR_WAEC = "junior_waec"
    BECE = "bece"
    SENIOR_WAEC = "senior_waec"
    NECO = "neco"
    NABTEB = "nabteb"
    GCE = "gce"
    JAMB = "jamb"
    POST_UTME = "post_utme"
    PROFESSIONAL = "professional"
    SCHOLARSHIP = "scholarship"
    APTITUDE = "aptitude"
    MOCK = "mock"
    CUSTOM = "custom"
    GENERAL = "general"


class AttemptStatus(str, Enum):
    """Status of an assessment attempt"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    SUBMITTED = "submitted"
    GRADED = "graded"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class GradingStatus(str, Enum):
    """Grading status"""

    PENDING = "pending"
    AUTO_GRADING = "auto_grading"
    MANUAL_GRADING = "manual_grading"
    COMPLETED = "completed"
    FAILED = "failed"


class AssessmentStatus(str, Enum):
    """Assessment publication status"""

    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"


class QuestionSelectionMode(str, Enum):
    """How questions are selected for assessment"""

    MANUAL = "manual"
    RANDOM = "random"
    ADAPTIVE = "adaptive"


class ResultDisplayMode(str, Enum):
    """When to show results"""

    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    NEVER = "never"
