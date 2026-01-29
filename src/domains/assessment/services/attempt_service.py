from typing import Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.assessment.repositories.attempt_repository import (
    AssessmentAttemptRepository,
)
from src.domains.assessment.repositories.answer_repository import AnswerRepository
from src.domains.assessment.schemas.attempt import (
    AttemptStartRequest,
    AttemptStartResponse,
    SaveAnswerRequest,
    AttemptProgressResponse,
    AttemptResultResponse,
    AttemptDetailResponse,
    AttemptListResponse,
    AttemptResponse,
)
from src.domains.assessment.enums import AssessmentType, AssessmentStatus, AttemptStatus
from src.domains.assessment.services.grading_service import GradingService
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.assessment.schemas.correction import AnswerCorrectionResponse

from src.shared.events.dispatcher import dispatch_assessment_completed
from src.shared.events.payloads import AssessmentCompletedPayload
from src.domains.guardian.models.guardian import AssessmentAssignment
from src.domains.auth.repositories.student_repositoty import StudentRepository


class AssessmentAttemptService:
    """Service for assessment attempt operations"""

    def __init__(self, db: Session):
        self.db = db
        self.question_repo = QuestionRepository(db)
        self.assessment_repo = AssessmentRepository(db)
        self.attempt_repo = AssessmentAttemptRepository(db)
        self.answer_repo = AnswerRepository(db)
        self.student_repo = StudentRepository(db)

    async def start_attempt(
        self, assessment_id: UUID, user_id: UUID, request_data: AttemptStartRequest
    ) -> AttemptStartResponse:
        """Start a new assessment attempt, increment assignment attempt_count if exists."""

        assessment = self.assessment_repo.get_with_questions(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        await self._validate_assessment_availability(assessment, user_id)

        if assessment.assessment_type == AssessmentType.EXAM:
            await self._verify_payment(assessment_id, user_id)

        active_attempt = self.attempt_repo.get_active_attempt(user_id, assessment_id)
        if active_attempt:
            return self._create_start_response(active_attempt, assessment)

        student = self.student_repo.get_by_user_id(user_id)
        assignment = None
        if student:
            assignment = (
                self.db.query(AssessmentAssignment)
                .filter(
                    AssessmentAssignment.assessment_id == assessment_id,
                    AssessmentAssignment.ward_id == student.id,
                )
                .with_for_update()  # Optional: locks row to prevent race conditions
                .first()
            )

        if assignment and assignment.attempt_count >= assessment.max_attempts:
            raise BusinessLogicException("Maximum attempts reached for this assignment")

        attempt_number = (
            self.attempt_repo.count_user_attempts(user_id, assessment_id) + 1
        )

        must_submit_by = (
            datetime.now(timezone.utc) + timedelta(minutes=assessment.duration_minutes)
        ).isoformat()

        attempt_data = {
            "assessment_id": assessment_id,
            "user_id": user_id,
            "attempt_number": attempt_number,
            "status": AttemptStatus.IN_PROGRESS,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "must_submit_by": must_submit_by,
            "total_questions": assessment.total_questions,
            "points_possible": assessment.total_points,
            "device_info": request_data.device_info,
            "created_by": user_id,
        }

        attempt = self.attempt_repo.create(attempt_data)

        if assignment:
            assignment.attempt_count += 1
            self.db.commit()

        self.assessment_repo.update_statistics(assessment_id)

        return self._create_start_response(attempt, assessment)

    async def start_attempt_old(
        self, assessment_id: UUID, user_id: UUID, request_data: AttemptStartRequest
    ) -> AttemptStartResponse:
        """Start a new assessment attempt"""

        # Get assessment
        assessment = self.assessment_repo.get_with_questions(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        await self._validate_assessment_availability(assessment, user_id)

        # await self._check_attempt_limits(assessment, user_id)

        if assessment.assessment_type == AssessmentType.EXAM:
            await self._verify_payment(assessment_id, user_id)

        # Check for active attempt
        active_attempt = self.attempt_repo.get_active_attempt(user_id, assessment_id)
        if active_attempt:
            return self._create_start_response(active_attempt, assessment)

        # Create new attempt
        attempt_number = (
            self.attempt_repo.count_user_attempts(user_id, assessment_id) + 1
        )

        # Calculate deadline
        must_submit_by = (
            datetime.now(timezone.utc) + timedelta(minutes=assessment.duration_minutes)
        ).isoformat()

        attempt_data = {
            "assessment_id": assessment_id,
            "user_id": user_id,
            "attempt_number": attempt_number,
            "status": AttemptStatus.IN_PROGRESS,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "must_submit_by": must_submit_by,
            "total_questions": assessment.total_questions,
            "points_possible": assessment.total_points,
            "device_info": request_data.device_info,
            "created_by": user_id,
        }

        attempt = self.attempt_repo.create(attempt_data)

        # Update assessment statistics
        self.assessment_repo.update_statistics(assessment_id)

        return self._create_start_response(attempt, assessment)

    async def save_answer_old(
        self, attempt_id: UUID, user_id: UUID, answer_data: SaveAnswerRequest
    ) -> Dict[str, Any]:
        """Save or update an answer"""
        # Get attempt
        attempt = self.attempt_repo.get_by_id(attempt_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        # Validate ownership
        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to update this attempt")

        # Validate status
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise BusinessLogicException("Attempt is not in progress")

        # Check if answer already exists
        existing_answer = self.answer_repo.get_by_question(
            attempt_id, answer_data.question_id
        )

        answer_dict = answer_data.model_dump(exclude_unset=True)
        answer_dict["attempt_id"] = attempt_id

        if existing_answer:
            # Update existing answer
            answer_dict["edit_count"] = existing_answer.edit_count + 1
            answer_dict["last_modified_at"] = datetime.now(timezone.utc).isoformat()
            answer = self.answer_repo.update(existing_answer.id, answer_dict)
        else:
            # Create new answer
            answer_dict["first_answered_at"] = datetime.now(timezone.utc).isoformat()
            answer_dict["created_by"] = user_id
            answer = self.answer_repo.create(answer_dict)

            # Update attempt stats
            attempt.questions_attempted += 1
            self.db.commit()

        return {
            "answer_id": answer.id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "message": "Answer saved successfully",
        }

    async def save_answer(
        self, attempt_id: UUID, user_id: UUID, answer_data: SaveAnswerRequest
    ) -> Dict[str, Any]:
        """Save or update an answer"""
        # Get attempt
        attempt = self.attempt_repo.get_by_id(attempt_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        # Validate ownership
        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to update this attempt")

        # Validate status
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise BusinessLogicException("Attempt is not in progress")

        # Check if answer already exists
        existing_answer = self.answer_repo.get_by_question(
            attempt_id, answer_data.question_id
        )

        # build answer dict
        answer_dict = answer_data.model_dump(exclude_unset=True)
        answer_dict["attempt_id"] = attempt_id

        question = None
        try:
            question = self.question_repo.get_with_options(answer_data.question_id)
        except AttributeError:
            question = None

        if existing_answer:
            # Update existing answer
            answer_dict["edit_count"] = existing_answer.edit_count + 1
            answer_dict["last_modified_at"] = datetime.now(timezone.utc).isoformat()

            if not existing_answer.question_snapshot and question:
                answer_dict["question_snapshot"] = self._build_question_snapshot(
                    question
                )

            answer = self.answer_repo.update(existing_answer.id, answer_dict)
        else:
            answer_dict["first_answered_at"] = datetime.now(timezone.utc).isoformat()
            answer_dict["created_by"] = user_id

            if question:
                answer_dict["question_snapshot"] = self._build_question_snapshot(
                    question
                )

            answer = self.answer_repo.create(answer_dict)

            attempt.questions_attempted += 1
            self.db.commit()

        return {
            "answer_id": answer.id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "message": "Answer saved successfully",
        }

    async def submit_attempt(
        self, attempt_id: UUID, user_id: UUID
    ) -> AttemptResultResponse:
        """Submit an assessment attempt"""
        # Get attempt with answers
        attempt = self.attempt_repo.get_with_answers(attempt_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        # Validate ownership
        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to submit this attempt")

        # Validate status
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise BusinessLogicException("Attempt is not in progress")

        # Update attempt
        attempt.status = AttemptStatus.SUBMITTED
        attempt.submitted_at = datetime.now(timezone.utc).isoformat()

        # Calculate time spent
        if attempt.started_at:
            started = datetime.fromisoformat(attempt.started_at)
            submitted = datetime.fromisoformat(attempt.submitted_at)
            attempt.time_spent_seconds = int((submitted - started).total_seconds())

        self.db.commit()

        # Auto-grade the attempt
        await self._auto_grade_attempt(attempt_id)

        # Update assessment statistics
        assessment = self.assessment_repo.get_by_id(attempt.assessment_id)

        self.assessment_repo.update_statistics(
            attempt.assessment_id,
            completed=True,
            passed=attempt.passed,
            score=float(attempt.score),
            completion_time=attempt.time_spent_seconds,
        )

        # Update rank
        self.attempt_repo.update_rank(attempt_id)

        # This is my entry point to gamification
        # (Samuel Kufre Willie : samuelkufrewillie)
        dispatch_assessment_completed(
            user_id=user_id,
            payload=AssessmentCompletedPayload(
                assessment_id=attempt.assessment_id,
                category_id=assessment.category_config_id,
                score=int(attempt.correct_answers),
                total_questions=attempt.total_questions,
                time_taken_seconds=attempt.time_spent_seconds,
                completed_at=datetime.now(timezone.utc),
            ),
        )

        # TODO: Email user the result with structure pdf
        return await self.get_attempt_result(attempt_id, user_id)

    async def get_attempt_progress(
        self, attempt_id: UUID, user_id: UUID
    ) -> AttemptProgressResponse:
        """Get current progress of an attempt"""
        attempt = self.attempt_repo.get_by_id(attempt_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to view this attempt")

        # Calculate time remaining
        time_remaining = None
        if attempt.must_submit_by and attempt.status == AttemptStatus.IN_PROGRESS:
            deadline = datetime.fromisoformat(attempt.must_submit_by)

            now = datetime.now(timezone.utc)
            remaining = (deadline - now).total_seconds()
            time_remaining = max(0, int(remaining))
        # Check unanswered questions
        assessment = self.assessment_repo.get_with_questions(attempt.assessment_id)
        question_ids = [q.id for q in assessment.questions]
        unanswered = self.answer_repo.get_unanswered_questions(attempt_id, question_ids)

        return AttemptProgressResponse(
            attempt_id=attempt_id,
            status=attempt.status,
            time_spent_seconds=attempt.time_spent_seconds,
            time_remaining_seconds=time_remaining,
            total_questions=attempt.total_questions,
            questions_attempted=attempt.questions_attempted,
            questions_unanswered=len(unanswered),
            questions_flagged=attempt.questions_flagged,
            can_submit=len(unanswered) == 0,
        )

    async def get_attempt_result(
        self, attempt_id: UUID, user_id: UUID, include_answers: bool = False
    ) -> AttemptResultResponse | AttemptDetailResponse:
        """Get attempt result"""
        if include_answers:
            attempt = self.attempt_repo.get_with_answers(attempt_id)
        else:
            attempt = self.attempt_repo.get_by_id(attempt_id)

        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to view this attempt")

        if include_answers:
            return AttemptDetailResponse.model_validate(attempt)
        else:
            return AttemptResultResponse.model_validate(attempt)

    async def get_attempt(self, attempt_id: UUID, user_id: UUID) -> AttemptResponse:
        """Get raw attempt with assessment"""

        attempt = self.attempt_repo.get_with_assessment(attempt_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to view this attempt")

        return AttemptResponse.model_validate(attempt)

    async def get_attempt_by_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
    ) -> AttemptResponse:
        """Get raw attempt with assessment"""

        attempt = self.attempt_repo.get_by_user_and_assessment(user_id, assessment_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt")

        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to view this attempt")

        return AttemptResponse.model_validate(attempt)

    async def get_attempt_correction(
        self, attempt_id: UUID, user_id: UUID
    ) -> AnswerCorrectionResponse:
        attempt = self.attempt_repo.get_with_answers(attempt_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        if attempt.user_id != user_id:
            raise ValidationException("Not authorized to view this correction")

        if attempt.status not in [AttemptStatus.SUBMITTED, AttemptStatus.GRADED]:
            raise BusinessLogicException("Attempt has not been submitted yet")

        answers_payload = []

        for answer in attempt.answers:
            snapshot = answer.question_snapshot or {}

            options = []
            for opt in snapshot.get("options", []):
                options.append(
                    {
                        "id": opt["id"],
                        "option_text": opt["option_text"],
                        "is_correct": opt.get("is_correct", False),
                        "selected": opt["id"] in (answer.selected_option_ids or []),
                    }
                )

            answers_payload.append(
                {
                    "answer_id": answer.id,
                    "question": {
                        "id": snapshot.get("id"),
                        "question_text": snapshot.get("question_text"),
                        "question_type": snapshot.get("question_type"),
                        "image_url": snapshot.get("image_url"),
                        "audio_url": snapshot.get("audio_url"),
                        "video_url": snapshot.get("video_url"),
                        "explanation": snapshot.get("explanation"),
                        "points": snapshot.get("points"),
                    },
                    "options": options,
                    "user_answer": {
                        "selected_option_ids": answer.selected_option_ids,
                        "text_answer": answer.text_answer,
                        "matching_pairs": answer.matching_pairs,
                        "ordered_items": answer.ordered_items,
                    },
                    "result": {
                        "is_correct": answer.is_correct,
                        "is_partially_correct": answer.is_partially_correct,
                        "points_earned": answer.points_earned,
                        "points_possible": answer.points_possible,
                    },
                }
            )

        response = {
            "attempt": {
                "id": attempt.id,
                "status": attempt.status,
                "score": attempt.score,
                "percentage": attempt.percentage,
                "points_earned": attempt.points_earned,
                "points_possible": attempt.points_possible,
                "passed": attempt.passed,
                "time_spent_seconds": attempt.time_spent_seconds,
                "submitted_at": attempt.submitted_at,
            },
            "answers": answers_payload,
        }

        return response

    async def get_user_attempts(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> AttemptListResponse:
        """Get all attempts for a user"""
        attempts = self.attempt_repo.get_user_attempts(user_id, None, skip, limit)
        total = self.attempt_repo.count({"user_id": user_id, "is_deleted": False})

        items = [AttemptResultResponse.model_validate(a) for a in attempts]
        page = (skip // limit) + 1

        return AttemptListResponse(items=items, total=total, page=page, page_size=limit)

    async def _validate_assessment_availability(
        self, assessment, user_id: UUID
    ) -> None:
        """Validate assessment is available"""
        if assessment.status != AssessmentStatus.PUBLISHED:
            raise BusinessLogicException("Assessment is not published")

        now = datetime.now(timezone.utc).isoformat()

        if assessment.available_from and now < assessment.available_from:
            raise BusinessLogicException("Assessment is not yet available")

        if assessment.available_until and now > assessment.available_until:
            raise BusinessLogicException("Assessment is no longer available")

    async def _check_attempt_limits(self, assessment, user_id: UUID) -> None:
        """Check if user has exceeded attempt limits"""
        attempts_count = self.attempt_repo.count_user_attempts(
            user_id, assessment.id, exclude_status=[AttemptStatus.ABANDONED]
        )

        if attempts_count >= assessment.max_attempts:
            raise BusinessLogicException(
                detail=f"Maximum attempts ({assessment.max_attempts}) reached"
            )

    async def _verify_payment(self, assessment_id: UUID, user_id: UUID) -> None:
        """Verify payment for paid exam"""
        # TODO: Implement payment verification
        # Check if user has paid for this exam
        pass

    async def _auto_grade_attempt(self, attempt_id: UUID) -> None:
        """Auto-grade an attempt"""

        grading_service = GradingService(self.db)
        await grading_service.auto_grade_attempt(attempt_id)

    def _create_start_response(self, attempt, assessment) -> AttemptStartResponse:
        """Create attempt start response"""
        return AttemptStartResponse(
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            attempt_number=attempt.attempt_number,
            duration_minutes=assessment.duration_minutes,
            must_submit_by=attempt.must_submit_by,
            total_questions=assessment.total_questions,
            instructions=assessment.instructions,
            proctoring_required=assessment.proctoring_enabled,
            proctoring_config=assessment.proctoring_config
            if assessment.proctoring_enabled
            else None,
        )

    def _build_question_snapshot(self, question) -> dict:
        q_snap = {
            "id": str(question.id),
            "question_text": question.question_text,
            "question_type": question.question_type,
            "image_url": question.image_url,
            "audio_url": question.audio_url,
            "video_url": question.video_url,
            "explanation": question.explanation,
            "difficulty_level": question.difficulty_level,
            "points": question.points,
            "time_limit_seconds": question.time_limit_seconds,
        }

        options = []
        for opt in getattr(question, "options", []) or []:
            options.append(
                {
                    "id": str(opt.id),
                    "option_text": opt.option_text,
                    "option_order": opt.option_order,
                    "is_correct": bool(getattr(opt, "is_correct", False)),
                    "image_url": getattr(opt, "image_url", None),
                    "match_pair_id": getattr(opt, "match_pair_id", None),
                }
            )

        q_snap["options"] = options
        return q_snap

    def delete_attempt(self, attempt_id: UUID) -> None:
        """Auto-grade an attempt"""
        return self.attempt_repo.delete(attempt_id)
