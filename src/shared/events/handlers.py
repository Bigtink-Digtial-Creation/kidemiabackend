from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event
from src.domains.payment.services.wallet_service import WalletService
from contextlib import contextmanager
from decimal import Decimal
from src.config.database import get_db


@contextmanager
def db_session():
    db_gen = get_db()
    db = next(db_gen)
    try:
        yield db
    finally:
        db.close()


@local_handler.register(event_name="user_registered")
async def handle_user_registered(event: Event):
    event_name, payload = event
    print(f"Event '{event_name}' received for {payload['email']}")

    with db_session() as db:
        # Actions:
        # - Send welcome email
        # - Award signup bonus points
        # - Log audit trail
        wallet_service = WalletService(db)
        await wallet_service.get_or_create_wallet(payload["user_id"])
        signup_bonus = Decimal("1000.00")
        await wallet_service.credit_wallet(
            user_id=payload["user_id"], amount=signup_bonus, description="Signup bonus"
        )


@local_handler.register(event_name="course_enrolled")
async def handle_course_enrolled(event: Event):
    event_name, payload = event
    print(f"Event '{event_name}' received for course {payload['course_title']}")
    # Actions:
    # - Send enrollment confirmation
    # - Notify instructor
    # - Initialize progress tracking


@local_handler.register(event_name="quiz_completed")
async def handle_quiz_completed(event: Event):
    event_name, payload = event
    print(f"Event '{event_name}' received for user {payload['user_id']}")
    # Actions:
    # - Update leaderboard
    # - Trigger certificate check
    # - Notify user of result


@local_handler.register(event_name="payment_successful")
async def handle_payment_successful(event: Event):
    event_name, payload = event
    print(f"Event '{event_name}' received — ref: {payload['reference']}")
    # Actions:
    # - Activate subscription
    # - Send receipt email
    # - Notify finance dashboard
