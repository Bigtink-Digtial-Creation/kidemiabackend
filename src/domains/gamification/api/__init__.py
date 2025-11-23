from fastapi import APIRouter

from src.domains.gamification.api import admin, gamify


gamification_router = APIRouter()

gamification_router.include_router(admin.router)
gamification_router.include_router(gamify.router)
