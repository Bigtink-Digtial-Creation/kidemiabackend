from fastapi_events.dispatcher import dispatch


async def user_registered(user: dict):
    dispatch(
        "user_registered",
        payload={
            "user_id": user["id"],
            "email": user["email"],
            "name": user["name"],
        },
    )
    print(f"Dispatched: user_registered for {user['email']}")


async def course_enrolled(enrollment: dict):
    dispatch(
        "course_enrolled",
        payload={
            "user_id": enrollment["user_id"],
            "course_id": enrollment["course_id"],
            "course_title": enrollment["course_title"],
        },
    )
    print(f"Dispatched: course_enrolled for course {enrollment['course_title']}")


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
    print(f"Dispatched: quiz_completed for quiz {result['quiz_id']}")


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
