from uuid import UUID
from sqlalchemy.orm import Session
from src.domains.payment.repositories.transaction_repository import (
    TransactionRepository,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.payment.repositories.subscription_repository import (
    SubscriptionRepository,
)
from src.domains.payment.enums import TransactionStatus
from src.domains.assessment.enums import AssessmentType


class AssessmentAccessService:
    """Service to check if user has paid for assessment"""

    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.assessment_repo = AssessmentRepository(db)

    async def has_access(self, user_id: UUID, assessment_id: UUID) -> bool:
        """Check if user has access to assessment"""
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if not assessment:
            return False

        # Free tests are always accessible
        if assessment.assessment_type == AssessmentType.TEST:
            return True

        # Check if user has active subscription

        sub_repo = SubscriptionRepository(self.db)
        subscription = sub_repo.get_active_subscription(user_id)

        if subscription and subscription.is_active:
            # Check subscription limits
            if subscription.exams_limit is None:  # Unlimited
                return True

            if subscription.exams_taken < subscription.exams_limit:
                return True

        # Check if user has purchased this specific exam
        purchases = self.transaction_repo.get_all(
            filters={
                "user_id": user_id,
                "assessment_id": assessment_id,
                "status": TransactionStatus.COMPLETED,
                "is_deleted": False,
            }
        )

        return len(purchases) > 0

    async def grant_access(
        self, user_id: UUID, assessment_id: UUID, transaction_id: UUID
    ) -> bool:
        """Grant access after successful payment"""
        # Create access record or update subscription usage
        subscription_repo = SubscriptionRepository(self.db)
        subscription = subscription_repo.get_active_subscription(user_id)

        if subscription:
            subscription.exams_taken += 1
            self.db.commit()

        return True
