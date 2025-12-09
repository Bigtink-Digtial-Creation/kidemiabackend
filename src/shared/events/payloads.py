from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class AssessmentCompletedPayload(BaseModel):
    assessment_id: UUID
    category_id: Optional[UUID]
    score: int
    total_questions: int
    time_taken_seconds: int
    completed_at: datetime
