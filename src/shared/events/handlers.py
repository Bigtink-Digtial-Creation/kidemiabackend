from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event
from decimal import Decimal
import secrets
from sqlalchemy import func
from contextlib import contextmanager, asynccontextmanager
from src.config.database import get_db, get_async_db
from src.domains.auth.enums import UserType
from src.domains.auth.models.student import Student
from src.domains.payment.services.wallet_service import WalletService
from src.domains.gamification.event import GamificationEvents
from src.domains.assessment.models.category import AssessmentCategoryConfig
from src.domains.institution.models.institution import Institution
from src.domains.guardian.models.guardian import Guardian


@contextmanager
def get_sync_db_session():
    """Wrap sync db generator in context manager"""
    db = next(get_db())
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_session():
    """Wrap async db generator in async context manager"""
    db_gen = get_async_db()
    db = await anext(db_gen)
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


@local_handler.register(event_name="user:registered")
async def handle_user_registered(event: Event):
    event_name, payload = event

    user_type = payload.get("user_type")

    handlers = {
        UserType.STUDENT: handle_student_registration,
        UserType.GUARDIAN: handle_guardian_registration,
        UserType.INSTITUTION_ADMIN: handle_institution_admin_registration,
    }

    handler = handlers.get(user_type)
    if handler:
        await handler(payload)


async def handle_student_registration(payload: dict):
    user_id = payload.get("user_id")
    registration_data = payload.get("registration_data")
    student_id = None
    student_code = None

    # STEP 1: Create student profile (sync DB)
    with get_sync_db_session() as db:
        # Resolve category
        category_id = None
        if getattr(registration_data, "category", None):
            category = (
                db.query(AssessmentCategoryConfig)
                .filter(
                    func.lower(AssessmentCategoryConfig.category_name)
                    == registration_data.category.lower()
                )
                .first()
            )
            if category:
                category_id = category.id
            else:
                default = (
                    db.query(AssessmentCategoryConfig)
                    .filter(AssessmentCategoryConfig.is_active.is_(True))
                    .first()
                )
                if default:
                    category_id = default.id

        # Resolve institution
        institution_id = None
        if getattr(registration_data, "institution_code", None):
            inst = (
                db.query(Institution)
                .filter(Institution.code == registration_data.institution_code)
                .first()
            )
            if inst:
                institution_id = inst.id

        # Create the student
        student = Student(
            user_id=user_id,
            student_code=_generate_student_code(),
            category_id=category_id,
            institution_id=institution_id,
            guardian_email=getattr(registration_data, "guardian_email", None),
            preparation_level=getattr(registration_data, "preparation_level", None),
            target_exam_date=getattr(registration_data, "target_exam_date", None),
            is_active=True,
            is_suspended=False,
        )

        db.add(student)
        db.flush()
        student_id = student.id
        student_code = student.student_code

    print(f"Student profile created: {student_code}")

    # STEP 2: Wallet operations (async DB )
    if student_id:
        async with get_async_db_session() as async_db:
            wallet_service = WalletService(async_db)

            # Create wallet if missing
            user_wallet = await wallet_service.get_or_create_wallet(user_id=user_id)

            if user_wallet:
                # Credit welcome bonus
                await wallet_service.credit_wallet(
                    user_id=user_id,
                    amount=Decimal("100.00"),
                    description="Registration bonus",
                )
                print(f"Wallet credited for student: {student_code}")

            # STEP 3: Gamification profile
            await GamificationEvents.on_student_registered(
                db=async_db,
                student_id=student_id,
            )
            print(f"Gamification profile created for student: {student_id}")


async def handle_guardian_registration(payload: dict):
    """Create guardian profile and link existing students"""

    user_id = payload.get("user_id")
    registration_data = payload.get("registration_data")
    guardian_email = registration_data.email

    with get_sync_db_session() as db:
        # Create guardian profile
        guardian = Guardian(
            user_id=user_id,
            guardian_code=_generate_guardian_code(),
            relationship_type=getattr(registration_data, "relationship_type", None),
            receive_progress_reports=True,
            receive_performance_alerts=True,
            receive_payment_reminders=True,
            is_active=True,
            is_verified=False,
        )
        db.add(guardian)
        db.flush()

        guardian_id = guardian.id
        guardian_code = guardian.guardian_code

        students_to_link = (
            db.query(Student)
            .filter(
                Student.guardian_email == guardian_email,
                Student.guardian_id.is_(None),
            )
            .all()
        )

        # Link students to this guardian
        linked_count = 0
        for student in students_to_link:
            student.guardian_id = guardian_id
            linked_count += 1

        db.flush()

    if linked_count > 0:
        print(f"Linked {linked_count} existing student(s) to guardian {guardian_code}")


async def handle_institution_admin_registration(payload: dict):
    """Create institution record for institution admin"""

    user_id = payload.get("user_id")
    registration_data = payload.get("registration_data")

    with get_sync_db_session() as db:
        institution = Institution(
            name=getattr(
                registration_data,
                "institution_name",
                f"Institution-{secrets.token_hex(4).upper()}",
            ),
            code=_generate_institution_code(),
            owner_id=user_id,
            email=registration_data.email,
            phone=getattr(registration_data, "phone_number", None),
            country=getattr(registration_data, "country", "Nigeria"),
            state=getattr(registration_data, "state", None),
            city=getattr(registration_data, "city", None),
            is_verified=False,
            is_public=True,
            tier="basic",
            total_users=1,
            total_students=0,
            total_assessments=0,
            total_courses=0,
        )
        db.add(institution)
        db.flush()
        institution_name = institution.name
        institution_code = institution.code

    print(f"Institution created: {institution_name} ({institution_code})")


def _generate_student_code() -> str:
    return f"STU-{secrets.token_hex(4).upper()}"


def _generate_guardian_code() -> str:
    return f"GRD-{secrets.token_hex(4).upper()}"


def _generate_institution_code() -> str:
    return f"INS-{secrets.token_hex(4).upper()}"


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
