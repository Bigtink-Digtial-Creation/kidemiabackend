from fastapi import APIRouter, Depends, status
from uuid import UUID
from typing import List
from fastapi.encoders import jsonable_encoder
from src.core.security import get_db, get_current_user, require_permissions
from src.domains.payment.services.plan_management_service import PlanManagementService
from src.domains.payment.schemas.plan import (
    PlanConfigResponse,
    PlanConfigCreate,
    PlanConfigUpdate,
    PlanFeatureCreate,
    PlanFeatureResponse,
    PromotionCreate,
    PromotionResponse,
    ApplyPromotionRequest,
    PublicPlanDisplay,
)
from src.shared.response import success_response

admin_router = APIRouter(
    prefix="/admin/manage/subscription-plans", tags=["Admin - Plans"]
)


@admin_router.post(
    "", response_model=PlanConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_plan(
    plan_data: PlanConfigCreate,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """
    Create a new subscription plan.
    Only accessible by admin users.
    """
    service = PlanManagementService(db)
    result = await service.create_plan(plan_data, admin_user.id)
    return result


@admin_router.get(
    "", response_model=List[PlanConfigResponse], status_code=status.HTTP_200_OK
)
async def get_all_plans_admin(
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """
    Get all plans (including inactive ones).
    Admin view with full details.
    """
    service = PlanManagementService(db)
    result = await service.get_all_plans(admin_view=True)
    return result


@admin_router.get(
    "/plan/{plan_id}", response_model=PlanConfigResponse, status_code=status.HTTP_200_OK
)
async def get_plan_by_id(
    plan_id: UUID,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """Get plan details by ID"""
    service = PlanManagementService(db)
    result = await service.get_plan_by_id(plan_id)
    return result


@admin_router.put(
    "/plan/{plan_id}", response_model=PlanConfigResponse, status_code=status.HTTP_200_OK
)
async def update_plan(
    plan_id: UUID,
    plan_data: PlanConfigUpdate,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """Update an existing plan"""
    service = PlanManagementService(db)
    result = await service.update_plan(plan_id, plan_data, admin_user.id)
    return PlanConfigResponse.model_validate(result)


@admin_router.delete("/plan/{plan_id}", status_code=status.HTTP_200_OK)
async def delete_plan(
    plan_id: UUID,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:delete")),
    admin_user=Depends(get_current_user),
):
    """Soft delete a plan (deactivates it)"""
    service = PlanManagementService(db)
    await service.delete_plan(plan_id, admin_user.id)
    return success_response(
        data={"deleted": True},
        message="Plan deactivated successfully",
    )


#  FEATURE MANAGEMENT


@admin_router.post(
    "/features/create",
    response_model=PlanFeatureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feature(
    feature_data: PlanFeatureCreate,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """Create a new reusable feature"""
    service = PlanManagementService(db)
    result = await service.create_feature(feature_data, admin_user.id)
    return result


@admin_router.get(
    "/features",
    response_model=List[PlanFeatureResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_features(
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """Get all available features"""
    service = PlanManagementService(db)
    features = await service.get_all_features()
    return features


#  PROMOTION MANAGEMENT
@admin_router.post(
    "/promotions", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED
)
async def create_promotion(
    promo_data: PromotionCreate,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """Create a new promotion/discount code"""
    service = PlanManagementService(db)
    promotion = await service.create_promotion(promo_data, admin_user.id)
    return promotion


@admin_router.get(
    "/promotions",
    response_model=List[PromotionResponse],
    status_code=status.HTTP_200_OK,
)
async def get_active_promotions(
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """Get all active promotions"""
    service = PlanManagementService(db)
    promotions = await service.get_active_promotions()
    return promotions


@admin_router.put(
    "/promotions/{promotion_id}",
    response_model=PromotionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_promotion(
    promotion_id: UUID,
    promo_data: PromotionCreate,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """
    Update an existing promotion code
    """
    service = PlanManagementService(db)
    promotion = await service.update_promotion(promotion_id, promo_data, admin_user.id)
    return promotion


@admin_router.patch(
    "/promotions/{promotion_id}/toggle",
    response_model=PromotionResponse,
    status_code=status.HTTP_200_OK,
)
async def toggle_promotion_status(
    promotion_id: UUID,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:create")),
    admin_user=Depends(get_current_user),
):
    """
    Enable or disable a promotion code
    """
    service = PlanManagementService(db)
    promotion = await service.toggle_promotion_status(promotion_id, admin_user.id)
    return promotion


@admin_router.delete(
    "/promotions/{promotion_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_promotion(
    promotion_id: UUID,
    db=Depends(get_db),
    _: None = Depends(require_permissions("content:delete")),
    admin_user=Depends(get_current_user),
):
    """
    Soft delete a promotion code
    """
    service = PlanManagementService(db)
    await service.delete_promotion(promotion_id, admin_user.id)

    return success_response(
        data={"deleted": True},
        message="Promotion deleted successfully",
    )


#  PUBLIC ROUTES (No Auth Required)

public_router = APIRouter(prefix="/subscription-plans", tags=["Subscription Plans"])


@public_router.get(
    "/pricing", response_model=List[PublicPlanDisplay], status_code=status.HTTP_200_OK
)
async def get_pricing_plans(
    for_individuals: bool = False,
    for_guardians: bool = False,
    for_institutions: bool = False,
    db=Depends(get_db),
):
    """
    Get subscription plans for public display on pricing page.

    Query params:
    - for_individuals: Show plans suitable for individual students
    - for_guardians: Show plans suitable for guardians/parents
    - for_institutions: Show plans suitable for schools/institutions
    """
    service = PlanManagementService(db)
    result = await service.get_public_plans(
        for_individuals=for_individuals,
        for_guardians=for_guardians,
        for_institutions=for_institutions,
    )
    return [PublicPlanDisplay.model_validate(plan) for plan in result]


@public_router.get(
    "/{plan_code}", response_model=PublicPlanDisplay, status_code=status.HTTP_200_OK
)
async def get_plan_details(
    plan_code: str,
    db=Depends(get_db),
):
    """Get detailed information about a specific plan"""
    service = PlanManagementService(db)
    plan = await service.get_plan_by_code(plan_code)
    return plan


@public_router.post("/promotions/validate", status_code=status.HTTP_200_OK)
async def validate_promotion(
    promo_request: ApplyPromotionRequest,
    db=Depends(get_db),
):
    """
    Validate a promotion code and calculate discount.
    Requires authentication to prevent abuse.
    """
    service = PlanManagementService(db)
    result = await service.validate_and_apply_promotion(promo_request)
    return success_response(
        data=jsonable_encoder(result),
        message="Promotion validated" if result.is_valid else "Invalid promotion",
    )


# INTEGRATION HELPER
@public_router.get("/compare/plans", status_code=status.HTTP_200_OK)
async def compare_plans(
    plan_codes: str,  # Comma-separated plan codes
    db=Depends(get_db),
):
    """
    Compare multiple plans side by side.

    Example: /compare/plans?plan_codes=student,family,institution
    """
    service = PlanManagementService(db)
    codes = [code.strip() for code in plan_codes.split(",")]

    plans = []
    for code in codes:
        try:
            plan = await service.get_plan_by_code(code)
            plans.append(plan)
        except Exception:
            continue

    return plans
