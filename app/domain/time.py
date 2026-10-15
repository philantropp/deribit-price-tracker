import time
from datetime import UTC, datetime


def current_unix_timestamp() -> int:
    return int(time.time())


def to_unix_timestamp(moment: datetime) -> int:
    """Convert a datetime to UNIX seconds; naive datetimes are treated as UTC."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp())
