from typing import Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from pydantic import Field

from src.shared.schemas.base import BaseSchema, CreateSchema, ResponseSchema
from src.domains.payment.enums import (
    TransactionType,
    TransactionStatus,
    PaymentMethod,
    PaymentGateway,
)


class TransactionBase(BaseSchema):
    """Base transaction schema"""

    transaction_type: TransactionType
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="NGN", max_length=3)
    payment_method: PaymentMethod
    payment_gateway: PaymentGateway
    description: Optional[str] = None


class TransactionCreate(TransactionBase, CreateSchema):
    """Schema for creating transaction"""

    assessment_id: Optional[UUID] = None
    subscription_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class TransactionResponse(TransactionBase, ResponseSchema):
    """Schema for transaction response"""

    transaction_reference: str
    status: TransactionStatus
    user_id: UUID
    institution_id: Optional[UUID]

    platform_fee: Decimal
    gateway_fee: Decimal
    total_amount: Decimal
    net_amount: Optional[Decimal]

    gateway_reference: Optional[str]
    card_last4: Optional[str]
    card_brand: Optional[str]

    assessment_id: Optional[UUID]
    subscription_id: Optional[UUID]

    initiated_at: str
    completed_at: Optional[str]
    is_reconciled: bool


class InitiatePaymentRequest(BaseSchema):
    """Request to initiate payment"""

    assessment_id: Optional[UUID] = None
    subscription_plan: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod
    callback_url: Optional[str] = None


class InitiatePaymentResponse(BaseSchema):
    """Response for payment initiation"""

    transaction_id: UUID
    transaction_reference: str
    payment_url: Optional[str] = None  # For redirects
    authorization_code: Optional[str] = None
    access_code: Optional[str] = None
    expires_at: Optional[str] = None


class VerifyPaymentResponse(BaseSchema):
    """Response for payment verification"""

    transaction_id: UUID
    status: TransactionStatus
    amount: Decimal
    message: str
    access_granted: bool = False
