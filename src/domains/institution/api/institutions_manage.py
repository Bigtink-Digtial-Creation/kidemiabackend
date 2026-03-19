from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
import io
from src.config.database import get_async_db
from src.core.security import require_permissions
from src.domains.institution.services.institution_onboarding_service import (
    BulkInstitutionOnboardingService,
    InstitutionOnboardingService,
)
from src.domains.institution.services.institution_service import (
    InstitutionAccessService,
)


from src.domains.institution.schemas.institution import (
    BulkInstitutionOnboardResult,
    InstitutionAdminDetail,
    InstitutionAdminListItem,
    InstitutionOnboardRequest,
    InstitutionOnboardResponse,
    InstitutionStatusUpdate,
    InstitutionTierUpdate,
)


Institution_manage_router = APIRouter(
    prefix="/admin/institutions", tags=["Admin - Institution Control"]
)


@Institution_manage_router.post(
    "", response_model=InstitutionOnboardResponse, status_code=201
)
async def onboard_institution(
    body: InstitutionOnboardRequest,
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permissions("institutions:create")),
):
    """
    Manually onboard a single institution.
    Creates the Institution record + an owner User account in one transaction.
    Optionally sends a welcome email with credentials.
    """
    svc = InstitutionOnboardingService(db)
    return await svc.onboard(body)


@Institution_manage_router.get("/list", response_model=List[InstitutionAdminListItem])
async def list_institutions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Filter by name or code"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permissions("institutions:read")),
):
    """List all institutions with optional filtering. Admin only."""
    svc = InstitutionOnboardingService(db)
    return await svc.get_all(
        skip=skip, limit=limit, search=search, tier=tier, is_public=is_public
    )


@Institution_manage_router.get(
    "/{institution_id}", response_model=InstitutionAdminDetail
)
async def get_institution_detail(
    institution_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permissions("institutions:read")),
):
    """Full detail view of a single institution. Admin only."""
    svc = InstitutionOnboardingService(db)
    return await svc.get_detail(institution_id)


@Institution_manage_router.get("/bulk/csv-template")
async def download_institution_csv_template(
    _: None = Depends(require_permissions("institutions:create")),
):
    """
    Download the CSV template for bulk institution onboarding.
    Includes two sample rows so admins know the expected format.
    """
    content = BulkInstitutionOnboardingService.get_csv_template()
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=institution_bulk_onboard_template.csv"
        },
    )


@Institution_manage_router.post(
    "/bulk/upload", response_model=BulkInstitutionOnboardResult
)
async def bulk_onboard_institutions(
    file: UploadFile = File(
        ...,
        description="CSV using the template from GET /admin/institutions/bulk/csv-template",
    ),
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permissions("institutions:create")),
):
    """
    Bulk onboard institutions from a CSV file.
    Each row creates one Institution + one owner User account.
    Failed rows are reported in the response without aborting successful rows.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    content = await file.read()
    svc = BulkInstitutionOnboardingService(db)
    return await svc.bulk_onboard(content)


@Institution_manage_router.patch("/{institution_id}/access")
async def toggle_institution_access(
    institution_id: UUID,
    body: InstitutionStatusUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permissions("institutions:update")),
):
    """
    Enable or disable an institution entirely.
    Disabled institutions cannot log in or use any features.
    """
    svc = InstitutionAccessService(db)
    return await svc.toggle_access(institution_id, body.is_public, body.reason)


@Institution_manage_router.patch("/{institution_id}/tier")
async def update_institution_tier(
    institution_id: UUID,
    body: InstitutionTierUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permissions("institutions:update")),
):
    """Change institution tier and student cap. Admin only."""
    svc = InstitutionAccessService(db)
    return await svc.update_tier(institution_id, body.tier, body.max_students)


@Institution_manage_router.get("/student-csv-template")
async def download_student_csv_template(
    _: None = Depends(require_permissions("institutions:read")),
):
    """Student bulk-upload CSV template (to share with onboarded institutions)."""
    headers = [
        "first_name",
        "last_name",
        "email",
        "date_of_birth",
        "phone_number",
        "guardian_email",
        "classroom_code",
        "student_code",
    ]
    sample = [
        "John",
        "Doe",
        "john.doe@example.com",
        "2010-01-15",
        "+2348000000000",
        "parent@example.com",
        "JSS1A",
        "",
    ]
    content = ",".join(headers) + "\n" + ",".join(sample) + "\n"
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=student_import_template.csv"
        },
    )
