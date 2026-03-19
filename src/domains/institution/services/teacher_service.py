import secrets
import bcrypt
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from src.domains.auth.enums import UserType
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.institution.repositories.institution_repository import TeacherRepo
from src.domains.institution.schemas.institution import (
    TeacherInviteRequest,
    TeacherResponse,
)
from src.domains.institution.models.teacher import InstitutionTeacher
from src.domains.institution.models.institution import InstitutionMember
from src.domains.auth.models.user import User
from src.config.settings import settings

from src.domains.institution.utils.helpers import _generate_code
from src.shared.events.payloads import (
    EmailVerificationPayload,
    TeacherInvitationPayload,
)


from src.shared.events.dispatcher import (
    dispatch_verification_email,
    dispatch_assigned_user_role,
    dispatch_teacher_invitation,
)


class TeacherService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TeacherRepo(db)

    async def invite_teacher(
        self, institution_id: UUID, data: TeacherInviteRequest
    ) -> TeacherResponse:
        """
        Creates a User account (or links existing) and creates InstitutionTeacher record.
        Sends an invite email with a temp password / magic link.
        """

        # Check if user exists
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user:
            temp_password = secrets.token_urlsafe(12)
            hashed = bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()
            user = User(
                email=str(data.email),
                first_name=data.first_name,
                last_name=data.last_name,
                password_hash=hashed,
                user_type=UserType.INSTITUTION_ADMIN,
                is_active=True,
            )

            verify_token = secrets.token_urlsafe(32)
            user.email_verification_token = verify_token
            user.email_verification_token_expires = datetime.utcnow() + timedelta(
                minutes=settings.VERIFY_TOKEN_EXPIRE_MINUTES
            )

            self.db.add(user)
            await self.db.flush()

        teacher = InstitutionTeacher(
            user_id=user.id,
            institution_id=institution_id,
            teacher_code=_generate_code("TCH"),
            specialization=data.specialization,
            bio=data.bio,
        )
        teacher = await self.repo.create(teacher)

        existing_member = (
            await self.db.execute(
                select(InstitutionMember).where(
                    InstitutionMember.institution_id == institution_id,
                    InstitutionMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()

        if not existing_member:
            member = InstitutionMember(
                institution_id=institution_id,
                user_id=user.id,
                role="staff",
                is_active=True,
            )
            self.db.add(member)

        # Assign to classrooms
        for cid in data.classroom_ids or []:
            await self.repo.assign_to_classroom(teacher.id, cid, data.subject)

        await self.db.commit()

        dispatch_verification_email(
            payload=EmailVerificationPayload(
                user_email=user.email,
                verify_token=verify_token,
                client_type="admin",
            )
        )

        dispatch_assigned_user_role(user_id=user.id, role_name="teacher")

        dispatch_teacher_invitation(
            payload=TeacherInvitationPayload(
                teacher_name=user.first_name,
                teacher_email=user.email,
                institution_name=await self._get_institution_name(institution_id),
                temp_password=temp_password,
                user_type="admin",
            )
        )

        reloaded = await self.db.execute(
            select(InstitutionTeacher)
            .options(
                selectinload(InstitutionTeacher.user),
                selectinload(InstitutionTeacher.taught_classrooms),
                selectinload(InstitutionTeacher.homeroom_class),
            )
            .where(InstitutionTeacher.id == teacher.id)
        )
        teacher_full = reloaded.scalar_one()
        return TeacherResponse.from_orm_full(teacher_full)

    async def list_teachers(self, institution_id: UUID) -> list[TeacherResponse]:
        result = await self.db.execute(
            select(InstitutionTeacher)
            .options(
                selectinload(InstitutionTeacher.user),
                selectinload(InstitutionTeacher.taught_classrooms),
                selectinload(InstitutionTeacher.homeroom_class),
            )
            .where(
                InstitutionTeacher.institution_id == institution_id,
                InstitutionTeacher.is_active.is_(True),
            )
            .order_by(InstitutionTeacher.joined_date.desc())
        )
        teachers = result.scalars().all()
        return [TeacherResponse.from_orm_full(t) for t in teachers]

    async def suspend_teacher(self, teacher_id: UUID, suspend: bool):
        await self.repo.suspend(teacher_id, suspend)

    async def assign_to_classroom(
        self,
        teacher_id: UUID,
        classroom_id: UUID,
        subject: Optional[str],
        is_class_teacher: bool = False,
    ):
        await self.repo.assign_to_classroom(
            teacher_id, classroom_id, subject, is_class_teacher
        )

    async def _get_institution_name(self, institution_id: UUID) -> str:
        """Helper to fetch institution name for the email."""
        from src.domains.institution.models.institution import Institution

        result = await self.db.execute(
            select(Institution.name).where(Institution.id == institution_id)
        )
        return result.scalar_one_or_none() or "Your Institution"
