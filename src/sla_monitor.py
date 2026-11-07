
from datetime import datetime, timezone

from src.config import parse_timestamp
from src.scheduling import (
    latest_expected_arrival,
    get_arrival_deadline
)


def evaluate_arrival_sla(schedule, arrivals, as_of=None):
    """
    Check whether the latest expected dataset arrival
    met its configured arrival SLA.

    Each arrival must contain:
        expected_arrival: logical scheduled arrival time
        arrived_at: actual arrival time
    """

    if as_of is None:
        evaluation_time = datetime.now(timezone.utc)
    else:
        evaluation_time = parse_timestamp(as_of)

    evaluation_time = evaluation_time.astimezone(timezone.utc)

    expected = latest_expected_arrival(schedule, evaluation_time)

    if expected is None:
        return {
            "status": "NOT_DUE",
            "expected_arrival": None,
            "deadline": None,
            "arrived_at": None
        }

    deadline = get_arrival_deadline(schedule, expected)

    # Find the arrival belonging to this exact schedule slot.
    matching_arrival = None

    for arrival in arrivals:
        arrival_expected = parse_timestamp(
            arrival["expected_arrival"]
        ).astimezone(timezone.utc)

        if arrival_expected == expected.astimezone(timezone.utc):
            actual_arrival = parse_timestamp(
                arrival["arrived_at"]
            ).astimezone(timezone.utc)

            if (
                matching_arrival is None
                or actual_arrival > matching_arrival
            ):
                matching_arrival = actual_arrival

    if matching_arrival is not None:
        status = (
            "ON_TIME"
            if matching_arrival <= deadline
            else "LATE"
        )
    elif evaluation_time > deadline:
        status = "MISSING"
    else:
        status = "PENDING"

    return {
        "status": status,
        "expected_arrival": expected.isoformat(),
        "deadline": deadline.isoformat(),
        "arrived_at": (
            matching_arrival.isoformat()
            if matching_arrival else None
        )
    }


def evaluate_completion_sla(started_at, completed_at,
                             threshold_minutes, as_of=None):
    """
    Check whether processing completed within its SLA.
    """

    if threshold_minutes < 0:
        raise ValueError("SLA threshold cannot be negative.")

    start = parse_timestamp(started_at).astimezone(timezone.utc)

    if completed_at is not None:
        end = parse_timestamp(completed_at).astimezone(timezone.utc)
    elif as_of is not None:
        end = parse_timestamp(as_of).astimezone(timezone.utc)
    else:
        end = datetime.now(timezone.utc)

    if end < start:
        raise ValueError("Completion time cannot be before start time.")

    duration_minutes = (end - start).total_seconds() / 60

    if completed_at is None:
        status = (
            "BREACHED"
            if duration_minutes > threshold_minutes
            else "IN_PROGRESS"
        )
    else:
        status = (
            "MET"
            if duration_minutes <= threshold_minutes
            else "BREACHED"
        )

    return {
        "status": status,
        "duration_minutes": round(duration_minutes, 2),
        "threshold_minutes": threshold_minutes
    }
