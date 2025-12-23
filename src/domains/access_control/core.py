"""
Elegant Access Control System
Combines subscription features with wallet balance for flexible access control
Intelligently handles sync/async session requirements
"""

from typing import Optional, Union
from uuid import UUID
from decimal import Decimal
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import AsyncSessionLocal

from src.domains.payment.repositories.subscription_repository import (
    SubscriptionMemberRepository,
)
from src.domains.payment.services.subscription_service import SubscriptionService
from src.domains.access_control.enum import AccessMethod


class AccessResult:
    """Result of access check with detailed context"""

    def __init__(
        self,
        allowed: bool,
        method: Optional[AccessMethod] = None,
        subscription_id: Optional[UUID] = None,
        wallet_balance: Optional[Decimal] = None,
        cost: Optional[Decimal] = None,
        reason: Optional[str] = None,
        upgrade_suggestion: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.allowed = allowed
        self.method = method
        self.subscription_id = subscription_id
        self.wallet_balance = wallet_balance
        self.cost = cost
        self.reason = reason
        self.upgrade_suggestion = upgrade_suggestion
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "allowed": self.allowed,
            "method": self.method.value if self.method else None,
            "subscription_id": str(self.subscription_id)
            if self.subscription_id
            else None,
            "wallet_balance": float(self.wallet_balance)
            if self.wallet_balance
            else None,
            "cost": float(self.cost) if self.cost else None,
            "reason": self.reason,
            "upgrade_suggestion": self.upgrade_suggestion,
            **self.metadata,
        }

    @property
    def is_subscription_access(self) -> bool:
        return self.method == AccessMethod.SUBSCRIPTION

    @property
    def is_wallet_access(self) -> bool:
        return self.method == AccessMethod.WALLET


class AccessControl:
    """
    Unified access control system combining subscriptions and wallet balance.

    Intelligently handles mixed sync/async requirements:
    - Accepts either sync or async session
    - Automatically creates async session for wallet operations when needed
    - Cleans up created resources properly
    """

    def __init__(self, db: Union[Session, AsyncSession]):
        self.db = db
        self.is_async_db = isinstance(db, AsyncSession)
        self.subscription_service = SubscriptionService(db)
        self.member_repo = SubscriptionMemberRepository(db)
        self._owned_async_session = None

    @asynccontextmanager
    async def _get_async_session(self):
        """
        this Context manager provides an async session for wallet operations.
        It intelligently reuses existing async session or creates a temporary one.

        [Samuel Kufre Willie - 2025-12-22]
        """
        if self.is_async_db:
            yield self.db
        else:
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

    async def check_access(
        self,
        user_id: UUID,
        resource: str,
        required_feature: Optional[str] = None,
        wallet_cost: Optional[Decimal] = None,
        activity_type: Optional[str] = None,
    ) -> AccessResult:
        """
        Unified access check - tries subscription first, falls back to wallet.

        Args:
            user_id: User requesting access
            resource: Resource being accessed (e.g., "test", "exam", "leaderboard")
            required_feature: Feature required from subscription (e.g., "unlimited_tests")
            wallet_cost: Cost in tokens if using wallet
            activity_type: Type of activity for usage tracking

        Returns:
            AccessResult with detailed context
        """
        # 1. Check subscription access first (preferred method)
        subscription_result = await self._check_subscription_access(
            user_id, required_feature, activity_type
        )

        if subscription_result.allowed:
            return subscription_result

        # 2. Fall back to wallet if available
        if wallet_cost:
            wallet_result = await self._check_wallet_access(
                user_id, wallet_cost, resource
            )
            if wallet_result.allowed:
                return wallet_result

        # 3. Neither method worked - return denial with suggestions
        return self._create_denial_result(subscription_result, wallet_cost, resource)

    async def _check_subscription_access(
        self,
        user_id: UUID,
        required_feature: Optional[str],
        activity_type: Optional[str],
    ) -> AccessResult:
        """Check if user has subscription access"""
        # Get user's active membership
        membership = self.member_repo.get_user_active_membership(user_id)

        if not membership:
            return AccessResult(
                allowed=False,
                reason="No active subscription",
                upgrade_suggestion="Subscribe to get unlimited access",
            )

        subscription = membership.subscription

        # Check if subscription is active
        if not subscription.is_active:
            return AccessResult(
                allowed=False,
                reason="Subscription expired",
                upgrade_suggestion="Renew your subscription to continue",
            )

        # Check required feature if specified
        if required_feature:
            features = subscription.features or {}
            if not features.get(required_feature):
                return AccessResult(
                    allowed=False,
                    subscription_id=subscription.id,
                    reason=f"Feature '{required_feature}' not included in your plan",
                    upgrade_suggestion=f"Upgrade to access {required_feature}",
                )

        # Check usage limits if activity type specified
        if activity_type:
            (
                within_limit,
                limit_message,
            ) = await self.subscription_service.check_usage_limit(
                user_id, activity_type
            )
            if not within_limit:
                return AccessResult(
                    allowed=False,
                    subscription_id=subscription.id,
                    reason=limit_message,
                    upgrade_suggestion="Upgrade to a higher plan for more usage",
                )

        # All checks passed - grant access
        return AccessResult(
            allowed=True,
            method=AccessMethod.SUBSCRIPTION,
            subscription_id=subscription.id,
            metadata={
                "plan_code": subscription.plan_code,
                "member_role": membership.role.value,
                "tests_taken": membership.tests_taken,
                "days_remaining": subscription.days_remaining,
            },
        )

    async def _check_wallet_access(
        self,
        user_id: UUID,
        cost: Decimal,
        resource: str,
    ) -> AccessResult:
        """
        Check if user has sufficient wallet balance.
        Automatically handles async session requirement for wallet service.
        """
        from src.domains.payment.services.wallet_service import WalletService

        # Use context manager to get appropriate async session
        async with self._get_async_session() as async_session:
            wallet_service = WalletService(async_session)

            # Now we can safely await wallet operations
            wallet = await wallet_service.get_wallet(user_id)

            if not wallet:
                return AccessResult(
                    allowed=False,
                    method=AccessMethod.WALLET,
                    reason="No wallet found",
                )

            if wallet.balance < cost:
                return AccessResult(
                    allowed=False,
                    method=AccessMethod.WALLET,
                    wallet_balance=wallet.balance,
                    cost=cost,
                    reason=f"Insufficient balance. Need {cost} token, have {wallet.balance} token",
                    upgrade_suggestion="Top up your wallet or subscribe for unlimited access",
                )

            # Sufficient balance
            return AccessResult(
                allowed=True,
                method=AccessMethod.WALLET,
                wallet_balance=wallet.balance,
                cost=cost,
                metadata={
                    "balance_after": wallet.balance - cost,
                },
            )

    def _create_denial_result(
        self,
        subscription_result: AccessResult,
        wallet_cost: Optional[Decimal],
        resource: str,
    ) -> AccessResult:
        """Create a comprehensive denial result with suggestions"""
        reasons = [subscription_result.reason]

        suggestions = []
        if subscription_result.upgrade_suggestion:
            suggestions.append(subscription_result.upgrade_suggestion)

        if wallet_cost:
            suggestions.append("Topup your wallet to continue")

        return AccessResult(
            allowed=False,
            reason=" | ".join(reasons),
            upgrade_suggestion=" OR ".join(suggestions) if suggestions else None,
            metadata={
                "subscription_reason": subscription_result.reason,
                "wallet_cost": float(wallet_cost) if wallet_cost else None,
            },
        )

    async def grant_access_and_charge(
        self,
        user_id: UUID,
        access_result: AccessResult,
        activity_type: str,
        activity_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Grant access and charge accordingly (deduct from wallet or log subscription usage).
        Call this after access is confirmed to be allowed.
        """
        if not access_result.allowed:
            return False

        if access_result.is_subscription_access:
            # Log subscription usage
            await self.subscription_service.log_activity(
                user_id=user_id,
                activity_type=activity_type,
                activity_id=activity_id,
                metadata=metadata,
            )
            return True

        elif access_result.is_wallet_access:
            # Deduct from wallet - automatically handle async session
            from src.domains.payment.services.wallet_service import WalletService

            async with self._get_async_session() as async_session:
                wallet_service = WalletService(async_session)

                wallet = await wallet_service.debit_wallet(
                    user_id=user_id,
                    amount=access_result.cost,
                    description=f"Payment for {activity_type}",
                )
                return wallet

        return False
