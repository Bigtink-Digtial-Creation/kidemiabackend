from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime
import random

from src.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
)
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.content.repositories.subject_repository import SubjectRepository
from src.domains.content.repositories.topic_repository import TopicRepository
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.assessment.schemas.assessment import (
    AutoAssessmentRequest,
    AutoAssessmentResponse,
    AssessmentCreate,
)
from src.domains.assessment.enums import (
    AssessmentType,
    AssessmentCategory,
    QuestionSelectionMode,
    ResultDisplayMode,
)
from src.domains.content.enums import QuestionStatus


class AutoAssessmentService:
    """Service for automatically generating assessments"""

    def __init__(self, db: Session):
        self.db = db
        self.assessment_repo = AssessmentRepository(db)
        self.subject_repo = SubjectRepository(db)
        self.topic_repo = TopicRepository(db)
        self.question_repo = QuestionRepository(db)

    async def generate_assessment(
        self, request: AutoAssessmentRequest, user_id: UUID
    ) -> AutoAssessmentResponse:
        """
        Auto-generate an assessment from selected topics

        Flow:
        1. Validate subject and topics
        2. Find approved questions from topics
        3. Apply filters (difficulty, type)
        4. Randomly select required number of questions
        5. Create assessment
        6. Return assessment details
        """

        # 1. Validate subject exists
        subject = self.subject_repo.get_by_id(request.subject_id)
        if not subject:
            raise ResourceNotFoundException("Subject", request.subject_id)

        # 2. Validate topics exist and belong to subject
        topics = []
        for topic_id in request.topic_ids:
            topic = self.topic_repo.get_by_id(topic_id)
            if not topic:
                raise ResourceNotFoundException("Topic", topic_id)

            if topic.subject_id != request.subject_id:
                raise ValidationException(
                    f"Topic {topic.name} does not belong to subject {subject.name}"
                )

            topics.append(topic)

        # 3. Find approved questions from these topics
        available_questions = await self._get_questions_from_topics(
            request.topic_ids, request.difficulty_level, request.question_types
        )

        # 4. Validate we have enough questions
        if len(available_questions) < request.number_of_questions:
            raise BusinessLogicException(
                f"Not enough questions available. Found {len(available_questions)}, "
                f"need {request.number_of_questions}. "
                f"Try selecting more topics or reducing question count."
            )

        # 5. Randomly select questions
        selected_questions = random.sample(
            available_questions, request.number_of_questions
        )

        # 6. Create assessment
        assessment_code = self._generate_unique_code(subject.code)
        topic_names = [t.name for t in topics]

        assessment_data = AssessmentCreate(
            title=self._generate_title(subject.name, topic_names),
            code=assessment_code,
            description=f"Practice test covering: {', '.join(topic_names)}",
            instructions=(
                "This is an automatically generated practice test. "
                "Answer all questions to the best of your ability."
            ),
            assessment_type=AssessmentType.TEST,
            category=AssessmentCategory.GENERAL,
            subject_id=request.subject_id,
            topic_ids=request.topic_ids,
            # Free for auto-generated tests
            price=0.00,
            currency="NGN",
            duration_minutes=request.duration_minutes,
            # Auto-selection mode
            question_selection_mode=QuestionSelectionMode.MANUAL,
            passing_percentage=50.00,
            # Behavior from request
            shuffle_questions=request.shuffle_questions,
            shuffle_options=request.shuffle_options,
            allow_question_navigation=True,
            allow_backward_navigation=request.allow_review,
            max_attempts=10,  # Unlimited for practice
            # Immediate results for practice
            result_display_mode=ResultDisplayMode.IMMEDIATE,
            show_correct_answers=True,
            show_explanations=True,
            # No proctoring for auto-generated
            proctoring_enabled=False,
            require_webcam=False,
            fullscreen_required=False,
            detect_tab_switching=False,
            # Public access
            is_public=True,
            require_enrollment=False,
            # Selected questions
            question_ids=[q.id for q in selected_questions],
            sections=[],
        )

        # Create through main assessment service
        from src.domains.assessment.services.assessment_service import AssessmentService

        assessment_service = AssessmentService(self.db)

        assessment = await assessment_service.create_assessment(
            assessment_data, user_id
        )

        # Auto-publish for immediate use
        await assessment_service.publish_assessment(assessment.id, user_id)

        return AutoAssessmentResponse(
            assessment_id=assessment.id,
            title=assessment.title,
            total_questions=assessment.total_questions,
            duration_minutes=assessment.duration_minutes,
            topics_covered=topic_names,
            message=(
                f"Assessment created successfully! "
                f"{assessment.total_questions} questions from {len(topics)} topics."
            ),
        )

    async def _get_questions_from_topics(
        self,
        topic_ids: List[UUID],
        difficulty_level: Optional[str] = None,
        question_types: Optional[List[str]] = None,
    ) -> List:
        """Get approved questions from topics with optional filters"""

        # Build filter
        filters = {"status": QuestionStatus.APPROVED, "is_deleted": False}

        # Get questions from all topics
        all_questions = []
        for topic_id in topic_ids:
            questions = self.question_repo.get_by_topic(topic_id)
            all_questions.extend(questions)

        # Apply difficulty filter
        # if difficulty_level:
        #     all_questions = [
        #         q for q in all_questions if q.difficulty_level == difficulty_level
        #     ]
        print(all_questions)

        # Apply question type filter
        if question_types:
            all_questions = [
                q for q in all_questions if q.question_type in question_types
            ]

        return all_questions

    def _generate_unique_code(self, subject_code: str) -> str:
        """Generate unique assessment code"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        code = f"AUTO-{subject_code}-{timestamp}-{random_suffix}"

        # Ensure uniqueness
        counter = 1
        original_code = code
        while self.assessment_repo.code_exists(code):
            code = f"{original_code}-{counter}"
            counter += 1

        return code

    def _generate_title(self, subject_name: str, topic_names: List[str]) -> str:
        """Generate assessment title"""
        if len(topic_names) <= 2:
            topics_str = " & ".join(topic_names)
        else:
            topics_str = f"{topic_names[0]} & {len(topic_names) - 1} more topics"

        return f"{subject_name}: {topics_str} Practice Test"
