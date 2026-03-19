from typing import List, Optional
from uuid import UUID
from sqlalchemy import insert, func, Integer
from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ValidationException,
    BusinessLogicException,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.content.repositories.subject_repository import SubjectRepository
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.assessment.schemas.assessment import (
    AssessmentCreate,
    AssessmentUpdate,
    AssessmentResponse,
    AssessmentSummaryResponse,
    AssessmentListResponse,
    AssessmentFilterParams,
)

from src.domains.assessment.models.assessment import assessment_questions
from src.domains.assessment.schemas.statistics import AssessmentStatistics
from src.domains.assessment.enums import (
    AssessmentStatus,
    QuestionSelectionMode,
    AttemptStatus,
)
from src.domains.assessment.services.section_service import SectionService

from statistics import median
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.models.answer import Answer
from src.domains.content.models.question import Question


class AssessmentService:
    """Service for assessment operations"""

    def __init__(self, db: Session):
        self.db = db
        self.assessment_repo = AssessmentRepository(db)
        self.subject_repo = SubjectRepository(db)
        self.question_repo = QuestionRepository(db)

    async def create_assessment(
        self, assessment_data: AssessmentCreate, created_by: UUID
    ) -> AssessmentResponse:
        """Create a new assessment"""
        # Validate code uniqueness
        if self.assessment_repo.code_exists(assessment_data.code):
            raise ResourceAlreadyExistsException(
                "Assessment", f"code '{assessment_data.code}'"
            )
        # Validate subject exists
        subject = self.subject_repo.get_by_id(assessment_data.subject_id)
        if not subject:
            raise ResourceNotFoundException("Subject", assessment_data.subject_id)
        if (
            assessment_data.question_selection_mode == QuestionSelectionMode.MANUAL
            and assessment_data.question_ids
        ):
            await self._validate_questions(assessment_data.question_ids)
        assessment_dict = assessment_data.model_dump(mode="json")
        assessment_dict.pop("question_ids", None)
        assessment_dict.pop("sections", None)

        assessment_dict["created_by"] = str(created_by)
        assessment_dict["status"] = AssessmentStatus.REVIEW

        assessment = self.assessment_repo.create(assessment_dict)

        if assessment_data.question_ids:
            await self._add_questions_to_assessment(
                assessment.id, assessment_data.question_ids
            )

        if assessment_data.sections:
            section_service = SectionService(self.db)

            for section_data in assessment_data.sections:
                await section_service.create_section(
                    assessment.id, section_data, created_by
                )
        await self._update_assessment_totals(assessment.id)

        return await self.get_assessment(assessment.id)

    async def get_assessment(
        self, assessment_id: UUID, include_questions: bool = False
    ) -> AssessmentResponse:
        """Get assessment by ID"""
        if include_questions:
            assessment = self.assessment_repo.get_with_questions(assessment_id)
        else:
            assessment = self.assessment_repo.get_by_id(assessment_id)

        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        return AssessmentResponse.model_validate(assessment)

    async def get_assessments(
        self, filters: AssessmentFilterParams, skip: int = 0, limit: int = 100
    ) -> AssessmentListResponse:
        """Get assessments with filters"""
        if filters.search:
            assessments = self.assessment_repo.search_assessments(
                filters.search, filters.assessment_type, filters.category, skip, limit
            )
            total = len(assessments)
        else:
            # Build filter dict
            query_filters = {"is_deleted": False}

            if filters.assessment_type:
                query_filters["assessment_type"] = filters.assessment_type
            if filters.category:
                query_filters["category"] = filters.category
            if filters.subject_id:
                query_filters["subject_id"] = filters.subject_id
            if filters.status:
                query_filters["status"] = filters.status
            if filters.exam_year:
                query_filters["exam_year"] = filters.exam_year
            if filters.is_public is not None:
                query_filters["is_public"] = filters.is_public

            assessments = self.assessment_repo.get_all(skip, limit, query_filters)
            total = self.assessment_repo.count(query_filters)

        items = [AssessmentSummaryResponse.model_validate(a) for a in assessments]
        page = (skip // limit) + 1

        return AssessmentListResponse(
            items=items, total=total, page=page, page_size=limit
        )

    async def update_assessment(
        self, assessment_id: UUID, assessment_data: AssessmentUpdate, updated_by: UUID
    ) -> AssessmentResponse:
        """Update an assessment"""
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        # Prevent updates to published assessments
        if (
            assessment.status == AssessmentStatus.PUBLISHED
            and assessment_data.status != AssessmentStatus.ARCHIVED
        ):
            raise BusinessLogicException(
                "Cannot modify published assessment. Archive it first to make changes."
            )

        # Update
        update_dict = assessment_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = updated_by

        self.assessment_repo.update(assessment_id, update_dict)

        return await self.get_assessment(assessment_id)

    async def delete_assessment(self, assessment_id: UUID) -> bool:
        """Soft delete an assessment"""
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        # Check if has active attempts
        from src.domains.assessment.repositories.attempt_repository import (
            AssessmentAttemptRepository,
        )

        attempt_repo = AssessmentAttemptRepository(self.db)

        active_attempts = attempt_repo.count(
            {
                "assessment_id": assessment_id,
                "status": "in_progress",
                "is_deleted": False,
            }
        )

        if active_attempts > 0:
            raise BusinessLogicException(
                f"Cannot delete assessment with {active_attempts} active attempts"
            )

        return self.assessment_repo.soft_delete(assessment_id) is not None

    async def publish_assessment(
        self, assessment_id: UUID, published_by: UUID
    ) -> AssessmentResponse:
        """Publish an assessment"""
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        # Validate assessment is ready for publishing
        await self._validate_for_publishing(assessment)

        # Update status
        self.assessment_repo.update(
            assessment_id,
            {"status": AssessmentStatus.PUBLISHED, "updated_by": published_by},
        )

        return await self.get_assessment(assessment_id)

    async def get_available_assessments(
        self,
        assessment_type: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AssessmentSummaryResponse]:
        """Get currently available assessments"""
        assessments = self.assessment_repo.get_available_now(
            assessment_type, category, skip, limit
        )

        return [AssessmentSummaryResponse.model_validate(a) for a in assessments]

    async def get_popular_assessments(
        self, assessment_type: Optional[str] = None, limit: int = 10
    ) -> List[AssessmentSummaryResponse]:
        """Get popular assessments"""
        assessments = self.assessment_repo.get_popular(assessment_type, limit)
        return [AssessmentSummaryResponse.model_validate(a) for a in assessments]

    async def get_statistics(self, assessment_id: UUID) -> AssessmentStatistics:
        """Get detailed statistics for an assessment."""

        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        # ── Base rates (already denormalised on the model) ────────────────────
        completion_rate = 0.0
        if assessment.total_attempts > 0:
            completion_rate = (
                assessment.total_completions / assessment.total_attempts
            ) * 100

        pass_rate = 0.0
        if assessment.total_completions > 0:
            pass_rate = (assessment.total_passes / assessment.total_completions) * 100

        # ── Fetch all completed attempt scores ────────────────────────────────
        # Only completed attempts have meaningful score/time data.
        completed_attempts: List[AssessmentAttempt] = (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                AssessmentAttempt.is_deleted.is_(False),
                AssessmentAttempt.percentage.isnot(None),
            )
            .all()
        )

        # ── Median score ──────────────────────────────────────────────────────
        percentages = [
            float(a.percentage) for a in completed_attempts if a.percentage is not None
        ]
        median_score = float(median(percentages)) if percentages else 0.0

        # ── Score distribution (10-point buckets) ─────────────────────────────
        # Produces: {"0-10": 3, "11-20": 7, ..., "91-100": 12}
        buckets = {f"{i}-{i + 10}": 0 for i in range(0, 100, 10)}
        for pct in percentages:
            # Clamp to [0, 100] in case of floating point edge cases
            clamped = max(0.0, min(100.0, pct))
            # bucket_index 10 means 100% — fold it into the last bucket
            bucket_index = min(int(clamped // 10), 9)
            lower = bucket_index * 10
            key = f"{lower}-{lower + 10}"
            buckets[key] += 1

        # ── Median completion time ────────────────────────────────────────────
        completion_times = [
            int(a.time_spent_seconds)
            for a in completed_attempts
            if a.time_spent_seconds is not None
        ]
        median_completion_time = (
            float(median(completion_times)) if completion_times else 0.0
        )

        # ── Question analysis ─────────────────────────────────────────────────
        # Aggregate correct/total answer counts per question in a single query.
        # Using func.sum on a boolean column works in Postgres (True = 1, False = 0).
        answer_stats = (
            self.db.query(
                Answer.question_id,
                func.count(Answer.id).label("total_answers"),
                func.sum(func.cast(Answer.is_correct, Integer)).label(
                    "correct_answers"
                ),
            )
            .join(
                AssessmentAttempt,
                Answer.attempt_id == AssessmentAttempt.id,
            )
            .filter(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                AssessmentAttempt.is_deleted.is_(False),
            )
            .group_by(Answer.question_id)
            .all()
        )

        # Fetch question metadata (name + difficulty) in one query
        question_ids = [row.question_id for row in answer_stats]
        questions_by_id = {}
        if question_ids:
            questions = (
                self.db.query(Question).filter(Question.id.in_(question_ids)).all()
            )
            questions_by_id = {q.id: q for q in questions}

        # Build per-question difficulty metric
        # correct_rate = correct / total → closer to 0 means harder
        question_metrics = []
        for row in answer_stats:
            total = row.total_answers or 0
            correct = int(row.correct_answers or 0)
            correct_rate = (correct / total) if total > 0 else 0.0

            q = questions_by_id.get(row.question_id)
            question_metrics.append(
                {
                    "question_id": str(row.question_id),
                    "question_text": getattr(q, "question_text", "")[:120] if q else "",
                    "difficulty": getattr(q, "difficulty", None),
                    "total_answers": total,
                    "correct_answers": correct,
                    "correct_rate": round(correct_rate * 100, 1),
                }
            )

        # Sort: hardest = lowest correct_rate, easiest = highest correct_rate
        sorted_by_difficulty = sorted(question_metrics, key=lambda x: x["correct_rate"])

        # Return top 5 hardest and top 5 easiest.
        # Guard against overlap when there are fewer than 10 questions total
        # by ensuring the two slices don't include the same question.
        half = max(1, len(sorted_by_difficulty) // 2)
        most_difficult = sorted_by_difficulty[: min(5, half)]
        easiest = sorted_by_difficulty[max(half, len(sorted_by_difficulty) - 5) :][::-1]

        return AssessmentStatistics(
            assessment_id=assessment_id,
            total_attempts=assessment.total_attempts,
            total_completions=assessment.total_completions,
            completion_rate=round(completion_rate, 1),
            total_passes=assessment.total_passes,
            total_fails=assessment.total_fails,
            pass_rate=round(pass_rate, 1),
            average_score=assessment.average_score,
            median_score=round(median_score, 1),
            highest_score=assessment.highest_score,
            lowest_score=assessment.lowest_score,
            score_distribution=buckets,
            average_completion_time=assessment.average_completion_time,
            median_completion_time=round(median_completion_time, 1),
            most_difficult_questions=most_difficult,
            easiest_questions=easiest,
        )

    async def _validate_questions(self, question_ids: List[UUID]) -> None:
        """Validate questions exist and are approved"""
        for question_id in question_ids:
            question = self.question_repo.get_by_id(question_id)
            if not question:
                raise ResourceNotFoundException("Question", question_id)

            from src.domains.content.enums import QuestionStatus

            if question.status != QuestionStatus.APPROVED:
                raise ValidationException(
                    f"Question {question_id} is not approved for use"
                )

    async def _add_questions_to_assessment(
        self, assessment_id: UUID, question_ids: List[UUID]
    ) -> None:
        """Add questions to assessment"""
        assessment = self.assessment_repo.get_by_id(assessment_id)

        for idx, question_id in enumerate(question_ids):
            question = self.question_repo.get_by_id(question_id)
            if question and question not in assessment.questions:
                stmt = insert(assessment_questions).values(
                    assessment_id=assessment.id,
                    question_id=question.id,
                    order=idx,
                    points=question.points,
                )
                self.db.execute(stmt)

        self.db.commit()
        self.db.expire(assessment, ["questions"])

    async def _update_assessment_totals(self, assessment_id: UUID) -> None:
        """Update total questions and points"""
        assessment = self.assessment_repo.get_with_questions(assessment_id)

        total_questions = len(assessment.questions)
        total_points = sum(q.points for q in assessment.questions)

        self.assessment_repo.update(
            assessment_id,
            {"total_questions": total_questions, "total_points": total_points},
        )

    async def _validate_for_publishing(self, assessment) -> None:
        """Validate assessment is ready for publishing"""
        errors = []

        if assessment.total_questions == 0:
            errors.append("Assessment must have at least one question")

        if assessment.duration_minutes <= 0:
            errors.append("Duration must be greater than 0")

        if assessment.passing_percentage < 0 or assessment.passing_percentage > 100:
            errors.append("Passing percentage must be between 0 and 100")

        # Add more validation rules as needed

        if errors:
            raise ValidationException("; ".join(errors))

    async def get_assessment_config(self, assessment_id: UUID, user_id: UUID) -> dict:
        """Get assessment configuration for pre-check screen"""

        # Get assessment
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if not assessment:
            raise ResourceNotFoundException("Assessment", assessment_id)

        # Get user's attempts
        from src.domains.assessment.repositories.attempt_repository import (
            AssessmentAttemptRepository,
        )
        from src.domains.auth.repositories.student_repositoty import StudentRepository

        attempt_repo = AssessmentAttemptRepository(self.db)
        student_repo = StudentRepository(self.db)

        student = student_repo.get_by_user_id(user_id)
        if not student:
            raise ResourceNotFoundException("Student")

        # Count attempts
        attempts = attempt_repo.get_all(
            skip=0,
            limit=1000,
            filters={
                "assessment_id": assessment_id,
                "user_id": user_id,
                "is_deleted": False,
            },
        )

        attempts_used = len(attempts)
        return {
            "assessment_id": str(assessment.id),
            "assessment_title": assessment.title,
            "duration_minutes": assessment.duration_minutes,
            "total_questions": assessment.total_questions,
            "max_attempts": assessment.max_attempts,
            "attempts_used": attempts_used,
            "requires_webcam": getattr(assessment, "require_webcam", False),
            "requires_fullscreen": getattr(assessment, "fullscreen_required", False),
            "detects_tab_switching": getattr(assessment, "detect_tab_switching", False),
            "max_tab_switches": getattr(assessment, "max_tab_switches", 3),
            "due_date": assessment.available_until,
            "instructions": assessment.instructions,
            "proctoring_enabled": getattr(assessment, "proctoring_enabled", False),
        }
