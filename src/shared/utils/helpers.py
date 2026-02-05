from datetime import datetime
from dateutil.parser import isoparse
from decimal import Decimal
from src.domains.auth.models.user import User
from src.config.config_service import ConfigService
from src.config.settings import settings
from src.shared.utils.db import get_sync_db_session


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


def get_client_base_url(client_type) -> str:
    base_url = ""
    with get_sync_db_session() as db:
        base_url = ConfigService.get_value(
            f"{client_type}_domain", settings.FRONTEND_URL, db
        )
    return base_url


def get_full_name(user: dict | object) -> str:
    """
    Returns the full name of a user, including optional middle name.

    user: object or dict with attributes or keys:
        - first_name (required)
        - middle_name (optional)
        - last_name (required)
    """
    # Access attributes if object, keys if dict
    first = getattr(user, "first_name", None) or user.get("first_name", "")
    middle = getattr(user, "middle_name", None) or user.get("middle_name", "")
    last = getattr(user, "last_name", None) or user.get("last_name", "")

    # Join non-empty parts with a space
    return " ".join(part for part in [first, middle, last] if part).strip()
