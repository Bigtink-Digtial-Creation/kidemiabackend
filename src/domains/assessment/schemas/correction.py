from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class OptionCorrectionResponse(BaseModel):
    id: UUID
    option_text: str
    is_correct: bool
    selected: bool
    image_url: Optional[str] = None


class QuestionCorrectionResponse(BaseModel):
    id: UUID
    question_text: str
    question_type: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    explanation: Optional[str] = None
    points: Optional[int] = None


class UserAnswerResponse(BaseModel):
    selected_option_ids: Optional[List[UUID]] = None
    text_answer: Optional[str] = None
    matching_pairs: Optional[dict] = None
    ordered_items: Optional[List] = None


class AnswerResultResponse(BaseModel):
    is_correct: bool
    is_partially_correct: bool
    points_earned: float
    points_possible: float


class SingleAnswerCorrectionResponse(BaseModel):
    answer_id: UUID
    question: QuestionCorrectionResponse
    options: List[OptionCorrectionResponse]
    user_answer: UserAnswerResponse
    result: AnswerResultResponse


class AttemptSummaryResponse(BaseModel):
    id: UUID
    status: str
    score: Optional[float] = None
    percentage: Optional[float] = None
    points_earned: float
    points_possible: float
    passed: Optional[bool] = None
    time_spent_seconds: Optional[int] = None
    submitted_at: Optional[datetime] = None


class AnswerCorrectionResponse(BaseModel):
    attempt: AttemptSummaryResponse
    answers: List[SingleAnswerCorrectionResponse]
