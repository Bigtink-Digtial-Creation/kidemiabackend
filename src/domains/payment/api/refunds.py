from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.payment.schemas.refund import RefundRequest, RefundResponse
from src.domains.payment.models.refund import Refund
from src.domains.payment.repositories.transaction_repository import (
    TransactionRepository,
)
from src.core.exceptions import ResourceNotFoundException, BusinessLogicException


router = APIRouter()


@router.post(
    "/request",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request refund",
)
async def request_refund(
    refund_data: RefundRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Request a refund for a transaction.

    - **transaction_id**: Transaction to refund
    - **reason**: Reason for refund (min 10 characters)

    Refund requests are reviewed by admins.
    """

    # Validate transaction
    transaction_repo = TransactionRepository(db)
    transaction = transaction_repo.get_by_id(refund_data.transaction_id)

    if not transaction:
        raise ResourceNotFoundException("Transaction", refund_data.transaction_id)

    if transaction.user_id != current_user_id:
        raise BusinessLogicException(
            "Not authorized to request refund for this transaction"
        )

    if transaction.status != "completed":
        raise BusinessLogicException("Can only refund completed transactions")

    # Check if refund already exists
    existing = (
        db.query(Refund)
        .filter(Refund.transaction_id == refund_data.transaction_id)
        .first()
    )

    if existing:
        raise BusinessLogicException(
            "Refund request already exists for this transaction"
        )

    # Create refund request
    refund = Refund(
        refund_reference=f"REF-{uuid4().hex[:12].upper()}",
        transaction_id=refund_data.transaction_id,
        amount=transaction.amount,
        currency=transaction.currency,
        reason=refund_data.reason,
        requested_by=current_user_id,
        status="requested",
        created_by=current_user_id,
    )

    db.add(refund)
    db.commit()
    db.refresh(refund)

    return RefundResponse.model_validate(refund)


@router.get(
    "/my-refunds", response_model=List[RefundResponse], summary="Get my refund requests"
)
async def get_my_refunds(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all refund requests by current user."""

    refunds = (
        db.query(Refund)
        .filter(Refund.requested_by == current_user_id, Refund.is_deleted.is_(False))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [RefundResponse.model_validate(r) for r in refunds]


@router.get(
    "/pending",
    response_model=List[RefundResponse],
    summary="Get pending refunds (Admin)",
)
async def get_pending_refunds(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("payment:manage")),
):
    """Get all pending refund requests. Requires payment:manage permission."""

    refunds = (
        db.query(Refund)
        .filter(Refund.status == "requested", Refund.is_deleted.is_(False))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [RefundResponse.model_validate(r) for r in refunds]


@router.post(
    "/{refund_id}/approve",
    response_model=RefundResponse,
    summary="Approve refund (Admin)",
)
async def approve_refund(
    refund_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("payment:manage")),
):
    """Approve a refund request. Requires payment:manage permission."""

    refund = db.query(Refund).filter(Refund.id == refund_id).first()

    if not refund:
        raise ResourceNotFoundException("Refund", refund_id)

    refund.status = "approved"
    refund.approved_by = current_user_id
    refund.approved_at = datetime.utcnow().isoformat()

    db.commit()
    db.refresh(refund)

    # TODO: Process actual refund through payment gateway

    return RefundResponse.model_validate(refund)


@router.post(
    "/{refund_id}/reject",
    response_model=RefundResponse,
    summary="Reject refund (Admin)",
)
async def reject_refund(
    refund_id: UUID,
    reason: str = Query(..., min_length=10),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("payment:manage")),
):
    """Reject a refund request. Requires payment:manage permission."""

    refund = db.query(Refund).filter(Refund.id == refund_id).first()

    if not refund:
        raise ResourceNotFoundException("Refund", refund_id)

    refund.status = "rejected"
    refund.rejected_by = current_user_id
    refund.rejected_at = datetime.utcnow().isoformat()
    refund.rejection_reason = reason

    db.commit()
    db.refresh(refund)

    return RefundResponse.model_validate(refund)
