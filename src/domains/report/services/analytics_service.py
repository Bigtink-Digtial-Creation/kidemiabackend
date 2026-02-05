"""
Enhanced Analytics Service - With Topic Analytics and Study Plans
Developed By Samuel Kufre Willie - 31 January 2026
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
import traceback

from src.domains.report.repositories.analytics_repository import (
    AnalyticsRepository,
)


class AnalyticsService:
    """Enhanced service layer with topic analytics and personalized study plans"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository(db)

    async def get_student_dashboard_data(self, student_id: UUID) -> Dict[str, Any]:
        """Get enhanced student-specific dashboard analytics with topic-level data"""

        performance = self.repo.get_student_performance_summary(student_id)
        subject_breakdown = self.repo.get_student_subject_performance(student_id)
        progress = self.repo.get_student_progress_over_time(student_id, days=30)

        # NEW: Add topic-level performance
        topic_performance = self.repo.get_student_topic_performance(student_id)

        # NEW: Add personalized recommendations
        recommendations = self._generate_enhanced_recommendations(
            student_id, performance, topic_performance
        )

        # NEW: Add study plan
        study_plan = self.repo.generate_personalized_study_plan(
            student_id, duration_days=14
        )

        return {
            "performance_summary": performance,
            "subject_breakdown": subject_breakdown,
            "topic_breakdown": topic_performance,  # NEW
            "progress_over_time": progress,
            "personalized_recommendations": recommendations,  # ENHANCED
            "study_plan": study_plan,  # NEW
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_topic_analytics(
        self, student_id: UUID, topic_id: UUID = None
    ) -> Dict[str, Any]:
        """Get detailed topic-level analytics
        I used this service for report generator in pdf_service.py.
        Change with care
        """

        if topic_id:
            # Get specific topic trend
            trend = self.repo.get_topic_trend_analysis(student_id, topic_id, days=30)
            return {
                "topic_id": str(topic_id),
                "trend_analysis": trend,
                "generated_at": datetime.utcnow().isoformat(),
            }
        else:
            # Get all topics
            all_topics = self.repo.get_student_topic_performance(student_id)
            weak_topics = self.repo.get_weak_topics_for_student(student_id)
            recommended_topics = self.repo.get_recommended_topics_for_practice(
                student_id
            )

            return {
                "all_topics": all_topics,
                "weak_topics": weak_topics,
                "recommended_for_practice": recommended_topics,
                "generated_at": datetime.utcnow().isoformat(),
            }

    def _generate_enhanced_recommendations(
        self,
        student_id: UUID,
        performance: Dict[str, Any],
        topic_performance: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate enhanced recommendations with topic-specific advice"""

        recommendations = []

        # Topic-based recommendations
        weak_topics = [t for t in topic_performance if t["success_rate"] < 60]
        if weak_topics:
            # Sort by success rate to prioritize worst topics
            weak_topics.sort(key=lambda x: x["success_rate"])

            for topic in weak_topics[:3]:  # Top 3 weak topics
                recommendations.append(
                    {
                        "type": "topic_focus",
                        "icon": "📚",
                        "title": f"Master {topic['topic_name']}",
                        "description": f"You're at {topic['success_rate']}% mastery. Focus on {topic['topic_name']} in {topic['subject_name']}.",
                        "action": {
                            "type": "practice_topic",
                            "topic_id": topic["topic_id"],
                            "subject_id": topic["subject_id"],
                        },
                        "priority": "high" if topic["success_rate"] < 40 else "medium",
                    }
                )

        # Streak-based recommendations
        if performance.get("gamification"):
            streak = performance["gamification"].get("current_streak", 0)
            if streak >= 7:
                recommendations.append(
                    {
                        "type": "streak_motivation",
                        "icon": "🔥",
                        "title": "Amazing Streak!",
                        "description": f"You're on a {streak}-day streak! Keep it going for bonus XP.",
                        "action": {"type": "continue_streak"},
                        "priority": "low",
                    }
                )
            elif streak == 0:
                recommendations.append(
                    {
                        "type": "streak_start",
                        "icon": "⚡",
                        "title": "Start Your Streak",
                        "description": "Complete an assessment today to start building your study streak!",
                        "action": {"type": "start_assessment"},
                        "priority": "medium",
                    }
                )

        # Performance-based recommendations
        avg_score = performance.get("average_score", 0)
        if avg_score >= 80:
            recommendations.append(
                {
                    "type": "level_up",
                    "icon": "🎯",
                    "title": "Try Harder Challenges",
                    "description": f"You're scoring {avg_score}% on average. Time to level up!",
                    "action": {"type": "advanced_assessments"},
                    "priority": "medium",
                }
            )
        elif avg_score < 50:
            recommendations.append(
                {
                    "type": "foundation",
                    "icon": "💪",
                    "title": "Build Strong Foundation",
                    "description": "Focus on fundamental concepts. Take easier assessments to build confidence.",
                    "action": {"type": "foundational_practice"},
                    "priority": "high",
                }
            )

        # Study plan recommendation
        recommendations.append(
            {
                "type": "study_plan",
                "icon": "📅",
                "title": "Follow Your Personalized Plan",
                "description": "We've created a 2-week study plan tailored to your weak areas.",
                "action": {"type": "view_study_plan"},
                "priority": "high",
            }
        )

        # Topic recommendations for practice
        recommended = self.repo.get_recommended_topics_for_practice(student_id, limit=2)
        for rec in recommended:
            recommendations.append(
                {
                    "type": "topic_practice",
                    "icon": "✍️",
                    "title": f"Practice {rec['topic_name']}",
                    "description": rec["reason"],
                    "action": {
                        "type": "practice_recommended_topic",
                        "topic_id": rec["topic_id"],
                        "assessments": rec["suggested_assessments"],
                    },
                    "priority": "high" if rec["current_mastery"] < 40 else "medium",
                }
            )

        # Sort by priority (high, medium, low)
        priority_order = {"high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))

        return recommendations

    # ==================== EXISTING METHODS (from your working code) ====================

    async def get_admin_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive admin dashboard analytics"""

        overview = self.repo.get_platform_overview()
        assessment_perf = self.repo.get_assessment_performance_overview()
        revenue = self.repo.get_revenue_overview()
        engagement = self.repo.get_engagement_metrics()

        user_growth = self.repo.get_user_growth_data(days=30)
        revenue_trend = self.repo.get_revenue_by_period(days=30)
        top_assessments = self.repo.get_top_performing_assessments(limit=5)
        difficult_assessments = self.repo.get_difficult_assessments(limit=5)

        return {
            "overview": overview,
            "assessment_performance": assessment_perf,
            "revenue": revenue,
            "engagement": engagement,
            "trends": {"user_growth": user_growth, "revenue": revenue_trend},
            "assessments": {
                "top_performing": top_assessments,
                "most_difficult": difficult_assessments,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_guardian_dashboard_data(self, guardian_id: UUID) -> Dict[str, Any]:
        """Get guardian dashboard showing all wards' performance"""
        return {
            "wards": [],
            "overall_performance": {},
            "recent_activities": [],
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_institution_dashboard_data(
        self, institution_id: UUID
    ) -> Dict[str, Any]:
        """Get institution-specific analytics"""
        overview = self.repo.get_institution_overview(institution_id)
        return {
            "overview": overview,
            "student_performance": {},
            "assessment_usage": {},
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_assessment_analytics(self, assessment_id: UUID) -> Dict[str, Any]:
        """Get detailed analytics for a specific assessment"""
        report = self.repo.get_detailed_assessment_report(assessment_id)
        if not report:
            return {"error": "Assessment not found"}
        return {"report": report, "generated_at": datetime.utcnow().isoformat()}

    async def get_assessment_category_comparison(self) -> Dict[str, Any]:
        """Compare performance across assessment categories"""
        category_data = self.repo.get_assessment_by_category()
        return {
            "categories": category_data,
            "insights": self._generate_category_insights(category_data),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_question_quality_report(self) -> Dict[str, Any]:
        """Analyze question quality and difficulty accuracy"""
        difficulty_analysis = self.repo.get_question_difficulty_analysis()
        most_missed = self.repo.get_most_missed_questions(limit=20)
        needs_review = [
            q for q in difficulty_analysis if q["accuracy_assessment"] != "accurate"
        ]

        return {
            "total_analyzed": len(difficulty_analysis),
            "needs_difficulty_adjustment": len(needs_review),
            "questions_needing_review": needs_review[:10],
            "most_missed_questions": most_missed,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_financial_overview(self, period: str = "monthly") -> Dict[str, Any]:
        """Get comprehensive financial analytics"""
        revenue_overview = self.repo.get_revenue_overview()
        subscription_analytics = self.repo.get_subscription_analytics()

        days = 30 if period == "monthly" else 90 if period == "quarterly" else 365
        revenue_trend = self.repo.get_revenue_by_period(days=days)

        return {
            "overview": revenue_overview,
            "subscriptions": subscription_analytics,
            "trend": revenue_trend,
            "insights": self._generate_financial_insights(
                revenue_overview, subscription_analytics
            ),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_platform_engagement_report(self) -> Dict[str, Any]:
        """Get platform-wide engagement metrics"""
        engagement = self.repo.get_engagement_metrics()
        return {
            "metrics": engagement,
            "insights": self._generate_engagement_insights(engagement),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def generate_comprehensive_report(
        self,
        report_type: str,
        entity_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive report for export"""

        print(report_type == "student_performance")
        try:
            if report_type == "platform_overview":
                return self.get_admin_dashboard_data()
            elif report_type == "student_performance" and entity_id:
                return self.get_student_dashboard_data(entity_id)
            elif report_type == "assessment_analysis" and entity_id:
                return self.get_assessment_analytics(entity_id)
            elif report_type == "financial":
                return self.get_financial_overview()
            elif report_type == "question_quality":
                return self.get_question_quality_report()
            else:
                return {"error": "Invalid report type or missing parameters"}
        except Exception as e:
            traceback.print_exc()
            return {
                "error": "report_generation_failed",
                "message": str(e),
                "report_type": report_type,
            }

    def _generate_category_insights(
        self, category_data: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate insights from category comparison"""
        insights = []
        if not category_data:
            return insights

        sorted_by_score = sorted(
            category_data, key=lambda x: x["average_score"], reverse=True
        )
        sorted_by_pass_rate = sorted(
            category_data, key=lambda x: x["pass_rate"], reverse=True
        )

        if sorted_by_score:
            insights.append(
                f"{sorted_by_score[0]['category']} has the highest average score ({sorted_by_score[0]['average_score']}%)"
            )
            insights.append(
                f"{sorted_by_score[-1]['category']} has the lowest average score ({sorted_by_score[-1]['average_score']}%)"
            )

        if sorted_by_pass_rate:
            insights.append(
                f"{sorted_by_pass_rate[0]['category']} has the best pass rate ({sorted_by_pass_rate[0]['pass_rate']}%)"
            )

        return insights

    def _generate_financial_insights(
        self, revenue_data: Dict[str, Any], subscription_data: Dict[str, Any]
    ) -> List[str]:
        """Generate financial insights"""
        insights = []

        if revenue_data.get("total_revenue", 0) > 0:
            subscription_pct = (
                revenue_data.get("subscription_revenue", 0)
                / revenue_data["total_revenue"]
                * 100
            )
            insights.append(
                f"Subscriptions account for {subscription_pct:.1f}% of total revenue"
            )

        churn_rate = subscription_data.get("churn_rate", 0)
        if churn_rate > 5:
            insights.append(
                f"Churn rate is {churn_rate:.1f}% - consider retention strategies"
            )
        elif churn_rate < 2:
            insights.append(f"Excellent churn rate of {churn_rate:.1f}%")

        return insights

    def _generate_engagement_insights(
        self, engagement_data: Dict[str, Any]
    ) -> List[str]:
        """Generate engagement insights"""
        insights = []

        dau = engagement_data.get("daily_active_users", 0)
        mau = engagement_data.get("monthly_active_users", 0)

        if mau > 0:
            stickiness = (dau / mau) * 100
            insights.append(f"Platform stickiness (DAU/MAU): {stickiness:.1f}%")

            if stickiness > 20:
                insights.append("Excellent user retention and engagement")
            elif stickiness < 10:
                insights.append("Consider strategies to improve daily engagement")

        forum_posts = engagement_data.get("forum_posts_this_week", 0)
        if forum_posts > 100:
            insights.append("Strong community engagement in forums")

        return insights

    async def predict_student_performance(self, student_id: UUID) -> Dict[str, Any]:
        """Predict student's future performance based on trends"""
        progress = self.repo.get_student_progress_over_time(student_id, days=60)

        if len(progress) < 5:
            return {
                "prediction": "insufficient_data",
                "message": "Need more assessment attempts for accurate prediction",
            }

        recent_scores = [p["average_score"] for p in progress[-10:]]
        trend = "improving" if recent_scores[-1] > recent_scores[0] else "declining"
        avg_recent = sum(recent_scores) / len(recent_scores)

        return {
            "prediction": trend,
            "current_average": round(avg_recent, 2),
            "trend_confidence": "moderate",
            "recommendation": self._get_performance_recommendation(trend, avg_recent),
        }

    def _get_performance_recommendation(self, trend: str, avg_score: float) -> str:
        """Get recommendation based on performance trend"""
        if trend == "improving" and avg_score > 70:
            return "Excellent progress! Consider taking more challenging assessments."
        elif trend == "improving" and avg_score < 60:
            return "Good improvement trend. Continue with current study pace."
        elif trend == "declining" and avg_score < 50:
            return "Performance declining. Consider reviewing fundamental concepts and seeking help."
        elif trend == "declining":
            return "Slight decline noticed. Review recent topics and maintain regular practice."
        else:
            return "Maintain current study habits and track progress regularly."

    async def get_student_peer_comparison(self, student_id: UUID) -> Dict[str, Any]:
        """Compare student performance with peers"""
        student_perf = self.repo.get_student_performance_summary(student_id)
        return {
            "student_performance": student_perf,
            "peer_average": {},
            "percentile": 0,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_realtime_activity_feed(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent platform activities for real-time monitoring"""
        return []
