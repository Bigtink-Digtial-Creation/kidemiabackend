from uuid import UUID
from fastapi_events.dispatcher import dispatch

from src.domains.auth.enums import UserType
from src.domains.auth.schemas.user import RegisterRequest
from src.shared.events.app_events import AppEvent
from src.shared.events.payloads import AssessmentCompletedPayload
from decimal import Decimal


def dispatch_user_registered(
    user_id: UUID, user_type: UserType, registration_data: RegisterRequest
):
    """Dispatch user registered event"""
    dispatch(
        "user:registered",
        payload={
            "user_id": user_id,
            "user_type": user_type,
            "registration_data": registration_data,
        },
    )


def dispatch_student_registered(student: dict):
    dispatch(
        "student_registered",
        payload={
            "student_id": student["id"],
            "user_id": student["user_id"],
        },
    )


def dispatch_assessment_completed(
    *,
    user_id: UUID,
    payload: AssessmentCompletedPayload,
):
    dispatch(
        AppEvent.ASSESSMENT_COMPLETED,
        payload={
            "user_id": user_id,
            **payload.model_dump(),
        },
    )


def dispatch_wallet_topup(user_id: UUID, amount: Decimal):
    """Dispatch wallet top up event"""
    dispatch(
        "token_topup",
        payload={"user_id": user_id, "amount": amount},
    )


def dispatch_payment_successful(transaction: dict):
    dispatch(
        "payment_successful",
        payload={
            "user_id": transaction["user_id"],
            "amount": transaction["amount"],
            "reference": transaction["reference"],
            "plan": transaction.get("plan", "unknown"),
        },
    )
    print(f"Dispatched: payment_successful for user {transaction['user_id']}")
