
from src.freshness import calculate_freshness


def test_fresh_dataset():
    records = [
        {"id": 1, "updated_at": "2026-11-07T09:45:00+00:00"}
    ]

    result = calculate_freshness(
        records,
        "updated_at",
        30,
        "2026-11-07T10:00:00+00:00"
    )

    assert result["status"] == "FRESH"
    assert result["age_minutes"] == 15


def test_stale_dataset():
    records = [
        {"id": 1, "updated_at": "2026-11-07T09:00:00+00:00"}
    ]

    result = calculate_freshness(
        records,
        "updated_at",
        30,
        "2026-11-07T10:00:00+00:00"
    )

    assert result["status"] == "STALE"
    assert result["age_minutes"] == 60


def test_latest_timestamp_is_used():
    records = [
        {"id": 1, "updated_at": "2026-11-07T08:00:00+00:00"},
        {"id": 2, "updated_at": "2026-11-07T09:50:00+00:00"},
        {"id": 3, "updated_at": "2026-11-07T09:00:00+00:00"}
    ]

    result = calculate_freshness(
        records,
        "updated_at",
        30,
        "2026-11-07T10:00:00+00:00"
    )

    assert result["age_minutes"] == 10
    assert result["status"] == "FRESH"


def test_empty_dataset():
    result = calculate_freshness(
        [],
        "updated_at",
        30,
        "2026-11-07T10:00:00+00:00"
    )

    assert result["status"] == "NO_DATA"


def test_future_timestamp():
    records = [
        {"id": 1, "updated_at": "2026-11-07T11:00:00+00:00"}
    ]

    result = calculate_freshness(
        records,
        "updated_at",
        30,
        "2026-11-07T10:00:00+00:00"
    )

    assert result["status"] == "FUTURE_TIMESTAMP"


def test_timezone_aware_freshness():
    records = [
        {"id": 1, "updated_at": "2026-11-07T09:00:00+05:30"}
    ]

    result = calculate_freshness(
        records,
        "updated_at",
        30,
        "2026-11-07T04:00:00+00:00"
    )

    assert result["age_minutes"] == 30
    assert result["status"] == "FRESH"
