from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from src.shared.repositories.base import BaseRepository
from src.domains.payment.models.transaction import Transaction
from src.domains.payment.enums import TransactionStatus, TransactionType


class TransactionRepository(BaseRepository[Transaction, dict, dict]):
    """Repository for Transaction model"""

    def __init__(self, db: Session):
        super().__init__(Transaction, db)

    def get_by_reference(self, reference: str) -> Optional[Transaction]:
        """Get transaction by reference"""
        return (
            self.db.query(Transaction)
            .filter(Transaction.transaction_reference == reference)
            .first()
        )

    def get_by_gateway_reference(self, gateway_ref: str) -> Optional[Transaction]:
        """Get transaction by gateway reference"""
        return (
            self.db.query(Transaction)
            .filter(Transaction.gateway_reference == gateway_ref)
            .first()
        )

    def get_user_transactions(
        self,
        user_id: UUID,
        status: Optional[TransactionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Transaction]:
        """Get transactions for a user"""
        query = self.db.query(Transaction).filter(
            Transaction.user_id == user_id, Transaction.is_deleted.is_(False)
        )

        if status:
            query = query.filter(Transaction.status == status)

        return (
            query.order_by(desc(Transaction.created_at)).offset(skip).limit(limit).all()
        )

    def get_pending_transactions(
        self, older_than_minutes: int = 30
    ) -> List[Transaction]:
        """Get pending transactions older than specified minutes"""
        cutoff_time = (
            datetime.utcnow() - timedelta(minutes=older_than_minutes)
        ).isoformat()

        return (
            self.db.query(Transaction)
            .filter(
                Transaction.status == TransactionStatus.PENDING,
                Transaction.initiated_at < cutoff_time,
                Transaction.is_deleted.is_(False),
            )
            .all()
        )

    def get_total_revenue(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Decimal:
        """Calculate total revenue"""
        query = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.transaction_type.in_(
                [TransactionType.EXAM_PURCHASE, TransactionType.SUBSCRIPTION]
            ),
            Transaction.is_deleted.is_(False),
        )

        if start_date:
            query = query.filter(Transaction.completed_at >= start_date)
        if end_date:
            query = query.filter(Transaction.completed_at <= end_date)

        result = query.scalar()
        return result or Decimal("0.00")

    def get_assessment_purchases(self, assessment_id: UUID) -> List[Transaction]:
        """Get all purchases for an assessment"""
        return (
            self.db.query(Transaction)
            .filter(
                Transaction.assessment_id == assessment_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.is_deleted.is_(False),
            )
            .all()
        )
