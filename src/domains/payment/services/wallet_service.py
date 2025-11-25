from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.exceptions import ResourceNotFoundException, BusinessLogicException

from src.domains.payment.models.wallet import Wallet
from src.domains.payment.schemas.wallet import WalletResponse


class WalletService:
    """Service for wallet operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_wallet(self, user_id: UUID) -> WalletResponse:
        """Get or create user wallet"""
        # Use select() instead of query()
        stmt = select(Wallet).filter(Wallet.user_id == user_id)
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()

        if not wallet:
            wallet = Wallet(
                user_id=user_id, balance=Decimal("0.00"), created_by=user_id
            )
            self.db.add(wallet)
            await self.db.flush()  # Use flush instead of commit
            await self.db.refresh(wallet)

        return WalletResponse.model_validate(wallet)

    async def credit_wallet(
        self, user_id: UUID, amount: Decimal, description: str = "Wallet credit"
    ) -> WalletResponse:
        """Credit wallet"""
        stmt = select(Wallet).filter(Wallet.user_id == user_id)
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise ResourceNotFoundException("Wallet", user_id)

        wallet.balance += amount
        await self.db.flush()  # Use flush instead of commit
        await self.db.refresh(wallet)

        return WalletResponse.model_validate(wallet)

    async def debit_wallet(
        self, user_id: UUID, amount: Decimal, description: str = "Wallet debit"
    ) -> WalletResponse:
        """Debit wallet"""
        stmt = select(Wallet).filter(Wallet.user_id == user_id)
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise ResourceNotFoundException("Wallet", user_id)

        if wallet.balance < amount:
            raise BusinessLogicException("Insufficient wallet balance")

        wallet.balance -= amount
        await self.db.flush()  # Use flush instead of commit
        await self.db.refresh(wallet)

        return WalletResponse.model_validate(wallet)

    async def get_wallet(self, user_id: UUID) -> WalletResponse:
        """Get user wallet"""
        stmt = select(Wallet).filter(Wallet.user_id == user_id)
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise ResourceNotFoundException("Wallet", user_id)

        return WalletResponse.model_validate(wallet)
