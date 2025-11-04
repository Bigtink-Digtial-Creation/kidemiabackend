import httpx
from typing import Dict, Any
from decimal import Decimal

from src.config.settings import settings


class PaystackProvider:
    """Paystack payment gateway integration"""

    BASE_URL = "https://api.paystack.com"

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    async def initialize_transaction(
        self, email: str, amount: Decimal, reference: str, callback_url: str = None
    ) -> Dict[str, Any]:
        """Initialize payment transaction"""

        payload = {
            "email": email,
            "amount": int(amount * 100),  # Convert to kobo
            "reference": reference,
            "callback_url": callback_url,
            "metadata": {"cancel_action": callback_url},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/transaction/initialize",
                json=payload,
                headers=self.headers,
            )

            return response.json()

    async def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """Verify transaction status"""

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/transaction/verify/{reference}", headers=self.headers
            )

            return response.json()

    async def list_banks(self, country: str = "nigeria") -> Dict[str, Any]:
        """List supported banks"""

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/bank",
                params={"country": country},
                headers=self.headers,
            )

            return response.json()

    async def resolve_account(
        self, account_number: str, bank_code: str
    ) -> Dict[str, Any]:
        """Resolve bank account details"""

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/bank/resolve",
                params={"account_number": account_number, "bank_code": bank_code},
                headers=self.headers,
            )

            return response.json()

    async def create_transfer_recipient(
        self, name: str, account_number: str, bank_code: str
    ) -> Dict[str, Any]:
        """Create transfer recipient"""

        payload = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/transferrecipient", json=payload, headers=self.headers
            )

            return response.json()

    async def initiate_transfer(
        self, recipient_code: str, amount: Decimal, reference: str, reason: str = None
    ) -> Dict[str, Any]:
        """Initiate bank transfer"""

        payload = {
            "source": "balance",
            "amount": int(amount * 100),  # Convert to kobo
            "recipient": recipient_code,
            "reference": reference,
            "reason": reason or "Payment",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/transfer", json=payload, headers=self.headers
            )

            return response.json()
