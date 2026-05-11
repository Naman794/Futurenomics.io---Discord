from datetime import datetime, timezone

import pytz

from config import TIMEZONE


def get_current_ist() -> datetime:
    return datetime.now(pytz.timezone("Asia/Kolkata"))


def utc_to_ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(pytz.timezone("Asia/Kolkata"))


def format_timestamp(value: datetime | str | None) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    return value.astimezone(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M %Z")
