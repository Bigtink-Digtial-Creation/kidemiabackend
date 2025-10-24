from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from src.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
)
from src.domains.assessment.repositories.attempt_repository import (
    AssessmentAttemptRepository,
)
from src.domains.assessment.repositories.answer_repository import AnswerRepository
from src.domains.assessment.repositories.assessment_repository import (
    AssessmentRepository,
)
from src.domains.content.repositories.question_repository import QuestionRepository
from src.domains.assessment.enums import AttemptStatus, GradingStatus
from src.domains.content.enums import QuestionType


class GradingService:
    """Service for grading assessment attempts"""

    def __init__(self, db: Session):
        self.db = db
        self.attempt_repo = AssessmentAttemptRepository(db)
        self.answer_repo = AnswerRepository(db)
        self.assessment_repo = AssessmentRepository(db)
        self.question_repo = QuestionRepository(db)

    async def auto_grade_attempt(self, attempt_id: UUID) -> Dict[str, Any]:
        """Auto-grade an assessment attempt"""
        # Get attempt with answers
        attempt = self.attempt_repo.get_with_answers(attempt_id)
        if not attempt:
            raise ResourceNotFoundException("Attempt", attempt_id)

        # Validate status
        if attempt.status != AttemptStatus.SUBMITTED:
            raise BusinessLogicException("Attempt must be submitted before grading")

        # Update grading status
        attempt.grading_status = GradingStatus.AUTO_GRADING
        self.db.commit()

        # Grade each answer
        total_correct = 0
        total_incorrect = 0
        total_partial = 0
        total_points_earned = Decimal("0.00")
        requires_manual = False

        for answer in attempt.answers:
            question = self.question_repo.get_with_options(answer.question_id)
            if not question:
                continue

            # Set points possible
            answer.points_possible = Decimal(str(question.points))

            # Grade based on question type
            if question.question_type == QuestionType.ESSAY:
                # Essays require manual grading
                answer.requires_manual_grading = True
                requires_manual = True
            else:
                grading_result = await self._grade_answer(answer, question)

                answer.is_correct = grading_result["is_correct"]
                answer.is_partially_correct = grading_result["is_partially_correct"]
                answer.points_earned = grading_result["points_earned"]

                if answer.is_correct:
                    total_correct += 1
                elif answer.is_partially_correct:
                    total_partial += 1
                else:
                    total_incorrect += 1

                total_points_earned += answer.points_earned

            self.db.commit()

        # Update attempt statistics
        attempt.correct_answers = total_correct
        attempt.incorrect_answers = total_incorrect
        attempt.partially_correct = total_partial
        attempt.points_earned = total_points_earned

        # Calculate score and percentage
        if attempt.points_possible > 0:
            attempt.percentage = (
                float(total_points_earned) / float(attempt.points_possible)
            ) * 100
            attempt.score = attempt.percentage

        # Determine pass/fail
        assessment = self.assessment_repo.get_by_id(attempt.assessment_id)
        if assessment:
            attempt.passed = attempt.percentage >= float(assessment.passing_percentage)
            attempt.grade = self._calculate_grade(attempt.percentage)

        # Update grading status
        if requires_manual:
            attempt.grading_status = GradingStatus.MANUAL_GRADING
            attempt.requires_manual_grading = True
            attempt.status = AttemptStatus.SUBMITTED
        else:
            attempt.grading_status = GradingStatus.COMPLETED
            attempt.status = AttemptStatus.GRADED
            attempt.graded_at = datetime.utcnow().isoformat()

        self.db.commit()

        return {
            "attempt_id": attempt_id,
            "grading_status": attempt.grading_status,
            "total_correct": total_correct,
            "total_incorrect": total_incorrect,
            "partially_correct": total_partial,
            "points_earned": float(total_points_earned),
            "points_possible": float(attempt.points_possible),
            "score": float(attempt.score),
            "percentage": float(attempt.percentage),
            "passed": attempt.passed,
            "requires_manual_grading": requires_manual,
        }

    async def manual_grade_answer(
        self,
        answer_id: UUID,
        grader_id: UUID,
        points_earned: Decimal,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manually grade an answer"""
        answer = self.answer_repo.get_by_id(answer_id)
        if not answer:
            raise ResourceNotFoundException("Answer", answer_id)

        # Validate points
        if points_earned < 0 or points_earned > answer.points_possible:
            raise ValidationException(
                f"Points must be between 0 and {answer.points_possible}"
            )

        # Update answer
        answer.points_earned = points_earned
        answer.is_correct = points_earned == answer.points_possible
        answer.is_partially_correct = (
            points_earned > 0 and points_earned < answer.points_possible
        )
        answer.manually_graded = True
        answer.manual_feedback = feedback
        answer.graded_by = grader_id
        answer.graded_at = datetime.utcnow().isoformat()

        self.db.commit()

        # Check if all answers are graded for this attempt
        await self._check_attempt_grading_completion(answer.attempt_id)

        return {
            "answer_id": answer_id,
            "points_earned": float(points_earned),
            "is_correct": answer.is_correct,
            "is_partially_correct": answer.is_partially_correct,
            "graded_at": answer.graded_at,
        }

    async def bulk_grade_answers(
        self, grading_data: List[Dict[str, Any]], grader_id: UUID
    ) -> Dict[str, Any]:
        """Bulk grade multiple answers"""
        results = []

        for item in grading_data:
            try:
                result = await self.manual_grade_answer(
                    answer_id=item["answer_id"],
                    grader_id=grader_id,
                    points_earned=Decimal(str(item["points_earned"])),
                    feedback=item.get("feedback"),
                )
                results.append(
                    {
                        "answer_id": item["answer_id"],
                        "status": "success",
                        "result": result,
                    }
                )
            except Exception as e:
                results.append(
                    {"answer_id": item["answer_id"], "status": "error", "error": str(e)}
                )

        return {
            "total": len(grading_data),
            "success": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "results": results,
        }

    async def get_pending_grading(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get attempts pending manual grading"""
        attempts = self.attempt_repo.get_pending_grading(skip, limit)

        return [
            {
                "attempt_id": attempt.id,
                "assessment_id": attempt.assessment_id,
                "user_id": attempt.user_id,
                "submitted_at": attempt.submitted_at,
                "answers_pending": len(
                    [
                        a
                        for a in attempt.answers
                        if a.requires_manual_grading and not a.manually_graded
                    ]
                ),
            }
            for attempt in attempts
        ]

    async def _grade_answer(self, answer, question) -> Dict[str, Any]:
        """Grade a single answer based on question type"""

        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return self._grade_multiple_choice(answer, question)

        elif question.question_type == QuestionType.TRUE_FALSE:
            return self._grade_true_false(answer, question)

        elif question.question_type == QuestionType.FILL_IN_BLANK:
            return self._grade_fill_in_blank(answer, question)

        elif question.question_type == QuestionType.MATCHING:
            return self._grade_matching(answer, question)

        elif question.question_type == QuestionType.ORDERING:
            return self._grade_ordering(answer, question)

        else:
            # Default: requires manual grading
            return {
                "is_correct": False,
                "is_partially_correct": False,
                "points_earned": Decimal("0.00"),
            }

    def _grade_multiple_choice(self, answer, question) -> Dict[str, Any]:
        """Grade multiple choice question"""
        if not answer.selected_option_ids:
            return {
                "is_correct": False,
                "is_partially_correct": False,
                "points_earned": Decimal("0.00"),
            }

        # Get correct option IDs
        correct_option_ids = {str(opt.id) for opt in question.options if opt.is_correct}

        # Convert selected IDs to strings for comparison
        selected_ids = {str(id) for id in answer.selected_option_ids}

        # Check if answer is correct
        is_correct = selected_ids == correct_option_ids

        # Partial credit for multiple correct answers
        is_partially_correct = False
        points_earned = Decimal("0.00")

        if is_correct:
            points_earned = Decimal(str(question.points))
        elif len(correct_option_ids) > 1:
            # Partial credit calculation
            correct_selected = len(selected_ids & correct_option_ids)
            incorrect_selected = len(selected_ids - correct_option_ids)

            if correct_selected > 0 and correct_selected > incorrect_selected:
                is_partially_correct = True
                points_earned = Decimal(str(question.points)) * (
                    Decimal(correct_selected) / Decimal(len(correct_option_ids))
                )

        return {
            "is_correct": is_correct,
            "is_partially_correct": is_partially_correct,
            "points_earned": points_earned,
        }

    def _grade_true_false(self, answer, question) -> Dict[str, Any]:
        """Grade true/false question"""
        if not answer.selected_option_ids or len(answer.selected_option_ids) == 0:
            return {
                "is_correct": False,
                "is_partially_correct": False,
                "points_earned": Decimal("0.00"),
            }

        selected_id = str(answer.selected_option_ids[0])
        correct_option = next((opt for opt in question.options if opt.is_correct), None)

        is_correct = correct_option and str(correct_option.id) == selected_id

        return {
            "is_correct": is_correct,
            "is_partially_correct": False,
            "points_earned": Decimal(str(question.points))
            if is_correct
            else Decimal("0.00"),
        }

    def _grade_fill_in_blank(self, answer, question) -> Dict[str, Any]:
        """Grade fill in the blank question"""
        if not answer.text_answer:
            return {
                "is_correct": False,
                "is_partially_correct": False,
                "points_earned": Decimal("0.00"),
            }

        # Get correct answers from options
        correct_answers = [
            opt.option_text.strip().lower()
            for opt in question.options
            if opt.is_correct
        ]

        user_answer = answer.text_answer.strip().lower()
        is_correct = user_answer in correct_answers

        return {
            "is_correct": is_correct,
            "is_partially_correct": False,
            "points_earned": Decimal(str(question.points))
            if is_correct
            else Decimal("0.00"),
        }

    def _grade_matching(self, answer, question) -> Dict[str, Any]:
        """Grade matching question"""
        if not answer.matching_pairs:
            return {
                "is_correct": False,
                "is_partially_correct": False,
                "points_earned": Decimal("0.00"),
            }

        # Build correct pairs map
        correct_pairs = {}
        for opt in question.options:
            if opt.match_pair_id:
                correct_pairs[opt.option_text] = opt.match_pair_id

        # Check user's matches
        correct_matches = 0
        total_pairs = len(correct_pairs)

        for key, value in answer.matching_pairs.items():
            if correct_pairs.get(key) == value:
                correct_matches += 1

        # Calculate score
        is_correct = correct_matches == total_pairs
        is_partially_correct = correct_matches > 0 and correct_matches < total_pairs

        points_earned = Decimal("0.00")
        if is_correct:
            points_earned = Decimal(str(question.points))
        elif is_partially_correct:
            points_earned = Decimal(str(question.points)) * (
                Decimal(correct_matches) / Decimal(total_pairs)
            )

        return {
            "is_correct": is_correct,
            "is_partially_correct": is_partially_correct,
            "points_earned": points_earned,
        }

    def _grade_ordering(self, answer, question) -> Dict[str, Any]:
        """Grade ordering question"""
        if not answer.ordered_items:
            return {
                "is_correct": False,
                "is_partially_correct": False,
                "points_earned": Decimal("0.00"),
            }

        # Get correct order
        correct_order = sorted(
            question.options, key=lambda x: x.correct_order if x.correct_order else 999
        )
        correct_sequence = [opt.option_text for opt in correct_order]

        # Check if order matches
        is_correct = answer.ordered_items == correct_sequence

        # Partial credit: count items in correct position
        correct_positions = sum(
            1
            for i, item in enumerate(answer.ordered_items)
            if i < len(correct_sequence) and item == correct_sequence[i]
        )

        is_partially_correct = correct_positions > 0 and correct_positions < len(
            correct_sequence
        )

        points_earned = Decimal("0.00")
        if is_correct:
            points_earned = Decimal(str(question.points))
        elif is_partially_correct:
            points_earned = Decimal(str(question.points)) * (
                Decimal(correct_positions) / Decimal(len(correct_sequence))
            )

        return {
            "is_correct": is_correct,
            "is_partially_correct": is_partially_correct,
            "points_earned": points_earned,
        }

    def _calculate_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage"""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"

    async def _check_attempt_grading_completion(self, attempt_id: UUID) -> None:
        """Check if all answers are graded and update attempt status"""
        answers = self.answer_repo.get_by_attempt(attempt_id)

        all_graded = all(
            not a.requires_manual_grading or a.manually_graded for a in answers
        )

        if all_graded:
            attempt = self.attempt_repo.get_by_id(attempt_id)

            # Recalculate total points
            total_points = sum(float(a.points_earned) for a in answers)

            attempt.points_earned = Decimal(str(total_points))
            attempt.percentage = (
                float(total_points) / float(attempt.points_possible)
            ) * 100
            attempt.score = attempt.percentage

            # Update pass/fail
            assessment = self.assessment_repo.get_by_id(attempt.assessment_id)
            if assessment:
                attempt.passed = attempt.percentage >= float(
                    assessment.passing_percentage
                )
                attempt.grade = self._calculate_grade(attempt.percentage)

            # Update status
            attempt.grading_status = GradingStatus.COMPLETED
            attempt.status = AttemptStatus.GRADED
            attempt.graded_at = datetime.utcnow().isoformat()

            self.db.commit()
