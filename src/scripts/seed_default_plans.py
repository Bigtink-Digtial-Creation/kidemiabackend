"""
Script to seed default subscription plans into the database.
"""

from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from src.domains.payment.models.subscription_plan import SubscriptionPlanConfig
from src.domains.payment.enums import SubscriptionPlanType, SubscriptionType


def seed_default_plans(
    db: Session, admin_id: str = "f2115d36-7acd-4df5-8ba6-cb2d436af79b"
):
    """Seed the default subscription plans"""

    plans = [
        {
            "plan_code": "free",
            "plan_name": "Free Plan",
            "plan_type": SubscriptionPlanType.FREE,
            "subscription_type": SubscriptionType.INDIVIDUAL,
            "description": "Get started with basic features at no cost",
            "short_description": "Perfect for trying out Kidemia",
            "tagline": "Start Learning Free",
            "price_monthly": Decimal("0.00"),
            "price_quarterly": Decimal("0.00"),
            "price_yearly": Decimal("0.00"),
            "monthly_discount_percentage": 0,
            "yearly_discount_percentage": 0,
            "currency": "NGN",
            "max_members": None,
            "trial_days": 0,
            "features": {
                "basic_subjects": True,
                "limited_tests": True,
                "leaderboard_access": False,
            },
            "limits": {
                "tests_per_month": 5,
                "subjects": ["Mathematics", "English"],
            },
            "is_active": True,
            "is_featured": False,
            "is_popular": False,
            "display_order": 1,
            "is_visible": True,
            "show_for_individuals": True,
            "show_for_guardians": False,
            "show_for_institutions": False,
            "benefits_list": [
                "5 tests per month",
                "Basic subjects only",
                "No leaderboard access",
            ],
        },
        {
            "plan_code": "student",
            "plan_name": "Student Plan",
            "plan_type": SubscriptionPlanType.STUDENT,
            "subscription_type": SubscriptionType.INDIVIDUAL,
            "description": "Comprehensive learning plan for individual students",
            "short_description": "Perfect for focused learners",
            "tagline": "Ace Your Exams",
            "price_monthly": Decimal("500.00"),
            "price_quarterly": Decimal("1400.00"),
            "price_yearly": Decimal("2100.00"),
            "monthly_discount_percentage": 0,
            "quarterly_discount_percentage": 7,
            "yearly_discount_percentage": 20,
            "currency": "NGN",
            "max_members": None,
            "trial_days": 7,
            "features": {
                "unlimited_subjects": True,
                "limited_tests": True,
                "leaderboard_access": True,
                "one_time_leaderboard": True,
                "progress_tracking": True,
            },
            "limits": {
                "tests_per_month": 10,
            },
            "is_active": True,
            "is_featured": False,
            "is_popular": False,
            "display_order": 2,
            "is_visible": True,
            "show_for_individuals": True,
            "show_for_guardians": False,
            "show_for_institutions": False,
            "benefits_list": [
                "Unlimited Subjects",
                "10 Tests per Month",
                "One-time leaderboard access",
                "Progress tracking",
                "7-day free trial",
            ],
        },
        {
            "plan_code": "sibling",
            "plan_name": "Sibling Plan",
            "plan_type": SubscriptionPlanType.SIBLING,
            "subscription_type": SubscriptionType.FAMILY,
            "description": "Perfect for families with 2-3 children learning together",
            "short_description": "Save on multiple children",
            "tagline": "Learn Together, Save Together",
            "price_monthly": Decimal("500.00"),
            "price_quarterly": Decimal("1400.00"),
            "price_yearly": Decimal("5000.00"),
            "monthly_discount_percentage": 0,
            "quarterly_discount_percentage": 7,
            "yearly_discount_percentage": 17,
            "currency": "NGN",
            "max_members": 3,
            "trial_days": 14,
            "features": {
                "unlimited_subjects": True,
                "unlimited_tests": True,
                "leaderboard_access": True,
                "one_time_leaderboard": True,
                "multiple_wards": True,
                "progress_tracking": True,
                "parent_dashboard": True,
            },
            "limits": {},
            "is_active": True,
            "is_featured": False,
            "is_popular": False,
            "display_order": 3,
            "is_visible": True,
            "show_for_individuals": False,
            "show_for_guardians": True,
            "show_for_institutions": False,
            "benefits_list": [
                "Unlimited Subjects",
                "Unlimited Tests per Month",
                "One-time leaderboard access",
                "Up to 3 children",
                "Parent dashboard",
                "14-day free trial",
            ],
        },
        {
            "plan_code": "family",
            "plan_name": "Family Plan",
            "plan_type": SubscriptionPlanType.FAMILY,
            "subscription_type": SubscriptionType.FAMILY,
            "description": "Complete learning solution for the entire family",
            "short_description": "Best value for families",
            "tagline": "Unlimited Learning for Everyone",
            "price_monthly": Decimal("1000.00"),
            "price_quarterly": Decimal("2800.00"),
            "price_yearly": Decimal("2100.00"),
            "monthly_discount_percentage": 0,
            "quarterly_discount_percentage": 7,
            "yearly_discount_percentage": 20,
            "currency": "NGN",
            "max_members": 5,
            "trial_days": 14,
            "features": {
                "unlimited_subjects": True,
                "unlimited_tests": True,
                "unlimited_leaderboard": True,
                "multiple_wards": True,
                "progress_tracking": True,
                "parent_dashboard": True,
                "priority_support": True,
                "ai_recommendations": True,
            },
            "limits": {},
            "is_active": True,
            "is_featured": True,
            "is_popular": True,
            "display_order": 4,
            "is_visible": True,
            "show_for_individuals": False,
            "show_for_guardians": True,
            "show_for_institutions": False,
            "benefits_list": [
                "Unlimited Subjects",
                "Unlimited Tests per Month",
                "Unlimited leaderboard access",
                "Up to 5 children",
                "Parent dashboard",
                "Priority support",
                "AI-powered recommendations",
                "14-day free trial",
            ],
        },
        {
            "plan_code": "institution",
            "plan_name": "Institution Plan",
            "plan_type": SubscriptionPlanType.INSTITUTION,
            "subscription_type": SubscriptionType.INSTITUTION,
            "description": "Comprehensive solution for schools and educational institutions",
            "short_description": "Built for schools",
            "tagline": "Empower Your Institution",
            "price_monthly": Decimal("10000.00"),
            "price_quarterly": Decimal("28000.00"),
            "price_yearly": Decimal("100000.00"),
            "monthly_discount_percentage": 0,
            "quarterly_discount_percentage": 7,
            "yearly_discount_percentage": 17,
            "currency": "NGN",
            "max_members": 100,
            "trial_days": 30,
            "features": {
                "custom_exams": True,
                "student_management": True,
                "bulk_enrollment": True,
                "analytics_dashboard": True,
                "unlimited_everything": True,
                "dedicated_support": True,
                "custom_branding": True,
                "api_access": True,
                "admin_controls": True,
            },
            "limits": {},
            "is_active": True,
            "is_featured": True,
            "is_popular": False,
            "display_order": 5,
            "is_visible": True,
            "show_for_individuals": False,
            "show_for_guardians": False,
            "show_for_institutions": True,
            "benefits_list": [
                "Custom exam creation",
                "Student management system",
                "Bulk enrollment",
                "Advanced analytics dashboard",
                "Up to 100 students (customizable)",
                "Dedicated support team",
                "Custom branding options",
                "API access",
                "30-day free trial",
            ],
        },
    ]

    created_plans = []
    for plan_data in plans:
        # Check if plan already exists
        existing = (
            db.query(SubscriptionPlanConfig)
            .filter(SubscriptionPlanConfig.plan_code == plan_data["plan_code"])
            .first()
        )

        if not existing:
            plan_data["created_by"] = admin_id
            plan_data["created_at"] = datetime.now(timezone.utc)
            plan_data["updated_at"] = datetime.now(timezone.utc)

            plan = SubscriptionPlanConfig(**plan_data)
            db.add(plan)
            created_plans.append(plan)
            print(f"✅ Created plan: {plan_data['plan_name']}")
        else:
            print(f"⏭️  Plan already exists: {plan_data['plan_name']}")

    db.commit()
    print(f"\n✨ Successfully seeded {len(created_plans)} plans!")

    return created_plans


def seed_sample_features(
    db: Session, admin_id: str = "f2115d36-7acd-4df5-8ba6-cb2d436af79b"
):
    """Seed sample features"""
    from src.domains.payment.models.subscription_plan import SubscriptionPlanFeature

    features = [
        {
            "feature_code": "unlimited_subjects",
            "feature_name": "Unlimited Subjects",
            "description": "Access to all available subjects",
            "icon": "📚",
            "category": "core",
        },
        {
            "feature_code": "unlimited_tests",
            "feature_name": "Unlimited Tests",
            "description": "Take unlimited practice tests",
            "icon": "✍️",
            "category": "core",
        },
        {
            "feature_code": "leaderboard_access",
            "feature_name": "Leaderboard Access",
            "description": "Compete with other students",
            "icon": "🏆",
            "category": "engagement",
        },
        {
            "feature_code": "progress_tracking",
            "feature_name": "Progress Tracking",
            "description": "Track your learning progress over time",
            "icon": "📊",
            "category": "analytics",
        },
        {
            "feature_code": "ai_recommendations",
            "feature_name": "AI Recommendations",
            "description": "Get personalized study recommendations",
            "icon": "🤖",
            "category": "premium",
        },
        {
            "feature_code": "parent_dashboard",
            "feature_name": "Parent Dashboard",
            "description": "Monitor children's progress",
            "icon": "👨‍👩‍👧‍👦",
            "category": "family",
        },
    ]

    created_features = []
    for feature_data in features:
        existing = (
            db.query(SubscriptionPlanFeature)
            .filter(
                SubscriptionPlanFeature.feature_code == feature_data["feature_code"]
            )
            .first()
        )

        if not existing:
            feature_data["created_by"] = admin_id
            feature_data["is_active"] = True
            feature = SubscriptionPlanFeature(**feature_data)
            db.add(feature)
            created_features.append(feature)
            print(f"✅ Created feature: {feature_data['feature_name']}")

    db.commit()
    print(f"\n✨ Successfully seeded {len(created_features)} features!")

    return created_features


# Run this script
if __name__ == "__main__":
    from src.config.database import SessionLocal

    db = SessionLocal()
    try:
        # print("🌱 Seeding default subscription plans...\n")
        # seed_default_plans(db)

        print("\n🌱 Seeding sample features...\n")
        seed_sample_features(db)

        print("\n✅ All done! Your subscription plans are ready.")
    except Exception as e:
        print(f"\n❌ Error seeding plans: {e}")
        db.rollback()
    finally:
        db.close()


"""
 {
"plan_code": "free",
"plan_name": "Free Plan",
"plan_type": "free",
"subscription_type": "individual",
"description": "Get started with basic features at no cost",
"short_description": "Perfect for trying out Kidemia",
"tagline": "Start Learning Free",
"price_monthly": 0.00,
"price_quarterly": 0.00,
"price_yearly": 0.00,
"monthly_discount_percentage": 0,
"yearly_discount_percentage": 0,
"currency": "NGN",
"max_members": null,
"trial_days": 0,
"features": {
    "basic_subjects": true,
    "limited_tests": true,
    "leaderboard_access": false
},
"limits": {
    "tests_per_month": 5,
    "subjects": ["Mathematics", "English"]
},
"is_active": true,
"is_featured": false,
"is_popular": false,
"display_order": 1,
"is_visible": true,
"show_for_individuals": true,
"show_for_guardians": false,
"show_for_institutions": false,
"benefits_list": [
    "5 tests per month",
    "Basic subjects only",
    "No leaderboard access"
]
}
"""
