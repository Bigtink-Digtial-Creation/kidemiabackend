from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timezone
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
from src.domains.payment.repositories.subscription_repository import (
    SubscriptionRepository,
)
from src.domains.auth.repositories.user_repository import UserRepository
from src.domains.payment.schemas.transaction import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    VerifyPaymentResponse,
    TransactionResponse,
)
from src.domains.payment.enums import (
    TransactionStatus,
    TransactionType,
    PaymentGateway,
)
from src.domains.payment.gateways.paystack import PaystackGateway
from src.domains.payment.gateways.flutterwave import FlutterwaveGateway
from src.domains.payment.services.plan_management_service import PlanManagementService
from src.domains.payment.services.subscription_service import SubscriptionService
from src.shared.utils.helpers import make_json_safe


class TransactionService:
    """Service for managing payment transactions"""

    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.assessment_repo = AssessmentRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.user_repo = UserRepository(db)
        self.plan_service = PlanManagementService(db)
        self.subscription_service = SubscriptionService(db)

        self.gateways = {
            PaymentGateway.PAYSTACK: PaystackGateway(),
            PaymentGateway.FLUTTERWAVE: FlutterwaveGateway(),
        }

    async def initiate_payment(
        self, user_id: UUID, payment_data: InitiatePaymentRequest
    ) -> InitiatePaymentResponse:
        """Initiate a payment transaction"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        transaction_type = self._determine_transaction_type(payment_data)

        subscription_id = None

        if transaction_type == TransactionType.EXAM_PURCHASE:
            await self._validate_exam_purchase(user_id, payment_data.assessment_id)
        elif transaction_type == TransactionType.SUBSCRIPTION:
            subscription_id = await self._validate_subscription_purchase(
                user_id, payment_data.plan_code
            )

        gateway = self._select_gateway(payment_data.payment_method)
        platform_fee = self._calculate_platform_fee(payment_data.amount)
        gateway_fee = self.gateways[gateway].calculate_fee(payment_data.amount)
        total_amount = payment_data.amount + platform_fee + gateway_fee

        transaction_ref = f"TXN-{uuid4().hex[:12].upper()}"

        transaction_data = {
            "transaction_reference": transaction_ref,
            "transaction_type": transaction_type,
            "user_id": user_id,
            "assessment_id": payment_data.assessment_id,
            "institution_id": payment_data.institution_id,
            "subscription_id": subscription_id,
            "amount": payment_data.amount,
            "platform_fee": platform_fee,
            "gateway_fee": gateway_fee,
            "total_amount": total_amount,
            "payment_method": payment_data.payment_method,
            "payment_gateway": gateway,
            "status": TransactionStatus.PENDING,
            "initiated_at": datetime.now(timezone.utc),
            "created_by": user_id,
        }

        transaction = self.transaction_repo.create(transaction_data)

        gateway_response = await self._initialize_gateway_payment(
            gateway, transaction, user.email, payment_data.callback_url
        )

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
            payment_url=gateway_response.get("authorization_url")
            or gateway_response.get("payment_url"),
            access_code=gateway_response.get("access_code"),
        )

    async def verify_payment(self, transaction_reference: str) -> VerifyPaymentResponse:
        """Verify a payment transaction"""
        transaction = self.transaction_repo.get_by_reference(transaction_reference)
        if not transaction:
            raise ResourceNotFoundException("Transaction", transaction_reference)

        if transaction.status == TransactionStatus.COMPLETED:
            return VerifyPaymentResponse(
                transaction_id=transaction.id,
                status=TransactionStatus.COMPLETED,
                amount=transaction.amount,
                message="Payment already verified",
                access_granted=bool(
                    transaction.assessment_id or transaction.subscription_id
                ),
            )

        gateway_status = await self._verify_with_gateway(
            transaction.payment_gateway, transaction.gateway_reference
        )
        if gateway_status.get("status") == "success":
            update_data = {
                "status": TransactionStatus.COMPLETED,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "gateway_response": make_json_safe(gateway_status),
                "card_last4": gateway_status.get("last4"),
                "card_brand": gateway_status.get("card_type"),
            }

            self.transaction_repo.update(transaction.id, update_data)

            access_granted = await self._grant_access(transaction)

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
                    "failed_at": datetime.now(timezone.utc),
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
        """Get user transaction history"""
        transactions = self.transaction_repo.get_user_transactions(
            user_id, skip=skip, limit=limit
        )
        return [TransactionResponse.model_validate(t) for t in transactions]

    async def handle_webhook(self, gateway: str, payload: Dict[str, Any]) -> bool:
        """Handle payment gateway webhook"""
        gateway_enum = PaymentGateway(gateway.lower())

        reference = self._extract_reference(gateway_enum, payload)
        if not reference:
            return False

        transaction = self.transaction_repo.get_by_gateway_reference(reference)
        if not transaction:
            return False

        event = payload.get("event")

        if gateway_enum == PaymentGateway.PAYSTACK:
            return await self._handle_paystack_webhook(transaction, event, payload)
        elif gateway_enum == PaymentGateway.FLUTTERWAVE:
            return await self._handle_flutterwave_webhook(transaction, event, payload)

        return False

    async def _validate_exam_purchase(
        self, user_id: UUID, assessment_id: Optional[UUID]
    ):
        """Validate exam purchase request"""
        if not assessment_id:
            raise BusinessLogicException("Assessment ID is required for exam purchase")

        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        existing = self.transaction_repo.get_all(
            filters={
                "user_id": user_id,
                "assessment_id": assessment_id,
                "status": TransactionStatus.COMPLETED,
                "is_deleted": False,
            }
        )

        if existing:
            raise BusinessLogicException("You have already purchased this exam")

    async def _validate_subscription_purchase(
        self, user_id: UUID, plan_code: Optional[str]
    ):
        """Validate subscription purchase request"""
        from src.domains.payment.enums import BillingCycle

        if not plan_code:
            raise BusinessLogicException("Subscription plan code is required")

        active_subscription = self.subscription_repo.get_active_subscription(user_id)
        if active_subscription:
            raise BusinessLogicException("You already have an active subscription")
        plan = self.plan_service.get_plan_by_code(plan_code=plan_code)

        if plan:
            plan_data = {
                "plam": plan_code,
                "billing_cycle": BillingCycle.YEARLY,
            }
            subscription_plan = await self.subscription_service.create_subscription(
                user_id, plan_data
            )
            return subscription_plan.id

    def _determine_transaction_type(
        self, payment_data: InitiatePaymentRequest
    ) -> TransactionType:
        """Determine transaction type from payment data"""
        if payment_data.assessment_id:
            return TransactionType.EXAM_PURCHASE
        elif payment_data.plan_code:
            return TransactionType.SUBSCRIPTION
        return TransactionType.WALLET_TOPUP

    def _select_gateway(self, payment_method) -> PaymentGateway:
        """Select payment gateway based on payment method"""
        if payment_method == "paystack":
            return PaymentGateway.PAYSTACK
        elif payment_method == "flutterwave":
            return PaymentGateway.FLUTTERWAVE
        return PaymentGateway.PAYSTACK

    def _calculate_platform_fee(self, amount: Decimal) -> Decimal:
        """Calculate platform fee (2.5%)"""
        return (amount * Decimal("0.025")).quantize(Decimal("0.01"))

    async def _initialize_gateway_payment(
        self,
        gateway: PaymentGateway,
        transaction,
        user_email: str,
        callback_url: Optional[str],
    ) -> Dict[str, Any]:
        """Initialize payment with selected gateway"""
        gateway_client = self.gateways[gateway]

        metadata = {
            "transaction_id": str(transaction.id),
            "user_id": str(transaction.user_id),
            "transaction_type": transaction.transaction_type,
        }

        return await gateway_client.initialize_payment(
            amount=transaction.total_amount,
            email=user_email,
            transaction_ref=transaction.transaction_reference,
            callback_url=callback_url,
            metadata=metadata,
        )

    async def _verify_with_gateway(
        self, gateway: PaymentGateway, reference: str
    ) -> Dict[str, Any]:
        """Verify transaction with gateway"""
        gateway_client = self.gateways[gateway]
        return await gateway_client.verify_payment(reference)

    async def _grant_access(self, transaction) -> bool:
        """Grant access to purchased resource"""
        if transaction.assessment_id:
            # grant accesss
            return True
        elif transaction.subscription:
            # activate service
            return True
        elif transaction.transaction_type == TransactionType.WALLET_TOPUP:
            await self._credit_wallet(transaction)
            return True
        return False

    def _extract_reference(
        self, gateway: PaymentGateway, payload: Dict[str, Any]
    ) -> Optional[str]:
        """Extract transaction reference from webhook payload"""
        if gateway == PaymentGateway.PAYSTACK:
            return payload.get("data", {}).get("reference")
        elif gateway == PaymentGateway.FLUTTERWAVE:
            return payload.get("data", {}).get("tx_ref")
        return None

    async def _handle_paystack_webhook(
        self, transaction, event: str, payload: Dict[str, Any]
    ) -> bool:
        """Handle Paystack webhook events"""
        if event == "charge.success":
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.COMPLETED,
                    "completed_at": datetime.now(timezone.utc),
                    "gateway_response": payload,
                },
            )

            # fire email on successful subscription
            await self._grant_access(transaction)
            return True

        elif event == "charge.failed":
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.FAILED,
                    "failed_at": datetime.now(timezone.utc),
                    "gateway_response": payload,
                },
            )
            # Fire email on inability to renew
            return True

        return False

    async def _handle_flutterwave_webhook(
        self, transaction, event: str, payload: Dict[str, Any]
    ) -> bool:
        """Handle Flutterwave webhook events"""
        status = payload.get("data", {}).get("status")

        if status == "successful":
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.COMPLETED,
                    "completed_at": datetime.now(timezone.utc),
                    "gateway_response": payload,
                },
            )
            # fire email on successful subscription
            await self._grant_access(transaction)
            return True

        elif status == "failed":
            self.transaction_repo.update(
                transaction.id,
                {
                    "status": TransactionStatus.FAILED,
                    "failed_at": datetime.now(timezone.utc),
                    "gateway_response": payload,
                },
            )
            # Fire email on inability to renew
            return True

        return False

    async def _credit_wallet(self, transaction):
        """Credit user wallet after successful payment"""
        from src.shared.events.dispatcher import dispatch_wallet_topup

        dispatch_wallet_topup(
            user_id=transaction.user_id,
            amount=transaction.amount,
        )
