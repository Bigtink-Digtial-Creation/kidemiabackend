from datetime import datetime
from dateutil.parser import isoparse
from decimal import Decimal


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
