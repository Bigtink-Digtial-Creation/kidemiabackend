from sqlalchemy.orm import Session
from src.domains.payment.models.paystack_subscription import PaystackPlan
from src.shared.repositories.base import BaseRepository
from typing import Optional


class PaystackPlanRepository(BaseRepository[PaystackPlan, dict, dict]):
    def __init__(self, db: Session):
        self.db = db
        self.model = PaystackPlan

    def get_by_internal_code(self, internal_plan_code: str) -> Optional[PaystackPlan]:
        """Get a Paystack plan by internal plan code"""
        return (
            self.db.query(self.model)
            .filter(self.model.internal_plan_code == internal_plan_code)
            .first()
        )

    def get_by_paystack_code(self, paystack_plan_code: str) -> Optional[PaystackPlan]:
        """Get a Paystack plan by Paystack plan code"""
        return (
            self.db.query(self.model)
            .filter(self.model.paystack_plan_code == paystack_plan_code)
            .first()
        )
