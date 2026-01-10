from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import timezone
from src.shared.repositories.base import BaseRepository
from src.domains.payment.models.subscription_plan import (
    SubscriptionPlanConfig,
    SubscriptionPlanFeature,
    SubscriptionPromotion,
)
from src.domains.payment.enums import SubscriptionType


class PlanConfigRepository(BaseRepository[SubscriptionPlanConfig, dict, dict]):
    """Repository for managing subscription plan configurations"""

    def __init__(self, db: Session):
        super().__init__(SubscriptionPlanConfig, db)

    def get_by_plan_code(self, plan_code: str) -> Optional[SubscriptionPlanConfig]:
        """Get plan by plan code"""
        return (
            self.db.query(SubscriptionPlanConfig)
            .filter(
                SubscriptionPlanConfig.plan_code == plan_code.lower(),
                SubscriptionPlanConfig.is_deleted.is_(False),
            )
            .first()
        )

    def get_active_plans(self) -> List[SubscriptionPlanConfig]:
        """Get all active plans"""
        return (
            self.db.query(SubscriptionPlanConfig)
            .filter(
                SubscriptionPlanConfig.is_active.is_(True),
                SubscriptionPlanConfig.is_deleted.is_(False),
            )
            .order_by(SubscriptionPlanConfig.display_order)
            .all()
        )

    def get_visible_plans(
        self,
        for_individuals: bool = False,
        for_guardians: bool = False,
        for_institutions: bool = False,
    ) -> List[SubscriptionPlanConfig]:
        """Get visible plans based on user type"""
        query = self.db.query(SubscriptionPlanConfig).filter(
            SubscriptionPlanConfig.is_active.is_(True),
            SubscriptionPlanConfig.is_visible.is_(True),
            SubscriptionPlanConfig.is_deleted.is_(False),
        )

        conditions = []
        if for_individuals:
            conditions.append(SubscriptionPlanConfig.show_for_individuals.is_(True))
        if for_guardians:
            conditions.append(SubscriptionPlanConfig.show_for_guardians.is_(True))
        if for_institutions:
            conditions.append(SubscriptionPlanConfig.show_for_institutions.is_(True))

        if conditions:
            query = query.filter(or_(*conditions))

        return query.order_by(SubscriptionPlanConfig.display_order).all()

    def get_featured_plans(self) -> List[SubscriptionPlanConfig]:
        """Get featured plans"""
        return (
            self.db.query(SubscriptionPlanConfig)
            .filter(
                SubscriptionPlanConfig.is_active.is_(True),
                SubscriptionPlanConfig.is_featured.is_(True),
                SubscriptionPlanConfig.is_visible.is_(True),
                SubscriptionPlanConfig.is_deleted.is_(False),
            )
            .order_by(SubscriptionPlanConfig.display_order)
            .all()
        )

    def get_by_subscription_type(
        self, subscription_type: SubscriptionType
    ) -> List[SubscriptionPlanConfig]:
        """Get plans by subscription type"""
        return (
            self.db.query(SubscriptionPlanConfig)
            .filter(
                SubscriptionPlanConfig.subscription_type == subscription_type,
                SubscriptionPlanConfig.is_active.is_(True),
                SubscriptionPlanConfig.is_deleted.is_(False),
            )
            .order_by(SubscriptionPlanConfig.display_order)
            .all()
        )


class PlanFeatureRepository(BaseRepository[SubscriptionPlanFeature, dict, dict]):
    """Repository for managing plan features"""

    def __init__(self, db: Session):
        super().__init__(SubscriptionPlanFeature, db)

    def get_by_feature_code(
        self, feature_code: str
    ) -> Optional[SubscriptionPlanFeature]:
        """Get feature by code"""
        return (
            self.db.query(SubscriptionPlanFeature)
            .filter(
                SubscriptionPlanFeature.feature_code == feature_code.lower(),
                SubscriptionPlanFeature.is_deleted.is_(False),
            )
            .first()
        )

    def get_active_features(self) -> List[SubscriptionPlanFeature]:
        """Get all active features"""
        return (
            self.db.query(SubscriptionPlanFeature)
            .filter(
                SubscriptionPlanFeature.is_active.is_(True),
                SubscriptionPlanFeature.is_deleted.is_(False),
            )
            .order_by(SubscriptionPlanFeature.display_order)
            .all()
        )

    def get_by_category(self, category: str) -> List[SubscriptionPlanFeature]:
        """Get features by category"""
        return (
            self.db.query(SubscriptionPlanFeature)
            .filter(
                SubscriptionPlanFeature.category == category,
                SubscriptionPlanFeature.is_active.is_(True),
                SubscriptionPlanFeature.is_deleted.is_(False),
            )
            .order_by(SubscriptionPlanFeature.display_order)
            .all()
        )


class PromotionRepository(BaseRepository[SubscriptionPromotion, dict, dict]):
    """Repository for managing promotions"""

    def __init__(self, db: Session):
        super().__init__(SubscriptionPromotion, db)

    def get_by_promo_code(self, promo_code: str) -> Optional[SubscriptionPromotion]:
        """Get promotion by code"""
        return (
            self.db.query(SubscriptionPromotion)
            .filter(
                SubscriptionPromotion.promo_code == promo_code.upper(),
                SubscriptionPromotion.is_deleted.is_(False),
            )
            .first()
        )

    def get_active_promotions(self) -> List[SubscriptionPromotion]:
        """Get all currently active promotions"""
        from datetime import datetime

        now = datetime.now(timezone.utc).isoformat()

        return (
            self.db.query(SubscriptionPromotion)
            .filter(
                # SubscriptionPromotion.is_active.is_(True),
                SubscriptionPromotion.start_date <= now,
                or_(
                    SubscriptionPromotion.end_date.is_(None),
                    SubscriptionPromotion.end_date >= now,
                ),
                SubscriptionPromotion.is_deleted.is_(False),
            )
            .order_by(SubscriptionPromotion.is_active.desc())
            .all()
        )

    def get_promotions_for_plan(self, plan_code: str) -> List[SubscriptionPromotion]:
        """Get active promotions applicable to a specific plan"""
        from datetime import datetime

        now = datetime.now(timezone.utc).isoformat()

        return (
            self.db.query(SubscriptionPromotion)
            .filter(
                SubscriptionPromotion.is_active.is_(True),
                SubscriptionPromotion.start_date <= now,
                or_(
                    SubscriptionPromotion.end_date.is_(None),
                    SubscriptionPromotion.end_date >= now,
                ),
                or_(
                    SubscriptionPromotion.applicable_plan_codes.is_(None),
                    SubscriptionPromotion.applicable_plan_codes.contains([plan_code]),
                ),
                SubscriptionPromotion.is_deleted.is_(False),
            )
            .all()
        )

    def increment_usage(self, promotion_id: UUID) -> bool:
        """Increment promotion usage counter"""
        promotion = self.get_by_id(promotion_id)
        if not promotion:
            return False

        self.update(promotion_id, {"current_uses": promotion.current_uses + 1})
        return True
