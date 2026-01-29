from fastapi import APIRouter

# Import domain routers
from src.domains.auth.api.auth import router as auth_router
from src.domains.auth.api.users import router as users_router
from src.domains.auth.api.roles import router as role_router
from src.domains.auth.api.permissions import router as permission_router


# from src.domains.auth.api.users import router as users_router
from src.domains.content.api.subjects import router as subjects_router
from src.domains.content.api.topics import router as topics_router
from src.domains.content.api.questions import router as questions_router
from src.domains.content.api.tags import router as tags_router

from src.domains.assessment.api import assessment_router
from src.domains.payment.api import payment_router

from src.domains.gamification.api import gamification_router
from src.shared.storage.routes import router as storage_router
# from src.domains.assessment.api.tests import router as tests_router


from src.domains.forum.api.feed_routes import feed_router
from src.domains.forum.api.post_routes import router as post_router
from src.domains.payment.api.paytack import router as webhook_router
from src.domains.report.api.dashboard import router as dashboard_router
from src.domains.settings.api.platform_settings import router as setting_router
from src.domains.guardian.api.guardians import router as guardian_router
from src.domains.guardian.api.ward import router as ward_router


api_router = APIRouter()

# Include all domain routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(guardian_router)
api_router.include_router(ward_router)
api_router.include_router(role_router, prefix="/roles", tags=["Roles"])
api_router.include_router(
    permission_router, prefix="/permissions", tags=["Permissions"]
)


api_router.include_router(subjects_router, prefix="/subjects", tags=["Subjects"])
api_router.include_router(topics_router, prefix="/topics", tags=["Subject Topics"])
api_router.include_router(
    questions_router, prefix="/questions", tags=["Topic Questions"]
)
api_router.include_router(tags_router, prefix="/tags", tags=["Tags"])

api_router.include_router(assessment_router)

api_router.include_router(post_router)
api_router.include_router(feed_router)
api_router.include_router(gamification_router)

api_router.include_router(payment_router)
api_router.include_router(dashboard_router)
api_router.include_router(storage_router)

api_router.include_router(setting_router)

api_router.include_router(webhook_router)


# api_router.include_router(tests_router, prefix="/tests", tags=["Tests"])
# api_router.include_router(exams_router, prefix="/exams", tags=["Exams"])
