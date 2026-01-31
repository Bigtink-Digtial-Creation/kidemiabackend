"""
Enhanced Analytics Repository - Adding Topic-Level Analytics
Developed By Samuel Kufre Willie - 31 January 2026
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy import func, and_, case, cast, DateTime
from sqlalchemy.orm import Session
from uuid import UUID

from src.domains.auth.models.user import User
from src.domains.auth.models.student import Student
from src.domains.assessment.models.assessment import Assessment
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.models.answer import Answer
from src.domains.content.models.subject import Subject
from src.domains.content.models.topic import Topic
from src.domains.content.models.question import Question
from src.domains.gamification.models.leaderboard import GamificationProfile
from src.domains.payment.models.subscription import Subscription
from src.domains.payment.models.transaction import Transaction
from src.domains.forum.models.forum import ForumPost, ForumReply
from src.domains.auth.repositories.student_repositoty import StudentRepository


class AnalyticsRepository:
    """Enhanced repository with topic-level analytics"""

    def __init__(self, db: Session):
        self.db = db
        self.student_repo = StudentRepository(db)

    # ==================== NEW: TOPIC-LEVEL ANALYTICS ====================

    def get_student_topic_performance(self, student_id: UUID) -> List[Dict[str, Any]]:
        """Get detailed topic-level performance for a student"""
        user_id = self._get_student_user_id(student_id)

        # Get all questions attempted by the student with topic info
        results = (
            self.db.query(
                Topic.id.label("topic_id"),
                Topic.name.label("topic_name"),
                Subject.name.label("subject_name"),
                Subject.id.label("subject_id"),
                func.count(Answer.id).label("questions_attempted"),
                func.sum(case((Answer.is_correct.is_(True), 1), else_=0)).label(
                    "correct_answers"
                ),
                func.avg(case((Answer.is_correct.is_(True), 100), else_=0)).label(
                    "mastery_score"
                ),
            )
            .join(Question, Topic.id == Question.topic_id)
            .join(Answer, Question.id == Answer.question_id)
            .join(AssessmentAttempt, Answer.attempt_id == AssessmentAttempt.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .filter(AssessmentAttempt.user_id == user_id)
            .group_by(Topic.id, Topic.name, Subject.name, Subject.id)
            .all()
        )

        topic_performance = []
        for result in results:
            success_rate = (
                (result.correct_answers / result.questions_attempted * 100)
                if result.questions_attempted > 0
                else 0
            )

            # Determine mastery level
            if success_rate >= 80:
                mastery_level = "MASTERED"
            elif success_rate >= 60:
                mastery_level = "GOOD"
            elif success_rate >= 40:
                mastery_level = "DEVELOPING"
            else:
                mastery_level = "NEEDS_WORK"

            topic_performance.append(
                {
                    "topic_id": str(result.topic_id),
                    "topic_name": result.topic_name,
                    "subject_name": result.subject_name,
                    "subject_id": str(result.subject_id),
                    "questions_attempted": result.questions_attempted,
                    "correct_answers": result.correct_answers,
                    "success_rate": round(success_rate, 2),
                    "mastery_score": round(float(result.mastery_score or 0), 2),
                    "mastery_level": mastery_level,
                }
            )

        return topic_performance

    def get_topic_trend_analysis(
        self, student_id: UUID, topic_id: UUID, days: int = 30
    ) -> Dict[str, Any]:
        """Analyze performance trend for a specific topic over time"""
        user_id = self._get_student_user_id(student_id)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get attempts for this topic over time
        results = (
            self.db.query(
                func.date(AssessmentAttempt.graded_at).label("date"),
                func.count(Answer.id).label("total_questions"),
                func.sum(case((Answer.is_correct.is_(True), 1), else_=0)).label(
                    "correct"
                ),
            )
            .join(Answer, AssessmentAttempt.id == Answer.attempt_id)
            .join(Question, Answer.question_id == Question.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    Question.topic_id == topic_id,
                    AssessmentAttempt.graded_at >= cutoff_date,
                )
            )
            .group_by(func.date(AssessmentAttempt.graded_at))
            .order_by(func.date(AssessmentAttempt.graded_at))
            .all()
        )

        trend_data = [
            {
                "date": result.date.isoformat() if result.date else None,
                "success_rate": round(
                    (result.correct / result.total_questions * 100), 2
                )
                if result.total_questions > 0
                else 0,
                "questions_attempted": result.total_questions,
            }
            for result in results
        ]

        # Calculate trend direction
        if len(trend_data) >= 2:
            recent_avg = sum([d["success_rate"] for d in trend_data[-3:]]) / len(
                trend_data[-3:]
            )
            earlier_avg = sum([d["success_rate"] for d in trend_data[:3]]) / len(
                trend_data[:3]
            )
            trend = "improving" if recent_avg > earlier_avg else "declining"
        else:
            trend = "insufficient_data"

        return {"trend_direction": trend, "data_points": trend_data}

    def get_weak_topics_for_student(
        self, student_id: UUID, threshold: float = 60.0, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Identify topics where student needs improvement"""
        all_topics = self.get_student_topic_performance(student_id)

        # Filter and sort by success rate
        weak_topics = [t for t in all_topics if t["success_rate"] < threshold]
        weak_topics.sort(key=lambda x: x["success_rate"])

        return weak_topics[:limit]

    def get_recommended_topics_for_practice(
        self, student_id: UUID, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get topic recommendations based on performance and prerequisites"""
        weak_topics = self.get_weak_topics_for_student(student_id, threshold=70.0)

        recommendations = []
        for topic in weak_topics[:limit]:
            # Get related assessments for this topic
            assessments = (
                self.db.query(Assessment.id, Assessment.title)
                .join(Question, Assessment.subject_id == Question.subject_id)
                .filter(Question.topic_id == topic["topic_id"])
                .distinct()
                .limit(3)
                .all()
            )

            recommendations.append(
                {
                    "topic_id": topic["topic_id"],
                    "topic_name": topic["topic_name"],
                    "subject_name": topic["subject_name"],
                    "current_mastery": topic["success_rate"],
                    "mastery_level": topic["mastery_level"],
                    "reason": self._get_recommendation_reason(topic),
                    "suggested_assessments": [
                        {
                            "id": str(a.id),
                            "title": a.title,
                            "difficulty": "Random",
                        }
                        for a in assessments
                    ],
                }
            )

        return recommendations

    def _get_recommendation_reason(self, topic: Dict[str, Any]) -> str:
        """Generate reason for topic recommendation"""
        mastery = topic["success_rate"]
        if mastery < 40:
            return f"Fundamental gaps in {topic['topic_name']}. Start with basics."
        elif mastery < 60:
            return "Below average performance. Focus on core concepts."
        else:
            return "Close to mastery. A few more practice sessions will help."

    def generate_personalized_study_plan(
        self, student_id: UUID, duration_days: int = 14
    ) -> Dict[str, Any]:
        """Generate a personalized study plan based on performance data"""

        # Get student's weak areas
        weak_topics = self.get_weak_topics_for_student(
            student_id, threshold=65.0, limit=10
        )

        # Get overall performance
        performance = self.get_student_performance_summary(student_id)

        # Calculate daily study time based on performance
        if performance["average_score"] < 50:
            daily_minutes = 120  # 2 hours for struggling students
        elif performance["average_score"] < 70:
            daily_minutes = 90
        else:
            daily_minutes = 60

        # Create weekly schedule
        plan = {
            "duration_days": duration_days,
            "daily_study_minutes": daily_minutes,
            "focus_areas": [],
            "weekly_schedule": [],
            "milestones": [],
        }

        # Organize topics by subject
        topics_by_subject = {}
        for topic in weak_topics:
            subject = topic["subject_name"]
            if subject not in topics_by_subject:
                topics_by_subject[subject] = []
            topics_by_subject[subject].append(topic)

        # Create focus areas with time allocation
        total_topics = len(weak_topics)
        for idx, topic in enumerate(weak_topics[:5]):  # Top 5 priorities
            time_allocation = max(
                20, int(daily_minutes * (5 - idx) / 15)
            )  # More time for weaker areas

            plan["focus_areas"].append(
                {
                    "topic": topic["topic_name"],
                    "subject": topic["subject_name"],
                    "current_level": topic["mastery_level"],
                    "target_improvement": "+20%",
                    "daily_minutes": time_allocation,
                    "priority": idx + 1,
                }
            )

        # Generate 2-week schedule
        for week in range(1, 3):
            subjects = list(topics_by_subject.keys())

            if week <= len(subjects):
                subject = subjects[week - 1]
                topics = topics_by_subject[subject]

                theme = f"Master {topics[0]['topic_name']}"
            else:
                theme = "Review"

            week_plan = {
                "week": week,
                "theme": theme,
                "days": [],
            }

            for day in range(1, 8):
                day_idx = (week - 1) * 7 + day - 1
                topic_idx = day_idx % len(weak_topics) if weak_topics else 0

                if day_idx < len(weak_topics):
                    topic = weak_topics[topic_idx]
                    day_plan = {
                        "day": day,
                        "focus": topic["topic_name"],
                        "activities": [
                            {
                                "type": "video_lesson",
                                "duration": 20,
                                "description": f"Watch tutorial on {topic['topic_name']}",
                            },
                            {
                                "type": "practice",
                                "duration": 30,
                                "description": "Complete 10-15 questions",
                            },
                            {
                                "type": "review",
                                "duration": 10,
                                "description": "Review mistakes and explanations",
                            },
                        ],
                    }
                else:
                    # Review day
                    day_plan = {
                        "day": day,
                        "focus": "Review & Assessment",
                        "activities": [
                            {
                                "type": "assessment",
                                "duration": 45,
                                "description": "Take a practice test",
                            },
                            {
                                "type": "review",
                                "duration": 15,
                                "description": "Analyze performance",
                            },
                        ],
                    }

                week_plan["days"].append(day_plan)

            plan["weekly_schedule"].append(week_plan)

        # Add milestones
        plan["milestones"] = [
            {
                "week": 1,
                "target": "Complete 50 practice questions",
                "metric": "questions_completed",
            },
            {
                "week": 1,
                "target": "Achieve 60% average on weak topics",
                "metric": "topic_mastery",
            },
            {
                "week": 2,
                "target": "Complete 2 full assessments",
                "metric": "assessments_completed",
            },
            {
                "week": 2,
                "target": "Reach 75% on previously weak topics",
                "metric": "topic_mastery",
            },
        ]

        return plan

    def get_platform_overview(self) -> Dict[str, Any]:
        """Get high-level platform statistics"""
        total_users = self.db.query(func.count(User.id)).scalar() or 0
        total_students = self.db.query(func.count(Student.id)).scalar() or 0
        total_assessments = self.db.query(func.count(Assessment.id)).scalar() or 0
        total_questions = self.db.query(func.count(Question.id)).scalar() or 0

        active_subscriptions = (
            self.db.query(func.count(Subscription.id))
            .filter(Subscription.status == "ACTIVE")
            .scalar()
            or 0
        )

        total_attempts = self.db.query(func.count(AssessmentAttempt.id)).scalar() or 0

        completed_attempts = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(AssessmentAttempt.status == "GRADED")
            .scalar()
            or 0
        )

        total_revenue = (
            self.db.query(func.sum(Transaction.amount))
            .filter(Transaction.status == "COMPLETED")
            .scalar()
            or 0
        )

        return {
            "total_users": total_users,
            "total_students": total_students,
            "total_assessments": total_assessments,
            "total_questions": total_questions,
            "active_subscriptions": active_subscriptions,
            "total_attempts": total_attempts,
            "completed_attempts": completed_attempts,
            "completion_rate": round((completed_attempts / total_attempts * 100), 2)
            if total_attempts > 0
            else 0,
            "total_revenue": float(total_revenue),
        }

    def get_student_performance_summary(self, student_id: UUID) -> Dict[str, Any]:
        """Get comprehensive performance summary for a student"""
        user_id = self._get_student_user_id(student_id)

        total_attempts = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(AssessmentAttempt.user_id == user_id)
            .scalar()
            or 0
        )

        completed_attempts = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .scalar()
            or 0
        )

        avg_score = (
            self.db.query(func.avg(AssessmentAttempt.score))
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .scalar()
            or 0
        )

        passed_count = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == "GRADED",
                    AssessmentAttempt.passed.is_(True),
                )
            )
            .scalar()
            or 0
        )

        best_score = (
            self.db.query(func.max(AssessmentAttempt.score))
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .scalar()
            or 0
        )

        worst_score = (
            self.db.query(func.min(AssessmentAttempt.score))
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .scalar()
            or 0
        )

        gamification = (
            self.db.query(GamificationProfile)
            .filter(GamificationProfile.student_id == student_id)
            .first()
        )

        return {
            "total_attempts": total_attempts,
            "completed_attempts": completed_attempts,
            "average_score": round(float(avg_score), 2),
            "passed_count": passed_count,
            "pass_rate": round((passed_count / completed_attempts * 100), 2)
            if completed_attempts > 0
            else 0,
            "best_score": round(float(best_score), 2),
            "worst_score": round(float(worst_score), 2),
            "gamification": {
                "level": gamification.current_level if gamification else 1,
                "total_points": gamification.total_points if gamification else 0,
                "current_streak": gamification.current_streak if gamification else 0,
                "longest_streak": gamification.longest_streak if gamification else 0,
            }
            if gamification
            else None,
        }

    def get_student_subject_performance(self, student_id: UUID) -> List[Dict[str, Any]]:
        """Get student performance breakdown by subject"""
        user_id = self._get_student_user_id(student_id)

        results = (
            self.db.query(
                Subject.id,
                Subject.name,
                func.count(AssessmentAttempt.id).label("total_attempts"),
                func.avg(AssessmentAttempt.score).label("avg_score"),
                func.sum(case((AssessmentAttempt.passed.is_(True), 1), else_=0)).label(
                    "passed_count"
                ),
            )
            .join(Assessment, Subject.id == Assessment.subject_id)
            .join(AssessmentAttempt, Assessment.id == AssessmentAttempt.assessment_id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .group_by(Subject.id, Subject.name)
            .all()
        )

        return [
            {
                "subject_id": str(result.id),
                "subject_name": result.name,
                "total_attempts": result.total_attempts,
                "average_score": round(float(result.avg_score or 0), 2),
                "pass_rate": round(
                    (result.passed_count / result.total_attempts * 100), 2
                )
                if result.total_attempts > 0
                else 0,
            }
            for result in results
        ]

    def get_student_progress_over_time(
        self, student_id: UUID, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get student's score progression over time"""
        user_id = self._get_student_user_id(student_id)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = (
            self.db.query(
                func.date(AssessmentAttempt.graded_at).label("date"),
                func.avg(AssessmentAttempt.score).label("avg_score"),
                func.count(AssessmentAttempt.id).label("attempts"),
            )
            .filter(
                and_(
                    AssessmentAttempt.user_id == user_id,
                    AssessmentAttempt.status == "GRADED",
                    AssessmentAttempt.graded_at >= cutoff_date,
                )
            )
            .group_by(func.date(AssessmentAttempt.graded_at))
            .order_by(func.date(AssessmentAttempt.graded_at))
            .all()
        )

        return [
            {
                "date": result.date.isoformat() if result.date else None,
                "average_score": round(float(result.avg_score), 2),
                "attempts": result.attempts,
            }
            for result in results
        ]

    def _get_student_user_id(self, student_id) -> UUID:
        student = self.student_repo.get_by_id(student_id)
        return student.user_id

    # Add all other existing methods from your working repository...
    # (I'm including key ones, add rest as needed)

    def get_user_growth_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get user registration trends over time"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = (
            self.db.query(
                func.date(User.created_at).label("date"),
                func.count(User.id).label("count"),
            )
            .filter(User.created_at >= cutoff_date)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
            .all()
        )

        return [
            {
                "date": result.date.isoformat() if result.date else None,
                "count": result.count,
            }
            for result in results
        ]

    def get_assessment_performance_overview(self) -> Dict[str, Any]:
        """Get overall assessment performance metrics"""
        avg_score = (
            self.db.query(func.avg(AssessmentAttempt.score))
            .filter(AssessmentAttempt.status == "GRADED")
            .scalar()
            or 0
        )

        total_completed = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(AssessmentAttempt.status == "GRADED")
            .scalar()
            or 0
        )

        total_passed = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(
                and_(
                    AssessmentAttempt.status == "GRADED",
                    AssessmentAttempt.passed.is_(True),
                )
            )
            .scalar()
            or 0
        )

        avg_time = (
            self.db.query(func.avg(AssessmentAttempt.time_spent_seconds))
            .filter(AssessmentAttempt.status == "GRADED")
            .scalar()
            or 0
        )

        return {
            "average_score": round(float(avg_score), 2),
            "total_completed": total_completed,
            "total_passed": total_passed,
            "pass_rate": round((total_passed / total_completed * 100), 2)
            if total_completed > 0
            else 0,
            "average_completion_time_minutes": round(float(avg_time) / 60, 2),
        }

    def get_revenue_overview(self) -> Dict[str, Any]:
        """Get comprehensive revenue statistics"""
        total_revenue = (
            self.db.query(func.sum(Transaction.amount))
            .filter(Transaction.status == "COMPLETED")
            .scalar()
            or 0
        )

        first_day_of_month = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        monthly_revenue = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                and_(
                    Transaction.status == "COMPLETED",
                    Transaction.created_at >= first_day_of_month,
                )
            )
            .scalar()
            or 0
        )

        subscription_revenue = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                and_(
                    Transaction.status == "COMPLETED",
                    Transaction.transaction_type == "SUBSCRIPTION",
                )
            )
            .scalar()
            or 0
        )

        wallet_topup = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                and_(
                    Transaction.status == "COMPLETED",
                    Transaction.transaction_type == "WALLET_TOPUP",
                )
            )
            .scalar()
            or 0
        )

        assessment_revenue = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                and_(
                    Transaction.status == "COMPLETED",
                    Transaction.transaction_type == "EXAM_PURCHASE",
                )
            )
            .scalar()
            or 0
        )

        total_transactions = (
            self.db.query(func.count(Transaction.id))
            .filter(Transaction.status == "COMPLETED")
            .scalar()
            or 0
        )

        avg_transaction = (
            float(total_revenue) / total_transactions if total_transactions > 0 else 0
        )

        return {
            "total_revenue": float(total_revenue),
            "monthly_revenue": float(monthly_revenue),
            "subscription_revenue": float(subscription_revenue),
            "wallet_topup": float(wallet_topup),
            "assessment_revenue": float(assessment_revenue),
            "total_transactions": total_transactions,
            "average_transaction_value": round(avg_transaction, 2),
        }

    def get_revenue_by_period(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily revenue breakdown"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = (
            self.db.query(
                func.date(Transaction.created_at).label("date"),
                func.sum(Transaction.amount).label("revenue"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .filter(
                and_(
                    Transaction.status == "COMPLETED",
                    Transaction.created_at >= cutoff_date,
                )
            )
            .group_by(func.date(Transaction.created_at))
            .order_by(func.date(Transaction.created_at))
            .all()
        )

        return [
            {
                "date": result.date.isoformat() if result.date else None,
                "revenue": float(result.revenue or 0),
                "transactions": result.transaction_count,
            }
            for result in results
        ]

    def get_engagement_metrics(self) -> Dict[str, Any]:
        """Get platform engagement statistics"""
        yesterday = datetime.utcnow() - timedelta(days=1)
        dau = (
            self.db.query(func.count(func.distinct(User.id)))
            .filter(cast(User.last_login, DateTime) >= yesterday)
            .scalar()
            or 0
        )

        last_month = datetime.utcnow() - timedelta(days=30)
        mau = (
            self.db.query(func.count(func.distinct(User.id)))
            .filter(cast(User.last_login, DateTime) >= last_month)
            .scalar()
            or 0
        )

        forum_posts_last_week = (
            self.db.query(func.count(ForumPost.id))
            .filter(ForumPost.created_at >= datetime.utcnow() - timedelta(days=7))
            .scalar()
            or 0
        )

        forum_replies_last_week = (
            self.db.query(func.count(ForumReply.id))
            .filter(ForumReply.created_at >= datetime.utcnow() - timedelta(days=7))
            .scalar()
            or 0
        )

        avg_session = (
            self.db.query(func.avg(AssessmentAttempt.time_spent_seconds))
            .filter(AssessmentAttempt.status == "GRADED")
            .scalar()
            or 0
        )

        return {
            "daily_active_users": dau,
            "monthly_active_users": mau,
            "forum_posts_this_week": forum_posts_last_week,
            "forum_replies_this_week": forum_replies_last_week,
            "average_session_minutes": round(float(avg_session) / 60, 2),
        }

    def get_subscription_analytics(self) -> Dict[str, Any]:
        """Get subscription-related metrics"""
        subscription_breakdown = (
            self.db.query(
                Subscription.subscription_type,
                func.count(Subscription.id).label("count"),
            )
            .filter(Subscription.status == "ACTIVE")
            .group_by(Subscription.subscription_type)
            .all()
        )

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        cancelled_last_month = (
            self.db.query(func.count(Subscription.id))
            .filter(
                Subscription.cancelled_at.isnot(None),
                cast(Subscription.cancelled_at, DateTime) >= thirty_days_ago,
            )
            .scalar()
            or 0
        )

        active_month_ago = (
            self.db.query(func.count(Subscription.id))
            .filter(
                and_(
                    Subscription.status == "ACTIVE",
                    Subscription.created_at < thirty_days_ago,
                )
            )
            .scalar()
            or 0
        )

        churn_rate = (
            (cancelled_last_month / active_month_ago * 100)
            if active_month_ago > 0
            else 0
        )

        mrr = (
            self.db.query(func.sum(Subscription.price))
            .filter(
                and_(
                    Subscription.status == "ACTIVE",
                    Subscription.billing_cycle == "monthly",
                )
            )
            .scalar()
            or 0
        )

        return {
            "breakdown": [
                {"type": result.subscription_type, "count": result.count}
                for result in subscription_breakdown
            ],
            "churn_rate": round(churn_rate, 2),
            "monthly_recurring_revenue": float(mrr),
        }

    # Add remaining methods from your working code...
    def get_assessment_by_category(self) -> List[Dict[str, Any]]:
        """Get assessment attempts grouped by category"""
        results = (
            self.db.query(
                Assessment.category,
                func.count(AssessmentAttempt.id).label("total_attempts"),
                func.avg(AssessmentAttempt.score).label("avg_score"),
                func.sum(case((AssessmentAttempt.passed.is_(True), 1), else_=0)).label(
                    "passed_count"
                ),
            )
            .join(AssessmentAttempt, Assessment.id == AssessmentAttempt.assessment_id)
            .filter(AssessmentAttempt.status == "GRADED")
            .group_by(Assessment.category)
            .all()
        )

        return [
            {
                "category": result.category,
                "total_attempts": result.total_attempts,
                "average_score": round(float(result.avg_score or 0), 2),
                "passed_count": result.passed_count,
                "pass_rate": round(
                    (result.passed_count / result.total_attempts * 100), 2
                )
                if result.total_attempts > 0
                else 0,
            }
            for result in results
        ]

    def get_top_performing_assessments(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get assessments with highest average scores"""
        results = (
            self.db.query(
                Assessment.id,
                Assessment.title,
                Assessment.category,
                func.count(AssessmentAttempt.id).label("total_attempts"),
                func.avg(AssessmentAttempt.score).label("avg_score"),
            )
            .join(AssessmentAttempt, Assessment.id == AssessmentAttempt.assessment_id)
            .filter(AssessmentAttempt.status == "GRADED")
            .group_by(Assessment.id, Assessment.title, Assessment.category)
            .order_by(func.avg(AssessmentAttempt.score).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "assessment_id": str(result.id),
                "title": result.title,
                "category": result.category,
                "total_attempts": result.total_attempts,
                "average_score": round(float(result.avg_score), 2),
            }
            for result in results
        ]

    def get_difficult_assessments(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get assessments with lowest pass rates"""
        results = (
            self.db.query(
                Assessment.id,
                Assessment.title,
                Assessment.category,
                func.count(AssessmentAttempt.id).label("total_attempts"),
                func.avg(AssessmentAttempt.score).label("avg_score"),
                func.sum(case((AssessmentAttempt.passed.is_(True), 1), else_=0)).label(
                    "passed_count"
                ),
            )
            .join(AssessmentAttempt, Assessment.id == AssessmentAttempt.assessment_id)
            .filter(AssessmentAttempt.status == "GRADED")
            .group_by(Assessment.id, Assessment.title, Assessment.category)
            .having(func.count(AssessmentAttempt.id) >= 10)
            .order_by(
                (
                    func.sum(case((AssessmentAttempt.passed.is_(True), 1), else_=0))
                    / func.count(AssessmentAttempt.id)
                ).asc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "assessment_id": str(result.id),
                "title": result.title,
                "category": result.category,
                "total_attempts": result.total_attempts,
                "average_score": round(float(result.avg_score), 2),
                "pass_rate": round(
                    (result.passed_count / result.total_attempts * 100), 2
                ),
            }
            for result in results
        ]

    def get_question_difficulty_analysis(self) -> List[Dict[str, Any]]:
        """Analyze question difficulty based on success rates"""
        results = (
            self.db.query(
                Question.id,
                Question.question_text,
                Question.difficulty_level,
                Question.subject_id,
                func.count(Answer.id).label("total_answers"),
                func.sum(case((Answer.is_correct.is_(True), 1), else_=0)).label(
                    "correct_answers"
                ),
            )
            .outerjoin(Answer, Question.id == Answer.question_id)
            .group_by(
                Question.id,
                Question.question_text,
                Question.difficulty_level,
                Question.subject_id,
            )
            .having(func.count(Answer.id) >= 10)
            .all()
        )

        analyzed_questions = []
        for result in results:
            success_rate = (
                (result.correct_answers / result.total_answers * 100)
                if result.total_answers > 0
                else 0
            )

            accuracy = "accurate"
            if result.difficulty_level == "EASY" and success_rate < 60:
                accuracy = "harder_than_rated"
            elif result.difficulty_level == "HARD" and success_rate > 70:
                accuracy = "easier_than_rated"

            analyzed_questions.append(
                {
                    "question_id": str(result.id),
                    "question_preview": result.question_text[:100] + "..."
                    if len(result.question_text) > 100
                    else result.question_text,
                    "rated_difficulty": result.difficulty_level,
                    "total_answers": result.total_answers,
                    "success_rate": round(success_rate, 2),
                    "accuracy_assessment": accuracy,
                }
            )

        return analyzed_questions

    def get_most_missed_questions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get questions with lowest success rates"""
        results = (
            self.db.query(
                Question.id,
                Question.question_text,
                Question.difficulty_level,
                Subject.name.label("subject_name"),
                func.count(Answer.id).label("total_answers"),
                func.sum(case((Answer.is_correct.is_(True), 1), else_=0)).label(
                    "correct_answers"
                ),
            )
            .join(Subject, Question.subject_id == Subject.id)
            .outerjoin(Answer, Question.id == Answer.question_id)
            .group_by(
                Question.id,
                Question.question_text,
                Question.difficulty_level,
                Subject.name,
            )
            .having(func.count(Answer.id) >= 10)
            .order_by(
                (
                    func.sum(case((Answer.is_correct.is_(True), 1), else_=0))
                    / func.count(Answer.id)
                ).asc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "question_id": str(result.id),
                "question_preview": result.question_text[:100] + "...",
                "difficulty": result.difficulty_level,
                "subject": result.subject_name,
                "total_answers": result.total_answers,
                "success_rate": round(
                    (result.correct_answers / result.total_answers * 100), 2
                )
                if result.total_answers > 0
                else 0,
            }
            for result in results
        ]

    def get_institution_overview(self, institution_id: UUID) -> Dict[str, Any]:
        """Get analytics for a specific institution"""
        total_students = (
            self.db.query(func.count(Student.id))
            .filter(Student.institution_id == institution_id)
            .scalar()
            or 0
        )

        total_assessments = (
            self.db.query(func.count(Assessment.id))
            .filter(Assessment.institution_id == institution_id)
            .scalar()
            or 0
        )

        user_id = self._get_student_user_id(Student.id)
        total_attempts = (
            self.db.query(func.count(AssessmentAttempt.id))
            .join(Student, AssessmentAttempt.user_id == user_id)
            .filter(Student.institution_id == institution_id)
            .scalar()
            or 0
        )

        avg_score = (
            self.db.query(func.avg(AssessmentAttempt.score))
            .join(Student, AssessmentAttempt.user_id == user_id)
            .filter(
                and_(
                    Student.institution_id == institution_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .scalar()
            or 0
        )

        return {
            "total_students": total_students,
            "total_assessments": total_assessments,
            "total_attempts": total_attempts,
            "average_score": round(float(avg_score), 2),
        }

    def get_detailed_assessment_report(self, assessment_id: UUID) -> Dict[str, Any]:
        """Generate comprehensive report for a specific assessment"""
        assessment = (
            self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        )

        if not assessment:
            return None

        total_attempts = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(AssessmentAttempt.assessment_id == assessment_id)
            .scalar()
            or 0
        )

        completed = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(
                and_(
                    AssessmentAttempt.assessment_id == assessment_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .scalar()
            or 0
        )

        passed = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(
                and_(
                    AssessmentAttempt.assessment_id == assessment_id,
                    AssessmentAttempt.status == "GRADED",
                    AssessmentAttempt.passed.is_(True),
                )
            )
            .scalar()
            or 0
        )

        score_stats = (
            self.db.query(
                func.avg(AssessmentAttempt.score).label("avg"),
                func.min(AssessmentAttempt.score).label("min"),
                func.max(AssessmentAttempt.score).label("max"),
                func.stddev(AssessmentAttempt.score).label("stddev"),
            )
            .filter(
                and_(
                    AssessmentAttempt.assessment_id == assessment_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .first()
        )

        time_stats = (
            self.db.query(
                func.avg(AssessmentAttempt.time_spent_seconds).label("avg"),
                func.min(AssessmentAttempt.time_spent_seconds).label("min"),
                func.max(AssessmentAttempt.time_spent_seconds).label("max"),
            )
            .filter(
                and_(
                    AssessmentAttempt.assessment_id == assessment_id,
                    AssessmentAttempt.status == "GRADED",
                )
            )
            .first()
        )

        return {
            "assessment": {
                "id": str(assessment.id),
                "title": assessment.title,
                "category": assessment.category,
                "total_questions": assessment.total_questions,
                "total_points": assessment.total_points,
            },
            "attempts": {
                "total": total_attempts,
                "completed": completed,
                "passed": passed,
                "pass_rate": round((passed / completed * 100), 2)
                if completed > 0
                else 0,
            },
            "scores": {
                "average": round(float(score_stats.avg or 0), 2),
                "minimum": round(float(score_stats.min or 0), 2),
                "maximum": round(float(score_stats.max or 0), 2),
                "standard_deviation": round(float(score_stats.stddev or 0), 2),
            },
            "time": {
                "average_minutes": round(float(time_stats.avg or 0) / 60, 2),
                "minimum_minutes": round(float(time_stats.min or 0) / 60, 2),
                "maximum_minutes": round(float(time_stats.max or 0) / 60, 2),
            },
        }
