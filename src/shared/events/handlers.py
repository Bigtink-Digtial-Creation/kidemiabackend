import secrets
from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event
from decimal import Decimal
from sqlalchemy import func, select
from src.domains.auth.enums import UserType
from src.domains.auth.models.student import Student
from src.domains.payment.services.wallet_service import WalletService
from src.domains.gamification.event import GamificationEvents
from src.domains.assessment.models.category import AssessmentCategoryConfig
from src.domains.institution.models.institution import Institution
from src.domains.guardian.models.guardian import Guardian
from src.shared.utils.db import get_async_db_session, get_sync_db_session
from src.shared.events.app_events import AppEvent
from src.shared.utils.helpers import parse_datetime

from src.core.email_service import EmailService
from src.shared.utils.helpers import get_full_name
from src.shared.utils.pdf_service import PDFService
from src.domains.guardian.services.notification_service import (
    ChallengNotificationService,
)
from src.domains.report.services.analytics_service import AnalyticsService
from src.domains.auth.repositories.student_repositoty import StudentRepository

from src.domains.templates.guardian_email_templates import (
    get_ward_invitation_html,
    get_ward_removal_html,
    get_category_change_request_html,
    get_category_decision_html,
)
from src.domains.templates.assessment_email_templates import (
    get_assessment_result_email_html,
)

from src.domains.templates.auth_email_templates import (
    get_welcome_email_html,
    get_auth_security_email_html,
    get_guardian_link_invitation_html,
)

from src.domains.templates.teacher_invite_email_template import (
    get_teacher_invitation_html,
)

from src.shared.events.payloads import UserRegisterPayload
from src.shared.events.dispatcher import dispatch_guardian_invitation
from src.domains.auth.schemas.user import AssignRolesToUserRequest
from src.domains.auth.services.user_service import UserService
from src.domains.auth.repositories.role_repository import RoleRepository


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

    with get_sync_db_session() as db:
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

        institution_id = getattr(registration_data, "institution_id", None)

        student = db.query(Student).filter(Student.user_id == user_id).first()
        is_new_student = student is None

        if student:
            student.category_id = category_id
            student.institution_id = institution_id
            student.guardian_email = getattr(
                registration_data, "guardian_email", student.guardian_email
            )
            student.preparation_level = getattr(
                registration_data, "preparation_level", student.preparation_level
            )
            student.target_exam_date = getattr(
                registration_data, "target_exam_date", student.target_exam_date
            )
            student.is_active = True
            student.is_suspended = False
        else:
            student = Student(
                user_id=user_id,
                student_code=_generate_student_code(),
                category_id=category_id,
                institution_id=institution_id,
                guardian_email=getattr(registration_data, "guardian_email", None),
                preparation_level=getattr(registration_data, "preparation_level", None),
                target_exam_date=getattr(registration_data, "target_exam_date", None),
                classroom_id=getattr(registration_data, "classroom_id", None),
                is_active=True,
                is_suspended=False,
            )
            db.add(student)

        db.flush()
        student_id = student.id

        user = student.user
        user_email = user.email
        user_full_name = get_full_name(user)
        guardian_email = student.guardian_email

        db.commit()

    if is_new_student:
        await send_registration_emails(
            payload=UserRegisterPayload(
                user_id=user_id,
                email=user_email,
                full_name=user_full_name,
                user_type="student",
            ),
        )

        if guardian_email:
            dispatch_guardian_invitation(
                student_name=user_full_name,
                guardian_email=guardian_email,
            )

    async with get_async_db_session() as async_db:
        wallet_service = WalletService(async_db)
        await wallet_service.get_or_create_wallet(user_id=user_id)
        await wallet_service.credit_wallet(
            user_id=user_id,
            amount=Decimal("100.00"),
            description="Registration bonus",
        )
        await GamificationEvents.on_student_registered(
            db=async_db,
            student_id=student_id,
        )


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
        # guardian_code = guardian.guardian_code

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
        pass
    await send_registration_emails(
        payload=UserRegisterPayload(
            user_id=user_id,
            email=guardian_email,
            full_name=get_full_name(guardian.user),
            user_type="guardian",
        )
    )


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


def _generate_student_code() -> str:
    return f"STU-{secrets.token_hex(4).upper()}"


def _generate_guardian_code() -> str:
    return f"GRD-{secrets.token_hex(4).upper()}"


def _generate_institution_code() -> str:
    return f"INS-{secrets.token_hex(4).upper()}"


async def send_registration_emails(payload: UserRegisterPayload):
    html_content = get_welcome_email_html(
        user_name=payload.full_name, user_type=payload.user_type
    )

    subject = (
        "Welcome to Kidemia! 🎁 Your Bonus is inside."
        if payload.user_type == "student"
        else f"Welcome to {'Kidemia'}!"
    )
    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=payload.email, subject=subject, html_content=html_content
        )


@local_handler.register(event_name=AppEvent.ASSESSMENT_COMPLETED)
async def handle_assessement_completed(event: Event):
    _, payload = event

    async with get_async_db_session() as async_db:
        stmt = select(Student).where(Student.user_id == payload["user_id"])
        result = await async_db.execute(stmt)
        student = result.scalar_one_or_none()

        if not student:
            return

        completed_at = parse_datetime(payload.get("completed_at"))

        await GamificationEvents.on_assessment_completed(
            db=async_db,
            student_id=student.id,
            assessment_id=payload["assessment_id"],
            category_id=payload.get("category_id"),
            score=payload["score"],
            total_questions=payload["total_questions"],
            time_taken_seconds=payload["time_taken_seconds"],
            completed_at=completed_at,
        )


@local_handler.register(event_name="token_topup")
async def handle_token_topup(event: Event):
    event_name, payload = event
    user_id = payload.get("user_id")
    amount = payload.get("amount")

    PRICE_PER_TOKEN = 10
    tokens_to_credit = amount / PRICE_PER_TOKEN

    async with get_async_db_session() as async_db:
        wallet_service = WalletService(async_db)
        user_wallet = await wallet_service.get_or_create_wallet(user_id=user_id)
        if user_wallet:
            await wallet_service.credit_wallet(
                user_id=user_id,
                amount=tokens_to_credit,
                description=f"Wallet topup: {amount} → {tokens_to_credit} tokens",
            )


@local_handler.register(event_name=AppEvent.WARD_ADD)
async def handle_ward_added(event: Event):
    _, payload = event

    html_content = get_ward_invitation_html(payload=payload)
    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=payload.get("email"),
            subject="Invitation to join Kidemia",
            html_content=html_content,
        )


@local_handler.register(event_name=AppEvent.WARD_REMOVE)
async def handle_ward_removed(event: Event):
    _, payload = event
    html_content = get_ward_removal_html(payload=payload)
    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=payload.get("email"),
            subject="KIDEMIA: Your Guardian just removed you!",
            html_content=html_content,
        )


@local_handler.register(event_name=AppEvent.CATEGORY_CHANGE)
async def handle_category_change_request(event: Event):
    _, payload = event
    html_content = get_category_change_request_html(payload=payload)
    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=payload.get("guardian_email"),
            subject="KIDEMIA: Your ward requested for a Category Change!",
            html_content=html_content,
        )


@local_handler.register(event_name=AppEvent.CATEGORY_APPROVED)
async def handle_category_change_approved(event: Event):
    _, payload = event
    html_content = get_category_decision_html(payload=payload)
    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=payload.get("ward_email"),
            subject="Study Category Change Decision",
            html_content=html_content,
        )


@local_handler.register(event_name=AppEvent.CHALLENGE_ASSIGNED)
async def handle_challenge_assign(event: Event):
    _, payload = event
    with get_sync_db_session() as db:
        service = ChallengNotificationService(db)
        await service.notify_ward_assignment(
            ward_user_id=payload.get("ward_user_id"),
            assessment_id=payload.get("assessment_id"),
            guardian_id=payload.get("guardian_id"),
            due_date=payload.get("due_date"),
            instructions=payload.get("instructions"),
        )


@local_handler.register(event_name=AppEvent.CHALLENGE_COMPLETED)
async def handle_challenge_completed(event: Event):
    _, payload = event
    with get_sync_db_session() as db:
        service = ChallengNotificationService(db)
        await service.notify_guardian_completion(
            guardian_user_id=payload.get("guardian_user_id"),
            ward_user_id=payload.get("ward_user_id"),
            assessment_id=payload.get("assessment_id"),
            attempt_id=payload.get("attempt_id"),
            score=payload.get("score"),
            percentage=payload.get("percentage"),
            passed=payload.get("passed"),
            auto_submitted=payload.get("auto_submitted"),
        )


@local_handler.register(event_name=AppEvent.ASSESSMENT_RESULT)
async def handle_assessment_result(event: Event):
    _, payload = event

    user_id = payload["user_id"]
    assessment_title = payload.get("assessment_title")
    score = payload.get("score")
    total_questions = payload.get("total_questions")
    passed = payload.get("passed")

    with get_sync_db_session() as db:
        student_repo = StudentRepository(db)
        student = student_repo.get_by_user_id(user_id)

        analytics_service = AnalyticsService(db)
        analytics_data = await analytics_service.get_topic_analytics(
            student_id=student.id
        )

        pdf_service = PDFService()
        pdf_bytes = await pdf_service.generate_detailed_report(
            base_data={
                "assessment_title": assessment_title,
                "student_name": get_full_name(student.user),
            },
            analytics=analytics_data,
        )

        html_content = get_assessment_result_email_html(
            student_name=student.user.first_name,
            assessment_title=assessment_title,
            score=score,
            total_questions=total_questions,
            passed=passed,
        )

        # Send email with PDF attachment
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=student.user.email,
            subject="Your Assessment Results & Study Plan",
            html_content=html_content,
            file_content=pdf_bytes,
            filename="Kidemia_Report.pdf",
        )


@local_handler.register(event_name=AppEvent.EMAIL_VERIFICATION)
async def handle_email_verification(event: Event):
    _, payload = event

    with get_sync_db_session() as db:
        email_service = EmailService(db)

        await email_service.send_email(
            to_email=payload["user_email"],
            subject="Email Verification",
            html_content=email_service.send_verification_email(
                token=payload["verify_token"], client_type=payload["client_type"]
            ),
        )


@local_handler.register(event_name=AppEvent.SECURITY_ALERT)
async def handle_security_email(event: Event):
    _, payload = event

    html_content = get_auth_security_email_html(
        user_name=payload["full_name"],
        action_type=payload["action_type"],
        details=payload["details"],
        user_type=payload["user_type"],
    )
    subject = (
        "⚠️ Security Alert: Account Deletion"
        if "deletion" in payload["action_type"]
        else "New Login Detected"
    )
    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=payload["email"], subject=subject, html_content=html_content
        )


@local_handler.register(event_name="auth:guardian_invite_requested")
async def handle_guardian_invitation_email(event: Event):
    _, payload = event

    html_content = get_guardian_link_invitation_html(
        student_name=payload["student_name"], guardian_email=payload["guardian_email"]
    )

    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=payload["guardian_email"],
            subject=f"Action Required: Join {payload['student_name']} on Kidemia",
            html_content=html_content,
        )


@local_handler.register(event_name=AppEvent.INSTITUTION_WELCOME_EMAIL)
async def handle_institution_welcome_email(event: Event):
    _, payload = event
    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_institution_welcome_email(
            email=payload["email"],
            temp_password=payload["temp_pw"],
            institution=payload["institution"],
            client_type="admin",
        )


async def assign_role(db, user_id: str, role_name: str):
    user_service = UserService(db)
    role_repo = RoleRepository(db)

    user = await user_service.get_user(user_id)
    if not user:
        print(f"User {user_id} not found")
        return

    role = role_repo.get_by_name(role_name)
    if not role:
        print(f"Role {role_name} not found")
        return

    roles_data = AssignRolesToUserRequest(role_ids=[role.id])
    await user_service.assign_roles(user_id, roles_data)


@local_handler.register(event_name=AppEvent.ASSIGNED_ROLE_USER)
async def assign_role_user(event: Event):
    _, payload = event
    user_id = payload.get("user_id")
    role_name = payload.get("role_name")
    if not user_id or not role_name:
        return

    with get_sync_db_session() as db:
        await assign_role(db, user_id, role_name)


@local_handler.register(event_name=AppEvent.ASSIGNED_INSTITUTION_ADMIN_ROLE)
async def assign_role_institution_admin(event: Event):
    _, payload = event
    user_id = payload.get("user_id")
    if not user_id:
        print("Missing user_id in payload")
        return

    with get_sync_db_session() as db:
        await assign_role(db, user_id, "institution_admin")


@local_handler.register(event_name=AppEvent.TEACHER_INVITATION)
async def handle_teacher_invitation_mail(event: Event):
    _, payload = event

    teacher_name = payload["teacher_name"]
    teacher_email = payload["teacher_email"]
    institution_name = payload["institution_name"]
    temp_password = payload["temp_password"]
    user_type = payload["user_type"]

    html_content = get_teacher_invitation_html(
        teacher_name=teacher_name,
        teacher_email=teacher_email,
        institution_name=institution_name,
        temp_password=temp_password,
        user_type=user_type,
    )

    with get_sync_db_session() as db:
        email_service = EmailService(db)
        await email_service.send_email(
            to_email=teacher_email,
            subject="KIDEMIA: Join Kidemia As A Teacher!",
            html_content=html_content,
        )
