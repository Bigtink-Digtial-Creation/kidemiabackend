from enum import Enum


class AppEvent(str, Enum):
    ASSESSMENT_COMPLETED = "assessment.completed"
    ASSESSMENT_RESULT = "assessment.result"

    WARD_ADD = "ward.add"
    WARD_REMOVE = "ward.remove"

    CATEGORY_CHANGE = "category.change"
    CATEGORY_APPROVED = "category.approved"

    CHALLENGE_ASSIGNED = "challenge.assigned"
    CHALLENGE_COMPLETED = "challenge.completed"

    USER_REGISTERED = "auth.user_registered"
    SECURITY_ALERT = "auth.security_alert"
    EMAIL_VERIFICATION = "auth.email_verification"

    INSTITUTION_WELCOME_EMAIL = "institution_welcome_email"
    ASSIGNED_INSTITUTION_ADMIN_ROLE = "assigned_role_institution_admin"

    ASSIGNED_ROLE_USER = "assigned_role_user"
    TEACHER_INVITATION = "teacher_invitation"
