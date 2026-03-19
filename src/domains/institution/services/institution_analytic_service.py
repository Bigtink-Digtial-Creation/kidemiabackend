from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from typing import List

from src.domains.institution.schemas.institution import (
    InstitutionDashboardStats,
    StudentWithClassroomResponse,
    ClassroomMinimal,
    UserRead,
)
from src.domains.institution.models.classroom import Classroom
from src.domains.institution.models.teacher import InstitutionTeacher
from src.domains.institution.models.classroom_group import ClassroomAssessmentAssignment
from src.domains.auth.models.student import Student
from src.domains.auth.models.user import User

from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Optional, Dict, Tuple


from src.domains.assessment.models.assessment import Assessment
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.models.answer import Answer


from src.domains.content.models.question import Question
from src.domains.institution.models.classroom_group import (
    StudentGroup,
    student_group_members,
)
from src.domains.institution.schemas.analytics import (
    AssessmentResult,
    BulkReportCardResult,
    ClassroomAnalytics,
    ClassroomComparison,
    GroupPerformance,
    InstitutionAnalytics,
    QuestionInsight,
    ScoreSnapshot,
    StudentPerformanceSummary,
    StudentReportCard,
    SubjectPerformance,
)


class InstitutionAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_institution_analytics(
        self, institution_id: UUID
    ) -> InstitutionAnalytics:
        classrooms = await self._get_classrooms(institution_id)
        classroom_ids = [c.id for c in classrooms]

        # All completed attempts for this institution's assessments
        attempts = await self._get_institution_attempts(institution_id)

        total_assigned = await self._count_assignments(institution_id)
        total_students = await self._count_students(institution_id)

        overall_avg, overall_pass, overall_completion = self._compute_top_stats(
            attempts, total_assigned
        )

        # Per-classroom breakdown
        classroom_comparisons = []
        for classroom in classrooms:
            comp = await self._classroom_comparison(classroom, institution_id)
            classroom_comparisons.append(comp)

        classroom_comparisons.sort(key=lambda x: x.avg_score, reverse=True)

        # Group performance
        groups = await self._get_groups(institution_id)
        group_performances = []
        for group in groups:
            gp = await self._group_performance(group, institution_id)
            group_performances.append(gp)

        # Score trend (monthly, last 6 months)
        score_trend = await self._institution_score_trend(institution_id)

        return InstitutionAnalytics(
            institution_id=institution_id,
            total_students=total_students,
            total_assessments_assigned=total_assigned,
            overall_avg_score=round(overall_avg, 1),
            overall_pass_rate=round(overall_pass, 1),
            overall_completion_rate=round(overall_completion, 1),
            score_trend=score_trend,
            classroom_comparison=classroom_comparisons,
            group_performance=group_performances,
            top_classrooms=classroom_comparisons[:3],
            struggling_classrooms=list(reversed(classroom_comparisons))[:3],
        )

    # ── Classroom analytics ───────────────────────────────────────

    async def get_classroom_analytics(
        self, institution_id: UUID, classroom_id: UUID
    ) -> ClassroomAnalytics:
        # Fetch classroom with teacher
        result = await self.db.execute(
            select(Classroom)
            .options(selectinload(Classroom.students))
            .where(
                Classroom.id == classroom_id,
                Classroom.institution_id == institution_id,
            )
        )
        classroom = result.scalar_one_or_none()
        if not classroom:
            raise ValueError("Classroom not found")

        # Students in classroom
        students_result = await self.db.execute(
            select(Student, User)
            .join(User, Student.user_id == User.id)
            .where(
                Student.classroom_id == classroom_id,
                Student.institution_id == institution_id,
                Student.is_active.is_(True),
            )
        )
        student_rows = students_result.all()

        # Assignments for this classroom
        assignments_result = await self.db.execute(
            select(ClassroomAssessmentAssignment)
            .options(selectinload(ClassroomAssessmentAssignment.assessment))
            .where(
                ClassroomAssessmentAssignment.classroom_id == classroom_id,
                ClassroomAssessmentAssignment.is_active.is_(True),
            )
        )
        assignments = assignments_result.scalars().all()
        assessment_ids = [a.assessment_id for a in assignments]

        # All attempts for these assessments by students in this class
        student_ids_user = [row[1].id for row in student_rows]
        attempts = await self._get_attempts_for_assessments_by_users(
            assessment_ids, student_ids_user
        )

        # Per-student performance
        student_performances = []
        for student, user in student_rows:
            perf = self._student_performance_summary(
                student, user, assessment_ids, attempts
            )
            student_performances.append(perf)

        student_performances.sort(key=lambda x: x.avg_score, reverse=True)

        # Classroom-level stats
        completed = [a for a in attempts if a.status.value == "graded"]
        scores = [float(a.percentage) for a in completed if a.percentage]
        avg_score = mean(scores) if scores else 0.0
        pass_count = sum(1 for a in completed if a.passed)
        pass_rate = (pass_count / len(completed) * 100) if completed else 0.0
        completion_rate = (
            (len(completed) / (len(assessment_ids) * len(student_rows)) * 100)
            if assessment_ids and student_rows
            else 0.0
        )

        # Score trend by month
        score_trend = self._score_trend_from_attempts(completed)

        # Question difficulty for this classroom
        difficult_questions = await self._question_difficulty_for_assessments(
            assessment_ids
        )

        return ClassroomAnalytics(
            classroom_id=classroom_id,
            classroom_name=classroom.name,
            level=classroom.level or "",
            teacher_name=None,  # enrich from InstitutionMember if needed
            total_students=len(student_rows),
            total_assessments_assigned=len(assignment_ids := assessment_ids),
            avg_score=round(avg_score, 1),
            pass_rate=round(pass_rate, 1),
            completion_rate=round(min(completion_rate, 100.0), 1),
            highest_avg_score=round(student_performances[0].avg_score, 1)
            if student_performances
            else 0.0,
            lowest_avg_score=round(student_performances[-1].avg_score, 1)
            if student_performances
            else 0.0,
            score_trend=score_trend,
            top_performers=student_performances[:5],
            needs_support=[
                s for s in reversed(student_performances) if s.total_assessments > 0
            ][:5],
            most_difficult_topics=difficult_questions[:5],
        )

    async def get_student_report_card(
        self, institution_id: UUID, student_id: UUID
    ) -> StudentReportCard:
        # Fetch student
        result = await self.db.execute(
            select(Student, User)
            .join(User, Student.user_id == User.id)
            .where(
                Student.id == student_id,
                Student.institution_id == institution_id,
            )
        )
        row = result.first()
        if not row:
            raise ValueError("Student not found in this institution")

        student, user = row

        # Classroom
        classroom_name = None
        if student.classroom_id:
            c_result = await self.db.execute(
                select(Classroom).where(Classroom.id == student.classroom_id)
            )
            classroom = c_result.scalar_one_or_none()
            classroom_name = classroom.name if classroom else None

        # All assignments for this student (via classroom + group + individual)
        # NOTE: _get_student_assignment_ids now eagerly loads assessment + subject
        assignment_ids = await self._get_student_assignment_ids(
            student_id, student.classroom_id, institution_id
        )

        # All attempts — eagerly load assessment + subject
        attempts_result = await self.db.execute(
            select(AssessmentAttempt)
            .options(
                selectinload(AssessmentAttempt.assessment).selectinload(
                    Assessment.subject
                )
            )
            .where(
                AssessmentAttempt.user_id == user.id,
                AssessmentAttempt.assessment_id.in_(
                    [a.assessment_id for a in assignment_ids]
                ),
                AssessmentAttempt.is_deleted.is_(False),
            )
            .order_by(AssessmentAttempt.started_at.desc())
        )
        attempts = attempts_result.scalars().all()

        # Best attempt per assessment
        best_per_assessment: Dict[UUID, AssessmentAttempt] = {}
        for attempt in attempts:
            existing = best_per_assessment.get(attempt.assessment_id)
            if not existing or (
                attempt.percentage is not None
                and (
                    existing.percentage is None
                    or attempt.percentage > existing.percentage
                )
            ):
                best_per_assessment[attempt.assessment_id] = attempt

        completed_best = [
            a
            for a in best_per_assessment.values()
            if a.status.value == "graded" and a.percentage is not None
        ]

        scores = [float(a.percentage) for a in completed_best]
        overall_avg = mean(scores) if scores else 0.0
        pass_rate = (
            sum(1 for a in completed_best if a.passed) / len(completed_best) * 100
            if completed_best
            else 0.0
        )
        completion_rate = (
            len(best_per_assessment) / len(assignment_ids) * 100
            if assignment_ids
            else 0.0
        )

        # Subject breakdown
        subject_map: Dict[str, List[float]] = defaultdict(list)
        for attempt in completed_best:
            if attempt.assessment and attempt.assessment.subject:
                subject_map[attempt.assessment.subject.name].append(
                    float(attempt.percentage)
                )

        subject_performance = [
            SubjectPerformance(
                subject_name=subject,
                total_assessments=len(s_scores),
                avg_score=round(mean(s_scores), 1),
                pass_rate=round(
                    sum(1 for s in s_scores if s >= 50) / len(s_scores) * 100, 1
                ),
                best_score=round(max(s_scores), 1),
                latest_score=round(s_scores[0], 1) if s_scores else None,
            )
            for subject, s_scores in subject_map.items()
        ]

        # Assessment results list
        assessment_results = []
        for assignment in assignment_ids:
            best = best_per_assessment.get(assignment.assessment_id)
            attempt_count = sum(
                1 for a in attempts if a.assessment_id == assignment.assessment_id
            )
            assessment_results.append(
                AssessmentResult(
                    assessment_id=assignment.assessment_id,
                    assessment_title=assignment.assessment.title
                    if assignment.assessment
                    else "—",
                    subject_name=assignment.assessment.subject.name
                    if assignment.assessment and assignment.assessment.subject
                    else None,
                    assigned_at=assignment.created_at,
                    completed_at=best.submitted_at if best else None,
                    score=float(best.score) if best and best.score else None,
                    percentage=float(best.percentage)
                    if best and best.percentage
                    else None,
                    passed=best.passed if best else None,
                    grade=best.grade if best else None,
                    time_spent_seconds=best.time_spent_seconds if best else None,
                    attempt_count=attempt_count,
                    status=best.status.value if best else "not_started",
                )
            )

        # Rank in class
        rank, class_size = await self._get_student_rank(
            student_id, student.classroom_id, institution_id
        )

        # Trend
        trend = self._calculate_trend(
            [
                float(a.percentage)
                for a in sorted(
                    completed_best, key=lambda x: x.submitted_at or datetime.min
                )
                if a.percentage
            ]
        )

        # Score over time
        score_over_time = self._score_trend_from_attempts(completed_best)

        return StudentReportCard(
            student_id=student_id,
            student_name=f"{user.first_name} {user.last_name}",
            student_code=student.student_code,
            classroom_name=classroom_name,
            guardian_email=student.guardian_email,
            generated_at=datetime.now(timezone.utc),
            total_assessments_assigned=len(assignment_ids),
            total_assessments_completed=len(completed_best),
            completion_rate=round(min(completion_rate, 100.0), 1),
            overall_avg_score=round(overall_avg, 1),
            overall_pass_rate=round(pass_rate, 1),
            grade=self._letter_grade(overall_avg),
            trend=trend,
            rank_in_class=rank,
            class_size=class_size,
            subject_performance=subject_performance,
            assessment_results=assessment_results,
            score_over_time=score_over_time,
        )

    async def get_bulk_report_cards(
        self,
        institution_id: UUID,
        student_ids: Optional[List[UUID]] = None,
        classroom_id: Optional[UUID] = None,
        group_id: Optional[UUID] = None,
    ) -> BulkReportCardResult:
        # Resolve which students to include
        if student_ids:
            target_ids = student_ids
        elif classroom_id:
            result = await self.db.execute(
                select(Student.id).where(
                    Student.classroom_id == classroom_id,
                    Student.institution_id == institution_id,
                    Student.is_active.is_(True),
                )
            )
            target_ids = [row[0] for row in result.all()]
        elif group_id:
            result = await self.db.execute(
                select(student_group_members.c.student_id).where(
                    student_group_members.c.group_id == group_id
                )
            )
            target_ids = [row[0] for row in result.all()]
        else:
            # All institution students
            result = await self.db.execute(
                select(Student.id).where(
                    Student.institution_id == institution_id,
                    Student.is_active.is_(True),
                )
            )
            target_ids = [row[0] for row in result.all()]

        report_cards = []
        for sid in target_ids:
            try:
                card = await self.get_student_report_card(institution_id, sid)
                report_cards.append(card)
            except ValueError:
                continue

        return BulkReportCardResult(
            total=len(report_cards),
            report_cards=report_cards,
        )

    # ── Private helpers ───────────────────────────────────────────

    async def _get_classrooms(self, institution_id: UUID) -> List[Classroom]:
        result = await self.db.execute(
            select(Classroom).where(
                Classroom.institution_id == institution_id,
                Classroom.is_active.is_(True),
            )
        )
        return result.scalars().all()

    async def _get_groups(self, institution_id: UUID) -> List[StudentGroup]:
        result = await self.db.execute(
            select(StudentGroup).where(
                StudentGroup.institution_id == institution_id,
                StudentGroup.is_active.is_(True),
            )
        )
        return result.scalars().all()

    async def _count_students(self, institution_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Student.id)).where(
                Student.institution_id == institution_id,
                Student.is_active.is_(True),
            )
        )
        return result.scalar() or 0

    async def _count_assignments(self, institution_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(ClassroomAssessmentAssignment.id)).where(
                ClassroomAssessmentAssignment.institution_id == institution_id,
                ClassroomAssessmentAssignment.is_active.is_(True),
            )
        )
        return result.scalar() or 0

    async def _get_institution_attempts(
        self, institution_id: UUID
    ) -> List[AssessmentAttempt]:
        # Get all assessment IDs belonging to this institution
        assess_result = await self.db.execute(
            select(Assessment.id).where(
                Assessment.institution_id == institution_id,
                Assessment.is_deleted.is_(False),
            )
        )
        assessment_ids = [row[0] for row in assess_result.all()]
        if not assessment_ids:
            return []

        result = await self.db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.assessment_id.in_(assessment_ids),
                AssessmentAttempt.is_deleted.is_(False),
            )
        )
        return result.scalars().all()

    async def _get_attempts_for_assessments_by_users(
        self, assessment_ids: List[UUID], user_ids: List[UUID]
    ) -> List[AssessmentAttempt]:
        if not assessment_ids or not user_ids:
            return []
        result = await self.db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.assessment_id.in_(assessment_ids),
                AssessmentAttempt.user_id.in_(user_ids),
                AssessmentAttempt.is_deleted.is_(False),
            )
        )
        return result.scalars().all()

    async def _get_student_assignment_ids(
        self,
        student_id: UUID,
        classroom_id: Optional[UUID],
        institution_id: UUID,
    ) -> List[ClassroomAssessmentAssignment]:

        seen_assessment_ids = set()
        assignments = []

        async def _fetch_and_merge(query):
            result = await self.db.execute(query)
            for assignment in result.scalars().all():
                if assignment.assessment_id not in seen_assessment_ids:
                    seen_assessment_ids.add(assignment.assessment_id)
                    assignments.append(assignment)

        # 1. Individual assignments
        await _fetch_and_merge(
            select(ClassroomAssessmentAssignment)
            .options(
                selectinload(ClassroomAssessmentAssignment.assessment).selectinload(
                    Assessment.subject
                )
            )
            .where(
                ClassroomAssessmentAssignment.student_id == student_id,
                ClassroomAssessmentAssignment.institution_id == institution_id,
                ClassroomAssessmentAssignment.is_active.is_(True),
            )
        )

        # 2. Classroom assignments
        if classroom_id:
            await _fetch_and_merge(
                select(ClassroomAssessmentAssignment)
                .options(
                    selectinload(ClassroomAssessmentAssignment.assessment).selectinload(
                        Assessment.subject
                    )
                )
                .where(
                    ClassroomAssessmentAssignment.classroom_id == classroom_id,
                    ClassroomAssessmentAssignment.institution_id == institution_id,
                    ClassroomAssessmentAssignment.is_active.is_(True),
                )
            )

        # 3. Group assignments
        groups_result = await self.db.execute(
            select(student_group_members.c.group_id).where(
                student_group_members.c.student_id == student_id
            )
        )
        group_ids = [row[0] for row in groups_result.all()]

        if group_ids:
            await _fetch_and_merge(
                select(ClassroomAssessmentAssignment)
                .options(
                    selectinload(ClassroomAssessmentAssignment.assessment).selectinload(
                        Assessment.subject
                    )
                )
                .where(
                    ClassroomAssessmentAssignment.student_group_id.in_(group_ids),
                    ClassroomAssessmentAssignment.institution_id == institution_id,
                    ClassroomAssessmentAssignment.is_active.is_(True),
                )
            )

        return assignments

    async def _classroom_comparison(
        self, classroom: Classroom, institution_id: UUID
    ) -> ClassroomComparison:
        students_result = await self.db.execute(
            select(func.count(Student.id)).where(
                Student.classroom_id == classroom.id,
                Student.institution_id == institution_id,
                Student.is_active.is_(True),
            )
        )
        student_count = students_result.scalar() or 0

        assignments_result = await self.db.execute(
            select(ClassroomAssessmentAssignment).where(
                ClassroomAssessmentAssignment.classroom_id == classroom.id,
                ClassroomAssessmentAssignment.is_active.is_(True),
            )
        )
        assignments = assignments_result.scalars().all()
        assessment_ids = [a.assessment_id for a in assignments]

        if not assessment_ids:
            return ClassroomComparison(
                classroom_id=classroom.id,
                classroom_name=classroom.name,
                level=classroom.level or "",
                avg_score=0.0,
                pass_rate=0.0,
                completion_rate=0.0,
                total_students=student_count,
                assessments_completed=0,
            )

        attempts_result = await self.db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.assessment_id.in_(assessment_ids),
                AssessmentAttempt.is_deleted.is_(False),
            )
        )
        attempts = attempts_result.scalars().all()
        completed = [a for a in attempts if a.status.value == "graded" and a.percentage]
        scores = [float(a.percentage) for a in completed]

        return ClassroomComparison(
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            level=classroom.level or "",
            avg_score=round(mean(scores), 1) if scores else 0.0,
            pass_rate=round(
                sum(1 for a in completed if a.passed) / len(completed) * 100, 1
            )
            if completed
            else 0.0,
            completion_rate=round(
                len(completed) / (len(assessment_ids) * student_count) * 100, 1
            )
            if assessment_ids and student_count
            else 0.0,
            total_students=student_count,
            assessments_completed=len(completed),
        )

    async def _group_performance(
        self, group: StudentGroup, institution_id: UUID
    ) -> GroupPerformance:
        # Get group members
        members_result = await self.db.execute(
            select(student_group_members.c.student_id).where(
                student_group_members.c.group_id == group.id
            )
        )
        student_ids = [row[0] for row in members_result.all()]

        # Assignments for this group
        assignments_result = await self.db.execute(
            select(ClassroomAssessmentAssignment).where(
                ClassroomAssessmentAssignment.student_group_id == group.id,
                ClassroomAssessmentAssignment.is_active.is_(True),
            )
        )
        assignments = assignments_result.scalars().all()
        assessment_ids = [a.assessment_id for a in assignments]

        classroom_name = ""
        if group.classroom_id:
            c_result = await self.db.execute(
                select(Classroom.name).where(Classroom.id == group.classroom_id)
            )
            classroom_name = c_result.scalar() or ""

        if not assessment_ids or not student_ids:
            return GroupPerformance(
                group_id=group.id,
                group_name=group.name,
                classroom_name=classroom_name,
                total_members=len(student_ids),
                avg_score=0.0,
                pass_rate=0.0,
                assessments_completed=0,
            )

        # Get user IDs for these students
        users_result = await self.db.execute(
            select(Student.user_id).where(Student.id.in_(student_ids))
        )
        user_ids = [row[0] for row in users_result.all()]

        attempts_result = await self.db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.assessment_id.in_(assessment_ids),
                AssessmentAttempt.user_id.in_(user_ids),
                AssessmentAttempt.is_deleted.is_(False),
            )
        )
        attempts = attempts_result.scalars().all()
        completed = [a for a in attempts if a.status.value == "graded" and a.percentage]
        scores = [float(a.percentage) for a in completed]

        return GroupPerformance(
            group_id=group.id,
            group_name=group.name,
            classroom_name=classroom_name,
            total_members=len(student_ids),
            avg_score=round(mean(scores), 1) if scores else 0.0,
            pass_rate=round(
                sum(1 for a in completed if a.passed) / len(completed) * 100, 1
            )
            if completed
            else 0.0,
            assessments_completed=len(completed),
        )

    async def _institution_score_trend(
        self, institution_id: UUID
    ) -> List[ScoreSnapshot]:
        attempts = await self._get_institution_attempts(institution_id)
        completed = [
            a
            for a in attempts
            if a.status.value == "graded"
            and a.percentage is not None
            and a.submitted_at is not None
        ]
        return self._score_trend_from_attempts(completed)

    def _score_trend_from_attempts(
        self, completed_attempts: List[AssessmentAttempt]
    ) -> List[ScoreSnapshot]:
        """Group completed attempts by month and compute avg + pass rate."""
        monthly: Dict[str, List[AssessmentAttempt]] = defaultdict(list)
        for attempt in completed_attempts:
            if attempt.submitted_at:
                submitted_at = attempt.submitted_at
                if isinstance(submitted_at, str):
                    submitted_at = datetime.fromisoformat(submitted_at)
                key = submitted_at.strftime("%Y-%m")
                monthly[key].append(attempt)

        snapshots = []
        for period in sorted(monthly.keys())[-6:]:  # last 6 months
            group = monthly[period]
            scores = [float(a.percentage) for a in group if a.percentage]
            pass_count = sum(1 for a in group if a.passed)
            snapshots.append(
                ScoreSnapshot(
                    period=period,
                    avg_score=round(mean(scores), 1) if scores else 0.0,
                    pass_rate=round(pass_count / len(group) * 100, 1),
                    total_attempts=len(group),
                )
            )
        return snapshots

    def _student_performance_summary(
        self,
        student: Student,
        user: User,
        assessment_ids: List[UUID],
        all_attempts: List[AssessmentAttempt],
    ) -> StudentPerformanceSummary:
        student_attempts = [
            a
            for a in all_attempts
            if a.user_id == user.id
            and a.assessment_id in assessment_ids
            and a.status.value == "graded"
            and a.percentage is not None
        ]

        scores = [float(a.percentage) for a in student_attempts]
        completed_ids = {a.assessment_id for a in student_attempts}

        return StudentPerformanceSummary(
            student_id=student.id,
            student_name=f"{user.first_name} {user.last_name}",
            student_code=student.student_code,
            total_assessments=len(assessment_ids),
            completed_assessments=len(completed_ids),
            avg_score=round(mean(scores), 1) if scores else 0.0,
            pass_rate=round(
                sum(1 for a in student_attempts if a.passed)
                / len(student_attempts)
                * 100,
                1,
            )
            if student_attempts
            else 0.0,
            highest_score=round(max(scores), 1) if scores else 0.0,
            lowest_score=round(min(scores), 1) if scores else 0.0,
            trend=self._calculate_trend(scores),
        )

    async def _question_difficulty_for_assessments(
        self, assessment_ids: List[UUID]
    ) -> List[QuestionInsight]:
        if not assessment_ids:
            return []

        from sqlalchemy import Integer, cast

        result = await self.db.execute(
            select(
                Answer.question_id,
                func.count(Answer.id).label("total"),
                func.sum(cast(Answer.is_correct, Integer)).label("correct"),
            )
            .join(
                AssessmentAttempt,
                Answer.attempt_id == AssessmentAttempt.id,
            )
            .where(AssessmentAttempt.assessment_id.in_(assessment_ids))
            .group_by(Answer.question_id)
        )
        rows = result.all()

        question_ids = [row.question_id for row in rows]
        questions_result = await self.db.execute(
            select(Question).where(Question.id.in_(question_ids))
        )
        questions_by_id = {q.id: q for q in questions_result.scalars().all()}

        insights = []
        for row in rows:
            total = row.total or 0
            correct = int(row.correct or 0)
            q = questions_by_id.get(row.question_id)
            insights.append(
                QuestionInsight(
                    question_id=row.question_id,
                    question_text=(getattr(q, "question_text", "") or "")[:120],
                    correct_rate=round(correct / total * 100, 1) if total else 0.0,
                    total_answers=total,
                    difficulty=getattr(q, "difficulty", None),
                )
            )

        return sorted(insights, key=lambda x: x.correct_rate)

    async def _get_student_rank(
        self,
        student_id: UUID,
        classroom_id: Optional[UUID],
        institution_id: UUID,
    ) -> Tuple[Optional[int], Optional[int]]:
        if not classroom_id:
            return None, None

        students_result = await self.db.execute(
            select(Student, User)
            .join(User, Student.user_id == User.id)
            .where(
                Student.classroom_id == classroom_id,
                Student.institution_id == institution_id,
                Student.is_active.is_(True),
            )
        )
        class_students = students_result.all()
        class_size = len(class_students)

        # Get assignments for classroom
        assignments_result = await self.db.execute(
            select(ClassroomAssessmentAssignment).where(
                ClassroomAssessmentAssignment.classroom_id == classroom_id,
                ClassroomAssessmentAssignment.is_active.is_(True),
            )
        )
        assignments = assignments_result.scalars().all()
        assessment_ids = [a.assessment_id for a in assignments]

        if not assessment_ids:
            return None, class_size

        user_ids = [row[1].id for row in class_students]
        attempts = await self._get_attempts_for_assessments_by_users(
            assessment_ids, user_ids
        )

        # Average score per student
        student_avgs: Dict[UUID, float] = {}
        for student, user in class_students:
            student_attempts = [
                a
                for a in attempts
                if a.user_id == user.id
                and a.status.value == "graded"
                and a.percentage is not None
            ]
            scores = [float(a.percentage) for a in student_attempts]
            student_avgs[student.id] = mean(scores) if scores else 0.0

        ranked = sorted(student_avgs.items(), key=lambda x: x[1], reverse=True)
        for i, (sid, _) in enumerate(ranked, start=1):
            if sid == student_id:
                return i, class_size

        return None, class_size

    def _calculate_trend(self, scores: List[float]) -> str:
        if len(scores) < 3:
            return "insufficient_data"
        # Compare average of first half vs second half
        mid = len(scores) // 2
        first_half = mean(scores[:mid])
        second_half = mean(scores[mid:])
        diff = second_half - first_half
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        return "stable"

    def _letter_grade(self, percentage: float) -> str:
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        return "F"

    def _compute_top_stats(
        self, attempts: List[AssessmentAttempt], total_assigned: int
    ) -> Tuple[float, float, float]:
        completed = [
            a
            for a in attempts
            if a.status.value == "graded" and a.percentage is not None
        ]
        scores = [float(a.percentage) for a in completed]
        avg = mean(scores) if scores else 0.0
        pass_rate = (
            sum(1 for a in completed if a.passed) / len(completed) * 100
            if completed
            else 0.0
        )
        completion_rate = (
            len(completed) / total_assigned * 100 if total_assigned else 0.0
        )
        return avg, pass_rate, completion_rate

    async def get_dashboard_stats(
        self, institution_id: UUID
    ) -> InstitutionDashboardStats:
        from sqlalchemy import select, func

        # Total students
        student_count = await self.db.execute(
            select(func.count(Student.id)).where(
                Student.institution_id == institution_id, Student.is_active.is_(True)
            )
        )
        total_students = student_count.scalar_one()

        teacher_count = await self.db.execute(
            select(func.count(InstitutionTeacher.id)).where(
                InstitutionTeacher.institution_id == institution_id
            )
        )
        total_teachers = teacher_count.scalar_one()

        classroom_count = await self.db.execute(
            select(func.count(Classroom.id)).where(
                Classroom.institution_id == institution_id,
                Classroom.is_active.is_(True),
            )
        )
        total_classrooms = classroom_count.scalar_one()

        assessment_count = await self.db.execute(
            select(func.count(ClassroomAssessmentAssignment.id)).where(
                ClassroomAssessmentAssignment.institution_id == institution_id
            )
        )
        total_assignments = assessment_count.scalar_one()

        recent_students = await self.get_recent_students(institution_id)

        return InstitutionDashboardStats(
            total_students=total_students,
            active_students=total_students,
            total_teachers=total_teachers,
            total_classrooms=total_classrooms,
            total_assessments_assigned=total_assignments,
            avg_score_across_institution=None,
            recent_activity=[],
            recent_students=recent_students,
        )

    async def list_students_detailed(
        self, institution_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[StudentWithClassroomResponse]:

        stmt = (
            select(Student, User)
            .join(User, Student.user_id == User.id)
            # Eagerly load the classroom relationship
            .options(selectinload(Student.category), selectinload(Student.classroom))
            .where(
                Student.institution_id == institution_id,
                Student.is_active.is_(True),
            )
            .options(selectinload(Student.category))
            .order_by(Student.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            StudentWithClassroomResponse(
                id=student.id,
                user_id=student.user_id,
                full_name=f"{user.first_name} {user.last_name}",
                email=user.email,
                student_code=student.student_code,
                registration_date=student.registration_date or student.created_at,
                is_active=student.is_active,
                classroom=ClassroomMinimal.model_validate(student.classroom)
                if student.classroom
                else None,
                path=student.category.display_name if student.category else None,
                user=UserRead.model_validate(student.user),
                institution_id=student.institution_id,
                guardian_email=student.guardian_email,
                created_at=student.created_at,
                updated_at=student.updated_at,
            )
            for student, user in rows
        ]

    async def list_students_by_classroom(
        self, institution_id: UUID, classroom_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[StudentWithClassroomResponse]:

        stmt = (
            select(Student, User)
            .join(User, Student.user_id == User.id)
            .options(selectinload(Student.category), selectinload(Student.classroom))
            .where(
                Student.institution_id == institution_id,
                Student.classroom_id == classroom_id,
                Student.is_active.is_(True),
            )
            .order_by(Student.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            StudentWithClassroomResponse(
                id=student.id,
                user_id=student.user_id,
                full_name=f"{user.first_name} {user.last_name}",
                email=user.email,
                student_code=student.student_code,
                registration_date=student.registration_date or student.created_at,
                is_active=student.is_active,
                classroom=ClassroomMinimal.model_validate(student.classroom)
                if student.classroom
                else None,
                path=student.category.display_name if student.category else None,
                user=UserRead.model_validate(
                    user
                ),  # Changed from student.user to user from row
                institution_id=student.institution_id,
                guardian_email=student.guardian_email,
                created_at=student.created_at,
                updated_at=student.updated_at,
            )
            for student, user in rows
        ]

    async def get_recent_students(self, institution_id: UUID) -> List[dict]:
        """
        Returns the 6 most recently added students in the institution.
        """

        stmt = (
            select(Student, User)
            .join(User, Student.user_id == User.id)
            .where(
                Student.institution_id == institution_id,
                Student.is_active.is_(True),
            )
            .options(selectinload(Student.category))
            .order_by(Student.created_at.desc())
            .limit(6)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "name": f"{user.first_name} {user.last_name}",
                "code": student.student_code,
                "class": student.category.display_name if student.category else None,
                "created_at": student.created_at,
                "status": student.is_active,
            }
            for student, user in rows
        ]
