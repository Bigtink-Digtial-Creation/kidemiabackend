from abc import ABC, abstractmethod
from typing import Dict, Any
from decimal import Decimal


class PaymentGatewayBase(ABC):
    """Base class for payment gateway implementations"""

    @abstractmethod
    async def initialize_payment(
        self,
        amount: Decimal,
        email: str,
        transaction_ref: str,
        callback_url: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Initialize payment with gateway"""
        pass

    @abstractmethod
    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify payment status"""
        pass

    @abstractmethod
    def calculate_fee(self, amount: Decimal) -> Decimal:
        """Calculate gateway transaction fee"""
        pass
