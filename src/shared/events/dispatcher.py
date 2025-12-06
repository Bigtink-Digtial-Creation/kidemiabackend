from uuid import UUID
from fastapi_events.dispatcher import dispatch

from src.domains.auth.enums import UserType
from src.domains.auth.schemas.user import RegisterRequest


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


async def student_registered(student: dict):
    dispatch(
        "student_registered",
        payload={
            "student_id": student["id"],
            "user_id": student["user_id"],
        },
    )


async def course_enrolled(enrollment: dict):
    dispatch(
        "course_enrolled",
        payload={
            "user_id": enrollment["user_id"],
            "course_id": enrollment["course_id"],
            "course_title": enrollment["course_title"],
        },
    )


async def quiz_completed(result: dict):
    dispatch(
        "quiz_completed",
        payload={
            "user_id": result["user_id"],
            "quiz_id": result["quiz_id"],
            "score": result["score"],
            "passed": result["passed"],
        },
    )


async def payment_successful(transaction: dict):
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
