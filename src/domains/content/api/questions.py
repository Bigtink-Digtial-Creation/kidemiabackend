from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.content.services.question_service import QuestionService
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
)
from src.domains.content.enums import QuestionType, DifficultyLevel, QuestionStatus
from src.shared.schemas.base import MessageResponse

router = APIRouter()


@router.post(
    "/bulk-questions",
    response_model=List[QuestionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create bulk questions",
)
async def create_bulk_question(
    question_data: List[QuestionCreate],
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:create")),
):
    service = QuestionService(db)
    return await service.create_questions_bulk(question_data, current_user_id)


@router.post(
    "/",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question",
)
async def create_question(
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:create")),
):
    """
    Create a new question.

    Parameters:
    ------------------------
    - subject_id : string <uuid> (required)
    - topic_id : string <uuid> (required)
    - question_text : string (required, non-empty)
    - question_type : string (required, enum)
        - multiple_choice
        - true_false
        - fill_in_blank
        - essay
        - matching
        - ordering
    - difficulty_level : string (required, enum)
        - easy
        - medium
        - hard
        - expert
    - explanation : string | null (optional)
    - image_url : string | null (optional)
    - audio_url : string | null (optional)
    - video_url : string | null (optional)
    - points : integer (default=1, range [1..100])
    - time_limit_seconds : integer | null (optional)
    - options : Array[object] (required, >= 2 items)
    - tag_ids : Array[string <uuid>] | null (optional)

    Responses:
    ----------
    - 201 Created : Question successfully created
    - 400 Bad Request : Invalid input
    - 401 Unauthorized : Authentication required
    - 403 Forbidden : Not enough permissions
    """
    service = QuestionService(db)
    return await service.create_question(question_data, current_user_id)


@router.get(
    "/", response_model=QuestionListResponse, summary="Get questions with filters"
)
async def get_questions(
    subject_id: Optional[UUID] = Query(None),
    topic_id: Optional[UUID] = Query(None),
    difficulty_level: Optional[DifficultyLevel] = Query(None),
    question_type: Optional[QuestionType] = Query(None),
    status: Optional[QuestionStatus] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get questions with various filters.

    - **subject_id**: Filter by subject
    - **topic_id**: Filter by topic
    - **difficulty_level**: Filter by difficulty
    - **question_type**: Filter by question type
    - **status**: Filter by status
    - **search**: Search in question text
    """
    filters = QuestionFilterParams(
        subject_id=subject_id,
        topic_id=topic_id,
        difficulty_level=difficulty_level,
        question_type=question_type,
        status=status,
        search=search,
    )

    service = QuestionService(db)
    return await service.get_questions(filters, skip, limit)


@router.get(
    "/random",
    response_model=List[QuestionPublicResponse],
    summary="Get random questions",
)
async def get_random_questions(
    count: int = Query(..., ge=1, le=100),
    subject_id: Optional[UUID] = Query(None),
    topic_id: Optional[UUID] = Query(None),
    difficulty: Optional[DifficultyLevel] = Query(None),
    question_type: Optional[QuestionType] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get random approved questions for test/exam generation.

    - **count**: Number of questions to return
    - **subject_id**: Filter by subject
    - **topic_id**: Filter by topic
    - **difficulty**: Filter by difficulty
    - **question_type**: Filter by question type
    """
    service = QuestionService(db)
    return await service.get_random_questions(
        count=count,
        subject_id=subject_id,
        topic_id=topic_id,
        difficulty=difficulty,
        question_type=question_type,
    )


@router.get(
    "/{question_id}", response_model=QuestionResponse, summary="Get question by ID"
)
async def get_question(
    question_id: UUID,
    include_answers: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Get a specific question by ID.

    - **include_answers**: Include correct answer information (default: true)
    """
    service = QuestionService(db)
    return await service.get_question(question_id, include_answers)


@router.put(
    "/{question_id}", response_model=QuestionResponse, summary="Update a question"
)
async def update_question(
    question_id: UUID,
    question_data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:update")),
):
    """
    Update a question.

    Requires `content:update` permission.
    """
    service = QuestionService(db)
    return await service.update_question(question_id, question_data, current_user_id)


@router.delete(
    "/{question_id}", response_model=MessageResponse, summary="Delete a question"
)
async def delete_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("content:delete")),
):
    """
    Delete a question (soft delete).

    Requires `content:delete` permission.
    """
    service = QuestionService(db)
    await service.delete_question(question_id)
    return MessageResponse(message="Question deleted successfully")


@router.post(
    "/{question_id}/submit-review",
    response_model=QuestionResponse,
    summary="Submit question for review",
)
async def submit_for_review(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:create")),
):
    """
    Submit a question for review.

    Requires `content:create` permission.
    """
    service = QuestionService(db)
    return await service.submit_for_review(question_id)


@router.post(
    "/{question_id}/review",
    response_model=QuestionResponse,
    summary="Review a question",
)
async def review_question(
    question_id: UUID,
    review_data: QuestionReviewRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:approve")),
):
    """
    Review a question (approve or reject).

    Requires `content:approve` permission.
    """
    service = QuestionService(db)
    return await service.review_question(question_id, review_data, current_user_id)


@router.post(
    "/bulk-import",
    response_model=BulkQuestionImportResponse,
    summary="Bulk import questions",
)
async def bulk_import_questions(
    import_data: BulkQuestionImportRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("content:create")),
):
    """
    Bulk import multiple questions.

    Requires `content:create` permission.
    """
    service = QuestionService(db)
    return await service.bulk_import_questions(import_data, current_user_id)
