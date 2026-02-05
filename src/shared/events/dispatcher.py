from uuid import UUID
from fastapi_events.dispatcher import dispatch
from src.domains.auth.enums import UserType
from src.domains.auth.schemas.user import RegisterRequest
from src.shared.events.app_events import AppEvent
from src.shared.events.payloads import (
    AssessmentCompletedPayload,
    AssessmentResultPayload,
    WardAddPayload,
    WardRemovePayload,
    CategoryChangePayload,
    CategoryChangeApproved,
    ChallengeCompleted,
    ChallengeAssigned,
    SecurityAlertPayload,
    EmailVerificationPayload,
)
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


def dispatch_ward_remove(payload: WardRemovePayload):
    dispatch(
        AppEvent.WARD_REMOVE,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_ward_add(payload: WardAddPayload):
    dispatch(
        AppEvent.WARD_ADD,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_category_change_approve(payload: CategoryChangeApproved):
    dispatch(
        AppEvent.CATEGORY_APPROVED,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_category_change_request(payload: CategoryChangePayload):
    dispatch(
        AppEvent.CATEGORY_CHANGE,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_challenge_assigned(payload: ChallengeAssigned):
    dispatch(
        AppEvent.CHALLENGE_ASSIGNED,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_challenge_completed(payload: ChallengeCompleted):
    dispatch(
        AppEvent.CHALLENGE_COMPLETED,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_assessment_result(payload: AssessmentResultPayload):
    """Dispatch assessment result event"""
    dispatch(
        AppEvent.ASSESSMENT_RESULT,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_verification_email(payload: EmailVerificationPayload):
    dispatch(
        AppEvent.EMAIL_VERIFICATION,
        payload={
            **payload.model_dump(),
        },
    )


def dispatch_security_alert(payload: SecurityAlertPayload):
    """Call this for login alerts or deletion requests"""
    dispatch(
        AppEvent.SECURITY_ALERT,
        payload={
            **payload.model_dump(),
        },
    )
