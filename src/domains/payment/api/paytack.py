from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
import json

from src.core.security import get_db
from src.domains.payment.gateways.paystack import PaystackGateway
from src.domains.payment.webhooks.paystack_webhook import PaystackWebHookHandler

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/paystack", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Paystack webhook endpoint for handling payment and subscription events.

    Important events:
    - charge.success: One-time payment successful
    - subscription.create: Subscription created
    - invoice.create: Invoice created (upcoming charge)
    - invoice.update: Invoice updated (payment processed)
    - invoice.payment_failed: Payment failed
    - subscription.disable: Subscription disabled/cancelled
    """
    # Get raw payload
    webhook = PaystackWebHookHandler(db)
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature"
        )

    # Verify webhook signature
    paystack = PaystackGateway()
    try:
        paystack.verify_webhook(payload, signature)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Parse event
    try:
        event_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    event_type = event_data.get("event")
    data = event_data.get("data", {})

    # Route to appropriate handler
    if event_type == "charge.success":
        # Handle one-time payment success
        return await webhook.handle_charge_success(data)

    elif event_type in [
        "subscription.create",
        "invoice.create",
        "invoice.update",
        "invoice.payment_failed",
        "subscription.disable",
        "subscription.not_renew",
    ]:
        # Handle subscription events
        return await webhook.handle_subscription_event(event_type, data)

    # Return success for unhandled events
    return {"status": "ok", "message": f"Event {event_type} received but not processed"}


# Optional: Add webhook verification endpoint for testing
@router.get("/paystack/test", status_code=status.HTTP_200_OK)
async def test_paystack_webhook():
    """Test endpoint to verify webhook is reachable"""
    return {"status": "ok", "message": "Webhook endpoint is active"}
