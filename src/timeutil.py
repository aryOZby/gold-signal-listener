from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def month_key(dt: datetime, tz: ZoneInfo) -> str:
    local = as_utc(dt)
    if local is None:
        local = utcnow()
    return local.astimezone(tz).strftime("%Y-%m")


def display_date(dt: datetime, tz: ZoneInfo) -> str:
    local = as_utc(dt)
    if local is None:
        return ""
    return local.astimezone(tz).strftime("%Y-%m-%d")


def display_time(dt: datetime, tz: ZoneInfo) -> str:
    local = as_utc(dt)
    if local is None:
        return ""
    return local.astimezone(tz).strftime("%H:%M:%S")
