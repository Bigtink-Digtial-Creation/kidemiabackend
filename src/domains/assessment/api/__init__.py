from fastapi import APIRouter

from src.domains.assessment.api import (
    assessments,
    attempts,
    grading,
    leaderboard,
    categories,
)

# Create assessment router
assessment_router = APIRouter()

# Include all sub-routers
assessment_router.include_router(
    assessments.router, prefix="/assessments", tags=["Assessments"]
)

assessment_router.include_router(attempts.router, prefix="/attempts", tags=["Attempts"])

assessment_router.include_router(grading.router, prefix="/grading", tags=["Grading"])

assessment_router.include_router(
    leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"]
)

assessment_router.include_router(
    categories.router, prefix="/categories", tags=["Assessment Categories"]
)
