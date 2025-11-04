from uuid import UUID
from pydantic import Field
from decimal import Decimal
from typing import Optional
from src.shared.schemas.base import BaseSchema, ResponseSchema
from src.domains.payment.enums import PaymentMethod


class WalletResponse(ResponseSchema):
    """Schema for wallet response"""

    user_id: UUID
    balance: Decimal
    currency: str
    is_active: bool
    is_locked: bool
    has_pin: bool


class WalletTopupRequest(BaseSchema):
    """Request to top up wallet"""

    amount: Decimal = Field(..., gt=0, le=100000)
    payment_method: PaymentMethod


class WalletTransferRequest(BaseSchema):
    """Request to transfer from wallet"""

    recipient_id: UUID
    amount: Decimal = Field(..., gt=0)
    pin: str = Field(..., min_length=4, max_length=6)
    description: Optional[str] = None
