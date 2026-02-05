from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from src.core.email_service import EmailService
from src.shared.utils.helpers import determine_client_type, get_client_base_url
from src.domains.guardian.repositories.guardian_repository import GuardianRepository
from src.domains.auth.repositories.student_repositoty import StudentRepository
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.templates.assessment_email_templates import (
    ward_assignment_template,
    guardian_completion_template,
    guardian_violation_template,
    due_date_reminder_template,
)


class ChallengNotificationService:
    """Handles all assessment-related email notifications via domain events."""

    def __init__(self, db: Session):
        self.db = db
        self.guardian_repo = GuardianRepository(db)
        self.student_repo = StudentRepository(db)
        self.assessment_repo = AssessmentRepository(db)
        self.email_service = EmailService(db)

    async def notify_ward_assignment(
        self,
        ward_user_id: UUID,
        assessment_id: UUID,
        guardian_id: UUID,
        due_date: Optional[datetime] = None,
        instructions: Optional[str] = None,
    ):
        student = self.student_repo.get_by_id(ward_user_id)
        if not student or not student.user:
            return

        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            return

        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian or not guardian.user:
            return

        client_type = determine_client_type(student.user)
        base_url = get_client_base_url(client_type)

        html_content = ward_assignment_template(
            student_name=student.user.full_name,
            guardian_name=guardian.user.full_name,
            assessment={
                "id": str(assessment.id),
                "title": assessment.title,
                "subject": assessment.subject.name if assessment.subject else "N/A",
                "total_questions": assessment.total_questions,
                "duration_minutes": assessment.duration_minutes,
                "max_attempts": assessment.max_attempts,
            },
            due_date=due_date,
            instructions=instructions,
            proctoring_enabled=assessment.proctoring_enabled,
            base_url=base_url,
        )

        await self.email_service.send_email(
            to_email=student.user.email,
            subject=f"New Assessment Assigned: {assessment.title}",
            html_content=html_content,
        )

    async def notify_guardian_completion(
        self,
        guardian_user_id: UUID,
        ward_user_id: UUID,
        assessment_id: UUID,
        attempt_id: UUID,
        score: float,
        percentage: float,
        passed: bool,
        auto_submitted: bool = False,
    ):
        guardian = self.guardian_repo.get_by_user_id(guardian_user_id)
        ward = self.student_repo.get_by_user_id(ward_user_id)
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if (
            not guardian
            or not guardian.user
            or not ward
            or not ward.user
            or not assessment
        ):
            return

        client_type = determine_client_type(guardian.user)
        base_url = get_client_base_url(client_type)

        html_content = guardian_completion_template(
            guardian_name=guardian.user.full_name,
            ward_name=ward.user.full_name,
            assessment={"id": str(assessment.id), "title": assessment.title},
            score=score,
            percentage=percentage,
            passed=passed,
            auto_submitted=auto_submitted,
            base_url=base_url,
            attempt_id=str(attempt_id),
        )

        await self.email_service.send_email(
            to_email=guardian.user.email,
            subject=f"Assessment Completed: {ward.user.full_name} - {assessment.title}",
            html_content=html_content,
        )

    async def notify_guardian_violation(
        self,
        guardian_user_id: UUID,
        ward_user_id: UUID,
        assessment_id: UUID,
        violation_type: str,
        violation_count: int,
    ):
        guardian = self.guardian_repo.get_by_user_id(guardian_user_id)
        ward = self.student_repo.get_by_user_id(ward_user_id)
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if (
            not guardian
            or not guardian.user
            or not ward
            or not ward.user
            or not assessment
        ):
            return

        client_type = determine_client_type(guardian.user)
        base_url = get_client_base_url(client_type)

        html_content = guardian_violation_template(
            guardian_name=guardian.user.full_name,
            ward_name=ward.user.full_name,
            assessment={"id": str(assessment.id), "title": assessment.title},
            violation_type=violation_type,
            violation_count=violation_count,
            base_url=base_url,
        )

        await self.email_service.send_email(
            to_email=guardian.user.email,
            subject=f"⚠️ Proctoring Alert: {ward.user.full_name} - {assessment.title}",
            html_content=html_content,
        )

    async def send_due_date_reminder(
        self,
        ward_user_id: UUID,
        assessment_id: UUID,
        due_date: datetime,
        hours_until_due: int,
    ):
        student = self.student_repo.get_by_user_id(ward_user_id)
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if not student or not student.user or not assessment:
            return

        client_type = determine_client_type(student.user)
        base_url = get_client_base_url(client_type)

        html_content = due_date_reminder_template(
            student_name=student.user.full_name,
            assessment={"id": str(assessment.id), "title": assessment.title},
            hours_until_due=hours_until_due,
            base_url=base_url,
            due_date=due_date,
        )

        await self.email_service.send_email(
            to_email=student.user.email,
            subject=f"⏰ Reminder: {assessment.title} due in {hours_until_due} hours",
            html_content=html_content,
        )
