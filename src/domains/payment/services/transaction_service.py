from typing import Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    BusinessLogicException,
)
from src.domains.payment.repositories.transaction_repository import (
    TransactionRepository,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.payment.schemas.transaction import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    VerifyPaymentResponse,
    TransactionResponse,
)
from src.domains.payment.enums import TransactionStatus, TransactionType, PaymentGateway


class TransactionService:
    """Service for transaction operations"""

    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.assessment_repo = AssessmentRepository(db)

    async def initiate_payment(
        self, user_id: UUID, payment_data: InitiatePaymentRequest
    ) -> InitiatePaymentResponse:
        """Initiate a payment transaction"""
        # Validate assessment if purchasing exam
        if payment_data.assessment_id:
            assessment = self.assessment_repo.get_by_id(payment_data.assessment_id)
            if not assessment:
                raise ResourceNotFoundException(
                    "Assessment", payment_data.assessment_id
                )

            # Check if already purchased
            existing = self.transaction_repo.get_all(
                filters={
                    "user_id": user_id,
                    "assessment_id": payment_data.assessment_id,
                    "status": TransactionStatus.COMPLETED,
                    "is_deleted": False,
                }
            )

            if existing:
                raise BusinessLogicException("You have already purchased this exam")

        # Calculate fees
        platform_fee = self._calculate_platform_fee(payment_data.amount)
        gateway_fee = self._calculate_gateway_fee(
            payment_data.amount, payment_data.payment_method
        )
        total_amount = payment_data.amount + platform_fee + gateway_fee

        # Generate transaction reference
        transaction_ref = f"TXN-{uuid4().hex[:12].upper()}"

        # Create transaction record
        transaction_data = {
            "transaction_reference": transaction_ref,
            "transaction_type": TransactionType.EXAM_PURCHASE
            if payment_data.assessment_id
            else TransactionType.SUBSCRIPTION,
            "user_id": user_id,
            "assessment_id": payment_data.assessment_id,
            "amount": payment_data.amount,
            "platform_fee": platform_fee,
            "gateway_fee": gateway_fee,
            "total_amount": total_amount,
            "payment_method": payment_data.payment_method,
            "payment_gateway": PaymentGateway.PAYSTACK,  # Default to Paystack
            "status": TransactionStatus.PENDING,
            "initiated_at": datetime.utcnow().isoformat(),
            "created_by": user_id,
        }

        transaction = self.transaction_repo.create(transaction_data)

        # Initialize payment with gateway
        gateway_response = await self._initialize_gateway_payment(
            transaction, payment_data.callback_url
        )

        # Update transaction with gateway reference
        self.transaction_repo.update(
            transaction.id,
            {
                "gateway_reference": gateway_response.get("reference"),
                "gateway_response": gateway_response,
            },
        )

        return InitiatePaymentResponse(
            transaction_id=transaction.id,
            transaction_reference=transaction_ref,
            payment_url=gateway_response.get("authorization_url"),
            access_code=gateway_response.get("access_code"),
            authorization_code=gateway_response.get("authorization_code"),
        )

    async def verify_payment(self, transaction_reference: str) -> VerifyPaymentResponse:
        """Verify a payment transaction"""
        transaction = self.transaction_repo.get_by_reference(transaction_reference)
        if not transaction:
            raise ResourceNotFoundException("Transaction", transaction_reference)

        # Verify with payment gateway
        gateway_status = await self._verify_with_gateway(transaction)

        # Update transaction status
        if gateway_status.get("status") == "success":
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.COMPLETED,
                    "completed_at": datetime.utcnow().isoformat(),
                    "gateway_response": gateway_status,
                },
            )

            # Grant access to assessment if exam purchase
            access_granted = False
            if transaction.assessment_id:
                access_granted = True
                # TODO: Create assessment access record

            return VerifyPaymentResponse(
                transaction_id=transaction.id,
                status=TransactionStatus.COMPLETED,
                amount=transaction.amount,
                message="Payment successful",
                access_granted=access_granted,
            )
        else:
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.FAILED,
                    "failed_at": datetime.utcnow().isoformat(),
                    "gateway_response": gateway_status,
                },
            )

            return VerifyPaymentResponse(
                transaction_id=transaction.id,
                status=TransactionStatus.FAILED,
                amount=transaction.amount,
                message=gateway_status.get("message", "Payment failed"),
                access_granted=False,
            )

    async def get_user_transactions(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[TransactionResponse]:
        """Get user's transaction history"""
        transactions = self.transaction_repo.get_user_transactions(
            user_id, skip=skip, limit=limit
        )

        return [TransactionResponse.model_validate(t) for t in transactions]

    async def handle_webhook(self, gateway: str, payload: Dict[str, Any]) -> bool:
        """Handle payment gateway webhook"""
        # Extract transaction reference from payload
        reference = payload.get("reference") or payload.get("data", {}).get("reference")

        if not reference:
            return False

        # Get transaction
        transaction = self.transaction_repo.get_by_gateway_reference(reference)
        if not transaction:
            return False

        # Update based on webhook event
        event = payload.get("event")

        if event == "charge.success":
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.COMPLETED,
                    "completed_at": datetime.utcnow().isoformat(),
                    "gateway_response": payload,
                },
            )
            return True

        elif event == "charge.failed":
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.FAILED,
                    "failed_at": datetime.utcnow().isoformat(),
                    "gateway_response": payload,
                },
            )
            return True

        return False

    def _calculate_platform_fee(self, amount: Decimal) -> Decimal:
        """Calculate platform fee (e.g., 2.5%)"""
        return (amount * Decimal("0.025")).quantize(Decimal("0.01"))

    def _calculate_gateway_fee(self, amount: Decimal, method: str) -> Decimal:
        """Calculate gateway fee"""
        # Paystack: 1.5% + NGN 100 (capped at NGN 2000)
        fee = (amount * Decimal("0.015")) + Decimal("100")
        return min(fee, Decimal("2000")).quantize(Decimal("0.01"))

    async def _initialize_gateway_payment(
        self, transaction, callback_url: str = None
    ) -> Dict[str, Any]:
        """Initialize payment with gateway (Paystack example)"""
        # TODO: Implement actual Paystack API integration
        # This is a placeholder

        return {
            "status": True,
            "message": "Authorization URL created",
            "reference": transaction.gateway_reference or f"PAY-{uuid4().hex[:16]}",
            "authorization_url": f"https://checkout.paystack.com/{uuid4().hex}",
            "access_code": uuid4().hex[:16],
        }

    async def _verify_with_gateway(self, transaction) -> Dict[str, Any]:
        """Verify transaction with gateway"""
        # TODO: Implement actual gateway verification
        # This is a placeholder

        return {
            "status": "success",
            "message": "Verification successful",
            "amount": float(transaction.amount),
            "reference": transaction.gateway_reference,
        }
