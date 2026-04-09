import csv
import io
import secrets
from uuid import UUID
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import update, select, or_
from src.config.settings import settings
from src.domains.institution.repositories.institution_repository import ClassroomRepo
from src.domains.institution.schemas.institution import BulkOnboardResult, LinkStudent
from src.domains.auth.models.user import User
from src.domains.auth.models.student import Student

from src.shared.events.dispatcher import (
    dispatch_user_registered,
    dispatch_verification_email,
    dispatch_assigned_user_role,
)

from src.domains.auth.schemas.user import RegisterRequest
from src.shared.events.payloads import EmailVerificationPayload
from src.domains.auth.enums import UserType
from src.core.security import hash_password


class BulkStudentOnboardingService:
    """
    Parses a CSV file and creates User + Student records for each valid row.
    Rolls back individual failures without aborting the whole batch.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def parse_csv(self, file_bytes: bytes) -> List[dict]:
        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)

    async def single_onboard(
        self, institution_id: UUID, data: RegisterRequest, send_invite: bool = True
    ) -> UUID:

        email = (data.email or "").strip().lower()
        password = (data.password or "").strip()

        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        # 1. Check for existing user
        existing_user = await self.db.execute(select(User).where(User.email == email))
        user = existing_user.scalar_one_or_none()

        is_new_user = False
        if not user:
            is_new_user = True
            user = await self._create_user_record(data, email, password)

        data.institution_id = institution_id

        # 2. Triggers: Wallet, Bonus, Gamification, Handler
        dispatch_user_registered(
            user_id=user.id,
            user_type=UserType.STUDENT,
            registration_data=data,
        )

        # 4. Handle Invite/Verification
        if is_new_user:
            verify_token = secrets.token_urlsafe(32)
            user.email_verification_token = verify_token
            user.email_verification_token_expires = datetime.utcnow() + timedelta(
                minutes=settings.VERIFY_TOKEN_EXPIRE_MINUTES
            )
            dispatch_verification_email(
                payload=EmailVerificationPayload(
                    user_email=user.email,
                    verify_token=verify_token,
                    client_type="user",
                )
            )

        await self.db.commit()
        return user.id

    async def bulk_onboard(
        self, institution_id: UUID, file_bytes: bytes, send_invite: bool = True
    ) -> BulkOnboardResult:
        rows = await self.parse_csv(file_bytes)
        errors = []
        created_ids = []

        # Map classroom codes for lookup
        classroom_repo = ClassroomRepo(self.db)
        classrooms = await classroom_repo.list_by_institution(institution_id)
        code_to_classroom = {c.code: c for c in classrooms}

        for i, row in enumerate(rows):
            try:
                email = row.get("email", "").strip().lower()
                if not email:
                    raise ValueError("Missing email")

                # 1. Handle User Creation or Retrieval
                existing_user = await self.db.execute(
                    select(User).where(User.email == email)
                )
                user = existing_user.scalar_one_or_none()

                is_new_user = False
                if not user:
                    is_new_user = True
                    user = await self._create_user_record(row, email)

                classroom_id = None
                classroom_code = row.get("classroom_code", "").strip()
                if classroom_code and classroom_code in code_to_classroom:
                    classroom_id = code_to_classroom[classroom_code].id

                # 2. Prepare the Registration Payload
                registration_data = RegisterRequest(
                    email=row.get("guardian_email", "").strip() or None,
                    first_name=row.get("first_name", "").strip(),
                    last_name=row.get("last_name", "").strip(),
                    middle_name=row.get("middle_name", "").strip() or None,
                    phone_number=row.get("phone_number", "").strip() or None,
                    date_of_birth=row.get("date_of_birth", "").strip() or None,
                    user_type=UserType.STUDENT,
                    password="SecurePass123#",
                    category=row.get("category", "").strip() or None,
                    guardian_email=row.get("guardian_email", "").strip() or None,
                    classroom_id=classroom_id,
                    institution_id=institution_id,
                )

                dispatch_user_registered(
                    user_id=user.id,
                    user_type=UserType.STUDENT,
                    registration_data=registration_data,
                )

                if is_new_user and send_invite:
                    dispatch_verification_email(
                        payload=EmailVerificationPayload(
                            user_email=user.email,
                            verify_token=secrets.token_urlsafe(32),
                            client_type="user",
                        )
                    )

                created_ids.append(user.id)

            except Exception as e:
                errors.append(
                    {"row": i + 2, "email": row.get("email", ""), "reason": str(e)}
                )
                await self.db.rollback()

        await self.db.commit()
        return BulkOnboardResult(
            total=len(rows),
            success=len(created_ids),
            failed=len(errors),
            errors=errors,
            created_student_ids=created_ids,
        )

    async def _create_user_record(
        self, row: dict, email: str, password: str | None = None
    ) -> User:
        actual_password = password if password else secrets.token_urlsafe(12)
        hashed = hash_password(actual_password)

        def get_field(obj, field: str):
            if isinstance(obj, dict):
                return obj.get(field)
            return getattr(obj, field, None)

        user = User(
            email=email,
            first_name=get_field(row, "first_name"),
            last_name=get_field(row, "last_name"),
            phone_number=get_field(row, "phone_number"),
            date_of_birth=get_field(row, "date_of_birth"),
            password_hash=hashed,
            user_type=UserType.STUDENT,
            is_active=True,
            is_verified=True,
            is_email_verified=False,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.commit()

        dispatch_assigned_user_role(user_id=user.id, role_name="student")

        return user

    async def remove_student_from_institution(
        self, institution_id: UUID, student_id: UUID
    ) -> bool:
        stmt = (
            update(Student)
            .where(Student.id == student_id, Student.institution_id == institution_id)
            .values(
                institution_id=None,
                classroom_id=None,
            )
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in this institution",
            )

        return True

    async def lookup_student(self, institution_id: UUID, q: str):
        result = await self.db.execute(
            select(Student, User)
            .join(User, Student.user_id == User.id)
            .where(or_(User.email == q.lower(), Student.student_code == q.upper()))
            .limit(1)
        )
        row = result.first()

        if not row:
            return {"found": False, "has_institution": False, "can_link": False}

        student, user = row

        if student.institution_id == institution_id:
            return {
                "found": True,
                "can_link": False,
                "has_institution": True,
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "message": "This student is already enrolled in your institution",
            }

        if student.institution_id is not None:
            return {
                "found": True,
                "can_link": True,
                "has_institution": True,
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "message": "This student is currently enrolled in another institution. If you continue, it will be onboard ro this one",
            }

        return {
            "found": True,
            "can_link": True,
            "has_institution": False,
            "student_id": str(student.id),
            "full_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
        }

    async def link_student(self, institution_id: UUID, data: LinkStudent):

        result = await self.db.execute(
            select(Student).where(Student.id == data.student_id).limit(1)
        )
        student = result.scalars().first()

        if not student:
            return {"found": False, "has_institution": False, "can_link": False}

        student.institution_id = institution_id
        student.classroom_id = data.classroom_id

        self.db.add(student)
        await self.db.commit()
        await self.db.refresh(student)

        return {
            "found": True,
            "has_institution": False,
            "can_link": True,
            "student_id": student.id,
            "institution_id": student.institution_id,
            "classroom_id": student.classroom_id,
        }
