import json
from datetime import datetime, timezone
from sqlalchemy import select
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.auth.models.student import Student
from src.domains.gamification.repositories.gamification_repository import (
    GamificationRepository,
)
from src.domains.gamification.models import (
    GamificationProfile,
    Badge,
    StudentAchievement,
)
from src.domains.gamification.schemas.schemas import (
    AssessmentCompletedEvent,
    GamificationResult,
    BadgeResponse,
    AchievementResponse,
    StudentAchievementResponse,
    LeaderboardResponse,
    LeaderboardEntryResponse,
)


# Level thresholds: level -> XP required
LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 300,
    4: 600,
    5: 1000,
    6: 1500,
    7: 2100,
    8: 2800,
    9: 3600,
    10: 4500,
}

RANK_TITLES = {
    1: "Beginner",
    2: "Learner",
    3: "Scholar",
    4: "Apprentice",
    5: "Adept",
    6: "Expert",
    7: "Master",
    8: "Grandmaster",
    9: "Champion",
    10: "Legend",
}


class GamificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GamificationRepository(db)

    # MAIN ENTRY POINT
    async def process_assessment_completed(
        self, event: AssessmentCompletedEvent
    ) -> GamificationResult:
        """Main method called when a student completes an assessment"""
        profile = await self.repo.get_or_create_profile(event.student_id)

        # Calculate points earned
        percentage = (event.score / event.total_questions) * 100
        points_earned = self._calculate_points(event.score, event.total_questions)

        # Update profile stats
        profile.total_points += points_earned
        profile.experience_points += points_earned
        profile.total_assessments_completed += 1
        profile.total_questions_answered += event.total_questions
        profile.correct_answers += event.score

        # Update streak
        await self._update_streak(profile)

        # Check level up
        level_up, new_level, new_rank = self._check_level_up(profile)

        # Check achievements
        completed, progressed = await self._check_achievements(profile)

        # Award points for completed achievements
        for achievement in completed:
            profile.total_points += achievement.points_reward

        # Check badges
        badges_earned = await self._check_badges(
            profile,
            event=AssessmentCompletedEvent,
            context={
                "score_percentage": percentage,
                "is_perfect": event.score == event.total_questions,
                "is_first_assessment": profile.total_assessments_completed == 1,
                "time_taken": event.time_taken_seconds,
                "completed_at": event.completed_at,
            },
        )

        # Save all changes
        await self.repo.update_profile(profile)
        await self.db.commit()

        return GamificationResult(
            points_earned=points_earned,
            total_points=profile.total_points,
            level_up=level_up,
            new_level=new_level,
            new_rank_title=new_rank,
            current_streak=profile.current_streak,
            badges_earned=[
                BadgeResponse.model_validate(b.badge) for b in badges_earned
            ],
            achievements_completed=[
                AchievementResponse.model_validate(a.achievement) for a in completed
            ],
            achievements_progressed=[
                self._to_student_achievement_response(a) for a in progressed
            ],
        )

    # ============== POINTS CALCULATION ==============
    def _calculate_points(self, score: int, total: int) -> int:
        """Calculate points based on score percentage"""
        percentage = (score / total) * 100
        base_points = int(percentage)

        # Bonus for perfect score
        if score == total:
            base_points += 20

        # Bonus for high scores
        if percentage >= 90:
            base_points += 10
        elif percentage >= 80:
            base_points += 5

        return base_points

    # ============== STREAK MANAGEMENT ==============
    async def _update_streak(self, profile: GamificationProfile) -> bool:
        """Update streak based on last activity date"""
        today = datetime.now(timezone.utc).date()
        last_activity = profile.last_activity_date

        if last_activity is None:
            profile.current_streak = 1
        else:
            last_date = last_activity.date()
            days_diff = (today - last_date).days

            if days_diff == 0:
                # Same day, no streak change
                pass
            elif days_diff == 1:
                # Consecutive day, increment streak
                profile.current_streak += 1
            else:
                # Streak broken, reset to 1
                profile.current_streak = 1

        # Update longest streak if needed
        if profile.current_streak > profile.longest_streak:
            profile.longest_streak = profile.current_streak

        profile.last_activity_date = datetime.now(timezone.utc).isoformat()
        return True

    # ============== LEVEL SYSTEM ==============
    def _check_level_up(
        self, profile: GamificationProfile
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """Check if profile should level up"""
        current_level = profile.current_level
        xp = profile.experience_points

        # Find the highest level the player qualifies for
        new_level = current_level
        for level, threshold in sorted(LEVEL_THRESHOLDS.items()):
            if xp >= threshold:
                new_level = level

        if new_level > current_level:
            profile.current_level = new_level
            profile.rank_title = RANK_TITLES.get(new_level, f"Level {new_level}")
            return True, new_level, profile.rank_title

        return False, None, None

    # ============== ACHIEVEMENTS ==============
    async def _check_achievements(
        self, profile: GamificationProfile
    ) -> Tuple[List[StudentAchievement], List[StudentAchievement]]:
        """Check and update all achievement progress"""
        completed = []
        progressed = []

        achievements = await self.repo.get_all_active_achievements()

        for achievement in achievements:
            student_achievement = await self.repo.get_student_achievement(
                profile.id, achievement.id
            )

            if not student_achievement:
                student_achievement = await self.repo.create_student_achievement(
                    profile.id, achievement.id
                )

            if student_achievement.is_completed:
                continue

            # Get current value based on achievement type
            current_value = self._get_achievement_value(
                profile, achievement.achievement_type
            )
            student_achievement.current_value = current_value

            # Check if completed
            if current_value >= achievement.target_value:
                student_achievement.is_completed = True
                student_achievement.completed_at = datetime.now(
                    timezone.utc
                ).isoformat()
                completed.append(student_achievement)
            else:
                progressed.append(student_achievement)

            await self.repo.update_student_achievement(student_achievement)

        return completed, progressed

    def _get_achievement_value(
        self, profile: GamificationProfile, achievement_type: str
    ) -> int:
        """Get the current value for an achievement type from profile"""
        mapping = {
            "assessments_completed": profile.total_assessments_completed,
            "questions_answered": profile.total_questions_answered,
            "correct_answers": profile.correct_answers,
            "streak_days": profile.current_streak,
            "points_earned": profile.total_points,
        }
        return mapping.get(achievement_type, 0)

    def _to_student_achievement_response(
        self, student_achievement: StudentAchievement
    ) -> StudentAchievementResponse:
        """Convert StudentAchievement to response with progress percentage"""
        target = student_achievement.achievement.target_value
        current = student_achievement.current_value
        progress = (current / target) * 100 if target > 0 else 0

        return StudentAchievementResponse(
            id=student_achievement.id,
            achievement=AchievementResponse.model_validate(
                student_achievement.achievement
            ),
            current_value=current,
            is_completed=student_achievement.is_completed,
            completed_at=student_achievement.completed_at,
            progress_percentage=min(progress, 100),
        )

    # ============== BADGES ==============
    async def _check_badges(
        self,
        profile: GamificationProfile,
        event: type,
        context: dict,
    ) -> List:
        """Check and award eligible badges"""
        earned = []
        badges = await self.repo.get_all_active_badges()

        for badge in badges:
            # Skip if already earned
            if await self.repo.has_badge(profile.id, badge.id):
                continue

            # Check criteria
            if self._evaluate_badge_criteria(badge, profile, context):
                student_badge = await self.repo.award_badge(profile.id, badge.id)
                student_badge.badge = badge
                earned.append(student_badge)

        return earned

    def _evaluate_badge_criteria(
        self, badge: Badge, profile: GamificationProfile, context: dict
    ) -> bool:
        """Evaluate if badge criteria are met"""
        try:
            criteria = (
                json.loads(badge.criteria)
                if isinstance(badge.criteria, str)
                else badge.criteria
            )
        except (json.JSONDecodeError, TypeError):
            return False

        event_type = criteria.get("event")

        # Event-based badges
        if event_type == "first_assessment" and context.get("is_first_assessment"):
            return True

        if event_type == "assessment_100_percent" and context.get("is_perfect"):
            return True

        if event_type == "assessment_after_10pm":
            completed_at = context.get("completed_at")
            if completed_at and completed_at.hour >= 22:
                return True

        if event_type == "assessment_before_6am":
            completed_at = context.get("completed_at")
            if completed_at and completed_at.hour < 6:
                return True

        if event_type == "speed_demon":
            time_taken = context.get("time_taken", 0)
            if time_taken > 0 and time_taken < 300:  # Under 5 minutes
                return True

        # Threshold-based badges
        if event_type == "streak_milestone":
            required_streak = criteria.get("streak_days", 0)
            if profile.current_streak >= required_streak:
                return True

        if event_type == "points_milestone":
            required_points = criteria.get("points", 0)
            if profile.total_points >= required_points:
                return True

        return False

    #  LEADERBOARD
    async def get_leaderboard(
        self,
        limit: int = 100,
        offset: int = 0,
        category_id: Optional[UUID] = None,
        institution_id: Optional[UUID] = None,
        current_student_id: Optional[UUID] = None,
    ) -> LeaderboardResponse:
        """Get leaderboard with rankings"""
        profiles = await self.repo.get_leaderboard(
            limit=limit,
            offset=offset,
            category_id=category_id,
            institution_id=institution_id,
        )

        entries = []
        for i, profile in enumerate(profiles, start=offset + 1):
            student = profile.student
            badges = await self.repo.get_student_badges(profile.id)

            entries.append(
                LeaderboardEntryResponse(
                    rank=i,
                    student_id=student.id,
                    student_name=student.user.full_name if student.user else "Unknown",
                    student_avatar=student.user.avatar_url if student.user else None,
                    points=profile.total_points,
                    level=profile.current_level,
                    streak_days=profile.current_streak,
                    badges=[
                        BadgeResponse.model_validate(sb.badge) for sb in badges[:3]
                    ],
                )
            )

        current_user_rank = None
        if current_student_id:
            current_user_rank = await self.repo.get_student_rank(current_student_id)

        total = await self.repo.get_total_participants()

        leaderboard_type = "global"
        if category_id:
            leaderboard_type = "category"
        elif institution_id:
            leaderboard_type = "institution"

        return LeaderboardResponse(
            leaderboard_type=leaderboard_type,
            entries=entries,
            total_participants=total,
            current_user_rank=current_user_rank,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    async def get_student_profile(
        self, student_id: UUID
    ) -> Optional[GamificationProfile]:
        """Get full gamification profile for a student"""
        return await self.repo.get_profile_by_student_id(student_id)

    async def get_student_badges(self, student_id: UUID) -> List:
        """Get all badges earned by a student"""
        profile = await self.repo.get_profile_by_student_id(student_id)
        if not profile:
            return []
        return await self.repo.get_student_badges(profile.id)

    async def get_student_achievements(self, student_id: UUID) -> List:
        """Get all achievements with progress for a student"""
        profile = await self.repo.get_profile_by_student_id(student_id)
        if not profile:
            return []
        return await self.repo.get_student_achievements(profile.id)

    async def get_student_profile_from_user(self, user_id: UUID) -> Student | None:
        stmt = select(Student).where(Student.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # INITIALIZATION
    async def initialize_student_gamification(
        self, student_id: UUID
    ) -> GamificationProfile:
        """Initialize gamification for a new student"""
        profile = await self.repo.create_profile(student_id)

        # Initialize all achievements with 0 progress
        achievements = await self.repo.get_all_active_achievements()
        for achievement in achievements:
            await self.repo.create_student_achievement(profile.id, achievement.id)

        await self.db.commit()
        return profile
