from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.shared.repositories.base import BaseRepository
from src.domains.payment.models.subscription import Subscription
from src.domains.payment.enums import SubscriptionStatus


class SubscriptionRepository(BaseRepository[Subscription, dict, dict]):
    """Repository for Subscription model"""

    def __init__(self, db: Session):
        super().__init__(Subscription, db)

    def get_active_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """Get active subscription for user"""
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.is_deleted.is_(False),
            )
            .first()
        )

    def get_expiring_soon(self, days: int = 7) -> List[Subscription]:
        """Get subscriptions expiring soon"""
        from datetime import datetime, timedelta

        cutoff_date = (datetime.utcnow() + timedelta(days=days)).isoformat()

        return (
            self.db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date <= cutoff_date,
                Subscription.is_deleted.is_(False),
            )
            .all()
        )
