import csv
import io

from uuid import UUID
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.institution.schemas.institution import (
    InstitutionOnboardRequest,
    InstitutionOnboardResponse,
    BulkInstitutionOnboardResult,
    InstitutionAdminListItem,
    InstitutionAdminDetail,
)
from src.domains.institution.models.institution import Institution
from src.domains.auth.models.user import User
from src.domains.institution.models.teacher import InstitutionTeacher
from src.domains.institution.models.classroom import Classroom
from src.domains.institution.utils.helpers import (
    _generate_institution_code,
    _random_password,
)

import bcrypt
from src.domains.auth.enums import UserType
from src.domains.institution.models.institution import InstitutionMember
from src.shared.events.dispatcher import (
    dispatch_institution_welcome_email,
    dispatch_institution_role_assignment,
)
from src.shared.events.payloads import InstitutionEmailPayload


async def _get_or_create_institution_admin_user(
    db: AsyncSession, email: str, first_name: str, last_name: str, phone: Optional[str]
) -> Tuple[User, str, bool]:
    """
    Returns (user, temp_password, is_new).
    If the user already exists we reuse the account (idempotent re-onboarding).
    """

    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    existing = result.scalar_one_or_none()
    if existing:
        return existing, "", False

    temp_pw = _random_password()
    hashed = bcrypt.hashpw(temp_pw.encode(), bcrypt.gensalt()).decode()

    user = User(
        email=email.strip().lower(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone_number=phone,
        password_hash=hashed,
        user_type=UserType.INSTITUTION_ADMIN,
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.flush()

    # assign_role
    return user, temp_pw, True


class InstitutionOnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def onboard(
        self, data: InstitutionOnboardRequest
    ) -> InstitutionOnboardResponse:
        """
        This order ensures:
          - The institution exists independently before any user is tied to it
          - The bridge table is the authoritative source for the relationship
          - owner_id on Institution is a denormalized convenience field only
        """

        if (
            await self.db.execute(
                select(Institution).where(Institution.name == data.name)
            )
        ).scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail=f"Institution name '{data.name}' already exists"
            )

        if (
            await self.db.execute(
                select(Institution).where(Institution.code == data.code)
            )
        ).scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail=f"Institution code '{data.code}' already taken"
            )

        # ── 3. Create or reuse the owner User
        owner, temp_pw, is_new_user = await _get_or_create_institution_admin_user(
            self.db,
            str(data.owner_email),
            data.owner_first_name,
            data.owner_last_name,
            data.owner_phone,
        )

        institution = Institution(
            name=data.name,
            code=data.code,
            description=data.description,
            motto=data.motto,
            established_date=data.established_date,
            email=str(data.email) if data.email else None,
            phone=data.phone,
            website=data.website,
            address=data.address,
            city=data.city,
            state=data.state,
            country=data.country,
            owner_id=owner.id,
            logo_url=data.logo_url,
            banner_url=data.banner_url,
            color_primary=data.color_primary,
            color_secondary=data.color_secondary,
            tier=data.tier,
            max_students=data.max_students,
            is_verified=data.is_verified,
            is_public=data.is_public,
            total_students=0,
            total_assessments=0,
            total_courses=0,
        )
        self.db.add(institution)
        await self.db.flush()

        # Check the user isn't already a member (handles idempotent re-onboarding)
        existing_member = (
            await self.db.execute(
                select(InstitutionMember).where(
                    InstitutionMember.institution_id == institution.id,
                    InstitutionMember.user_id == owner.id,
                )
            )
        ).scalar_one_or_none()

        if not existing_member:
            member = InstitutionMember(
                institution_id=institution.id,
                user_id=owner.id,
                role="owner",
                is_active=True,
            )
            self.db.add(member)

        # ── 5. Single commit
        await self.db.commit()
        await self.db.refresh(institution)

        institutionResponse = InstitutionOnboardResponse(
            institution_id=institution.id,
            name=institution.name,
            code=institution.code,
            owner_user_id=owner.id,
            owner_email=owner.email,
            tier=institution.tier,
            is_public=institution.is_public,
            temp_password_sent=is_new_user and data.send_welcome_email,
            created_at=institution.created_at,
        )

        dispatch_institution_role_assignment(user_id=owner.id)

        if data.send_welcome_email and is_new_user and temp_pw:
            dispatch_institution_welcome_email(
                payload=InstitutionEmailPayload(
                    email=owner.email, temp_pw=temp_pw, institution=institutionResponse
                )
            )

        return institutionResponse

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        tier: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> List[InstitutionAdminListItem]:
        q = select(Institution)
        if search:
            q = q.where(
                Institution.name.ilike(f"%{search}%")
                | Institution.code.ilike(f"%{search}%")
            )
        if tier:
            q = q.where(Institution.tier == tier)
        if is_public is not None:
            q = q.where(Institution.is_public == is_public)
        q = q.order_by(Institution.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        institutions = result.scalars().all()

        items = []
        for inst in institutions:
            # Fetch owner email
            owner = await self.db.get(User, inst.owner_id)
            # Count teachers
            t_count = await self.db.execute(
                select(func.count(InstitutionTeacher.id)).where(
                    InstitutionTeacher.institution_id == inst.id
                )
            )
            items.append(
                InstitutionAdminListItem(
                    id=inst.id,
                    name=inst.name,
                    code=inst.code,
                    city=inst.city,
                    state=inst.state,
                    country=inst.country,
                    tier=inst.tier,
                    is_public=inst.is_public,
                    is_verified=inst.is_verified,
                    total_students=inst.total_students,
                    total_teachers=t_count.scalar_one(),
                    owner_email=owner.email if owner else None,
                    created_at=inst.created_at,
                )
            )
        return items

    async def get_detail(self, institution_id: UUID) -> InstitutionAdminDetail:
        institution = await self.db.get(Institution, institution_id)
        if not institution:
            raise HTTPException(status_code=404, detail="Institution not found")

        owner = await self.db.get(User, institution.owner_id)

        t_count = await self.db.execute(
            select(func.count(InstitutionTeacher.id)).where(
                InstitutionTeacher.institution_id == institution_id
            )
        )
        c_count = await self.db.execute(
            select(func.count(Classroom.id)).where(
                Classroom.institution_id == institution_id
            )
        )

        return InstitutionAdminDetail(
            id=institution.id,
            name=institution.name,
            code=institution.code,
            description=institution.description,
            motto=institution.motto,
            city=institution.city,
            state=institution.state,
            country=institution.country,
            email=institution.email,
            phone=institution.phone,
            website=institution.website,
            address=institution.address,
            logo_url=institution.logo_url,
            tier=institution.tier,
            is_public=institution.is_public,
            is_verified=institution.is_verified,
            total_students=institution.total_students,
            total_teachers=t_count.scalar_one(),
            total_classrooms=c_count.scalar_one(),
            total_assessments=institution.total_assessments,
            max_students=institution.max_students,
            established_date=institution.established_date,
            owner_email=owner.email if owner else None,
            created_at=institution.created_at,
        )


class BulkInstitutionOnboardingService:
    """
    Parses a CSV where each row is one institution + its owner account.
    Processes rows one-by-one: a single bad row does NOT abort the whole batch.
    """

    # Expected CSV columns (order doesn't matter; matched by header name)
    REQUIRED_COLUMNS = {
        "name",
        "code",
        "owner_email",
        "owner_first_name",
        "owner_last_name",
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self._single_svc = InstitutionOnboardingService(db)

    @staticmethod
    def parse_csv(file_bytes: bytes) -> List[dict]:
        content = file_bytes.decode("utf-8-sig")  # handle BOM from Excel exports
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            raise ValueError("CSV file is empty")
        # Validate required columns present
        headers = set(rows[0].keys())
        missing = BulkInstitutionOnboardingService.REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(
                f"CSV missing required columns: {', '.join(sorted(missing))}"
            )
        return rows

    @staticmethod
    def _coerce_int(val: str) -> Optional[int]:
        try:
            return int(val.strip()) if val and val.strip() else None
        except ValueError:
            return None

    async def bulk_onboard(self, file_bytes: bytes) -> BulkInstitutionOnboardResult:
        try:
            rows = self.parse_csv(file_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        errors: List[dict] = []
        created_ids: List[UUID] = []

        for i, raw in enumerate(rows):
            row_num = i + 2  # 1-indexed + header row

            # Strip whitespace from all values
            row = {k: (v or "").strip() for k, v in raw.items()}

            try:
                # Validate required fields
                for col in self.REQUIRED_COLUMNS:
                    if not row.get(col):
                        raise ValueError(f"Missing required field: {col}")

                # Auto-generate code if not provided
                code = row["code"] or _generate_institution_code(row["name"])

                request = InstitutionOnboardRequest(
                    name=row["name"],
                    code=code,
                    email=row.get("email") or None,
                    phone=row.get("phone") or None,
                    city=row.get("city") or None,
                    state=row.get("state") or None,
                    country=row.get("country") or "Nigeria",
                    tier=row.get("tier") or "basic",
                    max_students=self._coerce_int(row.get("max_students", "")),
                    owner_email=row["owner_email"],
                    owner_first_name=row["owner_first_name"],
                    owner_last_name=row["owner_last_name"],
                    owner_phone=row.get("owner_phone") or None,
                    send_welcome_email=True,
                )

                result = await self._single_svc.onboard(request)
                created_ids.append(result.institution_id)

            except HTTPException as e:
                errors.append(
                    {
                        "row": row_num,
                        "name": row.get("name", ""),
                        "code": row.get("code", ""),
                        "reason": e.detail,
                    }
                )
                # Rollback the failed savepoint so the session stays healthy
                await self.db.rollback()

            except Exception as e:
                errors.append(
                    {
                        "row": row_num,
                        "name": row.get("name", ""),
                        "code": row.get("code", ""),
                        "reason": str(e),
                    }
                )
                await self.db.rollback()

        return BulkInstitutionOnboardResult(
            total=len(rows),
            success=len(created_ids),
            failed=len(errors),
            errors=errors,
            created_institution_ids=created_ids,
        )

    @staticmethod
    def get_csv_template() -> str:
        """Returns the CSV template content as a string for download."""
        headers = [
            "name",
            "code",
            "email",
            "phone",
            "city",
            "state",
            "country",
            "tier",
            "max_students",
            "owner_email",
            "owner_first_name",
            "owner_last_name",
            "owner_phone",
        ]
        sample = [
            "Greenfield Academy",
            "GFA-LG",
            "info@greenfield.edu.ng",
            "+2348001234567",
            "Lagos",
            "Lagos",
            "Nigeria",
            "premium",
            "500",
            "samuel@greenfield.edu.ng",
            "Samuel",
            "Adeyemi",
            "+2348001234568",
        ]
        sample2 = [
            "Sunrise Secondary School",
            "SSS-KN",
            "contact@sunrise.edu.ng",
            "",
            "Kano",
            "Kano",
            "Nigeria",
            "basic",
            "",
            "principal@sunrise.edu.ng",
            "Amina",
            "Yusuf",
            "",
        ]
        lines = [
            ",".join(headers),
            ",".join(sample),
            ",".join(sample2),
        ]
        return "\n".join(lines)
