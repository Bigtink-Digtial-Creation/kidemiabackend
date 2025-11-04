from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id
from src.domains.payment.services.subscription_service import SubscriptionService
from src.domains.payment.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpgradeRequest,
)

router = APIRouter()


@router.post(
    "/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create subscription",
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Create a new subscription.

    Plans:
    - **FREE**: Basic access, 3 exams/month
    - **BASIC**: NGN 2,000/month, 10 exams/month
    - **PREMIUM**: NGN 5,000/month, unlimited exams
    - **INSTITUTION**: NGN 50,000/month, institution features

    Billing cycles: monthly, quarterly, yearly
    """
    service = SubscriptionService(db)
    return await service.create_subscription(current_user_id, subscription_data)


@router.get(
    "/my-subscription",
    response_model=SubscriptionResponse,
    summary="Get my active subscription",
)
async def get_my_subscription(
    db: Session = Depends(get_db), current_user_id: UUID = Depends(get_current_user_id)
):
    """Get active subscription for current user."""
    from src.domains.payment.repositories.subscription_repository import (
        SubscriptionRepository,
    )
    from src.core.exceptions import ResourceNotFoundException

    repo = SubscriptionRepository(db)
    subscription = repo.get_active_subscription(current_user_id)

    if not subscription:
        raise ResourceNotFoundException("Active subscription", "not found")

    return SubscriptionResponse.model_validate(subscription)


@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel subscription",
)
async def cancel_subscription(
    subscription_id: UUID,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Cancel a subscription.

    Subscription remains active until end date.
    Auto-renewal will be disabled.
    """
    service = SubscriptionService(db)
    return await service.cancel_subscription(subscription_id, current_user_id, reason)


@router.post(
    "/{subscription_id}/upgrade",
    response_model=SubscriptionResponse,
    summary="Upgrade subscription",
)
async def upgrade_subscription(
    subscription_id: UUID,
    upgrade_data: SubscriptionUpgradeRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Upgrade subscription to a higher plan.

    Prorated charges apply for immediate upgrades.
    """
    service = SubscriptionService(db)
    return await service.upgrade_subscription(
        subscription_id, current_user_id, upgrade_data
    )


"""
# ==================== UPDATE MAIN API ROUTER ====================
# Add to src/api/v1/router.py


# Import payment router
from src.domains.payment.api import payment_router

# Add to api_router
api_router.include_router(
    payment_router,
    prefix="/payment",
    tags=["Payment"]
)
"""


# ==================== INTEGRATION WITH ASSESSMENT ====================
# Update src/domains/assessment/models/attempt.py to add payment relationship

"""
Add to AssessmentAttempt model:

# Payment (for paid exams)
payment_id = Column(
    PG_UUID(as_uuid=True),
    ForeignKey("transaction.id", ondelete="SET NULL"),
    nullable=True
)

# Relationship
payment = relationship("Transaction", backref="assessment_attempts")
"""


# ==================== PAYMENT VERIFICATION HOOK ====================
# src/domains/payment/services/access_service.py


# ==================== EXAMPLE API USAGE ====================
"""
# 1. Purchase an exam
POST /api/v1/payment/transactions/initiate
{
    "assessment_id": "uuid-of-exam",
    "amount": 500.00,
    "payment_method": "card",
    "callback_url": "https://yoursite.com/payment/callback"
}

Response:
{
    "transaction_id": "uuid",
    "transaction_reference": "TXN-ABC123XYZ",
    "payment_url": "https://checkout.paystack.com/xxx",
    "access_code": "xxx"
}

# 2. Verify payment (after redirect)
GET /api/v1/payment/transactions/verify/TXN-ABC123XYZ

Response:
{
    "transaction_id": "uuid",
    "status": "completed",
    "amount": 500.00,
    "message": "Payment successful",
    "access_granted": true
}

# 3. Start assessment (now has access)
POST /api/v1/assessment/attempts/{assessment_id}/start

# 4. Get transaction history
GET /api/v1/payment/transactions/my-transactions?skip=0&limit=20

# 5. Subscribe to premium
POST /api/v1/payment/subscriptions
{
    "plan": "premium",
    "billing_cycle": "monthly",
    "auto_renew": true
}

# 6. Check subscription
GET /api/v1/payment/subscriptions/my-subscription

Response:
{
    "subscription_reference": "SUB-XYZ123",
    "plan": "premium",
    "status": "active",
    "price": 5000.00,
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-02-01T00:00:00",
    "is_active": true,
    "days_remaining": 15,
    "exams_taken": 5,
    "exams_limit": null
}

# 7. Top up wallet
POST /api/v1/payment/wallet/topup
{
    "amount": 10000.00,
    "payment_method": "card"
}

# 8. Check wallet balance
GET /api/v1/payment/wallet

Response:
{
    "user_id": "uuid",
    "balance": 10000.00,
    "currency": "NGN",
    "is_active": true,
    "is_locked": false
}

# 9. Request refund
POST /api/v1/payment/refunds/request
{
    "transaction_id": "uuid",
    "reason": "Exam not available as expected"
}

# 10. Check refund status
GET /api/v1/payment/refunds/my-refunds

# 11. Approve refund (Admin only)
POST /api/v1/payment/refunds/{refund_id}/approve

# 12. Payment webhook (automatic)
POST /api/v1/payment/transactions/webhook/paystack
{
    "event": "charge.success",
    "data": {
        "reference": "TXN-ABC123XYZ",
        "status": "success",
        "amount": 50000
    }
}
"""


# ==================== DATABASE MIGRATION ====================
"""
After creating these models, generate migration:

alembic revision --autogenerate -m "Add payment and transaction tables"
alembic upgrade head

This will create:
- transaction table
- subscription table
- wallet table
- refund table
- payout table
"""
