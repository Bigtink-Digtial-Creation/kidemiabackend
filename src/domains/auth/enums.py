from enum import Enum


class UserType(str, Enum):
    """Types of users in the system"""

    STUDENT = "student"
    GUARDIAN = "guardian"
    INSTITUTION_ADMIN = "institution_admin"
    PLATFORM_ADMIN = "platform_admin"


class RoleType(str, Enum):
    """Categories of roles"""

    SYSTEM = "system"  # System-defined roles (cannot be deleted)
    INSTITUTION = "institution"  # Institution-specific roles
    CUSTOM = "custom"  # Custom user-defined roles


class AdminType(str, Enum):
    """Types of platform administrators"""

    SUPER_ADMIN = "super_admin"  # Full system access
    CONTENT_ADMIN = "content_admin"  # Manages content (questions, subjects, etc.)
    SUPPORT_ADMIN = "support_admin"  # Handles support tickets
    FINANCE_ADMIN = "finance_admin"  # Manages payments and subscriptions
    ANALYTICS_ADMIN = "analytics_admin"  # Views analytics and reports


class LoginProvider(str, Enum):
    """Authentication providers"""

    EMAIL = "email"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    FACEBOOK = "facebook"
