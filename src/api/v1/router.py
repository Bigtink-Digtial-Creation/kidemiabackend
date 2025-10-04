from fastapi import APIRouter

# Import domain routers
from src.domains.auth.api.auth import router as auth_router
# from src.domains.auth.api.users import router as users_router
# from src.domains.content.api.subjects import router as subjects_router
# from src.domains.assessment.api.tests import router as tests_router
# etc.

api_router = APIRouter()

# Include all domain routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(users_router, prefix="/users", tags=["Users"])

# api_router.include_router(subjects_router, prefix="/subjects", tags=["Subjects"])
# api_router.include_router(tests_router, prefix="/tests", tags=["Tests"])
# api_router.include_router(exams_router, prefix="/exams", tags=["Exams"])
