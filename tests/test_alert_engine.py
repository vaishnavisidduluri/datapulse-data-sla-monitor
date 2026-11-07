
import pytest

from src.alert_engine import generate_alerts, save_alerts
from src.database import (
    initialize_database,
    upsert_dataset_config,
    get_connection
)


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary database for testing."""

    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    upsert_dataset_config({
        "dataset_name": "customers",
        "schedule_type": "daily",
        "timezone": "UTC",
        "expected_time": "09:00"
    }, db_path)

    upsert_dataset_config({
        "dataset_name": "orders",
        "schedule_type": "daily",
        "timezone": "UTC",
        "expected_time": "10:00"
    }, db_path)

    return db_path


# --------------------------------------------------
# ALERT GENERATION TESTS
# --------------------------------------------------

def test_missing_arrival_generates_critical_alert():
    alerts = generate_alerts(
        "customers",
        arrival_result={"status": "MISSING"}
    )

    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"
    assert alerts[0]["alert_type"] == "MISSING_ARRIVAL"


def test_late_arrival_generates_warning():
    alerts = generate_alerts(
        "customers",
        arrival_result={"status": "LATE"}
    )

    assert alerts[0]["severity"] == "WARNING"
    assert alerts[0]["alert_type"] == "LATE_ARRIVAL"


def test_completion_sla_breach_generates_alert():
    alerts = generate_alerts(
        "customers",
        completion_result={"status": "BREACHED"}
    )

    assert alerts[0]["alert_type"] == "COMPLETION_SLA_BREACH"
    assert alerts[0]["severity"] == "CRITICAL"


def test_stale_data_generates_alert():
    alerts = generate_alerts(
        "customers",
        freshness_result={"status": "STALE"}
    )

    assert alerts[0]["alert_type"] == "STALE_DATA"


def test_no_data_generates_critical_alert():
    alerts = generate_alerts(
        "customers",
        freshness_result={"status": "NO_DATA"}
    )

    assert alerts[0]["severity"] == "CRITICAL"


def test_healthy_dataset_generates_no_alerts():
    alerts = generate_alerts(
        "customers",
        arrival_result={"status": "ON_TIME"},
        completion_result={"status": "MET"},
        freshness_result={"status": "FRESH"}
    )

    assert alerts == []


def test_multiple_issues_generate_multiple_alerts():
    alerts = generate_alerts(
        "orders",
        arrival_result={"status": "MISSING"},
        completion_result={"status": "BREACHED"},
        freshness_result={"status": "STALE"}
    )

    assert len(alerts) == 3
    assert {alert["severity"] for alert in alerts} == {
        "CRITICAL", "WARNING"
    }


def test_alert_contains_recommended_action():
    alerts = generate_alerts(
        "customers",
        arrival_result={"status": "MISSING"}
    )

    assert alerts[0]["recommended_action"]
    assert alerts[0]["dataset_name"] == "customers"


# --------------------------------------------------
# ALERT DATABASE STORAGE TESTS
# --------------------------------------------------

def test_save_alert_to_database(test_db):
    alerts = generate_alerts(
        "customers",
        arrival_result={"status": "MISSING"}
    )

    count = save_alerts(
        alerts,
        expected_arrival_at="2026-11-07T09:00:00+00:00",
        db_path=test_db
    )

    assert count == 1

    connection = get_connection(test_db)

    saved_alert = connection.execute(
        "SELECT * FROM alerts"
    ).fetchone()

    connection.close()

    assert saved_alert is not None
    assert saved_alert["dataset_name"] == "customers"
    assert saved_alert["alert_type"] == "MISSING_ARRIVAL"
    assert saved_alert["severity"] == "CRITICAL"
    assert saved_alert["status"] == "OPEN"


def test_duplicate_alert_is_not_saved(test_db):
    alerts = generate_alerts(
        "customers",
        arrival_result={"status": "MISSING"}
    )

    expected = "2026-11-07T09:00:00+00:00"

    first_count = save_alerts(
        alerts,
        expected_arrival_at=expected,
        db_path=test_db
    )

    second_count = save_alerts(
        alerts,
        expected_arrival_at=expected,
        db_path=test_db
    )

    assert first_count == 1
    assert second_count == 0

    connection = get_connection(test_db)

    total = connection.execute(
        "SELECT COUNT(*) FROM alerts"
    ).fetchone()[0]

    connection.close()

    assert total == 1


def test_different_expected_arrivals_create_separate_alerts(test_db):
    alerts = generate_alerts(
        "customers",
        arrival_result={"status": "MISSING"}
    )

    first_count = save_alerts(
        alerts,
        expected_arrival_at="2026-11-07T09:00:00+00:00",
        db_path=test_db
    )

    second_count = save_alerts(
        alerts,
        expected_arrival_at="2026-11-08T09:00:00+00:00",
        db_path=test_db
    )

    assert first_count == 1
    assert second_count == 1


def test_empty_alert_list_saves_nothing(test_db):
    count = save_alerts([], db_path=test_db)

    assert count == 0


def test_alert_for_unknown_dataset_fails(test_db):
    alerts = generate_alerts(
        "unknown_dataset",
        arrival_result={"status": "MISSING"}
    )

    with pytest.raises(Exception):
        save_alerts(
            alerts,
            expected_arrival_at="2026-11-07T09:00:00+00:00",
            db_path=test_db
        )
