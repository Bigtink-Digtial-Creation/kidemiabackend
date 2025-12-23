from fastapi import APIRouter, Depends, status
from uuid import UUID

from src.core.security import get_db, get_current_user
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


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new subscription for the current user.

    This will create a subscription in PENDING status.
    After payment is confirmed, call the activate endpoint.
    """
    service = SubscriptionService(db)
    result = await service.create_subscription(current_user.id, subscription_data)
    return success_response(
        data=result,
        message="Subscription created successfully. Please proceed with payment.",
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/{subscription_id}/activate", status_code=status.HTTP_200_OK)
async def activate_subscription(
    subscription_id: UUID,
    payment_reference: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Activate subscription after successful payment"""
    service = SubscriptionService(db)
    result = await service.activate_subscription(subscription_id, payment_reference)
    return success_response(
        data=result,
        message="Subscription activated successfully",
    )


@router.get("", status_code=status.HTTP_200_OK)
async def get_my_subscriptions(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all subscriptions for current user (as owner or member)"""
    service = SubscriptionService(db)
    result = await service.get_user_subscriptions(current_user.id)
    return success_response(
        data=result,
        message="Subscriptions retrieved successfully",
    )


@router.get("/{subscription_id}", status_code=status.HTTP_200_OK)
async def get_subscription(
    subscription_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get subscription details with members"""
    service = SubscriptionService(db)
    result = await service.get_subscription_with_members(
        subscription_id, current_user.id
    )
    return success_response(
        data=result,
        message="Subscription details retrieved successfully",
    )


@router.post("/{subscription_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    subscription_id: UUID,
    member_data: AddMemberRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Add a member (ward/student) to subscription.
    Only subscription owner can add members.
    """
    service = SubscriptionService(db)
    result = await service.add_member(subscription_id, current_user.id, member_data)
    return success_response(
        data=result,
        message="Member added successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.delete("/{subscription_id}/members", status_code=status.HTTP_200_OK)
async def remove_member(
    subscription_id: UUID,
    member_data: RemoveMemberRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Remove a member from subscription.
    Only subscription owner can remove members.
    """
    service = SubscriptionService(db)
    result = await service.remove_member(subscription_id, current_user.id, member_data)
    return success_response(
        data=result,
        message="Member removed successfully",
    )


@router.put("/{subscription_id}/upgrade", status_code=status.HTTP_200_OK)
async def upgrade_subscription(
    subscription_id: UUID,
    upgrade_data: SubscriptionUpgradeRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Upgrade subscription to a higher plan.
    This will calculate prorated charges.
    """
    service = SubscriptionService(db)
    result = await service.upgrade_subscription(
        subscription_id, current_user.id, upgrade_data
    )
    return success_response(
        data=result,
        message="Subscription upgraded successfully",
    )


@router.post("/{subscription_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_subscription(
    subscription_id: UUID,
    cancel_data: SubscriptionCancelRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Cancel subscription.
    If cancel_immediately is False, subscription remains active until end date.
    """
    service = SubscriptionService(db)
    result = await service.cancel_subscription(
        subscription_id,
        current_user.id,
        cancel_data.reason,
        cancel_data.cancel_immediately,
    )
    return success_response(
        data=result,
        message="Subscription cancelled successfully",
    )


@router.get("/{subscription_id}/usage", status_code=status.HTTP_200_OK)
async def get_usage_stats(
    subscription_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get usage statistics for subscription"""
    service = SubscriptionService(db)
    result = await service.get_usage_stats(subscription_id, current_user.id)
    return success_response(
        data=result,
        message="Usage statistics retrieved successfully",
    )


@router.get("/plans/available", status_code=status.HTTP_200_OK)
async def get_available_plans(
    db=Depends(get_db),
):
    """Get all available subscription plans with pricing"""
    service = SubscriptionService(db)
    result = service.get_available_plans()
    return success_response(
        data=result,
        message="Available plans retrieved successfully",
    )


@router.get("/check/feature/{feature}", status_code=status.HTTP_200_OK)
async def check_feature_access(
    feature: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check if current user has access to a specific feature"""
    service = SubscriptionService(db)
    has_access, message = await service.check_feature_access(current_user.id, feature)

    return success_response(
        data={"has_access": has_access, "message": message},
        message="Feature access checked",
    )


@router.get("/check/limit/{activity_type}", status_code=status.HTTP_200_OK)
async def check_usage_limit(
    activity_type: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check if current user has exceeded usage limits"""
    service = SubscriptionService(db)
    within_limit, message = await service.check_usage_limit(
        current_user.id, activity_type
    )

    return success_response(
        data={"within_limit": within_limit, "message": message},
        message="Usage limit checked",
    )
