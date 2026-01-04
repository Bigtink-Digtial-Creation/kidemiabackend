from sqlalchemy.orm import Session
from src.domains.payment.services.transaction_service import TransactionService
from src.domains.payment.services.subscription_billing_service import (
    SubscriptionBillingService,
)


class PaystackWebHookHandler:
    """Service for subscription operations"""

    def __init__(self, db: Session):
        self.db = db
        self.billing_service = SubscriptionBillingService(db)
        self.trans_service = TransactionService(db)

    async def handle_charge_success(self, data: dict):
        """Handle one-time payment success (wallet topup, exam purchase, etc.)"""
        reference = data.get("reference")

        if not reference:
            return {"status": "ignored", "message": "No reference found"}

        # Check if this is a subscription payment (skip if it is)
        metadata = data.get("metadata", {})
        if metadata.get("subscription_id"):
            return {
                "status": "ignored",
                "message": "Subscription payment, handled separately",
            }

        # Use transaction service to handle payment verification
        try:
            await self.trans_service.handle_webhook(
                "paystack", {"event": "charge.success", "data": data}
            )
            return {"status": "ok", "message": "Payment processed successfully"}
        except Exception as e:
            print(f"Error processing charge.success: {e}")
            return {"status": "error", "message": str(e)}

    async def handle_subscription_event(self, event_type: str, data: dict):
        """Handle subscription-related events"""

        try:
            success = await self.billing_service.handle_webhook_event(event_type, data)

            if success:
                return {
                    "status": "ok",
                    "message": f"Event {event_type} processed successfully",
                }
            else:
                return {
                    "status": "ignored",
                    "message": f"Event {event_type} could not be processed",
                }

        except Exception as e:
            print(f"Error processing {event_type}: {e}")
            return {"status": "error", "message": str(e)}
