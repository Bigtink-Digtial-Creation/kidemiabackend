from uuid import UUID
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from src.shared.repositories.base import BaseRepository
from src.domains.guardian.models.guardian import Guardian
from src.domains.auth.models.student import Student
from src.domains.auth.models.user import User


class GuardianRepository(BaseRepository[Guardian, dict, dict]):
    """Repository for Guardian operations"""

    def __init__(self, db: Session):
        super().__init__(Guardian, db)

    def get_by_user_id(self, user_id: UUID) -> Optional[Guardian]:
        """Get guardian by user ID"""
        return (
            self.db.query(Guardian)
            .filter(Guardian.user_id == user_id, Guardian.is_deleted.is_(False))
            .first()
        )

    def get_by_code(self, guardian_code: str) -> Optional[Guardian]:
        """Get guardian by guardian code"""
        return (
            self.db.query(Guardian)
            .filter(
                Guardian.guardian_code == guardian_code, Guardian.is_deleted.is_(False)
            )
            .first()
        )

    def get_with_user(self, guardian_id: UUID) -> Optional[Guardian]:
        """Get guardian with user details"""
        return (
            self.db.query(Guardian)
            .options(joinedload(Guardian.user))
            .filter(Guardian.id == guardian_id, Guardian.is_deleted.is_(False))
            .first()
        )

    def get_with_wards(self, guardian_id: UUID) -> Optional[Guardian]:
        """Get guardian with all wards"""
        return (
            self.db.query(Guardian)
            .options(
                joinedload(Guardian.students).joinedload(Student.user),
                joinedload(Guardian.students).joinedload(Student.category),
            )
            .filter(Guardian.id == guardian_id, Guardian.is_deleted.is_(False))
            .first()
        )

    def get_active_wards(self, guardian_id: UUID) -> List[Student]:
        """Get all active wards for a guardian"""
        return (
            self.db.query(Student)
            .filter(
                Student.guardian_id == guardian_id,
                Student.is_active.is_(True),
                Student.is_deleted.is_(False),
            )
            .all()
        )

    def code_exists(self, guardian_code: str) -> bool:
        """Check if guardian code exists"""
        return self.db.query(
            self.db.query(Guardian)
            .filter(
                Guardian.guardian_code == guardian_code, Guardian.is_deleted.is_(False)
            )
            .exists()
        ).scalar()

    def get_ward_count(self, guardian_id: UUID, active_only: bool = False) -> int:
        """Get count of wards for a guardian"""
        query = self.db.query(func.count(Student.id)).filter(
            Student.guardian_id == guardian_id, Student.is_deleted.is_(False)
        )

        if active_only:
            query = query.filter(Student.is_active.is_(True))

        return query.scalar() or 0

    def search_guardians(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> List[Guardian]:
        """Search guardians by name, email, or code"""
        return (
            self.db.query(Guardian)
            .join(User, Guardian.user_id == User.id)
            .filter(
                and_(
                    Guardian.is_deleted.is_(False),
                    or_(
                        Guardian.guardian_code.ilike(f"%{search_term}%"),
                        User.full_name.ilike(f"%{search_term}%"),
                        User.email.ilike(f"%{search_term}%"),
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_guardians_by_subscription(self, subscription_id: UUID) -> List[Guardian]:
        """Get all guardians with a specific subscription"""
        # This would join with subscription_members table
        # Implementation depends on your subscription structure
        pass

    def verify_guardian(self, guardian_id: UUID) -> bool:
        """Mark guardian as verified"""
        guardian = self.get_by_id(guardian_id)
        if guardian:
            guardian.is_verified = True
            self.db.commit()
            return True
        return False

    def deactivate_guardian(self, guardian_id: UUID) -> bool:
        """Deactivate a guardian account"""
        guardian = self.get_by_id(guardian_id)
        if guardian:
            guardian.is_active = False
            self.db.commit()
            return True
        return False
