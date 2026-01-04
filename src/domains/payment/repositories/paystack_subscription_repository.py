from sqlalchemy.orm import Session
from uuid import UUID
from src.domains.payment.models.paystack_subscription import PaystackSubscription


class PaystackSubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db
        self.model = PaystackSubscription

    def create(self, data: dict) -> PaystackSubscription:
        record = self.model(**data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_subscription_id(self, subscription_id: UUID):
        return (
            self.db.query(self.model)
            .filter(self.model.subscription_id == subscription_id)
            .first()
        )

    def get_by_paystack_code(self, subscription_code: str):
        return (
            self.db.query(self.model)
            .filter(self.model.paystack_subscription_code == subscription_code)
            .first()
        )

    def update(self, record_id: UUID, data: dict):
        self.db.query(self.model).filter(self.model.id == record_id).update(data)
        self.db.commit()
