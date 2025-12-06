from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.core.exceptions import ResourceNotFoundException, ValidationException
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.content.repositories.tag_repository import QuestionTagRepository
from src.domains.content.repositories.subject_repository import SubjectRepository
from src.domains.content.repositories.topic_repository import TopicRepository
from src.domains.content.models.option import QuestionOption
from src.domains.content.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionPublicResponse,
    QuestionListResponse,
    QuestionFilterParams,
    BulkQuestionImportRequest,
    BulkQuestionImportResponse,
    QuestionReviewRequest,
    TopicQuestionListResponse,
    QuestionResponseTrim,
)
from src.domains.content.enums import QuestionStatus


class QuestionService:
    """Service for question operations"""

    def __init__(self, db: Session):
        self.db = db
        self.question_repo = QuestionRepository(db)
        self.tag_repo = QuestionTagRepository(db)
        self.subject_repo = SubjectRepository(db)
        self.topic_repo = TopicRepository(db)

    async def create_questions_bulk(
        self, questions_data: List[QuestionCreate], created_by: UUID
    ) -> List[QuestionResponse]:
        """Create multiple questions at once"""
        created_questions = []
        errors = []

        for idx, question_data in enumerate(questions_data):
            try:
                # Validate subject exists
                subject = self.subject_repo.get_by_id(question_data.subject_id)
                if not subject:
                    errors.append(
                        {
                            "index": idx,
                            "error": f"Subject not found: {question_data.subject_id}",
                        }
                    )
                    continue

                # Validate topic exists
                topic = self.topic_repo.get_by_id(question_data.topic_id)
                if not topic:
                    errors.append(
                        {
                            "index": idx,
                            "error": f"Topic not found: {question_data.topic_id}",
                        }
                    )
                    continue

                # Ensure topic belongs to subject
                if topic.subject_id != question_data.subject_id:
                    errors.append(
                        {
                            "index": idx,
                            "error": "Topic must belong to the specified subject",
                        }
                    )
                    continue

                # Create question
                question_dict = question_data.model_dump(exclude={"options", "tag_ids"})
                question_dict["created_by"] = created_by
                question_dict["status"] = QuestionStatus.APPROVED

                question = self.question_repo.create(question_dict)

                # Create options
                for option_data in question_data.options:
                    option_dict = option_data.model_dump()
                    option_dict["question_id"] = question.id
                    option_dict["created_by"] = created_by

                    option = QuestionOption(**option_dict)
                    self.db.add(option)

                # Add tags
                if question_data.tag_ids:
                    for tag_id in question_data.tag_ids:
                        tag = self.tag_repo.get_by_id(tag_id)
                        if tag:
                            question.tags.append(tag)

                self.db.flush()  # Flush instead of commit for batch processing
                created_questions.append(question)

            except Exception as e:
                errors.append({"index": idx, "error": str(e)})
                continue

        # Commit all at once
        if created_questions:
            self.db.commit()
            for question in created_questions:
                self.db.refresh(question)

        if errors:
            # Log errors or handle them appropriately
            pass

        return [QuestionResponse.model_validate(q) for q in created_questions]

    async def create_question(
        self, question_data: QuestionCreate, created_by: UUID
    ) -> QuestionResponse:
        """Create a new question"""
        # Validate subject exists
        subject = self.subject_repo.get_by_id(question_data.subject_id)
        if not subject:
            raise ResourceNotFoundException("Subject", question_data.subject_id)

        # Validate topic exists
        topic = self.topic_repo.get_by_id(question_data.topic_id)
        if not topic:
            raise ResourceNotFoundException("Topic", question_data.topic_id)

        # Ensure topic belongs to subject
        if topic.subject_id != question_data.subject_id:
            raise ValidationException("Topic must belong to the specified subject")

        # Create question
        question_dict = question_data.model_dump(exclude={"options", "tag_ids"})
        question_dict["created_by"] = created_by
        # question_dict["status"] = QuestionStatus.DRAFT
        question_dict["status"] = QuestionStatus.APPROVED

        question = self.question_repo.create(question_dict)

        # Create options
        for option_data in question_data.options:
            option_dict = option_data.model_dump()
            option_dict["question_id"] = question.id
            option_dict["created_by"] = created_by

            option = QuestionOption(**option_dict)
            self.db.add(option)

        # Add tags
        if question_data.tag_ids:
            for tag_id in question_data.tag_ids:
                tag = self.tag_repo.get_by_id(tag_id)
                if tag:
                    question.tags.append(tag)

        self.db.commit()
        self.db.refresh(question)

        return QuestionResponse.model_validate(question)

    async def get_question(
        self, question_id: UUID, include_answers: bool = True
    ) -> QuestionResponse | QuestionPublicResponse:
        """Get question by ID"""
        question = self.question_repo.get_with_options(question_id)
        if not question:
            raise ResourceNotFoundException("Question", question_id)

        if include_answers:
            return QuestionResponse.model_validate(question)
        else:
            return QuestionPublicResponse.model_validate(question)

    async def get_questions(
        self, filters: QuestionFilterParams, skip: int = 0, limit: int = 100
    ) -> QuestionListResponse:
        """Get questions with filters"""
        query_filters = {}

        if filters.subject_id:
            query_filters["subject_id"] = filters.subject_id
        if filters.topic_id:
            query_filters["topic_id"] = filters.topic_id
        if filters.difficulty_level:
            query_filters["difficulty_level"] = filters.difficulty_level
        if filters.question_type:
            query_filters["question_type"] = filters.question_type
        if filters.status:
            query_filters["status"] = filters.status

        query_filters["is_deleted"] = False

        if filters.search:
            questions = self.question_repo.search_questions(
                filters.search, filters.subject_id, skip, limit
            )
            total = len(questions)
        elif filters.tag_ids:
            questions = self.question_repo.get_by_tags(filters.tag_ids, skip, limit)
            total = len(questions)
        else:
            questions = self.question_repo.get_all(skip, limit, query_filters)
            total = self.question_repo.count(query_filters)

        items = [QuestionResponse.model_validate(q) for q in questions]
        page = (skip // limit) + 1

        return QuestionListResponse(
            items=items, total=total, page=page, page_size=limit
        )

    async def get_questions_by_topics(
        self, topic_ids: list[UUID], limit: int = 20
    ) -> TopicQuestionListResponse:
        """Get questions grouped by multiple topics"""
        results = []

        for topic_id in topic_ids:
            topic = self.topic_repo.get_by_id(topic_id)
            if not topic:
                continue  # skip invalid topic IDs

            # Fetch questions under this topic
            questions = self.question_repo.get_all(
                skip=0, limit=limit, filters={"topic_id": topic_id, "is_deleted": False}
            )

            topic_block = {
                "topic_name": topic.name,
                "questions": [
                    QuestionResponseTrim.model_validate(q) for q in questions
                ],
            }
            results.append(topic_block)

        return TopicQuestionListResponse(topics=results)

    async def update_question(
        self, question_id: UUID, question_data: QuestionUpdate, updated_by: UUID
    ) -> QuestionResponse:
        """Update a question"""
        question = self.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundException("Question", question_id)

        # Update question
        update_dict = question_data.model_dump(exclude_unset=True, exclude={"tag_ids"})
        update_dict["updated_by"] = updated_by

        # Update tags if provided
        if question_data.tag_ids is not None:
            question.tags.clear()
            for tag_id in question_data.tag_ids:
                tag = self.tag_repo.get_by_id(tag_id)
                if tag:
                    question.tags.append(tag)

        self.question_repo.update(question_id, update_dict)

        return await self.get_question(question_id)

    async def delete_question(self, question_id: UUID) -> bool:
        """Soft delete a question"""
        question = self.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundException("Question", question_id)

        # TODO: Check if question is used in active assessments

        return self.question_repo.soft_delete(question_id) is not None

    async def submit_for_review(self, question_id: UUID) -> QuestionResponse:
        """Submit question for review"""
        question = self.question_repo.submit_for_review(question_id)
        if not question:
            raise ResourceNotFoundException("Question", question_id)

        return QuestionResponse.model_validate(question)

    async def review_question(
        self, question_id: UUID, review_data: QuestionReviewRequest, reviewer_id: UUID
    ) -> QuestionResponse:
        """Review a question (approve or reject)"""
        question = self.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundException("Question", question_id)

        if question.status != QuestionStatus.REVIEW:
            raise ValidationException("Question must be in review status")

        if review_data.approved:
            question = self.question_repo.approve_question(question_id, reviewer_id)
        else:
            question = self.question_repo.reject_question(question_id)

        return QuestionResponse.model_validate(question)

    async def get_random_questions(
        self,
        count: int,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
    ) -> List[QuestionPublicResponse]:
        """Get random approved questions"""
        questions = self.question_repo.get_random_questions(
            count=count,
            subject_id=subject_id,
            topic_id=topic_id,
            difficulty=difficulty,
            question_type=question_type,
        )

        return [QuestionPublicResponse.model_validate(q) for q in questions]

    async def bulk_import_questions(
        self, import_data: BulkQuestionImportRequest, created_by: UUID
    ) -> BulkQuestionImportResponse:
        """Bulk import questions"""
        success_count = 0
        failed_count = 0
        errors = []

        for idx, question_data in enumerate(import_data.questions):
            try:
                await self.create_question(question_data, created_by)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"index": idx, "error": str(e)})

        return BulkQuestionImportResponse(
            total=len(import_data.questions),
            success=success_count,
            failed=failed_count,
            errors=errors,
        )
