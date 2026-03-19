from fastapi import APIRouter, Depends, status, Query
from uuid import UUID
from typing import Optional
from fastapi.encoders import jsonable_encoder

from src.core.security import get_db, get_current_user_id
from src.domains.guardian.services.guardian_service import GuardianService
from src.domains.guardian.services.challenge_service import ChallengeAssessmentService

from src.domains.guardian.schemas.guardian import (
    GuardianUpdate,
    AddWardRequest,
    RemoveWardRequest,
    CategoryChangeRequest,
    ApproveCategoryChangeRequest,
    CreateAssessmentForWardsRequest,
)
from src.domains.guardian.models.guardian import CategoryChangeStatus, AssignmentStatus

from src.shared.response import success_response
from src.domains.access_control.dependency import RequireAccess
from src.domains.access_control.schema import ACCESS_RESPONSES
from src.domains.access_control.core import AccessResult

router = APIRouter(prefix="/guardians", tags=["Guardians"])


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_my_guardian_profile(
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get current user's guardian profile"""
    service = GuardianService(db)
    result = await service.get_guardian_by_user_id(user_id)

    if not result:
        return success_response(
            data=None,
            message="No guardian profile found for this user",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return success_response(
        data=jsonable_encoder(result),
        message="Guardian profile retrieved successfully",
    )


@router.get("/{guardian_id}", status_code=status.HTTP_200_OK)
async def get_guardian_detail(
    guardian_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get guardian details with wards"""
    service = GuardianService(db)
    result = await service.get_guardian_detail(guardian_id, user_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Guardian details retrieved successfully",
    )


@router.patch("/{guardian_id}", status_code=status.HTTP_200_OK)
async def update_guardian(
    guardian_id: UUID,
    update_data: GuardianUpdate,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Update guardian profile"""
    service = GuardianService(db)
    result = await service.update_guardian(guardian_id, user_id, update_data)

    return success_response(
        data=jsonable_encoder(result),
        message="Guardian profile updated successfully",
    )


@router.get("/{guardian_id}/wards", status_code=status.HTTP_200_OK)
async def get_my_wards(
    guardian_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get all wards for a guardian"""
    service = GuardianService(db)
    result = await service.get_my_wards(guardian_id, user_id, skip, limit)

    return success_response(
        data=jsonable_encoder(result),
        message="Wards retrieved successfully",
    )


@router.post(
    "/{guardian_id}/wards",
    status_code=status.HTTP_201_CREATED,
    responses={**ACCESS_RESPONSES},
)
async def add_ward(
    guardian_id: UUID,
    ward_data: AddWardRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
    access: AccessResult = Depends(
        RequireAccess(
            resource="ward",
            feature="multiple_wards",
            feature_only=True,
            auto_charge=False,
        )
    ),
):
    """Add a ward to guardian by email"""
    service = GuardianService(db)
    await service.add_ward(guardian_id, user_id, ward_data)

    return success_response(
        # data=jsonable_encoder(result),
        message="Ward Invitation Sent Successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.delete("/{guardian_id}/wards", status_code=status.HTTP_200_OK)
async def remove_ward(
    guardian_id: UUID,
    remove_data: RemoveWardRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Remove a ward from guardian"""
    service = GuardianService(db)

    result = await service.remove_ward(guardian_id, user_id, remove_data)

    return success_response(
        data={"success": result},
        message="Ward removed successfully",
    )


@router.post("/{guardian_id}/category-changes", status_code=status.HTTP_201_CREATED)
async def request_category_change(
    guardian_id: UUID,
    request_data: CategoryChangeRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Request a category change for a ward"""
    service = GuardianService(db)
    result = await service.request_category_change(guardian_id, user_id, request_data)

    return success_response(
        data=jsonable_encoder(result),
        message="Category change request created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/{guardian_id}/category-changes", status_code=status.HTTP_200_OK)
async def get_category_change_requests(
    guardian_id: Optional[UUID],
    status_filter: Optional[CategoryChangeStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get category change requests for guardian"""
    service = GuardianService(db)
    result = await service.get_category_change_requests(
        guardian_id, user_id, status_filter, skip, limit
    )

    return success_response(
        data=jsonable_encoder(result),
        message="Category change requests retrieved successfully",
    )


@router.post(
    "/{guardian_id}/category-changes/{request_id}/approve",
    status_code=status.HTTP_200_OK,
)
async def approve_category_change(
    guardian_id: UUID,
    request_id: UUID,
    approval_data: ApproveCategoryChangeRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Approve or reject a category change request"""
    service = GuardianService(db)
    result = await service.approve_category_change(
        guardian_id,
        user_id,
        approval_data.request_id,
        approval_data.approve,
        approval_data.admin_notes,
    )

    action = "approved" if approval_data.approve else "rejected"

    return success_response(
        data=jsonable_encoder(result),
        message=f"Category change request {action} successfully",
    )


@router.post("/request-category-update", status_code=status.HTTP_200_OK)
async def update_student_category(
    request_data: CategoryChangeRequest,
    db=Depends(get_db),
    current_user_id=Depends(get_current_user_id),
):
    """
    Student endpoint: Updates category directly if no guardian exists,
    otherwise creates a pending request.
    """
    service = GuardianService(db)
    result = await service.request_category_change_student(
        student_id=request_data.ward_id, request_data=request_data
    )

    return success_response(data=jsonable_encoder(result), message=result["message"])


@router.get("/latest-category-change/{ward_id}", status_code=status.HTTP_200_OK)
async def get_latest_category_change(
    ward_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),  # Validates the requester
):
    """Get only the most recent category change request for a specific ward"""
    service = GuardianService(db)
    result = await service.get_latest_ward_category_request(ward_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Latest category change request retrieved successfully",
    )


# ============= Reports & Analytics =============


@router.get("/{guardian_id}/wards/{ward_id}/report", status_code=status.HTTP_200_OK)
async def get_ward_performance_report(
    guardian_id: UUID,
    ward_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get performance report for a specific ward"""
    service = GuardianService(db)
    result = await service.get_ward_performance_report(guardian_id, user_id, ward_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Ward performance report retrieved successfully",
    )


@router.get("/{guardian_id}/wards/{ward_id}/stats", status_code=status.HTTP_200_OK)
async def get_ward_detailed_stats(
    guardian_id: UUID,
    ward_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get detailed performance statistics for a ward (tests, exams, charts, history)"""
    service = GuardianService(db)
    result = await service.get_ward_detailed_stats(guardian_id, user_id, ward_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Ward statistics retrieved successfully",
    )


@router.get("/{guardian_id}/comprehensive-report", status_code=status.HTTP_200_OK)
async def get_comprehensive_report(
    guardian_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get comprehensive report for all wards"""
    service = GuardianService(db)
    result = await service.get_comprehensive_report(guardian_id, user_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Comprehensive report retrieved successfully",
    )


# ============= Assessment Creation & Assignment =============


@router.post(
    "/{guardian_id}/assessments",
    status_code=status.HTTP_201_CREATED,
    responses={**ACCESS_RESPONSES},
)
async def create_and_assign_assessment(
    guardian_id: UUID,
    request_data: CreateAssessmentForWardsRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
    access: AccessResult = Depends(
        RequireAccess(
            resource="test",
            feature="unlimited_tests",
            feature_only=True,
            auto_charge=False,
        )
    ),
):
    """Create auto-generated assessment and assign to wards"""
    service = ChallengeAssessmentService(db)
    result = await service.create_and_assign_assessment(
        guardian_id, user_id, request_data
    )

    return success_response(
        data=jsonable_encoder(result),
        message="Assessment created and assigned successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/{guardian_id}/assignments", status_code=status.HTTP_200_OK)
async def get_ward_assignments(
    guardian_id: UUID,
    ward_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get assessment assignments for guardian's wards"""

    status_enum = None
    if status_filter:
        try:
            status_enum = AssignmentStatus(status_filter)
        except ValueError:
            pass

    service = GuardianService(db)
    result = await service.get_ward_assignments(
        guardian_id, user_id, ward_id, status_enum, skip, limit
    )

    return success_response(
        data=jsonable_encoder(result),
        message="Assignments retrieved successfully",
    )


@router.get("/assignments/{assignment_id}", status_code=status.HTTP_200_OK)
async def get_assignment_detail(
    assignment_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    from fastapi import HTTPException

    """Get detailed assignment information including attempts"""
    try:
        service = ChallengeAssessmentService(db)

        result = await service.get_assignment_detail_for_guardian(
            assignment_id=assignment_id,
            user_id=user_id,
        )

        return success_response(
            data=jsonable_encoder(result),
            message="Assignment details retrieved successfully",
        )
    except Exception as e:
        print(f"Error fetching assignment {assignment_id}: {e}")
        # Optional: raise an HTTPException so client gets a proper 500 response
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while fetching assignment {assignment_id}",
        )


@router.get("/{guardian_id}/subscription", status_code=status.HTTP_200_OK)
async def get_guardian_subscription(
    guardian_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get subscription details for guardian"""
    from src.domains.payment.services.subscription_service import SubscriptionService

    service = SubscriptionService(db)
    result = await service.get_user_subscriptions(user_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Subscription details retrieved successfully",
    )


@router.get("/{guardian_id}/subscription/limits", status_code=status.HTTP_200_OK)
async def check_subscription_limits(
    guardian_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Check subscription limits for wards"""
    from src.domains.payment.services.subscription_service import SubscriptionService

    service = SubscriptionService(db)

    # Check ward limit
    can_add_ward, ward_message = await service.check_usage_limit(user_id, "wards")

    # Check assessment creation limit
    can_create_assessment, assessment_message = await service.check_usage_limit(
        user_id, "assessments"
    )

    return success_response(
        data={
            "can_add_ward": can_add_ward,
            "ward_limit_message": ward_message,
            "can_create_assessment": can_create_assessment,
            "assessment_limit_message": assessment_message,
        },
        message="Subscription limits checked successfully",
    )
