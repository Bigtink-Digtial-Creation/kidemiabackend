from enum import Enum


class AppEvent(str, Enum):
    ASSESSMENT_COMPLETED = "assessment.completed"
