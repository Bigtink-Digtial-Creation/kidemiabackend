from uuid import UUID
from pydantic import Field
from decimal import Decimal
from typing import Optional
from src.domains.payment.enums import RefundStatus
from src.shared.schemas.base import BaseSchema, ResponseSchema


class RefundRequest(BaseSchema):
    """Request for refund"""

    transaction_id: UUID
    reason: str = Field(..., min_length=10, max_length=500)


class RefundResponse(ResponseSchema):
    """Schema for refund response"""

    refund_reference: str
    transaction_id: UUID
    status: RefundStatus
    amount: Decimal
    currency: str
    reason: str
    requested_at: str
    approved_at: Optional[str]
    completed_at: Optional[str]
