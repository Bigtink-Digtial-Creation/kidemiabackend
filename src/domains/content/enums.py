from enum import Enum


class QuestionType(str, Enum):
    """Types of questions"""

    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_IN_BLANK = "fill_in_blank"
    ESSAY = "essay"
    MATCHING = "matching"
    ORDERING = "ordering"


class DifficultyLevel(str, Enum):
    """Question difficulty levels"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class QuestionStatus(str, Enum):
    """Question status"""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
