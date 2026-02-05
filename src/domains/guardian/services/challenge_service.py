from uuid import UUID
import random
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session
from src.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
    AuthorizationException,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.content.repositories.subject_repository import SubjectRepository
from src.domains.content.repositories.topic_repository import TopicRepository
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.guardian.repositories.guardian_repository import GuardianRepository
from src.domains.auth.repositories.student_repositoty import StudentRepository
from src.domains.assessment.schemas.assessment import AssessmentCreate
from src.domains.guardian.schemas.guardian import (
    CreateAssessmentForWardsRequest,
    AssessmentAssignmentResponse,
    AssignmentResponse,
)
from src.domains.guardian.models.guardian import AssessmentAssignment
from src.domains.guardian.enums import AssignmentStatus
from src.domains.assessment.enums import (
    AssessmentType,
    AssessmentCategory,
    QuestionSelectionMode,
    ResultDisplayMode,
)
from src.domains.assessment.services.assessment_service import AssessmentService
from src.domains.payment.services.subscription_service import SubscriptionService
from src.domains.guardian.services.notification_service import (
    ChallengNotificationService,
)
from src.domains.assessment.services.attempt_service import AssessmentAttemptService
from src.domains.assessment.models.assessment import AssessmentProctoringEvent
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.auth.models.student import Student

from src.shared.events.dispatcher import (
    dispatch_challenge_assigned,
    dispatch_challenge_completed,
)
from src.shared.events.payloads import ChallengeAssigned, ChallengeCompleted


class ChallengeAssessmentService:
    """
    Dedicated service for creating and managing guardian-assigned assessments.
    """

    def __init__(self, db: Session):
        self.db = db
        self.assessment_repo = AssessmentRepository(db)
        self.subject_repo = SubjectRepository(db)
        self.topic_repo = TopicRepository(db)
        self.question_repo = QuestionRepository(db)
        self.guardian_repo = GuardianRepository(db)
        self.student_repo = StudentRepository(db)

    async def create_and_assign_assessment(
        self,
        guardian_id: UUID,
        user_id: UUID,
        request_data: CreateAssessmentForWardsRequest,
    ) -> AssessmentAssignmentResponse:
        """
        Create a fully-featured assessment and assign to wards.

        Flow:
        1. Validate guardian permissions
        2. Check subscription limits
        3. Verify wards belong to guardian
        4. Fetch and validate questions from selected topics
        5. Create assessment with FULL proctoring features
        6. Publish assessment
        7. Create assignment records for each ward
        8. Send notifications to wards
        9. Log activity
        10. Return assignment details
        """

        # 1. Validate guardian
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to create assessments")

        # 2. Check subscription limits
        subscription_service = SubscriptionService(self.db)
        can_create, message = await subscription_service.check_usage_limit(
            user_id, "test"
        )
        if not can_create:
            raise BusinessLogicException(message)

        # 3. Verify all wards belong to guardian
        ward_users = []
        for ward_id in request_data.ward_ids:
            student = self.student_repo.get_by_id(ward_id)
            if not student or student.guardian_id != guardian_id:
                raise ValidationException(f"Ward {ward_id} does not belong to you")
            ward_users.append(student.user_id)

        # 4. Validate subject and topics
        subject = self.subject_repo.get_by_id(request_data.subject_id)
        if not subject:
            raise ResourceNotFoundException("Subject", request_data.subject_id)

        topics = []
        for topic_id in request_data.topic_ids:
            topic = self.topic_repo.get_by_id(topic_id)
            if not topic:
                raise ResourceNotFoundException("Topic", topic_id)
            if topic.subject_id != request_data.subject_id:
                raise ValidationException(
                    f"Topic {topic.name} does not belong to subject {subject.name}"
                )
            topics.append(topic)

        # 5. Fetch questions from topics
        question_ids = self._select_questions(
            topic_ids=[t.id for t in topics],
            num_questions=request_data.number_of_questions,
        )

        # 6. Create assessment with FULL configuration
        assessment_code = self._generate_unique_code(subject.code)
        topic_names = [t.name for t in topics]

        assessment_data = AssessmentCreate(
            # Basic info
            title=f"{subject.name} Challenge",
            code=assessment_code,
            description=request_data.instructions
            or f"Challenge covering: {', '.join(topic_names)}",
            instructions=request_data.instructions
            or "Complete all questions to the best of your ability.",
            assessment_type=AssessmentType.TEST,
            category=AssessmentCategory.GENERAL,
            subject_id=request_data.subject_id,
            topic_ids=request_data.topic_ids,
            question_ids=question_ids,
            price=0.00,
            currency="NGN",
            duration_minutes=request_data.duration_minutes,
            available_from=(
                request_data.available_from or datetime.utcnow()
            ).isoformat(),
            available_until=request_data.due_date.isoformat()
            if request_data.due_date
            else None,
            question_selection_mode=QuestionSelectionMode.MANUAL,
            passing_percentage=request_data.passing_percentage or 50.00,
            shuffle_questions=request_data.shuffle_questions,
            shuffle_options=request_data.shuffle_options,
            allow_question_navigation=request_data.allow_question_navigation,
            allow_backward_navigation=request_data.allow_review,
            max_attempts=request_data.max_attempts or 1,
            result_display_mode=request_data.result_display_mode
            or ResultDisplayMode.AFTER_DUE_DATE,
            show_correct_answers=request_data.show_correct_answers
            if request_data.show_correct_answers is not None
            else False,
            show_explanations=request_data.show_explanations
            if request_data.show_explanations is not None
            else False,
            proctoring_enabled=request_data.enable_proctoring
            if request_data.enable_proctoring is not None
            else True,
            require_webcam=request_data.require_webcam
            if request_data.require_webcam is not None
            else True,
            fullscreen_required=request_data.fullscreen_required
            if request_data.fullscreen_required is not None
            else True,
            detect_tab_switching=request_data.detect_tab_switching
            if request_data.detect_tab_switching is not None
            else True,
            max_tab_switches=request_data.max_tab_switches or 3,
            is_public=False,
            require_enrollment=False,
            sections=[],
        )

        # 7. Create and publish assessment
        assessment_service = AssessmentService(self.db)
        assessment = await assessment_service.create_assessment(
            assessment_data, user_id
        )

        # Publish immediately so wards can access
        await assessment_service.publish_assessment(assessment.id, user_id)

        # 8. Create assignment records for each ward
        assignments = []
        for ward_id in request_data.ward_ids:
            assignment = AssessmentAssignment(
                assessment_id=assessment.id,
                ward_id=ward_id,
                assigned_by=guardian_id,
                status=AssignmentStatus.ASSIGNED,
                due_date=request_data.due_date,
                instructions=request_data.instructions,
                assigned_at=datetime.utcnow(),
            )
            self.db.add(assignment)
            self.db.flush()

            # Build response
            student = self.student_repo.get_by_id(ward_id)
            assignments.append(
                AssignmentResponse(
                    id=assignment.id,
                    assessment_id=assessment.id,
                    assessment_title=assessment.title,
                    ward_id=ward_id,
                    ward_name=student.user.full_name
                    if student and student.user
                    else "Unknown",
                    assigned_by=user_id,
                    due_date=request_data.due_date,
                    status="assigned",
                    assigned_at=assignment.assigned_at,
                )
            )

        self.db.commit()

        await subscription_service.log_activity(
            user_id=user_id,
            activity_type="test",
            activity_id=assessment.id,
        )

        # 10. Send notifications to wards
        for ward_id in request_data.ward_ids:
            dispatch_challenge_assigned(
                payload=ChallengeAssigned(
                    ward_user_id=ward_id,
                    assessment_id=assessment.id,
                    guardian_id=guardian.id,
                    due_date=request_data.due_date if request_data.due_date else None,
                    instructions=request_data.instructions
                    if request_data.instructions
                    else None,
                )
            )

        return AssessmentAssignmentResponse(
            assessment_id=assessment.id,
            assessment_title=assessment.title,
            total_questions=len(question_ids),
            duration_minutes=request_data.duration_minutes,
            assigned_to=request_data.ward_ids,
            assignments=assignments,
            message=f"Assessment created and assigned to {len(request_data.ward_ids)} ward(s) successfully!",
        )

    def _select_questions(
        self, topic_ids: List[UUID], num_questions: int
    ) -> List[UUID]:
        """
        Select questions from topics.

        Strategy:
        1. Distribute questions evenly across topics
        2. Prioritize variety in difficulty
        3. Ensure approved questions only
        """
        available_ids = self.question_repo.get_ids_by_topics(
            topic_ids=topic_ids,
            difficulty=None,  # Mix of all difficulties
            question_types=None,  # All types
        )

        if not available_ids:
            raise BusinessLogicException(
                "No approved questions found for the selected topics. "
                "Please select different topics or add more questions."
            )

        if len(available_ids) < num_questions:
            raise BusinessLogicException(
                f"Not enough questions available. Found {len(available_ids)}, "
                f"need {num_questions}. Please reduce the number of questions "
                f"or select more topics."
            )

        # Randomly select to ensure variety
        selected_ids = random.sample(available_ids, num_questions)
        return selected_ids

    def _generate_unique_code(self, subject_code: str) -> str:
        """Generate unique assessment code"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        code = f"GRD-{subject_code}-{timestamp}-{random_suffix}"

        # Ensure uniqueness
        counter = 1
        original_code = code
        while self.assessment_repo.code_exists(code):
            code = f"{original_code}-{counter}"
            counter += 1

        return code

    def _generate_title(self, subject_name: str, topic_names: List[str]) -> str:
        """Generate assessment title"""
        if len(topic_names) <= 2:
            topics_str = " & ".join(topic_names)
        else:
            topics_str = f"{topic_names[0]} & {len(topic_names) - 1} more"

        return f"{subject_name} - {topics_str}"

    async def get_ward_assignments_for_student(
        self,
        student_id: UUID,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """Get all assignments for a specific student (ward view)"""
        from src.domains.guardian.models.guardian import AssessmentAssignment
        from src.domains.guardian.enums import AssignmentStatus
        from datetime import datetime

        query = self.db.query(AssessmentAssignment).filter(
            AssessmentAssignment.ward_id == student_id
        )

        # Apply status filter
        if status_filter:
            try:
                status_enum = AssignmentStatus(status_filter)
                query = query.filter(AssessmentAssignment.status == status_enum)
            except ValueError:
                pass

        # Check for overdue assignments
        now = datetime.utcnow()
        query = query.outerjoin(AssessmentAssignment.assessment)

        assignments = query.offset(skip).limit(limit).all()

        # Build response
        result = []
        for assignment in assignments:
            assessment = assignment.assessment
            guardian = assignment.guardian

            # Calculate attempts remaining
            assessment.max_attempts - assignment.attempt_count

            # Check if overdue
            status = assignment.status
            if (
                assignment.due_date
                and assignment.due_date < now
                and status != AssignmentStatus.COMPLETED
            ):
                status = "overdue"

            result.append(
                {
                    "id": str(assignment.id),
                    "assessment_id": str(assessment.id),
                    "assessment_title": assessment.title,
                    "subject_name": assessment.subject.name
                    if assessment.subject
                    else None,
                    "topic_count": len(assessment.topic_ids)
                    if assessment.topic_ids
                    else 0,
                    "total_questions": assessment.total_questions,
                    "duration_minutes": assessment.duration_minutes,
                    "assigned_by_name": guardian.user.full_name
                    if guardian and guardian.user
                    else "Guardian",
                    "assigned_at": assignment.assigned_at.isoformat(),
                    "due_date": assignment.due_date.isoformat()
                    if assignment.due_date
                    else None,
                    "instructions": assignment.instructions,
                    "status": status,
                    "attempt_count": assignment.attempt_count,
                    "max_attempts": assessment.max_attempts,
                    "requires_webcam": assessment.require_webcam,
                    "requires_fullscreen": assessment.fullscreen_required,
                    "detects_tab_switching": assessment.detect_tab_switching,
                    "started_at": assignment.started_at.isoformat()
                    if assignment.started_at
                    else None,
                    "completed_at": assignment.completed_at.isoformat()
                    if assignment.completed_at
                    else None,
                    "score": None,  # TODO: Get from attempts
                    "passed": None,  # TODO: Get from attempts
                }
            )

        return result

    async def get_assignment_detail_for_student(
        self,
        assignment_id: UUID,
        student_id: UUID,
    ):
        """Get detailed assignment information for student"""
        from src.domains.guardian.models.guardian import AssessmentAssignment

        assignment = (
            self.db.query(AssessmentAssignment)
            .filter(
                AssessmentAssignment.id == assignment_id,
                AssessmentAssignment.ward_id == student_id,
            )
            .first()
        )

        if not assignment:
            raise ResourceNotFoundException("Assignment", assignment_id)

        assessment = assignment.assessment
        guardian = assignment.guardian

        return {
            "id": str(assignment.id),
            "assessment_id": str(assessment.id),
            "assessment_title": assessment.title,
            "subject_name": assessment.subject.name if assessment.subject else None,
            "topic_count": len(assessment.topic_ids) if assessment.topic_ids else 0,
            "total_questions": assessment.total_questions,
            "duration_minutes": assessment.duration_minutes,
            "assigned_by_name": guardian.user.full_name
            if guardian and guardian.user
            else "Guardian",
            "assigned_at": assignment.assigned_at.isoformat(),
            "due_date": assignment.due_date.isoformat()
            if assignment.due_date
            else None,
            "instructions": assignment.instructions,
            "status": assignment.status.value,
            "attempt_count": assignment.attempt_count,
            "max_attempts": assessment.max_attempts,
            "passing_percentage": assessment.passing_percentage,
            "requires_webcam": assessment.require_webcam,
            "requires_fullscreen": assessment.fullscreen_required,
            "detects_tab_switching": assessment.detect_tab_switching,
            "max_tab_switches": assessment.max_tab_switches,
            "proctoring_enabled": assessment.proctoring_enabled,
            "result_display_mode": assessment.result_display_mode,
            "show_correct_answers": assessment.show_correct_answers,
            "show_explanations": assessment.show_explanations,
        }

    async def get_assignment_detail_for_guardian(
        self,
        assignment_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get detailed assignment information for guardian view.

        Returns:
        - Assignment details
        - Ward information
        - All attempts with scores and violations
        - Proctoring event summary
        """

        def to_iso(dt_val):
            if dt_val is None:
                return None
            if isinstance(dt_val, datetime):
                return dt_val.isoformat()
            return str(dt_val)

        # Get assignment with related data
        assignment = (
            self.db.query(AssessmentAssignment)
            .options(
                joinedload(AssessmentAssignment.assessment),
                joinedload(AssessmentAssignment.ward).joinedload(Student.user),
                joinedload(AssessmentAssignment.guardian),
            )
            .filter(AssessmentAssignment.id == assignment_id)
            .first()
        )

        if not assignment:
            raise ResourceNotFoundException("Assignment", assignment_id)

        # Verify guardian ownership
        guardian = assignment.guardian
        if not guardian or guardian.user_id != user_id:
            raise AuthorizationException(
                "You don't have permission to view this assignment"
            )

        # Get assessment and ward details
        assessment = assignment.assessment
        ward = assignment.ward
        ward_user = ward.user if ward else None

        # Get all attempts for this assignment
        attempts = (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.user_id == ward_user.id,
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(AssessmentAttempt.started_at.desc())
            .all()
        )

        attempts_list = []
        for attempt in attempts:
            # Get proctoring violations for this attempt
            violations = (
                self.db.query(AssessmentProctoringEvent)
                .filter(AssessmentProctoringEvent.attempt_id == attempt.id)
                .all()
            )

            # Count violations by type
            tab_switches = len(
                [
                    v
                    for v in violations
                    if "tab" in v.event_type.lower() or "switch" in v.event_type.lower()
                ]
            )
            webcam_violations = len(
                [
                    v
                    for v in violations
                    if "webcam" in v.event_type.lower()
                    or "camera" in v.event_type.lower()
                ]
            )
            fullscreen_exits = len(
                [v for v in violations if "fullscreen" in v.event_type.lower()]
            )

            attempts_list.append(
                {
                    "id": str(attempt.id),
                    "started_at": to_iso(attempt.started_at)
                    if attempt.started_at
                    else None,
                    "completed_at": to_iso(attempt.submitted_at)
                    if attempt.submitted_at
                    else None,
                    "score": attempt.score,
                    "percentage": attempt.percentage,
                    "passed": attempt.passed,
                    "time_spent": attempt.time_spent_seconds,  # in seconds
                    "status": attempt.status,
                    "violations": {
                        "tab_switches": tab_switches,
                        "webcam_violations": webcam_violations,
                        "fullscreen_exits": fullscreen_exits,
                    },
                }
            )

        # Get latest attempt details (for summary)
        latest_attempt = attempts[0] if attempts else None

        # Get total violations across all attempts
        all_violations = (
            self.db.query(AssessmentProctoringEvent)
            .join(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.user_id == ward_user.id,
            )
            .all()
        )

        total_tab_switches = len(
            [
                v
                for v in all_violations
                if "tab" in v.event_type.lower() or "switch" in v.event_type.lower()
            ]
        )
        total_webcam_violations = len(
            [
                v
                for v in all_violations
                if "webcam" in v.event_type.lower() or "camera" in v.event_type.lower()
            ]
        )
        total_fullscreen_exits = len(
            [v for v in all_violations if "fullscreen" in v.event_type.lower()]
        )

        # Calculate attempts remaining
        attempts_remaining = assessment.max_attempts - len(attempts)

        # Build response
        result = {
            "id": str(assignment.id),
            "assessment_id": str(assessment.id),
            "assessment_title": assessment.title,
            # Ward info
            "ward_id": str(ward.id),
            "ward_name": ward_user.full_name if ward_user else "Unknown",
            "ward_email": ward_user.email if ward_user else None,
            # Assignment details
            "assigned_at": to_iso(assignment.assigned_at),
            "due_date": to_iso(assignment.due_date) if assignment.due_date else None,
            "status": assignment.status.value,
            "instructions": assignment.instructions,
            # Assessment configuration
            "duration_minutes": assessment.duration_minutes,
            "total_questions": assessment.total_questions,
            "passing_percentage": assessment.passing_percentage,
            "max_attempts": assessment.max_attempts,
            # Attempt tracking
            "attempt_count": len(attempts),
            "attempts_remaining": max(0, attempts_remaining),
            # Latest attempt info
            "started_at": to_iso(assignment.started_at)
            if assignment.started_at
            else None,
            "completed_at": to_iso(assignment.completed_at)
            if assignment.completed_at
            else None,
            "last_attempt_date": to_iso(latest_attempt.graded_at)
            if latest_attempt and to_iso(latest_attempt.graded_at)
            else None,
            "last_attempt_score": latest_attempt.score if latest_attempt else None,
            "last_attempt_time_spent": latest_attempt.time_spent_seconds
            if latest_attempt
            else None,
            # Final results (from latest completed attempt)
            "score": latest_attempt.score
            if latest_attempt and to_iso(latest_attempt.graded_at)
            else None,
            "percentage": latest_attempt.percentage
            if latest_attempt and to_iso(latest_attempt.graded_at)
            else None,
            "passed": latest_attempt.passed
            if latest_attempt and to_iso(latest_attempt.graded_at)
            else None,
            # Proctoring
            "proctoring_enabled": assessment.proctoring_enabled
            if hasattr(assessment, "proctoring_enabled")
            else False,
            "tab_switches": total_tab_switches,
            "webcam_violations": total_webcam_violations,
            "fullscreen_exits": total_fullscreen_exits,
            # All attempts (detailed)
            "attempts": attempts_list,
        }

        return result

    async def get_assignment_detail_for_guardian_complete(
        self,
        assignment_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Complete implementation with comprehensive error handling.
        """

        try:
            # Get assignment with eager loading
            assignment = (
                self.db.query(AssessmentAssignment)
                .options(
                    joinedload(AssessmentAssignment.assessment),
                    joinedload(AssessmentAssignment.ward).joinedload("user"),
                    joinedload(AssessmentAssignment.guardian),
                )
                .filter(AssessmentAssignment.id == assignment_id)
                .first()
            )

            if not assignment:
                raise ResourceNotFoundException("Assignment", assignment_id)

            # Verify guardian ownership
            guardian = assignment.guardian
            if not guardian or guardian.user_id != user_id:
                raise AuthorizationException(
                    "You don't have permission to view this assignment"
                )

            # Get related entities
            assessment = assignment.assessment
            ward = assignment.ward
            ward_user = ward.user if ward else None

            if not assessment or not ward or not ward_user:
                raise BusinessLogicException("Assignment has missing related data")

            # Get all attempts
            attempts = (
                self.db.query(AssessmentAttempt)
                .filter(
                    AssessmentAttempt.assessment_id == assessment.id,
                    AssessmentAttempt.user_id == ward_user.id,
                    AssessmentAttempt.is_deleted.is_(False),
                )
                .order_by(AssessmentAttempt.started_at.desc())
                .all()
            )

            # Process attempts
            attempts_list = []
            all_violations = []

            for attempt in attempts:
                # Get violations for this attempt
                violations = (
                    self.db.query(AssessmentProctoringEvent)
                    .filter(AssessmentProctoringEvent.attempt_id == attempt.id)
                    .all()
                )

                all_violations.extend(violations)

                # Count by type
                tab_switches = sum(
                    1
                    for v in violations
                    if "tab" in v.event_type.lower() or "switch" in v.event_type.lower()
                )
                webcam_violations = sum(
                    1
                    for v in violations
                    if "webcam" in v.event_type.lower()
                    or "camera" in v.event_type.lower()
                )
                fullscreen_exits = sum(
                    1 for v in violations if "fullscreen" in v.event_type.lower()
                )

                attempts_list.append(
                    {
                        "id": str(attempt.id),
                        "started_at": attempt.started_at.isoformat()
                        if attempt.started_at
                        else None,
                        "completed_at": attempt.submitted_at.isoformat()
                        if attempt.submitted_at
                        else None,
                        "score": float(attempt.score)
                        if attempt.score is not None
                        else None,
                        "percentage": float(attempt.percentage)
                        if attempt.percentage is not None
                        else None,
                        "passed": bool(attempt.passed)
                        if attempt.passed is not None
                        else None,
                        "time_spent": int(attempt.time_spent_seconds)
                        if attempt.time_spent_seconds
                        else None,
                        "status": attempt.status,
                        "violations": {
                            "tab_switches": tab_switches,
                            "webcam_violations": webcam_violations,
                            "fullscreen_exits": fullscreen_exits,
                        },
                    }
                )

            # Get latest completed attempt
            latest_attempt = next(
                (a for a in attempts if a.submitted_at is not None), None
            )

            # Count total violations
            total_tab_switches = sum(
                1
                for v in all_violations
                if "tab" in v.event_type.lower() or "switch" in v.event_type.lower()
            )
            total_webcam_violations = sum(
                1
                for v in all_violations
                if "webcam" in v.event_type.lower() or "camera" in v.event_type.lower()
            )
            total_fullscreen_exits = sum(
                1 for v in all_violations if "fullscreen" in v.event_type.lower()
            )

            # Build response
            return {
                "id": str(assignment.id),
                "assessment_id": str(assessment.id),
                "assessment_title": assessment.title,
                # Ward
                "ward_id": str(ward.id),
                "ward_name": ward_user.full_name,
                "ward_email": ward_user.email,
                # Assignment
                "assigned_at": assignment.assigned_at.isoformat(),
                "due_date": assignment.due_date.isoformat()
                if assignment.due_date
                else None,
                "status": assignment.status.value
                if hasattr(assignment.status, "value")
                else str(assignment.status),
                "instructions": assignment.instructions,
                # Assessment config
                "duration_minutes": int(assessment.duration_minutes),
                "total_questions": int(assessment.total_questions),
                "passing_percentage": float(assessment.passing_percentage),
                "max_attempts": int(assessment.max_attempts),
                # Tracking
                "attempt_count": len(attempts),
                "attempts_remaining": max(0, assessment.max_attempts - len(attempts)),
                # Latest attempt
                "started_at": assignment.started_at.isoformat()
                if assignment.started_at
                else None,
                "completed_at": assignment.completed_at.isoformat()
                if assignment.completed_at
                else None,
                "last_attempt_date": latest_attempt.submitted_at.isoformat()
                if latest_attempt and latest_attempt.submitted_at
                else None,
                "last_attempt_score": float(latest_attempt.score)
                if latest_attempt and latest_attempt.score is not None
                else None,
                "last_attempt_time_spent": int(latest_attempt.time_spent_seconds)
                if latest_attempt and latest_attempt.time_spent_seconds
                else None,
                # Results
                "score": float(latest_attempt.score)
                if latest_attempt and latest_attempt.score is not None
                else None,
                "percentage": float(latest_attempt.percentage)
                if latest_attempt and latest_attempt.percentage is not None
                else None,
                "passed": bool(latest_attempt.passed)
                if latest_attempt and latest_attempt.passed is not None
                else None,
                # Proctoring
                "proctoring_enabled": getattr(assessment, "proctoring_enabled", False),
                "tab_switches": total_tab_switches,
                "webcam_violations": total_webcam_violations,
                "fullscreen_exits": total_fullscreen_exits,
                # All attempts
                "attempts": attempts_list,
            }

        except (ResourceNotFoundException, AuthorizationException):
            # Re-raise these exceptions as-is
            raise
        except Exception as e:
            # Log and wrap any other exceptions
            print(f"Error getting assignment detail: {e}")
            raise BusinessLogicException(
                f"Failed to retrieve assignment details: {str(e)}"
            )

    async def notify_guardian_of_completion(
        self,
        ward_user_id: UUID,
        attempt_id: UUID,
        auto_submitted: bool = False,
    ):
        """
        Notify guardian when ward completes assessment.
        Also updates the assignment record with completion details.
        """

        # Get the attempt details
        attempt_service = AssessmentAttemptService(self.db)
        attempt = await attempt_service.get_attempt(attempt_id, ward_user_id)

        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        # Get assessment
        assessment_id = attempt.assessment_id

        # Get score details
        score = attempt.score or 0
        percentage = attempt.percentage or 0.0
        passed = attempt.passed or False

        # Get student/ward
        student_repo = StudentRepository(self.db)
        student = student_repo.get_by_user_id(ward_user_id)

        if not student:
            raise ResourceNotFoundException("Student", ward_user_id)

        # Find the assignment record
        assignment = (
            self.db.query(AssessmentAssignment)
            .filter(
                AssessmentAssignment.assessment_id == assessment_id,
                AssessmentAssignment.ward_id == student.id,
            )
            .first()
        )

        if not assignment:
            # No assignment found - this might be a self-initiated assessment
            # Just send notification to guardian if they exist
            if student.guardian_id:
                guardian = self.guardian_repo.get_by_id(student.guardian_id)
                if guardian and guardian.user_id:
                    notification_service = ChallengNotificationService(self.db)
                    await notification_service.notify_guardian_completion(
                        guardian_user_id=guardian.user_id,
                        ward_user_id=ward_user_id,
                        assessment_id=assessment_id,
                        attempt_id=attempt_id,
                        score=score,
                        percentage=percentage,
                        passed=passed,
                        auto_submitted=auto_submitted,
                    )
            return

        # Update the assignment record
        assignment.status = AssignmentStatus.COMPLETED
        assignment.completed_at = datetime.utcnow()
        assignment.attempt_count = (assignment.attempt_count or 0) + 1

        if auto_submitted:
            assignment.auto_submitted = True

        self.db.commit()
        self.db.refresh(assignment)

        # Get guardian
        guardian = self.guardian_repo.get_by_id(assignment.assigned_by)

        if not guardian or not guardian.user_id:
            return  # No guardian to notify

        # Send notification to guardian
        notification_service = ChallengNotificationService(self.db)

        dispatch_challenge_completed(
            payload=ChallengeCompleted(
                guardian_user_id=guardian.user_id,
                ward_user_id=ward_user_id,
                assessment_id=assessment_id,
                attempt_id=attempt_id,
                score=score,
                percentage=percentage,
                passed=passed,
                auto_submitted=auto_submitted,
            )
        )
        return True

    async def notify_guardian_of_violation(
        self,
        guardian_user_id: UUID,
        ward_user_id: UUID,
        assessment_id: UUID,
        violation_type: str,
        violation_count: int,
    ):
        """Send notification to guardian about proctoring violation"""
        notification_service = ChallengNotificationService(self.db)

        await notification_service.notify_guardian_violation(
            guardian_user_id=guardian_user_id,
            ward_user_id=ward_user_id,
            assessment_id=assessment_id,
            violation_type=violation_type,
            violation_count=violation_count,
        )

    async def send_due_date_reminders(self):
        """
        Background task: Send reminders for assignments due soon.

        This should be called by a scheduler (e.g., Celery, APScheduler)
        to run periodically (e.g., every hour).
        """
        from src.domains.guardian.models.guardian import AssessmentAssignment
        from src.domains.guardian.enums import AssignmentStatus
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        notification_service = ChallengNotificationService(self.db)

        # Find assignments due in 24 hours
        due_in_24h = now + timedelta(hours=24)
        assignments_24h = (
            self.db.query(AssessmentAssignment)
            .filter(
                AssessmentAssignment.status.in_(
                    [AssignmentStatus.ASSIGNED, AssignmentStatus.STARTED]
                ),
                AssessmentAssignment.due_date.isnot(None),
                AssessmentAssignment.due_date <= due_in_24h,
                AssessmentAssignment.due_date > now,
            )
            .all()
        )

        for assignment in assignments_24h:
            ward = assignment.ward
            if ward and ward.user_id:
                hours_until_due = int(
                    (assignment.due_date - now).total_seconds() / 3600
                )
                await notification_service.send_due_date_reminder(
                    ward_user_id=ward.user_id,
                    assessment_id=assignment.assessment_id,
                    due_date=assignment.due_date,
                    hours_until_due=hours_until_due,
                )

        # Find assignments due in 1 hour (final reminder)
        due_in_1h = now + timedelta(hours=1)
        assignments_1h = (
            self.db.query(AssessmentAssignment)
            .filter(
                AssessmentAssignment.status.in_(
                    [AssignmentStatus.ASSIGNED, AssignmentStatus.STARTED]
                ),
                AssessmentAssignment.due_date.isnot(None),
                AssessmentAssignment.due_date <= due_in_1h,
                AssessmentAssignment.due_date > now,
            )
            .all()
        )

        for assignment in assignments_1h:
            ward = assignment.ward
            if ward and ward.user_id:
                await notification_service.send_due_date_reminder(
                    ward_user_id=ward.user_id,
                    assessment_id=assignment.assessment_id,
                    due_date=assignment.due_date,
                    hours_until_due=1,
                )
