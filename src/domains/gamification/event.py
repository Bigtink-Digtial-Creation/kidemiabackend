from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.gamification.services.gamification_service import GamificationService
from src.domains.gamification.schemas.schemas import (
    AssessmentCompletedEvent,
    GamificationResult,
)


class GamificationEvents:
    """
    Event dispatcher for gamification system.
    """

    @staticmethod
    async def on_assessment_completed(
        db: AsyncSession,
        student_id: UUID,
        assessment_id: UUID,
        score: int,
        total_questions: int,
        time_taken_seconds: int,
        category_id: Optional[UUID] = None,
        completed_at: Optional[datetime] = None,
    ) -> GamificationResult:
        """
        Trigger gamification update when a student completes an assessment.

        Args:
            db: Database session
            student_id: The student who completed the assessment
            assessment_id: The assessment that was completed
            score: Number of correct answers
            total_questions: Total number of questions
            time_taken_seconds: Time taken to complete
            category_id: Optional category for category-specific badges
            completed_at: When the assessment was completed (defaults to now)

        Returns:
            GamificationResult with points earned, badges, achievements, etc.
        """
        event = AssessmentCompletedEvent(
            student_id=student_id,
            assessment_id=assessment_id,
            category_id=category_id,
            score=score,
            total_questions=total_questions,
            time_taken_seconds=time_taken_seconds,
            completed_at=completed_at or datetime.utcnow(),
        )

        service = GamificationService(db)
        return await service.process_assessment_completed(event)

    @staticmethod
    async def on_student_registered(
        db: AsyncSession,
        student_id: UUID,
    ) -> None:
        """
        Initialize gamification profile when a new student registers.

        Call this from your student registration service.
        """
        service = GamificationService(db)
        await service.initialize_student_gamification(student_id)

    @staticmethod
    async def get_student_gamification_summary(
        db: AsyncSession,
        student_id: UUID,
    ) -> dict:
        """
        Get gamification summary for display in student dashboard.

        Returns a dict with profile, streak, stats, badges, achievements, rank.
        """
        service = GamificationService(db)
        profile = await service.get_student_profile(student_id)
        if not profile:
            return None

        badges = await service.get_student_badges(student_id)
        achievements = await service.get_student_achievements(student_id)
        rank = await service.repo.get_student_rank(student_id)
        completed_achievements = [a for a in achievements if a.is_completed]

        return {
            "profile": {
                "total_points": profile.total_points,
                "level": profile.current_level,
                "rank_title": profile.rank_title,
            },
            "streak": {
                "current": profile.current_streak,
                "longest": profile.longest_streak,
            },
            "badges_count": len(badges),
            "achievements_completed": len(completed_achievements),
            "achievements_total": len(achievements),
            "rank": rank,
        }


# ============================================================
# EXAMPLE: How to use in Assessment Service
# ============================================================
"""
# src/domains/assessment/service.py

from src.domains.gamification.events import GamificationEvents

class AssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def submit_assessment(
        self,
        student_id: UUID,
        assessment_id: UUID,
        answers: List[Answer],
    ) -> AssessmentResultResponse:
        # 1. Grade the assessment
        assessment = await self.get_assessment(assessment_id)
        score = self._calculate_score(assessment, answers)
        total_questions = len(assessment.questions)
        time_taken = self._calculate_time_taken(...)
        
        # 2. Save the attempt
        attempt = await self._save_attempt(
            student_id=student_id,
            assessment_id=assessment_id,
            score=score,
            answers=answers,
        )
        
        # 3. Trigger gamification update
        gamification_result = await GamificationEvents.on_assessment_completed(
            db=self.db,
            student_id=student_id,
            assessment_id=assessment_id,
            category_id=assessment.category_id,
            score=score,
            total_questions=total_questions,
            time_taken_seconds=time_taken,
        )
        
        # 4. Return combined result
        return AssessmentResultResponse(
            attempt_id=attempt.id,
            score=score,
            total=total_questions,
            percentage=round((score / total_questions) * 100, 2),
            passed=score >= assessment.pass_mark,
            gamification=gamification_result,
        )
"""

# ============================================================
# EXAMPLE: How to use in Dashboard / Profile View
# ============================================================
"""
# src/domains/student/api.py

from src.domains.gamification.events import GamificationEvents

@router.get("/dashboard")
async def get_student_dashboard(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    # Get gamification summary
    gamification = await GamificationEvents.get_student_gamification_summary(
        db=db,
        student_id=student.id,
    )
    
    # Get other dashboard data...
    recent_assessments = await get_recent_assessments(student.id)
    upcoming = await get_upcoming_assessments(student.category_id)
    
    return {
        "student": student,
        "gamification": gamification,
        "recent_assessments": recent_assessments,
        "upcoming": upcoming,
    }
"""
