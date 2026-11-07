
from datetime import datetime, timezone

from src.config import parse_timestamp


def calculate_freshness(
    records,
    timestamp_field,
    threshold_minutes,
    as_of=None
):
    """
    Calculate dataset freshness using the latest event timestamp.
    """

    if threshold_minutes < 0:
        raise ValueError("Freshness threshold cannot be negative.")

    if as_of is None:
        evaluation_time = datetime.now(timezone.utc)
    else:
        evaluation_time = parse_timestamp(as_of)

    evaluation_time = evaluation_time.astimezone(timezone.utc)

    if not records:
        return {
            "status": "NO_DATA",
            "latest_timestamp": None,
            "age_minutes": None,
            "threshold_minutes": threshold_minutes
        }

    timestamps = []

    for record in records:
        value = record.get(timestamp_field)

        if value is None:
            continue

        timestamp = parse_timestamp(value).astimezone(timezone.utc)
        timestamps.append(timestamp)

    if not timestamps:
        return {
            "status": "NO_VALID_TIMESTAMP",
            "latest_timestamp": None,
            "age_minutes": None,
            "threshold_minutes": threshold_minutes
        }

    latest_timestamp = max(timestamps)

    if latest_timestamp > evaluation_time:
        return {
            "status": "FUTURE_TIMESTAMP",
            "latest_timestamp": latest_timestamp.isoformat(),
            "age_minutes": None,
            "threshold_minutes": threshold_minutes
        }

    age_minutes = (
        evaluation_time - latest_timestamp
    ).total_seconds() / 60

    status = (
        "STALE"
        if age_minutes > threshold_minutes
        else "FRESH"
    )

    return {
        "status": status,
        "latest_timestamp": latest_timestamp.isoformat(),
        "age_minutes": round(age_minutes, 2),
        "threshold_minutes": threshold_minutes
    }
