import httpx
from decimal import Decimal
from typing import Dict, Any

from src.config.settings import settings
from src.config.config_service import ConfigService
from .base import PaymentGatewayBase


class FlutterwaveGateway(PaymentGatewayBase):
    """Flutterwave payment gateway implementation"""

    BASE_URL = "https://api.flutterwave.com/v3"

    def __init__(self):
        self.secret_key = (
            ConfigService.get_value(
                "flutterwave_secret_key", settings.FLUTTERWAVE_SECRET_KEY
            ),
        )
        self.public_key = (
            ConfigService.get_value(
                "flutterwave_public_key", settings.FLUTTERWAVE_PUBLIC_KEY
            ),
        )

    async def initialize_payment(
        self,
        amount: Decimal,
        email: str,
        transaction_ref: str,
        callback_url: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Initialize Flutterwave payment"""
        url = f"{self.BASE_URL}/payments"

        payload = {
            "tx_ref": transaction_ref,
            "amount": str(amount),
            "currency": "NGN",
            "redirect_url": callback_url or settings.PAYMENT_CALLBACK_URL,
            "payment_options": "card,banktransfer,ussd",
            "customer": {"email": email},
            "customizations": {
                "title": settings.APP_F_NAME,
                "description": "Payment for services",
            },
            "meta": metadata or {},
        }

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise Exception(data.get("message", "Payment initialization failed"))

            return {
                "status": "success",
                "reference": transaction_ref,
                "payment_url": data["data"]["link"],
            }

    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify Flutterwave payment"""
        url = f"{self.BASE_URL}/transactions/verify_by_reference?tx_ref={reference}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.secret_key}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                return {
                    "status": "failed",
                    "message": data.get("message", "Verification failed"),
                }

            payment_data = data["data"]

            return {
                "status": "success"
                if payment_data["status"] == "successful"
                else "failed",
                "amount": Decimal(payment_data["amount"]),
                "reference": payment_data["tx_ref"],
                "paid_at": payment_data.get("created_at"),
                "channel": payment_data.get("payment_type"),
                "card_type": payment_data.get("card", {}).get("type"),
                "last4": payment_data.get("card", {}).get("last_4digits"),
                "message": payment_data.get("processor_response", "Payment verified"),
            }

    def calculate_fee(self, amount: Decimal) -> Decimal:
        """Calculate Flutterwave fee: 1.4% (capped at NGN 2000)"""
        fee = amount * Decimal("0.014")
        return min(fee, Decimal("2000")).quantize(Decimal("0.01"))
