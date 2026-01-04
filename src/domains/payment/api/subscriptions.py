from fastapi import APIRouter, Depends, status
from uuid import UUID
from fastapi.encoders import jsonable_encoder
from src.core.security import get_db, get_current_user, get_current_user_id
from src.domains.payment.services.subscription_billing_service import (
    SubscriptionBillingService,
)
from src.domains.payment.services.subscription_service import SubscriptionService
from src.domains.payment.schemas.subscription import (
    SubscriptionCreate,
    AddMemberRequest,
    RemoveMemberRequest,
    SubscriptionUpgradeRequest,
    SubscriptionCancelRequest,
)
from src.shared.response import success_response

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# NEW SUBSCRIPTION FLOW (Paystack Recurring)


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def start_subscription_checkout(
    subscription_data: SubscriptionCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Returns Paystack payment URL for redirect.
    This is the main entry point for recurring payment
    """
    billing_service = SubscriptionBillingService(db)
    result = await billing_service.start_checkout(
        user.id, user.email, subscription_data
    )

    return success_response(
        data=jsonable_encoder(result),
        message="Checkout initiated. Please complete payment.",
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/verify/{reference}", status_code=status.HTTP_200_OK)
async def verify_subscription_payment(
    reference: str,
    db=Depends(get_db),
):
    """
    Creates Paystack subscription for automatic renewals.
    """
    billing_service = SubscriptionBillingService(db)
    result = await billing_service.confirm_payment_and_activate(reference)

    return success_response(
        data=jsonable_encoder(result),
        message="Subscription activated successfully",
    )


# SUBSCRIPTION MANAGEMENT


@router.get("", status_code=status.HTTP_200_OK)
async def get_my_subscriptions(
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get all subscriptions for current user (as owner or member)"""
    service = SubscriptionService(db)
    result = await service.get_user_subscriptions(user_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Subscriptions retrieved successfully",
    )


@router.get("/{subscription_id}", status_code=status.HTTP_200_OK)
async def get_subscription(
    subscription_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get subscription details with members"""
    service = SubscriptionService(db)
    result = await service.get_subscription_with_members(subscription_id, user_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Subscription details retrieved successfully",
    )


# PAUSE/RESUME (NEW - Paystack specific)


@router.post("/{subscription_id}/pause", status_code=status.HTTP_200_OK)
async def pause_subscription(
    subscription_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """
    Pause subscription (stops future Paystack charges)
    Access continues until end of current period.
    """
    billing_service = SubscriptionBillingService(db)
    success = await billing_service.pause_subscription(subscription_id, user_id)

    return success_response(
        data={"success": success},
        message="Subscription paused. No future charges will be made.",
    )


@router.post("/{subscription_id}/resume", status_code=status.HTTP_200_OK)
async def resume_subscription(
    subscription_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Resume a paused subscription (restart Paystack charges)"""
    billing_service = SubscriptionBillingService(db)
    success = await billing_service.resume_subscription(subscription_id, user_id)

    return success_response(
        data={"success": success},
        message="Subscription resumed successfully",
    )


# CANCELLATION (Enhanced for Paystack)


@router.post("/{subscription_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_subscription(
    subscription_id: UUID,
    cancel_data: SubscriptionCancelRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """
    Cancel subscription (stops Paystack recurring charges).

    If cancel_immediately=False: Access continues until end of current period
    If cancel_immediately=True: Access ends immediately
    """
    billing_service = SubscriptionBillingService(db)

    # Cancel on Paystack (stops future charges)
    success = await billing_service.cancel_subscription(
        subscription_id, user_id, cancel_data.reason
    )

    # If immediate cancellation, also deactivate now
    if cancel_data.cancel_immediately:
        service = SubscriptionService(db)
        await service.cancel_subscription(
            subscription_id,
            user_id,
            cancel_data.reason,
            cancel_immediately=True,
        )

    return success_response(
        data={"success": success},
        message="Subscription cancelled successfully. "
        + (
            "Access ends immediately."
            if cancel_data.cancel_immediately
            else "Access continues until end of current period."
        ),
    )


@router.post("/{subscription_id}/upgrade", status_code=status.HTTP_200_OK)
async def upgrade_subscription(
    subscription_id: UUID,
    upgrade_data: SubscriptionUpgradeRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """
    Upgrade or downgrade subscription with proration.

    This will:
    1. Calculate prorated amount
    2. Charge difference (if upgrade) or credit (if downgrade)
    3. Update Paystack subscription plan
    4. Update internal subscription
    """
    billing_service = SubscriptionBillingService(db)
    result = await billing_service.upgrade_subscription(
        subscription_id, user_id, upgrade_data
    )

    return success_response(
        data=jsonable_encoder(result),
        message="Subscription updated successfully",
    )


@router.post("/{subscription_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    subscription_id: UUID,
    member_data: AddMemberRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """
    Add a member (ward/student) to subscription.
    Only subscription owner can add members.
    """
    service = SubscriptionService(db)
    result = await service.add_member(subscription_id, user_id, member_data)

    return success_response(
        data=jsonable_encoder(result),
        message="Member added successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.delete("/{subscription_id}/members", status_code=status.HTTP_200_OK)
async def remove_member(
    subscription_id: UUID,
    member_data: RemoveMemberRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """
    Remove a member from subscription.
    Only subscription owner can remove members.
    """
    service = SubscriptionService(db)
    result = await service.remove_member(subscription_id, user_id, member_data)

    return success_response(
        data=jsonable_encoder(result),
        message="Member removed successfully",
    )


@router.get("/{subscription_id}/usage", status_code=status.HTTP_200_OK)
async def get_usage_stats(
    subscription_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get usage statistics for subscription"""
    service = SubscriptionService(db)
    result = await service.get_usage_stats(subscription_id, user_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Usage statistics retrieved successfully",
    )


@router.get("/check/feature/{feature}", status_code=status.HTTP_200_OK)
async def check_feature_access(
    feature: str,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Check if current user has access to a specific feature"""
    service = SubscriptionService(db)
    has_access, message = await service.check_feature_access(user_id, feature)

    return success_response(
        data={"has_access": has_access, "message": message},
        message="Feature access checked",
    )


@router.get("/check/limit/{activity_type}", status_code=status.HTTP_200_OK)
async def check_usage_limit(
    activity_type: str,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Check if current user has exceeded usage limits"""
    service = SubscriptionService(db)
    within_limit, message = await service.check_usage_limit(user_id, activity_type)

    return success_response(
        data={"within_limit": within_limit, "message": message},
        message="Usage limit checked",
    )


@router.get("/plans/available", status_code=status.HTTP_200_OK)
async def get_available_plans(
    db=Depends(get_db),
):
    """Get all available subscription plans with pricing"""
    service = SubscriptionService(db)
    result = service.get_available_plans()

    return success_response(
        data=jsonable_encoder(result),
        message="Available plans retrieved successfully",
    )
