
from src.sla_monitor import (
    evaluate_arrival_sla,
    evaluate_completion_sla
)


def daily_schedule():
    return {
        "schedule_type": "daily",
        "timezone": "UTC",
        "expected_time": "09:00",
        "arrival_grace_minutes": 15
    }


def test_arrival_on_time():
    schedule = daily_schedule()

    arrivals = [{
        "expected_arrival": "2026-11-07T09:00:00+00:00",
        "arrived_at": "2026-11-07T09:10:00+00:00"
    }]

    result = evaluate_arrival_sla(
        schedule, arrivals, "2026-11-07T10:00:00+00:00"
    )

    assert result["status"] == "ON_TIME"


def test_arrival_late():
    schedule = daily_schedule()

    arrivals = [{
        "expected_arrival": "2026-11-07T09:00:00+00:00",
        "arrived_at": "2026-11-07T09:30:00+00:00"
    }]

    result = evaluate_arrival_sla(
        schedule, arrivals, "2026-11-07T10:00:00+00:00"
    )

    assert result["status"] == "LATE"


def test_missing_arrival():
    result = evaluate_arrival_sla(
        daily_schedule(),
        [],
        "2026-11-07T09:16:00+00:00"
    )

    assert result["status"] == "MISSING"


def test_arrival_still_pending():
    result = evaluate_arrival_sla(
        daily_schedule(),
        [],
        "2026-11-07T09:10:00+00:00"
    )

    assert result["status"] == "PENDING"


def test_old_arrival_does_not_satisfy_latest_schedule():
    schedule = daily_schedule()

    arrivals = [{
        "expected_arrival": "2026-11-06T09:00:00+00:00",
        "arrived_at": "2026-11-07T09:30:00+00:00"
    }]

    result = evaluate_arrival_sla(
        schedule, arrivals, "2026-11-07T10:00:00+00:00"
    )

    assert result["status"] == "MISSING"


def test_completion_sla_met():
    result = evaluate_completion_sla(
        "2026-11-07T09:00:00+00:00",
        "2026-11-07T09:30:00+00:00",
        60
    )

    assert result["status"] == "MET"
    assert result["duration_minutes"] == 30


def test_completion_sla_breached():
    result = evaluate_completion_sla(
        "2026-11-07T09:00:00+00:00",
        "2026-11-07T10:30:00+00:00",
        60
    )

    assert result["status"] == "BREACHED"


def test_completion_still_in_progress():
    result = evaluate_completion_sla(
        "2026-11-07T09:00:00+00:00",
        None,
        60,
        "2026-11-07T09:30:00+00:00"
    )

    assert result["status"] == "IN_PROGRESS"
