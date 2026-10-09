from datetime import datetime, timezone


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Normalize datetimes from SQLite (naive UTC) for aware comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
