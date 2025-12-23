"""
FastAPI Middleware for automatic access control context injection.
Makes subscription and wallet info available in every request.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
from uuid import UUID

from src.domains.payment.repositories.subscription_repository import (
    SubscriptionMemberRepository,
)
from src.domains.payment.services.wallet_service import WalletService
from sqlalchemy.ext.asyncio import AsyncSession


class AccessContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that injects access context into every request.
    Makes subscription and wallet info easily accessible without repeated queries.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip for non-authenticated routes
        if not hasattr(request.state, "user") or not request.state.user:
            return await call_next(request)

        user_id = request.state.user.id
        db = request.state.db

        # Fetch subscription context
        subscription_context = await self._get_subscription_context(user_id, db)
        request.state.subscription = subscription_context

        # Fetch wallet context
        wallet_context = await self._get_wallet_context(user_id, db)
        request.state.wallet = wallet_context

        # Combine into unified access context
        request.state.access = AccessContext(
            subscription=subscription_context,
            wallet=wallet_context,
        )

        response = await call_next(request)
        return response

    async def _get_subscription_context(
        self, user_id: UUID, db
    ) -> Optional["SubscriptionContext"]:
        """Get user's subscription context"""
        try:
            member_repo = SubscriptionMemberRepository(db)
            membership = member_repo.get_user_active_membership(user_id)

            if not membership:
                return None

            subscription = membership.subscription

            return SubscriptionContext(
                active=subscription.is_active,
                subscription_id=subscription.id,
                plan_code=subscription.plan_code,
                subscription_type=subscription.subscription_type,
                features=subscription.features or {},
                limits=subscription.limits or {},
                member_role=membership.role.value,
                tests_taken=membership.tests_taken,
                exams_taken=membership.exams_taken,
                days_remaining=subscription.days_remaining,
                max_members=subscription.max_members,
                current_members=subscription.current_members,
                is_owner=membership.role.value == "owner",
            )
        except Exception as e:
            # Log error but don't break the request
            print(f"Error fetching subscription context: {e}")
            return None

    async def _get_wallet_context(self, user_id: UUID, db) -> Optional["WalletContext"]:
        """Get user's wallet context"""
        try:
            db = AsyncSession
            wallet_service = WalletService(db)
            wallet = await wallet_service.get_wallet(user_id)

            if not wallet:
                return None

            return WalletContext(
                balance=wallet.balance,
                currency=wallet.currency,
                is_active=wallet.is_active,
            )
        except Exception as e:
            print(f"Error fetching wallet context: {e}")
            return None


class SubscriptionContext:
    """Subscription context available in request.state"""

    def __init__(
        self,
        active: bool,
        subscription_id: UUID,
        plan_code: str,
        subscription_type: str,
        features: dict,
        limits: dict,
        member_role: str,
        tests_taken: int,
        exams_taken: int,
        days_remaining: int,
        max_members: Optional[int],
        current_members: int,
        is_owner: bool,
    ):
        self.active = active
        self.subscription_id = subscription_id
        self.plan_code = plan_code
        self.subscription_type = subscription_type
        self.features = features
        self.limits = limits
        self.member_role = member_role
        self.tests_taken = tests_taken
        self.exams_taken = exams_taken
        self.days_remaining = days_remaining
        self.max_members = max_members
        self.current_members = current_members
        self.is_owner = is_owner

    def has_feature(self, feature: str) -> bool:
        """Check if subscription has a feature"""
        return self.features.get(feature, False)

    def within_limit(self, activity_type: str) -> bool:
        """Check if within usage limits"""
        limit_key = f"{activity_type}_per_month"
        limit = self.limits.get(limit_key)

        if not limit:  # Unlimited
            return True

        current = getattr(self, f"{activity_type}_taken", 0)
        return current < limit

    def get_usage_percentage(self, activity_type: str) -> Optional[float]:
        """Get usage percentage for an activity"""
        limit_key = f"{activity_type}_per_month"
        limit = self.limits.get(limit_key)

        if not limit:
            return None  # Unlimited

        current = getattr(self, f"{activity_type}_taken", 0)
        return (current / limit) * 100


class WalletContext:
    """Wallet context available in request.state"""

    def __init__(self, balance: float, currency: str, is_active: bool):
        self.balance = balance
        self.currency = currency
        self.is_active = is_active

    def can_afford(self, amount: float) -> bool:
        """Check if wallet can afford an amount"""
        return self.is_active and self.balance >= amount


class AccessContext:
    """Unified access context combining subscription and wallet"""

    def __init__(
        self,
        subscription: Optional[SubscriptionContext],
        wallet: Optional[WalletContext],
    ):
        self.subscription = subscription
        self.wallet = wallet

    @property
    def has_subscription(self) -> bool:
        """Check if user has active subscription"""
        return self.subscription is not None and self.subscription.active

    @property
    def has_wallet(self) -> bool:
        """Check if user has active wallet"""
        return self.wallet is not None and self.wallet.is_active

    def can_access(
        self,
        feature: Optional[str] = None,
        cost: Optional[float] = None,
    ) -> bool:
        """
        Quick check if user can access something via subscription or wallet.
        For full access check with logging, use AccessControl.check_access()
        """
        # Check subscription access
        if feature and self.has_subscription:
            if self.subscription.has_feature(feature):
                return True

        # Check wallet access
        if cost and self.has_wallet:
            if self.wallet.can_afford(cost):
                return True

        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "subscription": {
                "active": self.has_subscription,
                "plan_code": self.subscription.plan_code if self.subscription else None,
                "features": self.subscription.features if self.subscription else {},
                "days_remaining": self.subscription.days_remaining
                if self.subscription
                else None,
            }
            if self.subscription
            else None,
            "wallet": {
                "balance": self.wallet.balance if self.wallet else None,
                "currency": self.wallet.currency if self.wallet else None,
            }
            if self.wallet
            else None,
        }


#  DEPENDENCY INJECTION HELPER


def get_access_context(request: Request) -> AccessContext:
    """
    Dependency to inject access context into routes.
    Alternative to accessing request.state directly.
    """
    return request.state.access


def require_subscription_context(request: Request) -> SubscriptionContext:
    """
    Dependency that requires subscription context.
    Raises 402 if user doesn't have subscription.
    """
    from fastapi import HTTPException, status

    if not request.state.access.has_subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
        )

    return request.state.subscription


def require_wallet_context(request: Request) -> WalletContext:
    """
    Dependency that requires wallet context.
    Raises 400 if user doesn't have wallet.
    """
    from fastapi import HTTPException, status

    if not request.state.access.has_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet not found. Please set up your wallet first.",
        )

    return request.state.wallet
