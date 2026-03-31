from uuid import UUID

from fastapi import HTTPException
import random
from decimal import Decimal
from datetime import datetime
from typing import List

from sqlalchemy import select, func, Integer
from sqlalchemy.orm import Session, selectinload

from src.domains.auth.models.user import User
from src.domains.assessment.models.assessment import Assessment
from src.domains.assessment.schemas.assessment import AssessmentCreate
from src.domains.assessment.services.assessment_service import AssessmentService
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.content.repositories.subject_repository import SubjectRepository
from src.domains.content.repositories.topic_repository import TopicRepository
from src.domains.assessment.enums import (
    AssessmentType,
    AssessmentCategory,
    QuestionSelectionMode,
)
from src.domains.institution.models.classroom_group import (
    ClassroomAssessmentAssignment,
    student_group_members,
)


from src.domains.institution.schemas.institution import (
    AssignAssessmentRequest,
    InstitutionAssessmentResponse,
    InstitutionAssessmentCreate,
    AssessmentDetailResponse,
    StudentAttemptStatus,
)
from src.domains.institution.repositories.institution_repository import (
    AssessmentAssignmentRepo,
)

from statistics import median
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.models.answer import Answer
from src.domains.content.models.question import Question
from src.domains.assessment.enums import AttemptStatus
from src.core.exceptions import ResourceNotFoundException
from src.domains.assessment.schemas.statistics import AssessmentStatistics

from src.domains.auth.models.student import Student
from src.domains.institution.models.classroom_group import StudentGroup
from src.domains.institution.models.classroom import Classroom


class InstitutionAssessmentService:
    def __init__(self, db: Session):
        self.db = db

        self.repo = AssessmentAssignmentRepo(db)
        self.assessment_repo = AssessmentRepository(db)
        self.question_repo = QuestionRepository(db)
        self.subject_repo = SubjectRepository(db)
        self.topic_repo = TopicRepository(db)

    async def create_assessment(
        self,
        institution_id: UUID,
        user_id: UUID,
        data: InstitutionAssessmentCreate,
    ) -> Assessment:
        # 1. Validate subject
        subject = self.subject_repo.get_by_id(data.subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        # 2. Validate topics belong to subject
        topics = []
        for topic_id in data.topic_ids:
            topic = self.topic_repo.get_by_id(topic_id)
            if not topic:
                raise HTTPException(
                    status_code=404, detail=f"Topic {topic_id} not found"
                )
            if topic.subject_id != data.subject_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Topic '{topic.name}' does not belong to subject '{subject.name}'",
                )
            topics.append(topic)

        # 3. Select questions

        question_ids = self._select_questions(
            topic_ids=[t.id for t in topics],
            num_questions=data.number_of_questions,
        )

        # 4. Build assessment code
        code = self._generate_code(subject.code, institution_id)

        # 5. Build title
        topic_names = [t.name for t in topics]
        if len(topic_names) <= 2:
            topics_str = " & ".join(topic_names)
        else:
            topics_str = f"{topic_names[0]} & {len(topic_names) - 1} more"
        title = f"{subject.name} — {topics_str}"

        # 6. Create via AssessmentService (reuses all validation + publish logic)
        assessment_data = AssessmentCreate(
            title=title,
            code=code,
            description=data.instructions or f"Institution assessment: {topics_str}",
            instructions=data.instructions or "Complete all questions.",
            assessment_type=AssessmentType.TEST,
            category=AssessmentCategory.GENERAL,
            subject_id=data.subject_id,
            topic_ids=data.topic_ids,
            question_ids=question_ids,
            price=Decimal("0.00"),
            currency="NGN",
            duration_minutes=data.duration_minutes,
            available_from=data.available_from.isoformat()
            if data.available_from
            else None,
            available_until=data.available_until.isoformat()
            if data.available_until
            else None,
            question_selection_mode=QuestionSelectionMode.MANUAL,
            passing_percentage=data.passing_percentage,
            shuffle_questions=data.shuffle_questions,
            shuffle_options=data.shuffle_options,
            allow_question_navigation=data.allow_question_navigation,
            allow_backward_navigation=data.allow_backward_navigation,
            max_attempts=data.max_attempts,
            result_display_mode=data.result_display_mode,
            show_correct_answers=data.show_correct_answers,
            show_explanations=data.show_explanations,
            proctoring_enabled=data.proctoring_enabled,
            require_webcam=data.require_webcam,
            fullscreen_required=data.fullscreen_required,
            detect_tab_switching=data.detect_tab_switching,
            max_tab_switches=data.max_tab_switches,
            is_public=True,
            require_enrollment=False,
            institution_id=institution_id,  # ← stamps ownership
            sections=[],
        )

        assessment_service = AssessmentService(self.db)
        assessment = await assessment_service.create_assessment(
            assessment_data, user_id
        )
        assessment.subject_name = subject.name  # denormalise for convenience

        if data.publish:
            await assessment_service.publish_assessment(assessment.id, user_id)

        return assessment

    def list_assessments(
        self, institution_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[InstitutionAssessmentResponse]:

        stmt = (
            select(
                Assessment,
                func.count(ClassroomAssessmentAssignment.id).label("assignment_count"),
            )
            .outerjoin(
                ClassroomAssessmentAssignment,
                ClassroomAssessmentAssignment.assessment_id == Assessment.id,
            )
            .where(
                Assessment.institution_id == institution_id,
                Assessment.is_deleted.is_(False),
            )
            .options(selectinload(Assessment.subject))
            .group_by(Assessment.id)
            .order_by(Assessment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = self.db.execute(stmt)

        rows = result.all()

        out = []

        for assessment, assignment_count in rows:
            out.append(
                InstitutionAssessmentResponse(
                    id=assessment.id,
                    title=assessment.title,
                    subject_name=assessment.subject.name if assessment.subject else "—",
                    total_questions=assessment.total_questions or 0,
                    duration_minutes=assessment.duration_minutes,
                    status=assessment.status.value
                    if hasattr(assessment.status, "value")
                    else str(assessment.status),
                    created_at=assessment.created_at,
                    available_from=assessment.available_from,
                    available_until=assessment.available_until,
                    assignment_count=assignment_count,
                )
            )

        return out

    async def assign(
        self, institution_id: UUID, assigned_by: UUID, req: AssignAssessmentRequest
    ) -> dict:
        if not any([req.classroom_id, req.student_group_id, req.student_ids]):
            raise HTTPException(
                status_code=400,
                detail="Must specify at least one scope: classroom_id, student_group_id, or student_ids",
            )

        created = []

        # ── Classroom-level ───────────────────────────────────────────
        if req.classroom_id:
            # Verify classroom belongs to institution
            c_result = self.db.execute(
                select(Classroom).where(
                    Classroom.id == req.classroom_id,
                    Classroom.institution_id == institution_id,
                )
            )
            if not c_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=404,
                    detail="Classroom not found in this institution",
                )

            assignment = ClassroomAssessmentAssignment(
                institution_id=institution_id,
                assessment_id=req.assessment_id,
                classroom_id=req.classroom_id,
                assigned_by_id=assigned_by,
                due_date=req.due_date,
                available_from=req.available_from,
                instructions=req.instructions,
            )
            self.db.add(assignment)
            self.db.flush()
            created.append(assignment)

        # ── Group-level ───────────────────────────────────────────────
        if req.student_group_id:
            # Verify group belongs to institution
            g_result = self.db.execute(
                select(StudentGroup).where(
                    StudentGroup.id == req.student_group_id,
                    StudentGroup.institution_id == institution_id,
                )
            )
            if not g_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=404,
                    detail="Student group not found in this institution",
                )

            assignment = ClassroomAssessmentAssignment(
                institution_id=institution_id,
                assessment_id=req.assessment_id,
                student_group_id=req.student_group_id,
                assigned_by_id=assigned_by,
                due_date=req.due_date,
                available_from=req.available_from,
                instructions=req.instructions,
            )
            self.db.add(assignment)
            self.db.flush()
            created.append(assignment)

        # ── Individual students
        if req.student_ids:
            # Verify all students belong to this institution
            students_result = self.db.execute(
                select(Student).where(
                    Student.id.in_(req.student_ids),
                    Student.institution_id == institution_id,
                    Student.is_active.is_(True),
                )
            )
            students = students_result.scalars().all()

            found_ids = {s.id for s in students}
            missing = set(req.student_ids) - found_ids
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"{len(missing)} student(s) not found in this institution",
                )

            for student in students:
                # Check for duplicate assignment — skip silently
                existing = self.db.execute(
                    select(ClassroomAssessmentAssignment).where(
                        ClassroomAssessmentAssignment.assessment_id
                        == req.assessment_id,
                        ClassroomAssessmentAssignment.student_id == student.id,
                        ClassroomAssessmentAssignment.institution_id == institution_id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                assignment = ClassroomAssessmentAssignment(
                    institution_id=institution_id,
                    assessment_id=req.assessment_id,
                    student_id=student.id,
                    assigned_by_id=assigned_by,
                    due_date=req.due_date,
                    available_from=req.available_from,
                    instructions=req.instructions,
                )
                self.db.add(assignment)
                self.db.flush()
                created.append(assignment)

            self.db.commit()

        return {
            "created": len(created),
            "assessment_id": str(req.assessment_id),
            "scopes": {
                "classroom": str(req.classroom_id) if req.classroom_id else None,
                "group": str(req.student_group_id) if req.student_group_id else None,
                "individual_count": len(req.student_ids) if req.student_ids else 0,
            },
        }

    def _select_questions(
        self, topic_ids: List[UUID], num_questions: int
    ) -> List[UUID]:
        available = self.question_repo.get_ids_by_topics(
            topic_ids=topic_ids,
            difficulty=None,
            question_types=None,
        )
        if not available:
            raise HTTPException(
                status_code=400,
                detail="No approved questions found for the selected topics.",
            )
        if len(available) < num_questions:
            raise HTTPException(
                status_code=400,
                detail=f"Only {len(available)} questions available. Reduce question count or add more topics.",
            )
        return random.sample(available, num_questions)

    def _generate_code(self, subject_code: str, institution_id: UUID) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = random.randint(1000, 9999)
        code = f"INST-{subject_code}-{timestamp}-{suffix}"
        counter = 1
        while self.assessment_repo.code_exists(code):
            code = f"INST-{subject_code}-{timestamp}-{suffix}-{counter}"
            counter += 1
        return code

    def get_statistics(self, assessment_id: UUID) -> AssessmentStatistics:
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

    async def get_assessment_detail(
        self,
        institution_id: UUID,
        assessment_id: UUID,
    ) -> AssessmentDetailResponse:
        # Verify assessment belongs to this institution
        assess_result = await self.db.execute(
            select(Assessment)
            .options(selectinload(Assessment.subject))
            .where(
                Assessment.id == assessment_id,
                Assessment.institution_id == institution_id,
                Assessment.is_deleted.is_(False),
            )
        )
        assessment = assess_result.scalar_one_or_none()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # All assignments for this assessment in this institution
        assignments_result = await self.db.execute(
            select(ClassroomAssessmentAssignment)
            .options(
                selectinload(ClassroomAssessmentAssignment.assessment),
            )
            .where(
                ClassroomAssessmentAssignment.assessment_id == assessment_id,
                ClassroomAssessmentAssignment.institution_id == institution_id,
                ClassroomAssessmentAssignment.is_active.is_(True),
            )
        )
        assignments = assignments_result.scalars().all()

        # Resolve all student IDs across all scopes
        student_scope_map: dict[UUID, str] = {}  # student_id → assigned_via

        for assignment in assignments:
            if assignment.student_id:
                student_scope_map[assignment.student_id] = "individual"

            elif assignment.classroom_id:
                students_result = await self.db.execute(
                    select(Student)
                    .options(
                        selectinload(Student.classroom)
                    )  # FIX: eager load classroom
                    .where(
                        Student.classroom_id == assignment.classroom_id,
                        Student.institution_id == institution_id,
                        Student.is_active.is_(True),
                    )
                )
                for s in students_result.scalars().all():
                    student_scope_map.setdefault(s.id, "classroom")

            elif assignment.student_group_id:
                members_result = await self.db.execute(
                    select(student_group_members.c.student_id).where(
                        student_group_members.c.group_id == assignment.student_group_id
                    )
                )
                for row in members_result.all():
                    student_scope_map.setdefault(row[0], "group")

        student_ids = list(student_scope_map.keys())

        if not student_ids:
            return AssessmentDetailResponse(
                assessment_id=assessment_id,
                title=assessment.title,
                subject_name=assessment.subject.name if assessment.subject else None,
                total_questions=assessment.total_questions or 0,
                duration_minutes=assessment.duration_minutes,
                status=assessment.status.value
                if hasattr(assessment.status, "value")
                else str(assessment.status),
                created_at=assessment.created_at,
                available_from=assessment.available_from,
                available_until=assessment.available_until,
                total_assigned=0,
                total_started=0,
                total_submitted=0,
                total_graded=0,
                completion_rate=0.0,
                pass_rate=0.0,
                average_score=0.0,
                highest_score=0.0,
                lowest_score=0.0,
                score_distribution={},
                students=[],
            )

        # Fetch students with user info — eager load classroom to avoid lazy load on student.classroom.name
        students_result = await self.db.execute(
            select(Student, User)
            .join(User, Student.user_id == User.id)
            .options(selectinload(Student.classroom))  # already correct, kept as-is
            .where(Student.id.in_(student_ids))
        )
        students_map: dict[UUID, tuple[Student, User]] = {
            row[0].id: (row[0], row[1]) for row in students_result.all()
        }

        # Fetch all attempts for this assessment by these students' user IDs
        user_ids = [
            students_map[sid][1].id for sid in student_ids if sid in students_map
        ]
        attempts_result = await self.db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.user_id.in_(user_ids),
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(AssessmentAttempt.started_at.desc())
        )
        all_attempts = attempts_result.scalars().all()

        # Group attempts by user_id
        attempts_by_user: dict[UUID, list[AssessmentAttempt]] = {}
        for attempt in all_attempts:
            attempts_by_user.setdefault(attempt.user_id, []).append(attempt)

        # Build per-student status
        now = datetime.utcnow
        student_statuses: list[StudentAttemptStatus] = []
        total_started = 0
        total_submitted = 0
        total_graded = 0
        scores = []

        for student_id in student_ids:
            if student_id not in students_map:
                continue

            student, user = students_map[student_id]
            user_attempts = attempts_by_user.get(user.id, [])

            # Best completed attempt
            best = next((a for a in user_attempts if a.status.value == "graded"), None)

            # Determine status
            if not user_attempts:
                # Check if overdue
                due = assessment.available_until
                if due and due < now:
                    status_str = "overdue"
                else:
                    status_str = "not_started"
            else:
                latest = user_attempts[0]
                status_val = (
                    latest.status.value
                    if hasattr(latest.status, "value")
                    else str(latest.status)
                )
                if status_val == "graded":
                    status_str = "graded"
                    total_graded += 1
                    total_submitted += 1
                    total_started += 1
                elif status_val in ("submitted", "auto_submitted"):
                    status_str = "submitted"
                    total_submitted += 1
                    total_started += 1
                elif status_val == "in_progress":
                    status_str = "in_progress"
                    total_started += 1
                else:
                    status_str = status_val

            if best and best.percentage is not None:
                scores.append(float(best.percentage))

            student_statuses.append(
                StudentAttemptStatus(
                    student_id=student_id,
                    student_name=f"{user.first_name} {user.last_name}".strip(),
                    student_code=student.student_code,
                    classroom_name=student.classroom.name
                    if student.classroom
                    else None,
                    status=status_str,
                    attempt_count=len(user_attempts),
                    best_score=float(best.score) if best and best.score else None,
                    best_percentage=float(best.percentage)
                    if best and best.percentage
                    else None,
                    passed=best.passed if best else None,
                    grade=best.grade if best else None,
                    started_at=user_attempts[-1].started_at if user_attempts else None,
                    submitted_at=best.submitted_at
                    if best and best.submitted_at
                    else None,
                    time_spent_seconds=best.time_spent_seconds if best else None,
                    assigned_via=student_scope_map.get(student_id, "individual"),
                )
            )

        # Sort: graded first, then submitted, in_progress, not_started, overdue
        status_order = {
            "graded": 0,
            "submitted": 1,
            "in_progress": 2,
            "not_started": 3,
            "overdue": 4,
        }
        student_statuses.sort(key=lambda x: status_order.get(x.status, 5))

        total_assigned = len(student_ids)
        avg_score = sum(scores) / len(scores) if scores else 0.0
        pass_count = sum(1 for s in student_statuses if s.passed is True)
        completion_rate = (
            (total_graded / total_assigned * 100) if total_assigned else 0.0
        )
        pass_rate = (pass_count / total_graded * 100) if total_graded else 0.0

        # Score distribution
        buckets = {f"{i}-{i + 10}": 0 for i in range(0, 100, 10)}
        for score in scores:
            clamped = max(0.0, min(100.0, score))
            bucket_index = min(int(clamped // 10), 9)
            lower = bucket_index * 10
            buckets[f"{lower}-{lower + 10}"] += 1

        return AssessmentDetailResponse(
            assessment_id=assessment_id,
            title=assessment.title,
            subject_name=assessment.subject.name if assessment.subject else None,
            total_questions=assessment.total_questions or 0,
            duration_minutes=assessment.duration_minutes,
            status=assessment.status.value
            if hasattr(assessment.status, "value")
            else str(assessment.status),
            created_at=assessment.created_at,
            available_from=assessment.available_from,
            available_until=assessment.available_until,
            total_assigned=total_assigned,
            total_started=total_started,
            total_submitted=total_submitted,
            total_graded=total_graded,
            completion_rate=round(completion_rate, 1),
            pass_rate=round(pass_rate, 1),
            average_score=round(avg_score, 1),
            highest_score=round(max(scores), 1) if scores else 0.0,
            lowest_score=round(min(scores), 1) if scores else 0.0,
            score_distribution=buckets,
            students=student_statuses,
        )
