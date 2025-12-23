from typing import Optional, Callable
from functools import wraps
from decimal import Decimal

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from src.domains.payment.repositories.subscription_repository import (
    SubscriptionMemberRepository,
)
from src.domains.payment.services.subscription_service import SubscriptionService
from src.domains.access_control.core import AccessControl


def resolve_current_user(kwargs):
    for key in ("current_user", "user", "auth_user"):
        if key in kwargs:
            return kwargs[key]
    raise HTTPException(
        status_code=500,
        detail="Authenticated user not found in route dependencies",
    )


def resolve_db(kwargs):
    for key in ("db", "async_db"):
        if key in kwargs:
            return kwargs[key]

    raise HTTPException(
        status_code=500,
        detail="Database session not found in route dependencies",
    )


class AccessControlDecorators:
    """
    Elegant decorators for protecting routes with access control.
    Usage is clean and expressive.
    """

    @staticmethod
    def require_access(
        resource: str,
        feature: Optional[str] = None,
        wallet_cost: Optional[Decimal] = None,
        activity_type: Optional[str] = None,
        auto_charge: bool = True,
    ):
        """
        Decorator to require access to a resource.

        Example:
            @require_access("test", feature="unlimited_tests", wallet_cost=Decimal("50"), activity_type="test")
            async def take_test(test_id: UUID, ...):
                # User has access via subscription or wallet
                pass
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract dependencies from kwargs
                request: Request = kwargs.get("request")
                db: Session = resolve_db(kwargs)
                current_user = resolve_current_user(kwargs)

                if not all([db, current_user]):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Missing required dependencies",
                    )

                # Check access
                access_control = AccessControl(db)
                access_result = await access_control.check_access(
                    user_id=current_user.id,
                    resource=resource,
                    required_feature=feature,
                    wallet_cost=wallet_cost,
                    activity_type=activity_type,
                )

                if not access_result.allowed:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail={
                            "message": access_result.reason,
                            "suggestion": access_result.upgrade_suggestion,
                            "access_details": access_result.to_dict(),
                        },
                    )

                # Store access result in request state for the handler to use
                if request:
                    request.state.access_result = access_result

                # Auto-charge if enabled
                if auto_charge:
                    # Get activity_id from function kwargs if available
                    activity_id = (
                        kwargs.get("test_id")
                        or kwargs.get("exam_id")
                        or kwargs.get("id")
                    )

                    charged = await access_control.grant_access_and_charge(
                        user_id=current_user.id,
                        access_result=access_result,
                        activity_type=activity_type or resource,
                        activity_id=activity_id,
                    )

                    if not charged:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to process payment",
                        )

                # Call the actual function
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def require_feature(feature: str):
        """
        Simpler decorator - just check if user has a feature.
        No wallet fallback.

        Example:
            @require_feature("priority_support")
            async def get_priority_support(...):
                pass
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                db: Session = kwargs.get("db")
                current_user = kwargs.get("current_user")

                if not all([db, current_user]):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Missing required dependencies",
                    )

                subscription_service = SubscriptionService(db)
                has_access, message = await subscription_service.check_feature_access(
                    current_user.id, feature
                )

                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "message": message,
                            "feature": feature,
                            "suggestion": "Upgrade your plan to access this feature",
                        },
                    )

                return await func(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def require_subscription(plan_codes: Optional[list[str]] = None):
        """
        Require active subscription, optionally from specific plans.

        Example:
            @require_subscription(["family", "institution"])
            async def bulk_operations(...):
                pass
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                db: Session = kwargs.get("db")
                current_user = kwargs.get("current_user")

                if not all([db, current_user]):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Missing required dependencies",
                    )

                member_repo = SubscriptionMemberRepository(db)
                membership = member_repo.get_user_active_membership(current_user.id)

                if not membership or not membership.subscription.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail={
                            "message": "Active subscription required",
                            "suggestion": "Subscribe to access this feature",
                        },
                    )

                # Check plan if specified
                if plan_codes:
                    if membership.subscription.plan_code not in plan_codes:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail={
                                "message": f"This feature requires {' or '.join(plan_codes)} plan",
                                "current_plan": membership.subscription.plan_code,
                            },
                        )

                return await func(*args, **kwargs)

            return wrapper

        return decorator


require_access = AccessControlDecorators.require_access
require_feature = AccessControlDecorators.require_feature
require_subscription = AccessControlDecorators.require_subscription
