from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from src.shared.repositories.base import BaseRepository
from src.domains.payment.models.subscription import (
    Subscription,
    SubscriptionMember,
    SubscriptionUsageLog,
)
from src.domains.payment.enums import SubscriptionStatus, MemberRole


class SubscriptionRepository(BaseRepository[Subscription, dict, dict]):
    """Repository for Subscription model"""

    def __init__(self, db: Session):
        super().__init__(Subscription, db)

    def get_active_subscription(self, owner_id: UUID) -> Optional[Subscription]:
        """Get active subscription owned by user"""
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.owner_id == owner_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.is_deleted.is_(False),
            )
            .first()
        )

    def get_by_plan_code(
        self, plan_code: str, active_only: bool = True
    ) -> List[Subscription]:
        """Get subscriptions by plan code"""
        query = self.db.query(Subscription).filter(
            Subscription.plan_code == plan_code,
            Subscription.is_deleted.is_(False),
        )

        if active_only:
            query = query.filter(Subscription.status == SubscriptionStatus.ACTIVE)

        return query.all()

    def get_subscription_with_members(
        self, subscription_id: UUID
    ) -> Optional[Subscription]:
        """Get subscription with all members loaded"""
        return (
            self.db.query(Subscription)
            .options(joinedload(Subscription.members))
            .filter(
                Subscription.id == subscription_id,
                Subscription.is_deleted.is_(False),
            )
            .first()
        )

    def get_user_subscriptions(
        self, user_id: UUID, include_inactive: bool = False
    ) -> List[Subscription]:
        """Get all subscriptions where user is owner or member"""
        query = self.db.query(Subscription).join(
            SubscriptionMember,
            and_(
                SubscriptionMember.subscription_id == Subscription.id,
                SubscriptionMember.user_id == user_id,
                SubscriptionMember.is_active.is_(True),
            ),
        )

        if not include_inactive:
            query = query.filter(Subscription.status == SubscriptionStatus.ACTIVE)

        query = query.filter(Subscription.is_deleted.is_(False))

        return query.all()

    def get_expiring_soon(self, days: int = 7) -> List[Subscription]:
        """Get subscriptions expiring soon"""
        cutoff_date = (datetime.utcnow() + timedelta(days=days)).isoformat()

        return (
            self.db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date <= cutoff_date,
                Subscription.auto_renew.is_(True),
                Subscription.is_deleted.is_(False),
            )
            .all()
        )

    def get_institution_subscriptions(
        self, institution_id: UUID, active_only: bool = True
    ) -> List[Subscription]:
        """Get all subscriptions for an institution"""
        query = self.db.query(Subscription).filter(
            Subscription.institution_id == institution_id,
            Subscription.is_deleted.is_(False),
        )

        if active_only:
            query = query.filter(Subscription.status == SubscriptionStatus.ACTIVE)

        return query.all()


class SubscriptionMemberRepository(BaseRepository[SubscriptionMember, dict, dict]):
    """Repository for SubscriptionMember model"""

    def __init__(self, db: Session):
        super().__init__(SubscriptionMember, db)

    def get_by_user_and_subscription(
        self, user_id: UUID, subscription_id: UUID
    ) -> Optional[SubscriptionMember]:
        """Get member record for user in subscription"""
        return (
            self.db.query(SubscriptionMember)
            .filter(
                SubscriptionMember.user_id == user_id,
                SubscriptionMember.subscription_id == subscription_id,
                SubscriptionMember.is_deleted.is_(False),
            )
            .first()
        )

    def get_active_members(self, subscription_id: UUID) -> List[SubscriptionMember]:
        """Get all active members of a subscription"""
        return (
            self.db.query(SubscriptionMember)
            .filter(
                SubscriptionMember.subscription_id == subscription_id,
                SubscriptionMember.is_active.is_(True),
                SubscriptionMember.is_deleted.is_(False),
            )
            .all()
        )

    def get_user_active_membership(self, user_id: UUID) -> Optional[SubscriptionMember]:
        """Get user's current active subscription membership"""
        return (
            self.db.query(SubscriptionMember)
            .join(Subscription)
            .filter(
                SubscriptionMember.user_id == user_id,
                SubscriptionMember.is_active.is_(True),
                Subscription.status == SubscriptionStatus.ACTIVE,
                SubscriptionMember.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
            .first()
        )

    def count_active_members(self, subscription_id: UUID) -> int:
        """Count active members in subscription"""
        return (
            self.db.query(SubscriptionMember)
            .filter(
                SubscriptionMember.subscription_id == subscription_id,
                SubscriptionMember.is_active.is_(True),
                SubscriptionMember.is_deleted.is_(False),
            )
            .count()
        )

    def get_wards_by_guardian(self, guardian_id: UUID) -> List[SubscriptionMember]:
        """Get all wards added by a guardian"""
        return (
            self.db.query(SubscriptionMember)
            .filter(
                SubscriptionMember.added_by == guardian_id,
                SubscriptionMember.role == MemberRole.WARD,
                SubscriptionMember.is_active.is_(True),
                SubscriptionMember.is_deleted.is_(False),
            )
            .all()
        )


class SubscriptionUsageLogRepository(BaseRepository[SubscriptionUsageLog, dict, dict]):
    """Repository for SubscriptionUsageLog model"""

    def __init__(self, db: Session):
        super().__init__(SubscriptionUsageLog, db)

    def log_activity(
        self,
        subscription_id: UUID,
        member_id: UUID,
        user_id: UUID,
        activity_type: str,
        activity_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> SubscriptionUsageLog:
        """Log a subscription activity"""
        log_data = {
            "subscription_id": subscription_id,
            "member_id": member_id,
            "user_id": user_id,
            "activity_type": activity_type,
            "activity_id": activity_id,
            "timestamp": datetime.utcnow().isoformat(),
            "meta_data": metadata,
            "created_by": user_id,
        }
        return self.create(log_data)

    def get_user_activity(
        self, user_id: UUID, subscription_id: Optional[UUID] = None, limit: int = 50
    ) -> List[SubscriptionUsageLog]:
        """Get user's recent activity"""
        query = self.db.query(SubscriptionUsageLog).filter(
            SubscriptionUsageLog.user_id == user_id,
            SubscriptionUsageLog.is_deleted.is_(False),
        )

        if subscription_id:
            query = query.filter(
                SubscriptionUsageLog.subscription_id == subscription_id
            )

        return query.order_by(SubscriptionUsageLog.created_at.desc()).limit(limit).all()

    def get_subscription_stats(
        self, subscription_id: UUID, start_date: Optional[datetime] = None
    ) -> dict:
        """Get usage statistics for subscription"""
        query = self.db.query(SubscriptionUsageLog).filter(
            SubscriptionUsageLog.subscription_id == subscription_id,
            SubscriptionUsageLog.is_deleted.is_(False),
        )

        if start_date:
            query = query.filter(
                SubscriptionUsageLog.timestamp >= start_date.isoformat()
            )

        logs = query.all()

        stats = {
            "total_activities": len(logs),
            "tests": sum(1 for log in logs if log.activity_type == "test"),
            "exams": sum(1 for log in logs if log.activity_type == "exam"),
            "leaderboard_access": sum(
                1 for log in logs if log.activity_type == "leaderboard"
            ),
        }

        return stats
