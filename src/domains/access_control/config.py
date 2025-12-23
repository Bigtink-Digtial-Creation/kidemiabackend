"""
Centralized access control configuration.
this enables me to define all resources and their access requirements in one place.
"""

from decimal import Decimal
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResourceAccess:
    """Configuration for a resource's access requirements"""

    name: str
    description: str

    # Subscription requirements
    required_feature: Optional[str] = None
    activity_type: Optional[str] = None

    # Wallet alternative
    wallet_cost: Optional[Decimal] = None

    # Free tier limits
    free_tier_limit: Optional[int] = None
    free_tier_period: str = "monthly"  # "daily", "weekly", "monthly"


class AccessConfig:
    """
    Central configuration for all resource access requirements.
    This makes it easy to change pricing and features across the entire app.
    """

    # Tests
    PRACTICE_TEST = ResourceAccess(
        name="practice_test",
        description="Take a practice test",
        required_feature="unlimited_tests",
        activity_type="test",
        wallet_cost=Decimal("50.00"),
        free_tier_limit=5,
        free_tier_period="monthly",
    )

    MOCK_EXAM = ResourceAccess(
        name="mock_exam",
        description="Take a full mock exam",
        required_feature="unlimited_tests",
        activity_type="exam",
        wallet_cost=Decimal("200.00"),
        free_tier_limit=2,
        free_tier_period="monthly",
    )

    # Leaderboard
    LEADERBOARD_VIEW = ResourceAccess(
        name="leaderboard",
        description="View leaderboard",
        required_feature="leaderboard_access",
        activity_type="leaderboard",
        wallet_cost=Decimal("20.00"),
    )

    LEADERBOARD_UNLIMITED = ResourceAccess(
        name="leaderboard_unlimited",
        description="Unlimited leaderboard access",
        required_feature="unlimited_leaderboard",
        activity_type="leaderboard",
        wallet_cost=None,  # No wallet alternative
    )

    # Content access
    PAST_QUESTIONS = ResourceAccess(
        name="past_questions",
        description="Access past questions",
        required_feature="past_questions_access",
        wallet_cost=Decimal("30.00"),
    )

    VIDEO_TUTORIAL = ResourceAccess(
        name="video_tutorial",
        description="Watch video tutorials",
        required_feature="video_tutorials",
        wallet_cost=Decimal("100.00"),
    )

    # Premium features
    AI_TUTOR = ResourceAccess(
        name="ai_tutor",
        description="Get AI tutoring assistance",
        required_feature="ai_tutor",
        wallet_cost=Decimal("500.00"),
    )

    DETAILED_ANALYTICS = ResourceAccess(
        name="detailed_analytics",
        description="View detailed performance analytics",
        required_feature="detailed_analytics",
        wallet_cost=Decimal("150.00"),
    )

    PRIORITY_SUPPORT = ResourceAccess(
        name="priority_support",
        description="Access priority customer support",
        required_feature="priority_support",
        wallet_cost=None,  # Subscription only
    )

    # Institution features
    CUSTOM_EXAMS = ResourceAccess(
        name="custom_exams",
        description="Create custom exams",
        required_feature="custom_exams",
        wallet_cost=None,  # Subscription only
    )

    BULK_ENROLLMENT = ResourceAccess(
        name="bulk_enrollment",
        description="Enroll students in bulk",
        required_feature="bulk_enrollment",
        wallet_cost=None,  # Subscription only
    )

    ANALYTICS_DASHBOARD = ResourceAccess(
        name="analytics_dashboard",
        description="Access analytics dashboard",
        required_feature="analytics_dashboard",
        wallet_cost=None,  # Subscription only
    )

    @classmethod
    def get_all_resources(cls) -> dict:
        """Get all resource configurations"""
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if isinstance(getattr(cls, name), ResourceAccess)
        }

    @classmethod
    def get_resource(cls, name: str) -> Optional[ResourceAccess]:
        """Get resource configuration by name"""
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, ResourceAccess) and (
                attr.name == name or attr_name == name
            ):
                return attr
        return None


class PricingTiers:
    """Common pricing for different resource types"""

    # Tests
    QUICK_TEST = Decimal("20.00")
    PRACTICE_TEST = Decimal("50.00")
    FULL_EXAM = Decimal("200.00")

    # Content
    SINGLE_VIDEO = Decimal("50.00")
    COURSE_MODULE = Decimal("300.00")
    FULL_COURSE = Decimal("1500.00")

    # Features
    AI_ASSISTANCE = Decimal("500.00")
    ANALYTICS_REPORT = Decimal("150.00")
    CUSTOM_FEATURE = Decimal("1000.00")


# Feature categories for organizing UI
class FeatureCategories:
    """Organize features into logical categories"""

    CORE = {
        "unlimited_subjects": "Access to all subjects",
        "unlimited_tests": "Unlimited practice tests",
        "progress_tracking": "Track your learning progress",
    }

    ENGAGEMENT = {
        "leaderboard_access": "Compete on leaderboards",
        "unlimited_leaderboard": "Unlimited leaderboard access",
        "achievements": "Earn achievements and badges",
    }

    PREMIUM = {
        "ai_tutor": "AI-powered tutoring",
        "video_tutorials": "Video learning materials",
        "past_questions_access": "Access to past questions",
        "detailed_analytics": "Advanced performance analytics",
    }

    FAMILY = {
        "multiple_wards": "Add multiple children",
        "parent_dashboard": "Monitor children's progress",
        "family_reports": "Family performance reports",
    }

    INSTITUTION = {
        "custom_exams": "Create custom exams",
        "bulk_enrollment": "Bulk student enrollment",
        "student_management": "Student management system",
        "analytics_dashboard": "Institution analytics",
    }
