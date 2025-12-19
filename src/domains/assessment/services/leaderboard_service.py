from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from src.domains.assessment.repositories.attempt_repository import (
    AssessmentAttemptRepository,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.auth.repositories.user_repository import UserRepository
from src.domains.assessment.schemas.statistics import (
    LeaderboardEntry,
    LeaderboardResponse,
)
from src.domains.assessment.enums import AttemptStatus

from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.models.assessment import Assessment
from src.domains.content.models.subject import Subject
from sqlalchemy import and_, case


class LeaderboardService:
    """Service for leaderboard operations"""

    def __init__(self, db: Session):
        self.db = db
        self.attempt_repo = AssessmentAttemptRepository(db)
        self.assessment_repo = AssessmentRepository(db)
        self.user_repo = UserRepository(db)

    async def get_assessment_leaderboard(
        self,
        assessment_id: UUID,
        limit: int = 100,
        current_user_id: Optional[UUID] = None,
    ) -> LeaderboardResponse:
        """Get leaderboard for a specific assessment"""
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            from src.core.exceptions import ResourceNotFoundException

            raise ResourceNotFoundException("Assessment", assessment_id)

        # Get top attempts
        attempts = self.attempt_repo.get_leaderboard(assessment_id, limit)

        # Build leaderboard entries
        entries = []
        for rank, attempt in enumerate(attempts, 1):
            user = self.user_repo.get_by_id(attempt.user_id)

            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    user_id=attempt.user_id,
                    user_name=user.full_name if user else "Unknown",
                    score=attempt.score,
                    percentage=attempt.percentage,
                    time_spent_seconds=attempt.time_spent_seconds,
                    submitted_at=attempt.submitted_at,
                )
            )

        # Get user's rank if provided
        user_rank = None
        if current_user_id:
            user_attempt = self.attempt_repo.get_latest_attempt(
                current_user_id, assessment_id
            )
            if user_attempt and user_attempt.status == AttemptStatus.GRADED:
                user_rank = self.attempt_repo.calculate_rank(user_attempt.id)

        # Count total participants
        total_participants = self.attempt_repo.count(
            {
                "assessment_id": assessment_id,
                "status": AttemptStatus.GRADED,
                "is_deleted": False,
            }
        )

        return LeaderboardResponse(
            assessment_id=assessment_id,
            assessment_title=assessment.title,
            entries=entries,
            total_participants=total_participants,
            user_rank=user_rank,
        )

    async def get_global_leaderboard(
        self,
        limit: int = 100,
        assessment_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get global leaderboard across all assessments"""
        # TODO: Implement global leaderboard with aggregation
        # This would aggregate scores across multiple assessments
        pass

    async def get_subject_leaderboard(
        self, subject_id: UUID, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific subject"""
        # Get all assessments for subject
        assessments = self.assessment_repo.get_by_subject(subject_id)
        assessment_ids = [a.id for a in assessments]

        # Aggregate user scores
        from sqlalchemy import and_
        from src.domains.assessment.models.attempt import AssessmentAttempt

        user_scores = (
            self.db.query(
                AssessmentAttempt.user_id,
                func.count(AssessmentAttempt.id).label("total_attempts"),
                func.avg(AssessmentAttempt.score).label("average_score"),
                func.sum(AssessmentAttempt.points_earned).label("total_points"),
            )
            .filter(
                and_(
                    AssessmentAttempt.assessment_id.in_(assessment_ids),
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                )
            )
            .group_by(AssessmentAttempt.user_id)
            .order_by(desc("average_score"), desc("total_points"))
            .limit(limit)
            .all()
        )

        # Build leaderboard
        leaderboard = []
        for rank, (user_id, attempts, avg_score, total_points) in enumerate(
            user_scores, 1
        ):
            user = self.user_repo.get_by_id(user_id)

            leaderboard.append(
                {
                    "rank": rank,
                    "user_id": str(user_id),
                    "user_name": user.full_name if user else "Unknown",
                    "total_attempts": attempts,
                    "average_score": float(avg_score) if avg_score else 0.0,
                    "total_points": float(total_points) if total_points else 0.0,
                }
            )

        return leaderboard

    async def get_user_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """Get comprehensive statistics for a user"""
        from src.domains.assessment.models.attempt import AssessmentAttempt
        from sqlalchemy import and_

        # Overall stats
        total_attempts = self.attempt_repo.count(
            {"user_id": user_id, "is_deleted": False}
        )

        graded_attempts = self.attempt_repo.count(
            {"user_id": user_id, "status": AttemptStatus.GRADED, "is_deleted": False}
        )

        passed_attempts = self.attempt_repo.count(
            {
                "user_id": user_id,
                "status": AttemptStatus.GRADED,
                "passed": True,
                "is_deleted": False,
            }
        )

        # Average score
        avg_result = (
            self.db.query(func.avg(AssessmentAttempt.score))
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                )
            )
            .scalar()
        )

        average_score = float(avg_result) if avg_result else 0.0
        pass_rate = (
            (passed_attempts / graded_attempts * 100) if graded_attempts > 0 else 0.0
        )

        # Recent attempts
        recent_attempts = self.attempt_repo.get_user_attempts(
            user_id, status=AttemptStatus.GRADED, skip=0, limit=10
        )

        return {
            "user_id": str(user_id),
            "total_attempts": total_attempts,
            "graded_attempts": graded_attempts,
            "passed_attempts": passed_attempts,
            "pass_rate": pass_rate,
            "average_score": average_score,
            "recent_attempts": [
                {
                    "assessment_id": str(a.assessment_id),
                    "score": float(a.score),
                    "percentage": float(a.percentage),
                    "passed": a.passed,
                    "submitted_at": a.submitted_at,
                }
                for a in recent_attempts
            ],
        }

    async def dashboard_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get comprehensive statistics for a user including tests and exams"""

        # Tests stats
        test_attempts_count = self.attempt_repo.count(
            {
                "user_id": user_id,
                "is_deleted": False,
                "assessment.assessment_type": "TEST",
            }
        )

        # Exams stats
        exam_attempts_count = self.attempt_repo.count(
            {
                "user_id": user_id,
                "is_deleted": False,
                "assessment.assessment_type": "EXAM",
            }
        )

        # Count correct answers for tests
        test_correct_answers = (
            self.db.query(func.sum(AssessmentAttempt.correct_answers))
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == "TEST",
                )
            )
            .scalar()
            or 0
        )

        # Count correct answers for exams
        exam_correct_answers = (
            self.db.query(func.sum(AssessmentAttempt.correct_answers))
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == "EXAM",
                )
            )
            .scalar()
            or 0
        )

        # Average time per question (in minutes)
        attempt_time_minutes = AssessmentAttempt.time_spent_seconds / 60

        avg_time_result = (
            self.db.query(
                func.avg(
                    case(
                        (
                            attempt_time_minutes > 0,
                            attempt_time_minutes
                            / func.nullif(AssessmentAttempt.total_questions, 0),
                        )
                    )
                )
            )
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    AssessmentAttempt.time_spent_seconds.isnot(None),
                )
            )
            .scalar()
        )

        avg_time_per_question = (
            round(float(avg_time_result), 2) if avg_time_result else 0.0
        )

        # Recent test performance for chart (last 10 tests) with subject info
        recent_tests = (
            self.db.query(AssessmentAttempt, Assessment, Subject)
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .outerjoin(Subject, Assessment.subject_id == Subject.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == "TEST",
                )
            )
            .order_by(desc(AssessmentAttempt.submitted_at))
            .limit(10)
            .all()
        )

        # Recent exam performance for chart (last 10 exams) with subject info
        recent_exams = (
            self.db.query(AssessmentAttempt, Assessment, Subject)
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .outerjoin(Subject, Assessment.subject_id == Subject.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == "EXAM",
                )
            )
            .order_by(desc(AssessmentAttempt.submitted_at))
            .limit(10)
            .all()
        )

        # Overall test average
        test_avg_score = (
            self.db.query(func.avg(AssessmentAttempt.percentage))
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == "TEST",
                )
            )
            .scalar()
            or 0.0
        )

        # Overall exam average
        exam_avg_score = (
            self.db.query(func.avg(AssessmentAttempt.percentage))
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == "EXAM",
                )
            )
            .scalar()
            or 0.0
        )

        # Assessment history by subject (last 20)
        subject_history = (
            self.db.query(AssessmentAttempt, Assessment, Subject)
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .outerjoin(Subject, Assessment.subject_id == Subject.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.subject_id.isnot(None),
                )
            )
            .order_by(desc(AssessmentAttempt.created_at))
            .limit(20)
            .all()
        )

        # Assessment history by exam type (last 20)
        exam_history = (
            self.db.query(AssessmentAttempt, Assessment, Subject)
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .outerjoin(Subject, Assessment.subject_id == Subject.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == "EXAM",
                )
            )
            .order_by(desc(AssessmentAttempt.created_at))
            .limit(20)
            .all()
        )

        # Reverse to show oldest first (chronological order)
        recent_tests_reversed = list(reversed(recent_tests))
        recent_exams_reversed = list(reversed(recent_exams))

        return {
            "user_id": str(user_id),
            # Stat cards data
            "stats": {
                "tests_attempted": test_attempts_count,
                "test_correct_answers": int(test_correct_answers),
                "exams_attempted": exam_attempts_count,
                "exam_correct_answers": int(exam_correct_answers),
                "avg_time_per_question": avg_time_per_question,
            },
            # Chart data for tests
            "test_performance_chart": {
                "categories": [
                    subject.name if subject else f"Test {i + 1}"
                    for i, (_, _, subject) in enumerate(recent_tests_reversed)
                ],
                "series": [
                    {
                        "name": "Score",
                        "data": [
                            float(attempt.percentage)
                            for attempt, _, _ in recent_tests_reversed
                        ],
                    }
                ],
            },
            # Chart data for exams
            "exam_performance_chart": {
                "categories": [
                    subject.name if subject else f"Exam {i + 1}"
                    for i, (_, _, subject) in enumerate(recent_exams_reversed)
                ],
                "series": [
                    {
                        "name": "Score",
                        "data": [
                            float(attempt.percentage)
                            for attempt, _, _ in recent_exams_reversed
                        ],
                    }
                ],
            },
            # Assessment history - Subjects
            "subject_history": [
                {
                    "sn": idx + 1,
                    "title": assessment.title
                    or (subject.name if subject else "Untitled"),
                    "assessment_id": str(assessment.id),
                    "attempt_id": str(attempt.id),
                    "average_score": f"{float(attempt.percentage):.1f}%",
                    "status": self._get_status(attempt),
                    "comment": self._get_comment(attempt),
                    "date_created": attempt.created_at.strftime("%Y-%m-%d %H:%M"),
                }
                for idx, (attempt, assessment, subject) in enumerate(subject_history)
            ],
            # Assessment history - Exams
            "exam_history": [
                {
                    "sn": idx + 1,
                    "title": assessment.title or (subject.name if subject else "Exam"),
                    "assessment_id": str(assessment.id),
                    "attempt_id": str(attempt.id),
                    "average_score": f"{float(attempt.percentage):.1f}%",
                    "status": self._get_status(attempt),
                    "comment": self._get_comment(attempt),
                    "date_created": attempt.created_at.strftime("%Y-%m-%d %H:%M"),
                }
                for idx, (attempt, assessment, subject) in enumerate(exam_history)
            ],
            # Report summary radial chart values
            "summary": {
                "test_performance": round(float(test_avg_score), 1),
                "exam_performance": round(float(exam_avg_score), 1),
            },
        }

    def _get_status(self, attempt):
        """Determine status based on score"""
        if attempt.status != AttemptStatus.GRADED:
            return "pending"
        if attempt.percentage >= 75:
            return "excellent"
        elif attempt.percentage >= 50:
            return "good"
        else:
            return "needs improvement"

    def _get_comment(self, attempt):
        """Generate comment based on performance"""
        if attempt.status != AttemptStatus.GRADED:
            return "Not yet graded"
        if attempt.percentage >= 75:
            return "Great performance!"
        elif attempt.percentage >= 50:
            return "Good effort, keep improving"
        else:
            return "More practice needed"

        """Generate comment based on performance"""
        if attempt.status != AttemptStatus.GRADED:
            return "Not yet graded"
        if attempt.percentage >= 75:
            return "Great performance!"
        elif attempt.percentage >= 50:
            return "Good effort, keep improving"
        else:
            return "More practice needed"
