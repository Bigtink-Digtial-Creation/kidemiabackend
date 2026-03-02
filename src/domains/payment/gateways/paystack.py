import httpx
import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Any, Optional

from src.config.settings import settings
from src.domains.payment.gateways.base import PaymentGatewayBase
from src.config.config_service import ConfigService


class PaystackGateway(PaymentGatewayBase):
    """Paystack payment gateway implementation with subscription support"""

    BASE_URL = "https://api.paystack.co"

    def __init__(self):
        self.secret_key = ConfigService.get_value(
            "paystack_secret_key", settings.PAYSTACK_SECRET_KEY
        )
        self.public_key = ConfigService.get_value(
            "paystack_public_key", settings.PAYSTACK_PUBLIC_KEY
        )

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    async def initialize_payment(
        self,
        amount: Decimal,
        email: str,
        transaction_ref: str = None,
        callback_url: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Initialize Paystack payment"""
        url = f"{self.BASE_URL}/transaction/initialize"

        amount_kobo = int(amount * 100)

        payload = {
            "amount": amount_kobo,
            "email": email,
            # "reference": transaction_ref,
            "callback_url": callback_url or settings.PAYMENT_CALLBACK_URL,
            "metadata": metadata or {},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers())
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

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers())
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
                "authorization": payment_data.get("authorization", {}),
                "customer": payment_data.get("customer", {}),
                "metadata": payment_data.get("metadata", {}),
                "message": payment_data.get("gateway_response", "Payment verified"),
            }

    async def create_plan(
        self,
        plan_code: str,
        name: str,
        amount: Decimal,
        interval: str,
        description: str = None,
    ) -> Dict[str, Any]:
        """Create a subscription plan on Paystack"""
        url = f"{self.BASE_URL}/plan"

        payload = {
            "name": name,
            "amount": int(amount * 100),
            "interval": interval,  # daily, weekly, monthly, annually
            "description": description or name,
            "currency": "NGN",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                raise Exception(data.get("message", "Plan creation failed"))

            return data["data"]

    async def get_plan(self, plan_code: str) -> Optional[Dict[str, Any]]:
        """Get plan details from Paystack"""
        url = f"{self.BASE_URL}/plan/{plan_code}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers())

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                return None

            return data["data"]

    async def create_subscription(
        self,
        customer: str,
        plan: str,
        authorization: str,
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a subscription on Paystack"""
        url = f"{self.BASE_URL}/subscription"

        payload = {
            "customer": customer,
            "plan": plan,
            "authorization": authorization,
        }

        if start_date:
            payload["start_date"] = start_date

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                raise Exception(data.get("message", "Subscription creation failed"))

            return data["data"]

    async def disable_subscription(self, code: str, token: str) -> bool:
        """Disable a subscription on Paystack"""
        url = f"{self.BASE_URL}/subscription/disable"

        payload = {"code": code, "token": token}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()

            return data.get("status", False)

    async def enable_subscription(self, code: str, token: str) -> bool:
        """Enable a subscription on Paystack"""
        url = f"{self.BASE_URL}/subscription/enable"

        payload = {"code": code, "token": token}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()

            return data.get("status", False)

    async def fetch_subscription(self, id_or_code: str) -> Dict[str, Any]:
        """Fetch subscription details from Paystack"""
        url = f"{self.BASE_URL}/subscription/{id_or_code}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                raise Exception(data.get("message", "Failed to fetch subscription"))

            return data["data"]

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Paystack webhook signature"""
        computed = hmac.new(
            self.secret_key.encode(), payload, hashlib.sha512
        ).hexdigest()

        if computed != signature:
            raise ValueError("Invalid Paystack signature")

        return True

    def calculate_fee(self, amount: Decimal) -> Decimal:
        """Calculate Paystack fee: 1.5% + NGN 100 (capped at NGN 2000)"""
        fee = (amount * Decimal("0.015")) + Decimal("100")
        return min(fee, Decimal("2000")).quantize(Decimal("0.01"))
