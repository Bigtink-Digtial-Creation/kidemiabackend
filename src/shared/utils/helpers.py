from datetime import datetime
from dateutil.parser import isoparse


def parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return isoparse(value)
    raise TypeError(f"Invalid datetime value: {value!r}")
