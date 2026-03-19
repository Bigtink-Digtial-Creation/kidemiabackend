from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.institution.repositories.institution_repository import StudentGroupRepo
from src.domains.institution.schemas.institution import (
    StudentGroupCreate,
    StudentGroupUpdate,
    StudentGroupResponse,
)


class StudentGroupService:
    def __init__(self, db: AsyncSession):
        self.repo = StudentGroupRepo(db)

    async def create_group(self, institution_id: UUID, data: StudentGroupCreate):
        payload = data.model_dump(exclude={"student_ids"})
        return await self.repo.create(institution_id, payload, data.student_ids or [])

    async def update_group(self, group_id: UUID, data: StudentGroupUpdate):
        if data.student_ids is not None:
            await self.repo.update_members(group_id, data.student_ids)

    async def list_groups(self, classroom_id: UUID) -> List[StudentGroupResponse]:
        groups = await self.repo.list_by_classroom(classroom_id)
        return [StudentGroupResponse.from_orm_with_count(g) for g in groups]

    async def list_groups_by_institution(
        self, institution_id: UUID
    ) -> List[StudentGroupResponse]:
        groups = await self.repo.list_by_institution(institution_id)
        return [StudentGroupResponse.from_orm_with_count(g) for g in groups]
