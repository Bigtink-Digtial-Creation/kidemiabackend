from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload, Session

from src.domains.institution.models.classroom import Classroom
from src.domains.institution.models.teacher import InstitutionTeacher
from src.domains.institution.models.classroom_group import (
    StudentGroup,
    ClassroomTeacherAssignment,
    ClassroomAssessmentAssignment,
    student_group_members,
)
from src.domains.auth.models.student import Student
from src.domains.institution.models.institution import Institution


class InstitutionRepo:
    """Repository for Institution entity (admin-controlled fields)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, institution_id: UUID) -> Optional[Institution]:
        result = await self.db.execute(
            select(Institution).where(Institution.id == institution_id)
        )
        return result.scalar_one_or_none()

    async def set_active(self, institution_id: UUID, is_public: bool) -> None:
        await self.db.execute(
            update(Institution)
            .where(Institution.id == institution_id)
            .values(is_public=is_public)
        )
        await self.db.commit()

    async def update_tier(
        self, institution_id: UUID, tier: str, max_students: Optional[int]
    ) -> None:
        values = {"tier": tier}
        if max_students is not None:
            values["max_students"] = max_students
        await self.db.execute(
            update(Institution).where(Institution.id == institution_id).values(**values)
        )
        await self.db.commit()


class ClassroomRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, institution_id: UUID, data: dict) -> Classroom:
        classroom = Classroom(institution_id=institution_id, **data)
        self.db.add(classroom)
        await self.db.commit()
        await self.db.refresh(classroom)
        return classroom

    async def get_by_id(self, classroom_id: UUID) -> Optional[Classroom]:
        result = await self.db.execute(
            select(Classroom)
            .options(selectinload(Classroom.students))
            .where(Classroom.id == classroom_id)
        )
        return result.scalar_one_or_none()

    async def list_by_institution(self, institution_id: UUID) -> List[Classroom]:
        result = await self.db.execute(
            select(Classroom)
            .options(
                selectinload(Classroom.students),
                # Load the teacher AND the teacher's user profile in one go
                selectinload(Classroom.class_teacher).selectinload(
                    InstitutionTeacher.user
                ),
            )
            .where(
                Classroom.institution_id == institution_id,
                Classroom.is_active.is_(True),
            )
            .order_by(Classroom.level, Classroom.name)
        )

        return result.scalars().all()

    async def update(self, classroom_id: UUID, data: dict) -> Optional[Classroom]:
        await self.db.execute(
            update(Classroom).where(Classroom.id == classroom_id).values(**data)
        )
        await self.db.commit()
        return await self.get_by_id(classroom_id)

    async def move_student(self, student_id: UUID, target_classroom_id: UUID) -> None:
        await self.db.execute(
            update(Student)
            .where(Student.id == student_id)
            .values(classroom_id=target_classroom_id)
        )
        await self.db.commit()

    async def bulk_move_students(
        self, student_ids: List[UUID], target_classroom_id: UUID
    ) -> None:
        await self.db.execute(
            update(Student)
            .where(Student.id.in_(student_ids))
            .values(classroom_id=target_classroom_id)
        )
        await self.db.commit()

    async def get_student_count(self, classroom_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Student.id)).where(Student.classroom_id == classroom_id)
        )
        return result.scalar_one()


class StudentGroupRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, institution_id: UUID, data: dict, student_ids: List[UUID]
    ) -> StudentGroup:
        group = StudentGroup(institution_id=institution_id, **data)
        self.db.add(group)
        await self.db.flush()
        if student_ids:
            await self._sync_members(group.id, student_ids, add=True)
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def _sync_members(
        self, group_id: UUID, student_ids: List[UUID], add: bool = True
    ) -> None:
        if add:
            for sid in student_ids:
                await self.db.execute(
                    student_group_members.insert().values(
                        group_id=group_id, student_id=sid
                    )
                )
        else:
            await self.db.execute(
                student_group_members.delete().where(
                    student_group_members.c.group_id == group_id
                )
            )
            for sid in student_ids:
                await self.db.execute(
                    student_group_members.insert().values(
                        group_id=group_id, student_id=sid
                    )
                )

    async def update_members(self, group_id: UUID, student_ids: List[UUID]) -> None:
        await self._sync_members(group_id, student_ids, add=False)
        await self.db.commit()

    async def list_by_classroom(self, classroom_id: UUID) -> List[StudentGroup]:
        result = await self.db.execute(
            select(StudentGroup)
            .options(selectinload(StudentGroup.students))
            .where(StudentGroup.classroom_id == classroom_id)
        )
        return result.scalars().all()

    # In StudentGroupRepo
    async def list_by_institution(self, institution_id: UUID) -> List[StudentGroup]:
        result = await self.db.execute(
            select(StudentGroup)
            .options(selectinload(StudentGroup.students))
            .where(
                StudentGroup.institution_id == institution_id,
                StudentGroup.is_active.is_(True),
            )
        )
        return result.scalars().all()


class TeacherRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, teacher: InstitutionTeacher) -> InstitutionTeacher:
        self.db.add(teacher)
        await self.db.commit()
        await self.db.refresh(teacher)
        return teacher

    async def get_by_id(self, teacher_id: UUID) -> Optional[InstitutionTeacher]:
        result = await self.db.execute(
            select(InstitutionTeacher)
            .options(selectinload(InstitutionTeacher.user))
            .where(InstitutionTeacher.id == teacher_id)
        )
        return result.scalar_one_or_none()

    async def list_by_institution(
        self, institution_id: UUID
    ) -> List[InstitutionTeacher]:

        result = await self.db.execute(
            select(InstitutionTeacher)
            .options(
                selectinload(InstitutionTeacher.user),
                selectinload(InstitutionTeacher.homeroom_class),
                selectinload(InstitutionTeacher.taught_classes).selectinload(
                    ClassroomTeacherAssignment.classroom
                ),
            )
            .where(InstitutionTeacher.institution_id == institution_id)
        )

        return result.scalars().unique().all()

    async def suspend(self, teacher_id: UUID, suspend: bool) -> None:
        await self.db.execute(
            update(InstitutionTeacher)
            .where(InstitutionTeacher.id == teacher_id)
            .values(is_suspended=suspend)
        )
        await self.db.commit()

    async def assign_to_classroom(
        self,
        teacher_id: UUID,
        classroom_id: UUID,
        subject: Optional[str],
        is_class_teacher: bool = False,
    ) -> ClassroomTeacherAssignment:

        assignment = ClassroomTeacherAssignment(
            teacher_id=teacher_id, classroom_id=classroom_id, subject=subject
        )

        self.db.add(assignment)

        if is_class_teacher:
            result = await self.db.execute(
                select(Classroom).where(Classroom.id == classroom_id)
            )
            classroom = result.scalar_one()
            classroom.class_teacher_id = teacher_id

        await self.db.commit()

        return assignment


class AssessmentAssignmentRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, assignment: ClassroomAssessmentAssignment
    ) -> ClassroomAssessmentAssignment:
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment
