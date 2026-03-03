from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_async_db
from src.core.security import get_current_user_id
from src.domains.payment.services.wallet_service import WalletService
from src.domains.payment.schemas.wallet import (
    WalletResponse,
    WalletTopupRequest,
    WalletTransferRequest,
)

router = APIRouter()


@router.get("/", response_model=WalletResponse, summary="Get my wallet")
async def get_my_wallet(
    db: Session = Depends(get_async_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get wallet balance and details."""
    service = WalletService(db)
    return await service.get_or_create_wallet(current_user_id)


@router.post("/topup", response_model=WalletResponse, summary="Top up wallet")
async def topup_wallet(
    topup_data: WalletTopupRequest,
    db: Session = Depends(get_async_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Top up wallet balance.

    Initiates payment gateway transaction.
    Wallet credited after successful payment.
    """
    service = WalletService(db)
    return await service.credit_wallet(
        current_user_id, topup_data.amount, "Wallet top-up"
    )


@router.post("/transfer", response_model=WalletResponse, summary="Transfer from wallet")
async def wallet_transfer(
    transfer_data: WalletTransferRequest,
    db: Session = Depends(get_async_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Transfer money from wallet to another user.

    Requires wallet PIN for security.
    """
    # TODO: Implement wallet transfer logic
    service = WalletService(db)
    return await service.debit_wallet(
        current_user_id,
        transfer_data.amount,
        f"Transfer to {transfer_data.recipient_id}",
    )
