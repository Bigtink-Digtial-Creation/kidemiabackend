from datetime import datetime
from dateutil.parser import isoparse
from decimal import Decimal
from src.domains.auth.models.user import User


def parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return isoparse(value)
    raise TypeError(f"Invalid datetime value: {value!r}")


def make_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [make_json_safe(v) for v in value]
    return value


def determine_client_type(user: User) -> str:
    u_type = str(
        user.user_type.value if hasattr(user.user_type, "value") else user.user_type
    ).lower()

    user_portal_types = ["student", "guardian"]

    if u_type in user_portal_types:
        return "user"

    return "admin"
