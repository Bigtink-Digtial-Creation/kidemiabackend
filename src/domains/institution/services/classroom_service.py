from uuid import UUID
from typing import List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.institution.repositories.institution_repository import ClassroomRepo
from src.domains.institution.schemas.institution import (
    ClassroomCreate,
    ClassroomUpdate,
    MoveStudentRequest,
    BulkMoveStudentsRequest,
)
from src.domains.institution.models.classroom import Classroom


class ClassroomService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ClassroomRepo(db)

    async def create_classroom(
        self, institution_id: UUID, data: ClassroomCreate
    ) -> Classroom:
        payload = data.model_dump(exclude_none=True)
        classroom = await self.repo.create(institution_id, payload)
        return classroom

    async def update_classroom(
        self, classroom_id: UUID, institution_id: UUID, data: ClassroomUpdate
    ) -> Classroom:
        classroom = await self.repo.get_by_id(classroom_id)
        if not classroom or classroom.institution_id != institution_id:
            raise HTTPException(status_code=404, detail="Classroom not found")
        payload = data.model_dump(exclude_none=True)
        return await self.repo.update(classroom_id, payload)

    async def list_classrooms(self, institution_id: UUID) -> List[Classroom]:
        return await self.repo.list_by_institution(institution_id)

    async def move_student(self, institution_id: UUID, req: MoveStudentRequest) -> dict:
        classroom = await self.repo.get_by_id(req.target_classroom_id)
        if not classroom or classroom.institution_id != institution_id:
            raise HTTPException(
                status_code=404, detail="Target classroom not found in this institution"
            )
        await self.repo.move_student(req.student_id, req.target_classroom_id)
        return {
            "student_id": str(req.student_id),
            "new_classroom_id": str(req.target_classroom_id),
        }

    async def bulk_move_students(
        self, institution_id: UUID, req: BulkMoveStudentsRequest
    ) -> dict:
        classroom = await self.repo.get_by_id(req.target_classroom_id)
        if not classroom or classroom.institution_id != institution_id:
            raise HTTPException(
                status_code=404, detail="Target classroom not found in this institution"
            )
        await self.repo.bulk_move_students(req.student_ids, req.target_classroom_id)
        return {
            "moved_count": len(req.student_ids),
            "new_classroom_id": str(req.target_classroom_id),
        }
