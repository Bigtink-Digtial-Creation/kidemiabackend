from typing import List, Tuple, Dict
from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session

from src.domains.payment.repositories.plan_management_repository import (
    PlanConfigRepository,
    PlanFeatureRepository,
    PromotionRepository,
)
from src.domains.payment.schemas.plan import (
    PlanConfigCreate,
    PlanConfigUpdate,
    PlanConfigResponse,
    PublicPlanDisplay,
    PlanFeatureCreate,
    PlanFeatureResponse,
    PromotionCreate,
    PromotionResponse,
    ApplyPromotionRequest,
    PromotionCalculationResponse,
)
from src.domains.payment.enums import BillingCycle
from src.core.exceptions import (
    BusinessLogicException,
    ResourceNotFoundException,
)


class PlanManagementService:
    """Service for managing subscription plans (Admin operations)"""

    def __init__(self, db: Session):
        self.db = db
        self.plan_repo = PlanConfigRepository(db)
        self.feature_repo = PlanFeatureRepository(db)
        self.promo_repo = PromotionRepository(db)

    async def get_plan_by_id(self, plan_id: str) -> PlanConfigResponse:
        """Get plan by ID"""
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise ResourceNotFoundException("Plan", plan_id)

        return PlanConfigResponse.model_validate(plan)

    async def create_plan(
        self, plan_data: PlanConfigCreate, admin_id: UUID
    ) -> PlanConfigResponse:
        """Create a new subscription plan"""
        # Check if plan code already exists
        existing = self.plan_repo.get_by_plan_code(plan_data.plan_code)
        if existing:
            raise BusinessLogicException(
                f"Plan with code '{plan_data.plan_code}' already exists"
            )

        # Validate pricing
        if plan_data.price_yearly > plan_data.price_monthly * 12:
            raise BusinessLogicException(
                "Yearly price should not be more than 12x monthly price"
            )

        plan_dict = plan_data.model_dump()
        plan_dict["created_by"] = admin_id

        plan = self.plan_repo.create(plan_dict)
        return PlanConfigResponse.model_validate(plan)

    async def update_plan(
        self, plan_id: UUID, plan_data: PlanConfigUpdate, admin_id: UUID
    ) -> PlanConfigResponse:
        """Update an existing plan"""
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise ResourceNotFoundException("Plan", plan_id)

        update_dict = plan_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = admin_id

        self.plan_repo.update(plan_id, update_dict)
        plan = self.plan_repo.get_by_id(plan_id)

        return PlanConfigResponse.model_validate(plan)

    async def delete_plan(self, plan_id: UUID, admin_id: UUID) -> bool:
        """Soft delete a plan"""
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise ResourceNotFoundException("Plan", plan_id)

        # Check if plan has active subscriptions
        # TODO: Add check for active subscriptions using this plan
        # For now, just deactivate instead of delete
        self.plan_repo.update(
            plan_id, {"is_active": False, "is_visible": False, "updated_by": admin_id}
        )

        return True

    async def get_plan_by_code(self, plan_code: str) -> PlanConfigResponse:
        """Get plan by code"""
        plan = self.plan_repo.get_by_plan_code(plan_code)
        if not plan:
            raise ResourceNotFoundException("Plan", plan_code)

        return PlanConfigResponse.model_validate(plan)

    async def get_all_plans(self, admin_view: bool = False) -> List[PlanConfigResponse]:
        """Get all plans (admin view shows inactive too)"""
        if admin_view:
            plans = (
                self.db.query(self.plan_repo.model)
                .filter(self.plan_repo.model.is_deleted.is_(False))
                .order_by(self.plan_repo.model.display_order)
                .all()
            )
        else:
            plans = self.plan_repo.get_active_plans()

        return [PlanConfigResponse.model_validate(plan) for plan in plans]

    #  PUBLIC PLAN DISPLAY
    async def get_public_plans(
        self,
        for_individuals: bool = False,
        for_guardians: bool = False,
        for_institutions: bool = False,
    ) -> List[PublicPlanDisplay]:
        """Get plans for public display on pricing page"""
        plans = self.plan_repo.get_visible_plans(
            for_individuals=for_individuals,
            for_guardians=for_guardians,
            for_institutions=for_institutions,
        )

        return [
            PublicPlanDisplay(
                plan_code=plan.plan_code,
                plan_name=plan.plan_name,
                plan_type=plan.plan_type,
                subscription_type=plan.subscription_type,
                tagline=plan.tagline,
                short_description=plan.short_description,
                price_monthly=plan.price_monthly,
                price_yearly=plan.price_yearly,
                yearly_discount_percentage=plan.yearly_discount_percentage,
                yearly_savings=plan.yearly_savings,
                effective_monthly_price_yearly=plan.effective_monthly_price_yearly,
                max_members=plan.max_members,
                trial_days=plan.trial_days,
                features=plan.features,
                benefits_list=plan.benefits_list,
                is_featured=plan.is_featured,
                is_popular=plan.is_popular,
                currency=plan.currency,
            )
            for plan in plans
        ]

    async def get_plan_pricing(
        self, plan_code: str, billing_cycle: BillingCycle
    ) -> Tuple[Decimal, Dict]:
        """Get pricing for a specific plan and billing cycle"""
        plan = self.plan_repo.get_by_plan_code(plan_code)
        if not plan:
            raise ResourceNotFoundException("Plan", plan_code)

        if not plan.is_active:
            raise BusinessLogicException("This plan is no longer available")

        price_map = {
            BillingCycle.MONTHLY: plan.price_monthly,
            BillingCycle.QUARTERLY: plan.price_quarterly or plan.price_monthly * 3,
            BillingCycle.YEARLY: plan.price_yearly,
        }

        price = price_map.get(billing_cycle, plan.price_monthly)

        return price, {
            "plan_code": plan.plan_code,
            "plan_name": plan.plan_name,
            "price": price,
            "currency": plan.currency,
            "billing_cycle": billing_cycle.value,
            "features": plan.features,
            "limits": plan.limits,
        }

    #  FEATURE MANAGEMENT

    async def create_feature(
        self, feature_data: PlanFeatureCreate, admin_id: UUID
    ) -> PlanFeatureResponse:
        """Create a new feature"""
        existing = self.feature_repo.get_by_feature_code(feature_data.feature_code)
        if existing:
            raise BusinessLogicException(
                f"Feature '{feature_data.feature_code}' already exists"
            )

        feature_dict = feature_data.model_dump()
        feature_dict["created_by"] = admin_id

        feature = self.feature_repo.create(feature_dict)
        return PlanFeatureResponse.model_validate(feature)

    async def get_all_features(self) -> List[PlanFeatureResponse]:
        """Get all features"""
        features = self.feature_repo.get_active_features()
        return [PlanFeatureResponse.model_validate(f) for f in features]

    #  PROMOTION MANAGEMENT

    async def create_promotion(
        self, promo_data: PromotionCreate, admin_id: UUID
    ) -> PromotionResponse:
        """Create a new promotion"""
        existing = self.promo_repo.get_by_promo_code(promo_data.promo_code)
        if existing:
            raise BusinessLogicException(
                f"Promotion code '{promo_data.promo_code}' already exists"
            )

        promo_dict = promo_data.model_dump()
        promo_dict["created_by"] = admin_id

        promotion = self.promo_repo.create(promo_dict)
        return PromotionResponse.model_validate(promotion)

    async def get_active_promotions(self) -> List[PromotionResponse]:
        """Get all active promotions"""
        promotions = self.promo_repo.get_active_promotions()
        return [PromotionResponse.model_validate(p) for p in promotions]

    async def validate_and_apply_promotion(
        self, request: ApplyPromotionRequest
    ) -> PromotionCalculationResponse:
        """Validate and calculate promotion discount"""
        promotion = self.promo_repo.get_by_promo_code(request.promo_code)

        if not promotion:
            return PromotionCalculationResponse(
                promo_code=request.promo_code,
                plan_code=request.plan_code,
                original_price=Decimal("0"),
                discount_amount=Decimal("0"),
                final_price=Decimal("0"),
                is_valid=False,
                message="Invalid promotion code",
            )

        # Check if promotion is valid
        if not promotion.is_valid:
            return PromotionCalculationResponse(
                promo_code=request.promo_code,
                plan_code=request.plan_code,
                original_price=Decimal("0"),
                discount_amount=Decimal("0"),
                final_price=Decimal("0"),
                is_valid=False,
                message="Promotion is no longer valid or has expired",
            )

        # Check if promotion applies to this plan
        if (
            promotion.applicable_plan_codes
            and request.plan_code not in promotion.applicable_plan_codes
        ):
            return PromotionCalculationResponse(
                promo_code=request.promo_code,
                plan_code=request.plan_code,
                original_price=Decimal("0"),
                discount_amount=Decimal("0"),
                final_price=Decimal("0"),
                is_valid=False,
                message=f"This promotion is not valid for the {request.plan_code} plan",
            )

        # Check billing cycle requirement
        if (
            promotion.min_billing_cycle
            and request.billing_cycle.value < promotion.min_billing_cycle.value
        ):
            return PromotionCalculationResponse(
                promo_code=request.promo_code,
                plan_code=request.plan_code,
                original_price=Decimal("0"),
                discount_amount=Decimal("0"),
                final_price=Decimal("0"),
                is_valid=False,
                message=f"This promotion requires {promotion.min_billing_cycle.value} billing cycle",
            )

        # Get plan pricing
        price, _ = await self.get_plan_pricing(request.plan_code, request.billing_cycle)

        # Calculate discount
        discount_amount = Decimal("0")
        discount_percentage = None
        trial_extension_days = None

        if promotion.discount_type == "percentage":
            discount_amount = (price * promotion.discount_value) / 100
            discount_percentage = float(promotion.discount_value)
        elif promotion.discount_type == "fixed_amount":
            discount_amount = promotion.discount_value
        elif promotion.discount_type == "trial_extension":
            trial_extension_days = int(promotion.discount_value)

        final_price = max(Decimal("0"), price - discount_amount)

        return PromotionCalculationResponse(
            promo_code=request.promo_code,
            plan_code=request.plan_code,
            original_price=price,
            discount_amount=discount_amount,
            final_price=final_price,
            discount_percentage=discount_percentage,
            trial_extension_days=trial_extension_days,
            is_valid=True,
            message="Promotion applied successfully",
        )

    async def apply_promotion_to_subscription(
        self, promotion_id: UUID, subscription_id: UUID
    ) -> bool:
        """Mark promotion as used for a subscription"""
        self.promo_repo.increment_usage(promotion_id)
        return True

    #  HELPER METHODS

    def get_plan_details_for_subscription(
        self, plan_code: str, billing_cycle: BillingCycle
    ) -> dict:
        """
        Get plan details in format compatible with subscription service.
        Used when creating subscriptions based on selected plans.
        """
        plan = self.plan_repo.get_by_plan_code(plan_code)
        if not plan:
            raise ResourceNotFoundException("Plan", plan_code)

        if not plan.is_active:
            raise BusinessLogicException("This plan is no longer available")

        price_map = {
            BillingCycle.MONTHLY: plan.price_monthly,
            BillingCycle.QUARTERLY: plan.price_quarterly or plan.price_monthly * 3,
            BillingCycle.YEARLY: plan.price_yearly,
        }

        return {
            "name": plan.plan_name,
            "description": plan.description,
            "type": plan.subscription_type,
            "price": price_map.get(billing_cycle, plan.price_monthly),
            "max_members": plan.max_members,
            "features": plan.features,
            "limits": plan.limits,
            "trial_days": plan.trial_days,
        }
