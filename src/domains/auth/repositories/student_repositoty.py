from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from src.shared.repositories.base import BaseRepository
from src.domains.auth.models.student import Student
from src.domains.guardian.models.guardian import Guardian
from src.domains.assessment.models.category import AssessmentCategoryConfig
from sqlalchemy.orm import joinedload
from src.domains.auth.models.user import User
from sqlalchemy import and_, or_


class StudentRepository(BaseRepository[Student, dict, dict]):
    """Repository for Student model"""

    def __init__(self, db: Session):
        super().__init__(Student, db)

    # --------------------
    # Getters
    # --------------------

    def get_by_user_id(self, user_id: UUID) -> Optional[Student]:
        """Get student by linked user ID"""
        return self.db.query(Student).filter(Student.user_id == user_id).first()

    def get_by_student_code(self, student_code: str) -> Optional[Student]:
        """Get student by unique student code"""
        return (
            self.db.query(Student).filter(Student.student_code == student_code).first()
        )

    def get_by_guardian_email(self, email: str) -> List[Student]:
        """Get students by guardian email"""
        return self.db.query(Student).filter(Student.guardian_email == email).all()

    def get_active_students(self) -> List[Student]:
        """Get all active students"""
        return (
            self.db.query(Student)
            .filter(Student.is_active.is_(True))
            .filter(Student.is_suspended.is_(False))
            .all()
        )

    def get_suspended_students(self) -> List[Student]:
        """Get all suspended students"""
        return self.db.query(Student).filter(Student.is_suspended.is_(True)).all()

    # --------------------
    # State management
    # --------------------

    def suspend(self, student_id: UUID) -> Optional[Student]:
        """Suspend a student"""
        student = self.get_by_id(student_id)
        if not student:
            return None

        student.is_suspended = True
        self.db.commit()
        self.db.refresh(student)
        return student

    def activate(self, student_id: UUID) -> Optional[Student]:
        """Activate a student"""
        student = self.get_by_id(student_id)
        if not student:
            return None

        student.is_suspended = False
        student.is_active = True
        self.db.commit()
        self.db.refresh(student)
        return student

    def deactivate(self, student_id: UUID) -> Optional[Student]:
        """Deactivate a student"""
        student = self.get_by_id(student_id)
        if not student:
            return None

        student.is_active = False
        self.db.commit()
        self.db.refresh(student)
        return student

    # --------------------
    # Relationships
    # --------------------

    def assign_category(self, student_id: UUID, category_id: UUID) -> Optional[Student]:
        """Assign assessment category to student"""
        student = self.get_by_id(student_id)
        if not student:
            return None

        category = (
            self.db.query(AssessmentCategoryConfig)
            .filter(AssessmentCategoryConfig.id == category_id)
            .first()
        )

        student.category = category
        self.db.commit()
        self.db.refresh(student)
        return student

    def assign_guardian(self, student_id: UUID, guardian_id: UUID) -> Optional[Student]:
        """Assign guardian to student"""
        student = self.get_by_id(student_id)
        if not student:
            return None

        guardian = self.db.query(Guardian).filter(Guardian.id == guardian_id).first()

        student.guardian = guardian
        student.guardian_email = guardian.email if guardian else None

        self.db.commit()
        self.db.refresh(student)
        return student

    # --------------------
    # Bulk / Utility
    # --------------------

    def update_guardian_email(self, old_email: str, new_email: str) -> int:
        """
        Update guardian email for all matching students.
        Returns number of affected rows.
        """
        rows = (
            self.db.query(Student)
            .filter(Student.guardian_email == old_email)
            .update(
                {Student.guardian_email: new_email},
                synchronize_session=False,
            )
        )
        self.db.commit()
        return rows

    def update_target_exam(
        self,
        student_id: UUID,
        exam_date: Optional[datetime],
        preparation_level: Optional[str] = None,
    ) -> Optional[Student]:
        """Update target exam info"""
        student = self.get_by_id(student_id)
        if not student:
            return None

        student.target_exam_date = exam_date
        if preparation_level is not None:
            student.preparation_level = preparation_level

        self.db.commit()
        self.db.refresh(student)
        return student

    def get_with_user(self, student_id: UUID) -> Optional[Student]:
        """Get student with user details"""
        return (
            self.db.query(Student)
            .options(joinedload(Student.user))
            .filter(Student.id == student_id, Student.is_deleted.is_(False))
            .first()
        )

    def get_by_guardian_id(self, guardian_id: UUID) -> List[Student]:
        """Get all students for a guardian"""
        return (
            self.db.query(Student)
            .filter(Student.guardian_id == guardian_id, Student.is_deleted.is_(False))
            .all()
        )

    def get_by_category(self, category_id: UUID) -> List[Student]:
        """Get all students in a category"""
        return (
            self.db.query(Student)
            .filter(Student.category_id == category_id, Student.is_deleted.is_(False))
            .all()
        )

    def search_students(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> List[Student]:
        """Search students by name, email, or code"""
        return (
            self.db.query(Student)
            .join(User, Student.user_id == User.id)
            .filter(
                and_(
                    Student.is_deleted.is_(False),
                    or_(
                        Student.student_code.ilike(f"%{search_term}%"),
                        User.full_name.ilike(f"%{search_term}%"),
                        User.email.ilike(f"%{search_term}%"),
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def code_exists(self, student_code: str) -> bool:
        """Check if student code exists"""
        return self.db.query(
            self.db.query(Student)
            .filter(Student.student_code == student_code, Student.is_deleted.is_(False))
            .exists()
        ).scalar()

    def suspend_student(self, student_id: UUID) -> bool:
        """Suspend a student"""
        student = self.get_by_id(student_id)
        if student:
            student.is_suspended = True
            self.db.commit()
            return True
        return False

    def reactivate_student(self, student_id: UUID) -> bool:
        """Reactivate a suspended student"""
        student = self.get_by_id(student_id)
        if student:
            student.is_suspended = False
            self.db.commit()
            return True
        return False
