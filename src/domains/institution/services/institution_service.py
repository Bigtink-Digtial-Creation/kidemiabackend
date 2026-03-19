from uuid import UUID
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.institution.repositories.institution_repository import InstitutionRepo


class InstitutionAccessService:
    """
    Used ONLY by system admins to control institution-level access.
    Institution owners cannot call these methods.
    """

    def __init__(self, db: AsyncSession):
        self.repo = InstitutionRepo(db)

    async def toggle_access(
        self, institution_id: UUID, is_public: bool, reason: Optional[str]
    ) -> dict:
        institution = await self.repo.get_by_id(institution_id)
        if not institution:
            raise HTTPException(status_code=404, detail="Institution not found")
        await self.repo.set_active(institution_id, is_public)
        return {
            "institution_id": str(institution_id),
            "is_public": is_public,
            "reason": reason,
        }

    async def update_tier(
        self, institution_id: UUID, tier: str, max_students: Optional[int]
    ) -> dict:
        institution = await self.repo.get_by_id(institution_id)
        if not institution:
            raise HTTPException(status_code=404, detail="Institution not found")
        await self.repo.update_tier(institution_id, tier, max_students)
        return {
            "institution_id": str(institution_id),
            "tier": tier,
            "max_students": max_students,
        }
