import httpx
from decimal import Decimal
from typing import Dict, Any

from src.config.settings import settings
from src.domains.payment.services.gateways.base import PaymentGatewayBase


class PaystackGateway(PaymentGatewayBase):
    """Paystack payment gateway implementation"""

    BASE_URL = "https://api.paystack.co"

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY

    async def initialize_payment(
        self,
        amount: Decimal,
        email: str,
        transaction_ref: str,
        callback_url: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Initialize Paystack payment"""
        url = f"{self.BASE_URL}/transaction/initialize"

        amount_kobo = int(amount * 100)

        payload = {
            "amount": amount_kobo,
            "email": email,
            "reference": transaction_ref,
            "callback_url": callback_url or settings.PAYMENT_CALLBACK_URL,
            "metadata": metadata or {},
        }

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                raise Exception(data.get("message", "Payment initialization failed"))

            return {
                "status": "success",
                "reference": data["data"]["reference"],
                "authorization_url": data["data"]["authorization_url"],
                "access_code": data["data"]["access_code"],
            }

    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify Paystack payment"""
        url = f"{self.BASE_URL}/transaction/verify/{reference}"

        headers = {"Authorization": f"Bearer {self.secret_key}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                return {
                    "status": "failed",
                    "message": data.get("message", "Verification failed"),
                }

            payment_data = data["data"]

            return {
                "status": "success"
                if payment_data["status"] == "success"
                else "failed",
                "amount": Decimal(payment_data["amount"]) / 100,
                "reference": payment_data["reference"],
                "paid_at": payment_data.get("paid_at"),
                "channel": payment_data.get("channel"),
                "card_type": payment_data.get("authorization", {}).get("card_type"),
                "last4": payment_data.get("authorization", {}).get("last4"),
                "bank": payment_data.get("authorization", {}).get("bank"),
                "message": payment_data.get("gateway_response", "Payment verified"),
            }

    def calculate_fee(self, amount: Decimal) -> Decimal:
        """Calculate Paystack fee: 1.5% + NGN 100 (capped at NGN 2000)"""
        fee = (amount * Decimal("0.015")) + Decimal("100")
        return min(fee, Decimal("2000")).quantize(Decimal("0.01"))
