from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id
from src.domains.payment.services.transaction_service import TransactionService
from src.domains.payment.schemas.transaction import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    VerifyPaymentResponse,
    TransactionResponse,
)

router = APIRouter()


@router.post(
    "/initiate",
    response_model=InitiatePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate payment",
)
async def initiate_payment(
    payment_data: InitiatePaymentRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Initiate a payment transaction.

    - **assessment_id**: ID of exam to purchase
    - **amount**: Amount to pay
    - **payment_method**: CARD, BANK_TRANSFER, USSD, WALLET
    - **callback_url**: URL to redirect after payment

    Returns payment URL for redirect to gateway.
    """
    service = TransactionService(db)
    return await service.initiate_payment(current_user_id, payment_data)


@router.get(
    "/verify/{transaction_reference}",
    response_model=VerifyPaymentResponse,
    summary="Verify payment",
)
async def verify_payment(transaction_reference: str, db: Session = Depends(get_db)):
    """
    Verify a payment transaction.

    Called after payment gateway redirect or to check payment status.
    """
    service = TransactionService(db)
    return await service.verify_payment(transaction_reference)


@router.get(
    "/my-transactions",
    response_model=List[TransactionResponse],
    summary="Get my transactions",
)
async def get_my_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get transaction history for current user."""
    service = TransactionService(db)
    return await service.get_user_transactions(current_user_id, skip, limit)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction details",
)
async def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get details of a specific transaction."""
    from src.domains.payment.repositories.transaction_repository import (
        TransactionRepository,
    )
    from src.core.exceptions import ResourceNotFoundException, ValidationException

    repo = TransactionRepository(db)
    transaction = repo.get_by_id(transaction_id)

    if not transaction:
        raise ResourceNotFoundException("Transaction", transaction_id)

    # Verify ownership
    if transaction.user_id != current_user_id:
        raise ValidationException("Not authorized to view this transaction")

    return TransactionResponse.model_validate(transaction)


@router.post(
    "/webhook/{gateway}",
    status_code=status.HTTP_200_OK,
    summary="Payment gateway webhook",
)
async def payment_webhook(
    gateway: str, request: Request, db: Session = Depends(get_db)
):
    """
    Webhook endpoint for payment gateway callbacks.

    - **gateway**: paystack, stripe, flutterwave

    Automatically updates transaction status based on gateway events.
    """
    payload = await request.json()

    service = TransactionService(db)
    success = await service.handle_webhook(gateway, payload)

    return {"status": "success" if success else "ignored"}
