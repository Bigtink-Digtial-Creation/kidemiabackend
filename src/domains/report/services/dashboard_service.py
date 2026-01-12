from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from src.domains.auth.models.user import User
from src.domains.content.models.topic import Topic
from src.domains.content.models.question import Question
from src.domains.content.models.subject import Subject
from src.domains.assessment.models.assessment import Assessment
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.assessment.enums import AttemptStatus


class DashboardService:
    """Service for dashboard statistics and analytics"""

    @staticmethod
    def get_dashboard_stats(
        db: Session, category_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get dashboard statistics

        Args:
            db: Database session
            category_id: Optional category filter

        Returns:
            Dictionary with stats counts
        """
        # Base queries
        students_query = db.query(func.count(User.id)).filter(
            User.user_type == "student"
        )

        subjects_query = db.query(func.count(Subject.id))
        topics_query = db.query(func.count(Topic.id))
        questions_query = db.query(func.count(Question.id))

        # Apply category filter if provided
        if category_id:
            subjects_query = subjects_query.filter(Subject.category_id == category_id)

            # Get subject IDs for this category
            subject_ids = (
                db.query(Subject.id).filter(Subject.category_id == category_id).all()
            )
            subject_ids = [s[0] for s in subject_ids]

            if subject_ids:
                topics_query = topics_query.filter(Topic.subject_id.in_(subject_ids))

                # Get topic IDs
                topic_ids = (
                    db.query(Topic.id).filter(Topic.subject_id.in_(subject_ids)).all()
                )
                topic_ids = [t[0] for t in topic_ids]

                if topic_ids:
                    questions_query = questions_query.filter(
                        Question.topic_id.in_(topic_ids)
                    )

        return {
            "total_students": students_query.scalar() or 0,
            "total_subjects": subjects_query.scalar() or 0,
            "total_topics": topics_query.scalar() or 0,
            "total_questions": questions_query.scalar() or 0,
        }

    @staticmethod
    def get_dashboard_analytics(
        db: Session, category_id: Optional[str] = None, months: int = 6
    ) -> Dict[str, Any]:
        """
        Get dashboard analytics data for charts

        Args:
            db: Database session
            category_id: Optional category filter
            months: Number of months to include

        Returns:
            Dictionary with analytics data
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)

        # Get month names
        month_names = []
        current = start_date
        while current <= end_date:
            month_names.append(current.strftime("%b"))
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        # Get exams data
        exams_data = DashboardService._get_assessment_data(
            db, category_id, start_date, end_date, assessment_type="exam"
        )

        # Get tests data
        tests_data = DashboardService._get_assessment_data(
            db, category_id, start_date, end_date, assessment_type="test"
        )

        return {
            "exams_by_month": {"categories": month_names, "series": exams_data},
            "tests_by_month": {"categories": month_names, "series": tests_data},
        }

    @staticmethod
    def _get_assessment_data(
        db: Session,
        category_id: Optional[str],
        start_date: datetime,
        end_date: datetime,
        assessment_type: str,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(
                Subject.name.label("subject_name"),
                extract("year", AssessmentAttempt.graded_at).label("year"),
                extract("month", AssessmentAttempt.graded_at).label("month"),
                func.count(AssessmentAttempt.id).label("count"),
            )
            .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
            .join(Subject, Assessment.subject_id == Subject.id)
            .filter(
                AssessmentAttempt.graded_at.between(start_date, end_date),
                AssessmentAttempt.status == AttemptStatus.GRADED,
                Assessment.assessment_type == assessment_type,
            )
        )

        if category_id:
            query = query.filter(Subject.category_id == category_id)

        query = query.group_by(
            Subject.name,
            extract("year", AssessmentAttempt.graded_at),
            extract("month", AssessmentAttempt.graded_at),
        )

        results = query.all()

        if not results:
            return []

        subject_totals = {}
        for row in results:
            subject_totals[row.subject_name] = (
                subject_totals.get(row.subject_name, 0) + row.count
            )

        top_subject_names = [
            s[0]
            for s in sorted(subject_totals.items(), key=lambda x: x[1], reverse=True)[
                :4
            ]
        ]

        formatted_data = {}
        for row in results:
            series_name = (
                row.subject_name if row.subject_name in top_subject_names else "Others"
            )

            if series_name not in formatted_data:
                formatted_data[series_name] = {}

            month_key = f"{int(row.year)}-{int(row.month):02d}"
            formatted_data[series_name][month_key] = (
                formatted_data[series_name].get(month_key, 0) + row.count
            )

        series = []
        # Ensure "Others" appears last in the list if it exists
        sorted_series_names = [
            name for name in top_subject_names if name in formatted_data
        ]
        if "Others" in formatted_data:
            sorted_series_names.append("Others")

        for name in sorted_series_names:
            months_dict = formatted_data[name]
            data_points = []

            # Iterate through the actual date range to ensure 0s for missing months
            current = start_date
            while current <= end_date:
                m_key = f"{current.year}-{current.month:02d}"
                data_points.append(months_dict.get(m_key, 0))

                # Advance to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            series.append({"name": name, "data": data_points})

        return series

    @staticmethod
    def _get_assessment_data_old(
        db: Session,
        category_id: Optional[str],
        start_date: datetime,
        end_date: datetime,
        assessment_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Get assessment completion data grouped by subject/category

        Args:
            db: Database session
            category_id: Optional category filter
            start_date: Start date for data
            end_date: End date for data
            assessment_type: Type of assessment (exam or test)

        Returns:
            List of series data for chart
        """
        # Base query for user assessments
        query = (
            db.query(
                Subject.name.label("subject_name"),
                extract("year", AssessmentAttempt.graded_at).label("year"),
                extract("month", AssessmentAttempt.graded_at).label("month"),
                func.count(AssessmentAttempt.id).label("count"),
            )
            .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
            .join(Subject, Assessment.subject_id == Subject.id)
            .filter(
                AssessmentAttempt.graded_at.between(start_date, end_date),
                AssessmentAttempt.status == AttemptStatus.GRADED,
                Assessment.assessment_type == assessment_type,
            )
        )

        # Apply category filter
        if category_id:
            query = query.filter(Subject.category_id == category_id)

        # Group by subject and month
        query = query.group_by(
            Subject.name,
            extract("year", AssessmentAttempt.graded_at),
            extract("month", AssessmentAttempt.graded_at),
        )

        results = query.all()

        # Organize data by subject
        subjects_data = {}
        for row in results:
            subject_name = row.subject_name
            if subject_name not in subjects_data:
                subjects_data[subject_name] = {}

            # Create month key (YYYY-MM format)
            month_key = f"{int(row.year)}-{int(row.month):02d}"
            subjects_data[subject_name][month_key] = row.count

        # Convert to series format
        series = []
        for subject_name, months_data in subjects_data.items():
            # Create data array for all months
            data = []
            current = start_date
            while current <= end_date:
                month_key = f"{current.year}-{current.month:02d}"
                data.append(months_data.get(month_key, 0))

                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            series.append({"name": subject_name, "data": data})

        return series

    @staticmethod
    def get_recent_activities(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent platform activities

        Args:
            db: Database session
            limit: Number of activities to return

        Returns:
            List of recent activities
        """
        # Get recent assessments completed
        recent_completions = (
            db.query(
                AssessmentAttempt.graded_at,
                func.concat(User.first_name, " ", User.last_name).label("user_name"),
                Assessment.title.label("assessment_title"),
                AssessmentAttempt.score,
            )
            .join(User, AssessmentAttempt.user_id == User.id)
            .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
            .filter(
                AssessmentAttempt.status == AttemptStatus.GRADED,
                AssessmentAttempt.graded_at.isnot(None),
            )
            .order_by(AssessmentAttempt.graded_at.desc())
            .limit(limit)
            .all()
        )

        activities = []
        for completion in recent_completions:
            activities.append(
                {
                    "type": "assessment_completed",
                    "timestamp": completion.graded_at,
                    "user_name": completion.user_name,
                    "description": f"Completed '{completion.assessment_title}'",
                    "score": completion.score,
                }
            )

        return activities

    @staticmethod
    def get_performance_overview(
        db: Session, category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get overall performance metrics

        Args:
            db: Database session
            category_id: Optional category filter

        Returns:
            Performance overview data
        """
        # Base query
        query = db.query(
            func.avg(AssessmentAttempt.score).label("avg_score"),
            func.count(AssessmentAttempt.id).label("total_attempts"),
            func.count(func.distinct(AssessmentAttempt.user_id)).label(
                "unique_students"
            ),
        ).filter(AssessmentAttempt.status == AttemptStatus.GRADED)

        # Apply category filter
        if category_id:
            query = (
                query.join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
                .join(Subject, Assessment.subject_id == Subject.id)
                .filter(Subject.category_id == category_id)
            )

        result = query.first()

        return {
            "average_score": round(result.avg_score or 0, 2),
            "total_attempts": result.total_attempts or 0,
            "active_students": result.unique_students or 0,
            "completion_rate": DashboardService._calculate_completion_rate(
                db, category_id
            ),
        }

    @staticmethod
    def _calculate_completion_rate(
        db: Session, category_id: Optional[str] = None
    ) -> float:
        """Calculate assessment completion rate"""
        # Total started
        started_query = db.query(func.count(AssessmentAttempt.id)).filter(
            AssessmentAttempt.status.in_(
                [AttemptStatus.IN_PROGRESS, AttemptStatus.GRADED]
            )
        )

        # Total completed
        completed_query = db.query(func.count(AssessmentAttempt.id)).filter(
            AssessmentAttempt.status == AttemptStatus.GRADED
        )

        # Apply category filter
        if category_id:
            started_query = (
                started_query.join(
                    Assessment, AssessmentAttempt.assessment_id == Assessment.id
                )
                .join(Subject, Assessment.subject_id == Subject.id)
                .filter(Subject.category_id == category_id)
            )

            completed_query = (
                completed_query.join(
                    Assessment, AssessmentAttempt.assessment_id == Assessment.id
                )
                .join(Subject, Assessment.subject_id == Subject.id)
                .filter(Subject.category_id == category_id)
            )

        total_started = started_query.scalar() or 0
        total_completed = completed_query.scalar() or 0

        if total_started == 0:
            return 0.0

        return round((total_completed / total_started) * 100, 2)
