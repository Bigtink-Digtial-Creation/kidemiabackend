from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions, get_current_user
from src.domains.assessment.services.assessment_service import AssessmentService
from src.domains.assessment.services.practice_test_service import AutoAssessmentService
from src.shared.response import success_response
from fastapi.encoders import jsonable_encoder
from src.domains.assessment.schemas.assessment import (
    AssessmentCreate,
    AssessmentUpdate,
    AssessmentResponse,
    AssessmentSummaryResponse,
    AssessmentListResponse,
    AssessmentFilterParams,
    AutoAssessmentRequest,
    AutoAssessmentResponse,
)

from src.domains.assessment.schemas.statistics import AssessmentStatistics
from src.domains.assessment.enums import (
    AssessmentType,
    AssessmentCategory,
    AssessmentStatus,
)
from src.shared.schemas.base import MessageResponse

router = APIRouter()


@router.post(
    "/",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assessment",
)
async def create_assessment(
    assessment_data: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("assessment:create")),
):
    """
    Create a new assessment (test or exam).

    Requires `assessment:create` permission.

    - **assessment_type**: TEST (free) or EXAM (paid)
    - **category**: JAMB, WAEC, NECO, Common Entrance, etc.
    - **question_selection_mode**: MANUAL, RANDOM, or ADAPTIVE
    """
    service = AssessmentService(db)
    return await service.create_assessment(assessment_data, current_user_id)


@router.post(
    "/auto-generate",
    response_model=AutoAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-generate assessment from topics",
)
async def auto_generate_assessment(
    request: AutoAssessmentRequest,
    db: Session = Depends(get_db),
    # current_user_id: UUID = Depends(get_current_user_id),
    current_user=Depends(get_current_user),
):
    """
    Automatically generate a practice assessment from selected topics.

    This endpoint allows students to create personalized practice tests by:
    - Selecting a subject
    - Choosing specific topics they want to practice
    - Setting number of questions and duration
    - Optionally filtering by difficulty and question types

    The system will:
    1. Find approved questions from selected topics
    2. Randomly select the requested number of questions
    3. Create and publish the assessment immediately
    4. Return assessment details for the student to start

    **Use Case:** Student wants to practice specific topics before an exam

    Example:
    ```json
    {
        "subject_id": "uuid-mathematics",
        "topic_ids": ["uuid-algebra", "uuid-geometry"],
        "number_of_questions": 20,
        "duration_minutes": 30,
        "difficulty_level": "MEDIUM"
    }
    ```
    """

    service = AutoAssessmentService(db)
    return await service.generate_assessment(request, current_user.id)


@router.get("/", response_model=AssessmentListResponse, summary="Get all assessments")
async def get_assessments(
    assessment_type: Optional[AssessmentType] = Query(None),
    category: Optional[AssessmentCategory] = Query(None),
    subject_id: Optional[UUID] = Query(None),
    status: Optional[AssessmentStatus] = Query(None),
    exam_year: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    is_public: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get assessments with filters.

    - **assessment_type**: Filter by TEST or EXAM
    - **category**: Filter by JAMB, WAEC, NECO, etc.
    - **subject_id**: Filter by subject
    - **exam_year**: Filter by year (e.g., 2024, 2023)
    - **search**: Search by title, code, or description
    """
    filters = AssessmentFilterParams(
        assessment_type=assessment_type,
        category=category,
        subject_id=subject_id,
        status=status,
        exam_year=exam_year,
        min_price=min_price,
        max_price=max_price,
        is_public=is_public,
        search=search,
    )

    service = AssessmentService(db)
    return await service.get_assessments(filters, skip, limit)


@router.get(
    "/available",
    response_model=List[AssessmentSummaryResponse],
    summary="Get currently available assessments",
)
async def get_available_assessments(
    assessment_type: Optional[AssessmentType] = Query(None),
    category: Optional[AssessmentCategory] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get assessments that are currently available for taking."""
    service = AssessmentService(db)
    return await service.get_available_assessments(
        assessment_type, category, skip, limit
    )


@router.get(
    "/popular",
    response_model=List[AssessmentSummaryResponse],
    summary="Get popular assessments",
)
async def get_popular_assessments(
    assessment_type: Optional[AssessmentType] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get popular assessments based on attempt count."""
    service = AssessmentService(db)
    return await service.get_popular_assessments(assessment_type, limit)


@router.get(
    "/categories/{category}/years",
    response_model=List[int],
    summary="Get available years for a category",
)
async def get_category_years(
    category: AssessmentCategory, db: Session = Depends(get_db)
):
    """Get list of years with assessments for a specific category (e.g., JAMB 2024, 2023, etc.)."""
    from src.domains.assessment.repositories.assessment_repository import (
        AssessmentRepository,
    )

    repo = AssessmentRepository(db)
    return repo.get_years_available(category)


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
    summary="Get assessment by ID",
)
async def get_assessment(
    assessment_id: UUID,
    include_questions: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Get a specific assessment by ID.

    - **include_questions**: Include full question details
    """
    service = AssessmentService(db)
    return await service.get_assessment(assessment_id, include_questions)


@router.get("/{assessment_id}/config", status_code=status.HTTP_200_OK)
async def get_assessment_config(
    assessment_id: UUID,
    db=Depends(get_db),
    user_id=Depends(get_current_user_id),
):
    """Get assessment configuration for pre-check screen"""
    service = AssessmentService(db)
    result = await service.get_assessment_config(assessment_id, user_id)

    return success_response(
        data=jsonable_encoder(result),
        message="Assessment configuration retrieved successfully",
    )


@router.put(
    "/{assessment_id}",
    response_model=AssessmentResponse,
    summary="Update an assessment",
)
async def update_assessment(
    assessment_id: UUID,
    assessment_data: AssessmentUpdate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("assessment:update")),
):
    """
    Update an assessment.

    Requires `assessment:update` permission.
    Note: Published assessments must be archived before updating.
    """
    service = AssessmentService(db)
    return await service.update_assessment(
        assessment_id, assessment_data, current_user_id
    )


@router.delete(
    "/{assessment_id}", response_model=MessageResponse, summary="Delete an assessment"
)
async def delete_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("assessment:delete")),
):
    """
    Delete an assessment (soft delete).

    Requires `assessment:delete` permission.
    Cannot delete assessments with active attempts.
    """
    service = AssessmentService(db)
    await service.delete_assessment(assessment_id)
    return MessageResponse(message="Assessment deleted successfully")


@router.post(
    "/{assessment_id}/publish",
    response_model=AssessmentResponse,
    summary="Publish an assessment",
)
async def publish_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(require_permissions("assessment:publish")),
):
    """
    Publish an assessment to make it available to students.

    Requires `assessment:publish` permission.
    """
    service = AssessmentService(db)
    return await service.publish_assessment(assessment_id, current_user_id)


@router.get(
    "/{assessment_id}/statistics",
    response_model=AssessmentStatistics,
    summary="Get assessment statistics",
)
async def get_assessment_statistics(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions("assessment:read")),
):
    """Get detailed statistics for an assessment."""
    service = AssessmentService(db)
    return await service.get_statistics(assessment_id)
