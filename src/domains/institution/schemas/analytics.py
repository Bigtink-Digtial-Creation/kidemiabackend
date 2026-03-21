from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ScoreSnapshot(BaseModel):
    period: str  # "2024-01", "Term 1", etc.
    avg_score: float
    pass_rate: float
    total_attempts: int


class QuestionInsight(BaseModel):
    question_id: UUID
    question_text: str
    question_content: Optional[str] = None
    correct_rate: float
    total_answers: int
    difficulty: Optional[str]


class StudentPerformanceSummary(BaseModel):
    student_id: UUID
    student_name: str
    student_code: Optional[str]
    total_assessments: int
    completed_assessments: int
    avg_score: float
    pass_rate: float
    highest_score: float
    lowest_score: float
    trend: str  # "improving" | "declining" | "stable" | "insufficient_data"


class ClassroomAnalytics(BaseModel):
    classroom_id: UUID
    classroom_name: str
    level: str
    teacher_name: Optional[str]
    total_students: int
    total_assessments_assigned: int
    avg_score: float
    pass_rate: float
    completion_rate: float
    highest_avg_score: float  # best student avg
    lowest_avg_score: float  # weakest student avg
    score_trend: List[ScoreSnapshot]
    top_performers: List[StudentPerformanceSummary]
    needs_support: List[StudentPerformanceSummary]
    most_difficult_topics: List[QuestionInsight]


class ClassroomComparison(BaseModel):
    classroom_id: UUID
    classroom_name: str
    level: str
    avg_score: float
    pass_rate: float
    completion_rate: float
    total_students: int
    assessments_completed: int


class GroupPerformance(BaseModel):
    group_id: UUID
    group_name: str
    classroom_name: str
    total_members: int
    avg_score: float
    pass_rate: float
    assessments_completed: int


class InstitutionAnalytics(BaseModel):
    institution_id: UUID
    total_students: int
    total_assessments_assigned: int
    overall_avg_score: float
    overall_pass_rate: float
    overall_completion_rate: float
    score_trend: List[ScoreSnapshot]
    classroom_comparison: List[ClassroomComparison]
    group_performance: List[GroupPerformance]
    top_classrooms: List[ClassroomComparison]
    struggling_classrooms: List[ClassroomComparison]


class AssessmentResult(BaseModel):
    assessment_id: UUID
    assessment_title: str
    subject_name: Optional[str]
    assigned_at: datetime
    completed_at: Optional[datetime]
    score: Optional[float]
    percentage: Optional[float]
    passed: Optional[bool]
    grade: Optional[str]
    time_spent_seconds: Optional[int]
    attempt_count: int
    status: str


class SubjectPerformance(BaseModel):
    subject_name: str
    total_assessments: int
    avg_score: float
    pass_rate: float
    best_score: float
    latest_score: Optional[float]


class StudentReportCard(BaseModel):
    student_id: UUID
    student_name: str
    student_code: Optional[str]
    classroom_name: Optional[str]
    guardian_email: Optional[str]
    generated_at: datetime

    # Summary stats
    total_assessments_assigned: int
    total_assessments_completed: int
    completion_rate: float
    overall_avg_score: float
    overall_pass_rate: float
    grade: str  # overall letter grade
    trend: str  # "improving" | "declining" | "stable"
    rank_in_class: Optional[int]
    class_size: Optional[int]

    # Breakdown
    subject_performance: List[SubjectPerformance]
    assessment_results: List[AssessmentResult]
    score_over_time: List[ScoreSnapshot]


class BulkReportCardRequest(BaseModel):
    student_ids: Optional[List[UUID]] = None  # None = all institution students
    classroom_id: Optional[UUID] = None  # filter by class
    group_id: Optional[UUID] = None  # filter by group


class BulkReportCardResult(BaseModel):
    total: int
    report_cards: List[StudentReportCard]
