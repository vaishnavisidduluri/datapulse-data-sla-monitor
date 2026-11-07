from datetime import datetime, timezone

from src.scheduling import (
    latest_expected_arrival,
    is_arrival_late
)


def test_daily_schedule():
    schedule = {
        "schedule_type": "daily",
        "timezone": "Asia/Kolkata",
        "expected_time": "09:00",
        "arrival_grace_minutes": 15
    }

    as_of = datetime.fromisoformat(
        "2026-11-07T10:00:00+05:30"
    )

    result = latest_expected_arrival(schedule, as_of)

    assert result == datetime(
        2026, 11, 7, 3, 30, tzinfo=timezone.utc
    )


def test_interval_schedule():
    schedule = {
        "schedule_type": "interval",
        "timezone": "UTC",
        "interval_minutes": 15,
        "schedule_anchor": "2026-11-07T00:00:00+00:00"
    }

    as_of = datetime.fromisoformat(
        "2026-11-07T10:37:00+00:00"
    )

    result = latest_expected_arrival(schedule, as_of)

    assert result == datetime(
        2026, 11, 7, 10, 30, tzinfo=timezone.utc
    )


def test_weekly_schedule():
    schedule = {
        "schedule_type": "weekly",
        "timezone": "Asia/Kolkata",
        "expected_weekday": 0,  # Monday
        "expected_time": "09:00"
    }

    as_of = datetime.fromisoformat(
        "2026-11-09T10:00:00+05:30"
    )

    result = latest_expected_arrival(schedule, as_of)

    assert result == datetime(
        2026, 11, 9, 3, 30, tzinfo=timezone.utc
    )


def test_dataset_is_not_late_before_deadline():
    schedule = {
        "schedule_type": "daily",
        "timezone": "UTC",
        "expected_time": "09:00",
        "arrival_grace_minutes": 15
    }

    expected = datetime.fromisoformat(
        "2026-11-07T09:00:00+00:00"
    )

    as_of = datetime.fromisoformat(
        "2026-11-07T09:10:00+00:00"
    )

    assert is_arrival_late(schedule, expected, as_of) is False


def test_dataset_is_late_after_deadline():
    schedule = {
        "schedule_type": "daily",
        "timezone": "UTC",
        "expected_time": "09:00",
        "arrival_grace_minutes": 15
    }

    expected = datetime.fromisoformat(
        "2026-11-07T09:00:00+00:00"
    )

    as_of = datetime.fromisoformat(
        "2026-11-07T09:16:00+00:00"
    )

    assert is_arrival_late(schedule, expected, as_of) is True