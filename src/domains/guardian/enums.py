import enum


class CategoryChangeStatus(str, enum.Enum):
    """Status of category change request"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AssignmentStatus(str, enum.Enum):
    """Status of assessment assignment"""

    ASSIGNED = "assigned"
    STARTED = "started"
    COMPLETED = "completed"
    OVERDUE = "overdue"
