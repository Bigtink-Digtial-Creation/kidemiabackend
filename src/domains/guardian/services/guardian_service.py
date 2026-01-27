from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from src.domains.auth.models.student import Student

from src.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
    AuthorizationException,
)
from src.domains.assessment.models.assessment import Assessment
from src.domains.assessment.models.category import AssessmentCategoryConfig
from src.domains.assessment.models.attempt import AssessmentAttempt
from src.domains.guardian.repositories.guardian_repository import GuardianRepository
from src.domains.auth.repositories.user_repository import UserRepository
from src.domains.guardian.schemas.guardian import (
    GuardianUpdate,
    GuardianResponse,
    GuardianDetailResponse,
    AddWardRequest,
    WardResponse,
    RemoveWardRequest,
    CategoryChangeRequest as CategoryChangeRequestSchema,
    CategoryChangeResponse,
    WardPerformanceReport,
    ComprehensiveGuardianReport,
    AssessmentAssignmentResponse,
    AssignmentResponse,
    CreateAssessmentForWardsRequest,
)
from src.domains.guardian.models.guardian import (
    CategoryChangeRequest,
    CategoryChangeStatus,
    AssessmentAssignment,
)
from src.domains.payment.services.subscription_service import SubscriptionService
from src.domains.assessment.enums import AssessmentType, AttemptStatus
from src.domains.auth.repositories.student_repositoty import StudentRepository
from src.domains.assessment.services.practice_test_service import AutoAssessmentService
from src.domains.guardian.enums import AssignmentStatus


class GuardianService:
    """Service for guardian operations"""

    def __init__(self, db: Session):
        self.db = db
        self.guardian_repo = GuardianRepository(db)
        self.user_repo = UserRepository(db)
        self.student_repo = StudentRepository(db)

    async def get_guardian_by_user_id(
        self, user_id: UUID
    ) -> Optional[GuardianResponse]:
        """Get guardian profile by user ID"""
        guardian = self.guardian_repo.get_by_user_id(user_id)
        if not guardian:
            return None

        return await self._build_guardian_response(guardian)

    async def get_guardian_detail(
        self, guardian_id: UUID, user_id: UUID
    ) -> GuardianDetailResponse:
        """Get guardian with wards"""
        guardian = self.guardian_repo.get_with_wards(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        # Verify access
        if guardian.user_id != user_id:
            raise AuthorizationException(
                "You don't have access to this guardian profile"
            )

        response = await self._build_guardian_response(guardian)

        # Build ward responses
        wards = []
        for student in guardian.students:
            if not student.is_deleted:
                ward_response = await self._build_ward_response(student)
                wards.append(ward_response)

        return GuardianDetailResponse(**response.model_dump(), wards=wards)

    async def update_guardian(
        self, guardian_id: UUID, user_id: UUID, update_data: GuardianUpdate
    ) -> GuardianResponse:
        """Update guardian profile"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException(
                "You don't have access to update this guardian"
            )

        update_dict = update_data.model_dump(exclude_unset=True)
        self.guardian_repo.update(guardian_id, update_dict)

        updated_guardian = self.guardian_repo.get_by_id(guardian_id)
        return await self._build_guardian_response(updated_guardian)

    async def add_ward(
        self, guardian_id: UUID, user_id: UUID, ward_data: AddWardRequest
    ) -> WardResponse:
        """Add a ward to guardian"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to add wards")

        # Check subscription limits
        subscription_service = SubscriptionService(self.db)
        can_add, message = await subscription_service.check_usage_limit(
            user_id, "wards"
        )
        if not can_add:
            raise BusinessLogicException(message)

        # Find student by email
        student_user = self.user_repo.get_by_email(ward_data.ward_email)
        if not student_user:
            raise ResourceNotFoundException(
                "Student", f"with email {ward_data.ward_email}"
            )

        # Get student profile
        student = self.student_repo.get_by_user_id(student_user.id)
        if not student:
            raise ValidationException("This user is not registered as a student")

        # Check if already has a guardian
        if student.guardian_id and student.guardian_id != guardian_id:
            raise BusinessLogicException("This student already has a guardian assigned")

        # Add ward
        self.student_repo.update(
            student.id,
            {
                "guardian_id": guardian_id,
                "guardian_email": guardian.user.email if guardian.user else None,
            },
        )

        updated_student = self.student_repo.get_by_id(student.id)
        return await self._build_ward_response(updated_student)

    async def remove_ward(
        self, guardian_id: UUID, user_id: UUID, remove_data: RemoveWardRequest
    ) -> bool:
        """Remove a ward from guardian"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to remove wards")

        # Verify ward belongs to guardian
        student = self.student_repo.get_by_id(remove_data.ward_id)
        if not student or student.guardian_id != guardian_id:
            raise ValidationException("This ward does not belong to you")

        # Remove guardian association
        self.student_repo.update(
            remove_data.ward_id, {"guardian_id": None, "guardian_email": None}
        )

        return True

    async def get_my_wards(
        self, guardian_id: UUID, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[WardResponse]:
        """Get all wards for a guardian"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to view these wards")

        students = (
            self.db.query(Student)
            .filter(Student.guardian_id == guardian_id, Student.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
            .all()
        )

        wards = []
        for student in students:
            ward_response = await self._build_ward_response(student)
            wards.append(ward_response)

        return wards

    async def request_category_change(
        self,
        guardian_id: UUID,
        user_id: UUID,
        request_data: CategoryChangeRequestSchema,
    ) -> CategoryChangeResponse:
        """Request category change for a ward"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to request changes")

        # Verify ward belongs to guardian
        student = self.student_repo.get_by_id(request_data.ward_id)
        if not student or student.guardian_id != guardian_id:
            raise ValidationException("This ward does not belong to you")

        # Verify new category exists
        new_category = (
            self.db.query(AssessmentCategoryConfig)
            .filter(AssessmentCategoryConfig.id == request_data.new_category_id)
            .first()
        )

        if not new_category:
            raise ResourceNotFoundException("Category", request_data.new_category_id)

        # Check for pending requests
        existing_request = (
            self.db.query(CategoryChangeRequest)
            .filter(
                and_(
                    CategoryChangeRequest.ward_id == request_data.ward_id,
                    CategoryChangeRequest.status == CategoryChangeStatus.PENDING,
                    CategoryChangeRequest.is_deleted.is_(False),
                )
            )
            .first()
        )

        if existing_request:
            raise BusinessLogicException(
                "There is already a pending category change request for this ward"
            )

        # Create request
        change_request = CategoryChangeRequest(
            ward_id=request_data.ward_id,
            guardian_id=guardian_id,
            old_category_id=student.category_id,
            new_category_id=request_data.new_category_id,
            reason=request_data.reason,
            status=CategoryChangeStatus.PENDING,
        )

        self.db.add(change_request)
        self.db.commit()
        self.db.refresh(change_request)

        return CategoryChangeResponse.model_validate(change_request)

    async def approve_category_change(
        self,
        guardian_id: UUID,
        user_id: UUID,
        request_id: UUID,
        approve: bool,
        admin_notes: Optional[str] = None,
    ) -> CategoryChangeResponse:
        """Approve or reject category change request"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to approve changes")

        change_request = (
            self.db.query(CategoryChangeRequest)
            .filter(
                CategoryChangeRequest.id == request_id,
                CategoryChangeRequest.is_deleted.is_(False),
            )
            .first()
        )

        if not change_request:
            raise ResourceNotFoundException("CategoryChangeRequest", request_id)

        if change_request.guardian_id != guardian_id:
            raise AuthorizationException("This request does not belong to you")

        if change_request.status != CategoryChangeStatus.PENDING:
            raise BusinessLogicException(
                f"Cannot modify request with status: {change_request.status}"
            )

        # Update request
        change_request.status = (
            CategoryChangeStatus.APPROVED if approve else CategoryChangeStatus.REJECTED
        )
        change_request.resolved_at = datetime.utcnow()
        change_request.resolved_by = user_id
        change_request.admin_notes = admin_notes

        # If approved, update student category
        if approve:
            self.student_repo.update(
                change_request.ward_id, {"category_id": change_request.new_category_id}
            )

        self.db.commit()
        self.db.refresh(change_request)

        return CategoryChangeResponse.model_validate(change_request)

    async def get_category_change_requests(
        self,
        guardian_id: UUID,
        user_id: UUID,
        status: Optional[CategoryChangeStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CategoryChangeResponse]:
        """Get category change requests for guardian"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to view these requests")

        query = self.db.query(CategoryChangeRequest).filter(
            CategoryChangeRequest.guardian_id == guardian_id,
            CategoryChangeRequest.is_deleted.is_(False),
        )

        if status:
            query = query.filter(CategoryChangeRequest.status == status)

        requests = (
            query.order_by(CategoryChangeRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Collect all IDs for batch queries
        ward_ids = [req.ward_id for req in requests]
        category_ids = set()
        for req in requests:
            if req.old_category_id:
                category_ids.add(req.old_category_id)
            category_ids.add(req.new_category_id)

        # Batch fetch wards
        wards_map = {}
        if ward_ids:
            wards = self.db.query(Student).filter(Student.id.in_(ward_ids)).all()
            for ward in wards:
                if ward.user:
                    wards_map[ward.id] = ward.user.full_name

        # Batch fetch categories
        categories_map = {}
        if category_ids:
            categories = (
                self.db.query(AssessmentCategoryConfig)
                .filter(AssessmentCategoryConfig.id.in_(category_ids))
                .all()
            )
            for cat in categories:
                categories_map[cat.id] = cat.display_name

        # Build enriched responses
        enriched_responses = []
        for req in requests:
            response = CategoryChangeResponse.model_validate(req)
            response.ward_name = wards_map.get(req.ward_id)
            response.old_category_name = (
                categories_map.get(req.old_category_id) if req.old_category_id else None
            )
            response.new_category_name = categories_map.get(req.new_category_id)

            enriched_responses.append(response)

        return enriched_responses

    async def request_category_change_student(
        self,
        student_id: UUID,
        request_data: CategoryChangeRequest,
    ) -> dict:
        """Handle category change: Auto-update if no guardian, else create request"""

        student = self.student_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundException("Student")

        new_category = (
            self.db.query(AssessmentCategoryConfig)
            .filter(AssessmentCategoryConfig.id == request_data.new_category_id)
            .first()
        )
        if not new_category:
            raise ResourceNotFoundException("Category", request_data.new_category_id)

        has_guardian = student.guardian_id is not None and (
            student.guardian_email and student.guardian_email.strip() != ""
        )

        if not has_guardian:
            student.category_id = request_data.new_category_id
            self.db.commit()
            return {
                "status": "approved",
                "auto_updated": True,
                "message": "Category updated successfully (No guardian linked).",
            }

        existing_pending = (
            self.db.query(CategoryChangeRequest)
            .filter(
                CategoryChangeRequest.ward_id == student_id,
                CategoryChangeRequest.status == CategoryChangeStatus.PENDING,
                CategoryChangeRequest.is_deleted.is_(False),
            )
            .first()
        )
        if existing_pending:
            raise BusinessLogicException(
                "You already have a pending category change request"
            )

        change_request = CategoryChangeRequest(
            ward_id=student_id,
            guardian_id=student.guardian_id,
            old_category_id=student.category_id,
            new_category_id=request_data.new_category_id,
            reason=request_data.reason,
            status=CategoryChangeStatus.PENDING,
        )

        self.db.add(change_request)
        self.db.commit()
        self.db.refresh(change_request)

        return {
            "status": "pending",
            "auto_updated": False,
            "request_id": change_request.id,
            "message": "Request sent to your guardian for approval.",
        }

    async def get_latest_ward_category_request(
        self, ward_id: UUID
    ) -> Optional[CategoryChangeResponse]:
        """Fetch only the latest request for a student to track its current status"""

        # 1. Get the latest request for this ward (Student ID)
        request = (
            self.db.query(CategoryChangeRequest)
            .filter(
                CategoryChangeRequest.ward_id == ward_id,
                CategoryChangeRequest.is_deleted.is_(False),
            )
            .order_by(CategoryChangeRequest.created_at.desc())
            .first()  # We only want the newest one
        )

        if not request:
            return None

        # 2. Simple Enrichment (Single fetch is faster than batch logic for 1 item)
        response = CategoryChangeResponse.model_validate(request)

        # Fetch Category names for display
        new_cat = (
            self.db.query(AssessmentCategoryConfig)
            .filter_by(id=request.new_category_id)
            .first()
        )
        if new_cat:
            response.new_category_name = new_cat.display_name

        return response

    async def get_ward_performance_report(
        self, guardian_id: UUID, user_id: UUID, ward_id: UUID
    ) -> WardPerformanceReport:
        """Get performance report for a specific ward"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to view reports")

        student = self.student_repo.get_by_id(ward_id)
        if not student or student.guardian_id != guardian_id:
            raise ValidationException("This ward does not belong to you")

        # Get assessment statistics
        # This would query assessment attempts, results, etc.
        # For now, returning mock structure

        from src.domains.assessment.repositories.attempt_repository import (
            AssessmentAttemptRepository,
        )

        attempt_repo = AssessmentAttemptRepository(self.db)

        attempts = attempt_repo.get_user_attempts(student.user_id)

        total_assessments = len(attempts)
        completed = len([a for a in attempts if a.status == AttemptStatus.GRADED])
        pending = total_assessments - completed

        avg_score = 0.0
        if completed > 0:
            scores = [
                a.score
                for a in attempts
                if a.status == AttemptStatus.GRADED and a.score
            ]
            avg_score = sum(scores) / len(scores) if scores else 0.0

        # Build subject performance
        subject_performance = []  # TODO: Implement subject breakdown

        return WardPerformanceReport(
            ward_id=ward_id,
            ward_name=student.user.full_name if student.user else "Unknown",
            category_name=student.category.display_name if student.category else None,
            total_assessments=total_assessments,
            completed_assessments=completed,
            pending_assessments=pending,
            avg_overall_score=avg_score,
            subject_performance=subject_performance,
            performance_trend="stable",
            strengths=[],
            weaknesses=[],
            last_assessment_date=attempts[0].created_at if attempts else None,
            generated_at=datetime.utcnow(),
        )

    async def get_comprehensive_report(
        self, guardian_id: UUID, user_id: UUID
    ) -> ComprehensiveGuardianReport:
        """Get comprehensive report for all wards"""
        guardian = self.guardian_repo.get_with_wards(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to view reports")

        ward_summaries = []
        total_score_sum = 0.0
        total_assessments = 0
        total_completed = 0
        wards_with_scores = 0

        for student in guardian.students:
            if not student.is_deleted:
                report = await self.get_ward_performance_report(
                    guardian_id, user_id, student.id
                )
                ward_summaries.append(report)

                if report.completed_assessments > 0:
                    total_score_sum += report.avg_overall_score
                    wards_with_scores += 1

                total_assessments += report.total_assessments
                total_completed += report.completed_assessments

        overall_avg = (
            total_score_sum / wards_with_scores if wards_with_scores > 0 else 0.0
        )

        # Find top performer
        top_ward = None
        if ward_summaries:
            top_report = max(
                ward_summaries, key=lambda x: x.avg_overall_score, default=None
            )
            if top_report:
                top_ward = top_report.ward_name

        return ComprehensiveGuardianReport(
            guardian_id=guardian_id,
            total_wards=len(guardian.students),
            active_wards=len([s for s in guardian.students if s.is_active]),
            overall_avg_score=overall_avg,
            total_assessments_assigned=total_assessments,
            total_assessments_completed=total_completed,
            ward_summaries=ward_summaries,
            top_performing_ward=top_ward,
            needs_attention=[],
            generated_at=datetime.utcnow(),
        )

    async def get_ward_detailed_stats(
        self, guardian_id: UUID, user_id: UUID, ward_id: UUID
    ) -> Dict[str, Any]:
        """Get detailed statistics for a ward (similar to dashboard stats but for guardian view)"""
        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to view reports")

        student = self.student_repo.get_by_id(ward_id)
        if not student or student.guardian_id != guardian_id:
            raise ValidationException("This ward does not belong to you")

        ward_user_id = student.user_id

        # Tests stats
        test_attempts_count = (
            self.db.query(func.count(AssessmentAttempt.id))
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .filter(
                and_(
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == AssessmentType.TEST,
                )
            )
            .scalar()
            or 0
        )

        # Exams stats
        exam_attempts_count = (
            self.db.query(func.count(AssessmentAttempt.id))
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .filter(
                and_(
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == AssessmentType.EXAM,
                )
            )
            .scalar()
            or 0
        )

        # Count correct answers for tests
        test_correct_answers = (
            self.db.query(func.sum(AssessmentAttempt.correct_answers))
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .filter(
                and_(
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == AssessmentType.TEST,
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
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == AssessmentType.EXAM,
                )
            )
            .scalar()
            or 0
        )

        # Recent test performance for chart (last 6 tests) with subject info
        from src.domains.content.models.subject import Subject

        recent_tests = (
            self.db.query(AssessmentAttempt, Assessment, Subject)
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .outerjoin(Subject, Assessment.subject_id == Subject.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == AssessmentType.TEST,
                )
            )
            .order_by(AssessmentAttempt.submitted_at.desc())
            .limit(6)
            .all()
        )

        # Recent exam performance for chart (last 6 exams) with subject info
        recent_exams = (
            self.db.query(AssessmentAttempt, Assessment, Subject)
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .outerjoin(Subject, Assessment.subject_id == Subject.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.status == AttemptStatus.GRADED,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == AssessmentType.EXAM,
                )
            )
            .order_by(AssessmentAttempt.submitted_at.desc())
            .limit(6)
            .all()
        )

        # Assessment history by subject (last 20)
        subject_history = (
            self.db.query(AssessmentAttempt, Assessment, Subject)
            .select_from(AssessmentAttempt)
            .join(Assessment)
            .outerjoin(Subject, Assessment.subject_id == Subject.id)
            .filter(
                and_(
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.subject_id.isnot(None),
                )
            )
            .order_by(AssessmentAttempt.created_at.desc())
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
                    AssessmentAttempt.user_id == ward_user_id,
                    AssessmentAttempt.is_deleted.is_(False),
                    Assessment.assessment_type == AssessmentType.EXAM,
                )
            )
            .order_by(AssessmentAttempt.created_at.desc())
            .limit(20)
            .all()
        )

        return {
            "ward_id": str(ward_id),
            "ward_name": student.user.full_name if student.user else "Unknown",
            "stats": {
                "tests_attempted": test_attempts_count,
                "test_correct_answers": int(test_correct_answers),
                "exams_attempted": exam_attempts_count,
                "exam_correct_answers": int(exam_correct_answers),
            },
            "test_performance_chart": {
                "categories": [
                    subject.name if subject else f"Test {i + 1}"
                    for i, (_, _, subject) in enumerate(recent_tests)
                ],
                "series": [
                    {
                        "name": "Score",
                        "data": [
                            float(attempt.percentage) for attempt, _, _ in recent_tests
                        ],
                    }
                ],
            },
            "exam_performance_chart": {
                "categories": [
                    subject.name if subject else f"Exam {i + 1}"
                    for i, (_, _, subject) in enumerate(recent_exams)
                ],
                "series": [
                    {
                        "name": "Score",
                        "data": [
                            float(attempt.percentage) for attempt, _, _ in recent_exams
                        ],
                    }
                ],
            },
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

    async def _build_guardian_response(self, guardian) -> GuardianResponse:
        """Build guardian response with computed fields"""
        total_wards = self.guardian_repo.get_ward_count(guardian.id, active_only=False)
        active_wards = self.guardian_repo.get_ward_count(guardian.id, active_only=True)

        return GuardianResponse(
            id=guardian.id,
            user_id=guardian.user_id,
            guardian_code=guardian.guardian_code,
            relationship_type=guardian.relationship_type,
            receive_progress_reports=guardian.receive_progress_reports,
            receive_performance_alerts=guardian.receive_performance_alerts,
            receive_payment_reminders=guardian.receive_payment_reminders,
            is_active=guardian.is_active,
            is_verified=guardian.is_verified,
            created_at=guardian.created_at,
            updated_at=guardian.updated_at,
            full_name=guardian.user.full_name if guardian.user else None,
            email=guardian.user.email if guardian.user else None,
            total_wards=total_wards,
            active_wards=active_wards,
        )

    async def _build_ward_response(self, student: Student) -> WardResponse:
        """Build ward response with computed fields"""
        # Get assessment statistics
        from src.domains.assessment.repositories.attempt_repository import (
            AssessmentAttemptRepository,
        )

        AssessmentAttemptRepository(self.db)

        # Calculate average scores
        avg_exam = (
            self.db.query(func.avg(AssessmentAttempt.score))
            .join(Assessment)
            .filter(
                AssessmentAttempt.user_id == student.user_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                Assessment.assessment_type == AssessmentType.EXAM,
            )
            .scalar()
            or 0.0
        )

        avg_test = (
            self.db.query(func.avg(AssessmentAttempt.score))
            .join(Assessment)
            .filter(
                AssessmentAttempt.user_id == student.user_id,
                AssessmentAttempt.status == AttemptStatus.GRADED,
                Assessment.assessment_type == AssessmentType.TEST,
            )
            .scalar()
            or 0.0
        )

        total_assessments = (
            self.db.query(func.count(AssessmentAttempt.id))
            .filter(AssessmentAttempt.user_id == student.user_id)
            .scalar()
            or 0
        )

        return WardResponse(
            id=student.id,
            user_id=student.user_id,
            student_code=student.student_code,
            full_name=student.user.full_name if student.user else "Unknown",
            email=student.user.email if student.user else "",
            category_name=student.category.display_name if student.category else None,
            category_id=student.category_id,
            is_active=student.is_active,
            is_suspended=student.is_suspended,
            avg_exam_score=round(avg_exam, 2) if avg_exam else None,
            avg_test_score=round(avg_test, 2) if avg_test else None,
            total_assessments=total_assessments,
            created_at=student.created_at,
        )

    async def create_and_assign_assessment(
        self,
        guardian_id: UUID,
        user_id: UUID,
        request_data: CreateAssessmentForWardsRequest,
    ) -> AssessmentAssignmentResponse:
        """Create auto-generated assessment and assign to wards"""

        from src.domains.assessment.schemas.assessment import AutoAssessmentRequest

        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to create assessments")

        # Check subscription limits for assessment creation
        subscription_service = SubscriptionService(self.db)
        can_create, message = await subscription_service.check_usage_limit(
            user_id, "test"
        )
        if not can_create:
            raise BusinessLogicException(message)

        # Verify all wards belong to this guardian
        for ward_id in request_data.ward_ids:
            student = self.student_repo.get_by_id(ward_id)
            if not student or student.guardian_id != guardian_id:
                raise ValidationException(f"Ward {ward_id} does not belong to you")

        # Create auto-generated assessment using AutoAssessmentService
        auto_service = AutoAssessmentService(self.db)

        auto_request = AutoAssessmentRequest(
            subject_id=request_data.subject_id,
            topic_ids=request_data.topic_ids,
            number_of_questions=request_data.number_of_questions,
            duration_minutes=request_data.duration_minutes,
            difficulty_level=None,  # Mixed difficulty
            question_types=None,  # All types
            shuffle_questions=request_data.shuffle_questions,
            shuffle_options=request_data.shuffle_options,
            allow_review=request_data.allow_review,
        )

        assessment_result = await auto_service.generate_assessment(
            auto_request, user_id
        )

        # Create assignments for each ward
        assignments = []
        for ward_id in request_data.ward_ids:
            assignment = AssessmentAssignment(
                assessment_id=assessment_result.assessment_id,
                ward_id=ward_id,
                assigned_by=guardian_id,
                status=AssignmentStatus.ASSIGNED,
                due_date=request_data.due_date,
                instructions=request_data.instructions,
            )
            self.db.add(assignment)
            self.db.flush()

            # Build response for this assignment
            student = self.student_repo.get_by_id(ward_id)
            assignments.append(
                AssignmentResponse(
                    id=assignment.id,
                    assessment_id=assessment_result.assessment_id,
                    assessment_title=assessment_result.title,
                    ward_id=ward_id,
                    ward_name=student.user.full_name
                    if student and student.user
                    else "Unknown",
                    assigned_by=user_id,
                    due_date=request_data.due_date,
                    status="assigned",
                    assigned_at=assignment.assigned_at,
                )
            )

        self.db.commit()

        # Here, We log activity count for subscribe members
        await subscription_service.log_activity(user_id=user_id, activity_type="test")

        # TODO: Send notifications to wards about new assignment

        return AssessmentAssignmentResponse(
            assessment_id=assessment_result.assessment_id,
            assessment_title=assessment_result.title,
            total_questions=assessment_result.total_questions,
            duration_minutes=assessment_result.duration_minutes,
            assigned_to=request_data.ward_ids,
            assignments=assignments,
            message=f"Assessment created and assigned to {len(request_data.ward_ids)} ward(s) successfully!",
        )

    async def get_ward_assignments(
        self,
        guardian_id: UUID,
        user_id: UUID,
        ward_id: Optional[UUID] = None,
        status: Optional[AssignmentStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AssignmentResponse]:
        """Get assessment assignments for guardian's wards"""

        guardian = self.guardian_repo.get_by_id(guardian_id)
        if not guardian:
            raise ResourceNotFoundException("Guardian", guardian_id)

        if guardian.user_id != user_id:
            raise AuthorizationException("You don't have access to view assignments")

        query = self.db.query(AssessmentAssignment).filter(
            AssessmentAssignment.assigned_by == guardian_id,
            AssessmentAssignment.is_deleted.is_(False),
        )

        if ward_id:
            query = query.filter(AssessmentAssignment.ward_id == ward_id)

        if status:
            query = query.filter(AssessmentAssignment.status == status)

        assignments = (
            query.order_by(AssessmentAssignment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Build responses
        responses = []
        for assignment in assignments:
            student = self.student_repo.get_by_id(assignment.ward_id)

            responses.append(
                AssignmentResponse(
                    id=assignment.id,
                    assessment_id=assignment.assessment_id,
                    assessment_title=assignment.assessment.title
                    if assignment.assessment
                    else "Unknown",
                    ward_id=assignment.ward_id,
                    ward_name=student.user.full_name
                    if student and student.user
                    else "Unknown",
                    assigned_by=user_id,
                    due_date=assignment.due_date,
                    status=assignment.status,
                    assigned_at=assignment.assigned_at,
                )
            )

        return responses
