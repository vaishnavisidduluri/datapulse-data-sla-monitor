from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

from src.config import parse_timestamp


def validate_schedule(schedule):
    """Validate a dataset's schedule configuration."""

    schedule_type = schedule["schedule_type"]

    if schedule_type not in ("interval", "daily", "weekly"):
        raise ValueError("Unsupported schedule type.")

    ZoneInfo(schedule["timezone"])

    if schedule_type == "interval":
        if not schedule.get("interval_minutes") or schedule["interval_minutes"] <= 0:
            raise ValueError("Interval must be greater than zero.")

        if not schedule.get("schedule_anchor"):
            raise ValueError("Interval schedule requires schedule_anchor.")

        parse_timestamp(schedule["schedule_anchor"])

    elif schedule_type == "daily":
        time.fromisoformat(schedule["expected_time"])

    elif schedule_type == "weekly":
        time.fromisoformat(schedule["expected_time"])

        weekday = schedule.get("expected_weekday")
        if weekday is None or not 0 <= weekday <= 6:
            raise ValueError("Weekday must be between 0 and 6.")


def latest_expected_arrival(schedule, as_of=None):
    """
    Find the most recent scheduled arrival at or before as_of.

    as_of is injectable so tests can use fixed timestamps.
    The returned timestamp is always UTC.
    """

    validate_schedule(schedule)

    if as_of is None:
        as_of = datetime.now(timezone.utc)
    else:
        as_of = parse_timestamp(as_of)

    local_timezone = ZoneInfo(schedule["timezone"])
    local_now = as_of.astimezone(local_timezone)

    schedule_type = schedule["schedule_type"]

    # Every N minutes
    if schedule_type == "interval":
        anchor = parse_timestamp(
            schedule["schedule_anchor"]
        ).astimezone(timezone.utc)

        now_utc = as_of.astimezone(timezone.utc)

        if now_utc < anchor:
            return None

        interval = timedelta(
            minutes=schedule["interval_minutes"]
        )

        elapsed = now_utc - anchor
        completed_intervals = elapsed // interval

        expected = anchor + completed_intervals * interval

        return expected

    expected_time = time.fromisoformat(
        schedule["expected_time"]
    )

    # Daily schedule
    if schedule_type == "daily":
        expected_local = datetime.combine(
            local_now.date(),
            expected_time,
            tzinfo=local_timezone
        )

        if expected_local > local_now:
            expected_local -= timedelta(days=1)

        return expected_local.astimezone(timezone.utc)

    # Weekly schedule
    if schedule_type == "weekly":
        expected_weekday = schedule["expected_weekday"]

        days_since_expected = (
            local_now.weekday() - expected_weekday
        ) % 7

        expected_date = (
            local_now.date() - timedelta(days=days_since_expected)
        )

        expected_local = datetime.combine(
            expected_date,
            expected_time,
            tzinfo=local_timezone
        )

        if expected_local > local_now:
            expected_local -= timedelta(days=7)

        return expected_local.astimezone(timezone.utc)


def get_arrival_deadline(schedule, expected_arrival):
    """Calculate the arrival deadline using the grace period."""

    return expected_arrival + timedelta(
        minutes=schedule.get("arrival_grace_minutes", 0)
    )


def is_arrival_late(schedule, expected_arrival, as_of=None):
    """
    Check whether an expected arrival has passed its deadline.

    Returns True only when the current time is strictly
    later than the deadline.
    """

    if as_of is None:
        as_of = datetime.now(timezone.utc)
    else:
        as_of = parse_timestamp(as_of)

    deadline = get_arrival_deadline(
        schedule,
        expected_arrival
    )

    return as_of.astimezone(timezone.utc) > deadline.astimezone(timezone.utc)