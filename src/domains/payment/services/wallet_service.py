from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session

from src.core.exceptions import ResourceNotFoundException, BusinessLogicException

# from src.core.security import verify_password
from src.domains.payment.models.wallet import Wallet
from src.domains.payment.schemas.wallet import WalletResponse


class WalletService:
    """Service for wallet operations"""

    def __init__(self, db: Session):
        self.db = db

    async def get_or_create_wallet(self, user_id: UUID) -> WalletResponse:
        """Get or create user wallet"""
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user_id).first()

        if not wallet:
            wallet = Wallet(
                user_id=user_id, balance=Decimal("0.00"), created_by=user_id
            )
            self.db.add(wallet)
            self.db.commit()
            self.db.refresh(wallet)

        return WalletResponse.model_validate(wallet)

    async def credit_wallet(
        self, user_id: UUID, amount: Decimal, description: str = "Wallet credit"
    ) -> WalletResponse:
        """Credit wallet"""
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            raise ResourceNotFoundException("Wallet", user_id)

        wallet.balance += amount
        self.db.commit()
        self.db.refresh(wallet)

        return WalletResponse.model_validate(wallet)

    async def debit_wallet(
        self, user_id: UUID, amount: Decimal, description: str = "Wallet debit"
    ) -> WalletResponse:
        """Debit wallet"""
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            raise ResourceNotFoundException("Wallet", user_id)

        if wallet.balance < amount:
            raise BusinessLogicException("Insufficient wallet balance")

        wallet.balance -= amount
        self.db.commit()
        self.db.refresh(wallet)

        return WalletResponse.model_validate(wallet)
