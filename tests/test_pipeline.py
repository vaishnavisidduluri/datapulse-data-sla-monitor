
import csv
import pytest
from datetime import datetime, timedelta, timezone

from src.database import (
    initialize_database,
    upsert_dataset_config,
    get_connection
)
from src.pipeline import run_pipeline


def setup_pipeline_test(tmp_path, as_of=None):
    db_path = tmp_path / "pipeline_test.db"
    initialize_database(db_path)

    if as_of is None:
        as_of = datetime.now(timezone.utc)

    schedule = {
        "dataset_name": "customers",
        "schedule_type": "interval",
        "timezone": "UTC",
        "interval_minutes": 60,
        "schedule_anchor": (
            as_of - timedelta(minutes=5)
        ).isoformat(),
        "arrival_grace_minutes": 15,
        "completion_sla_minutes": 60,
        "freshness_threshold_minutes": 120
    }

    upsert_dataset_config(schedule, db_path)

    return db_path, as_of


def create_csv(
    tmp_path,
    records,
    fieldnames=None,
    filename="customers.csv"
):
    file_path = tmp_path / filename

    if fieldnames is None:
        fieldnames = ["id", "name", "event_time"]

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    return file_path


def test_pipeline_success(tmp_path):
    db_path, as_of = setup_pipeline_test(tmp_path)

    event_time = (
        as_of - timedelta(minutes=1)
    ).isoformat()

    file_path = create_csv(tmp_path, [
        {"id": "1", "name": " Alice ", "event_time": event_time},
        {"id": "2", "name": " Bob ", "event_time": event_time}
    ])

    result = run_pipeline(
        dataset_name="customers",
        file_path=file_path,
        required_fields=["id", "name", "event_time"],
        primary_key="id",
        timestamp_field="event_time",
        timestamp_fields=["event_time"],
        as_of=as_of,
        db_path=db_path
    )

    assert result["status"] == "SUCCESS"
    assert result["input_count"] == 2
    assert result["valid_count"] == 2
    assert result["rejected_count"] == 0
    assert result["stored_count"] == 2

    connection = get_connection(db_path)

    stored_count = connection.execute(
        "SELECT COUNT(*) FROM processed_records"
    ).fetchone()[0]

    run_count = connection.execute(
        "SELECT COUNT(*) FROM dataset_runs"
    ).fetchone()[0]

    connection.close()

    assert stored_count == 2
    assert run_count == 1


def test_pipeline_handles_rejected_records(tmp_path):
    db_path, as_of = setup_pipeline_test(tmp_path)

    event_time = (
        as_of - timedelta(minutes=1)
    ).isoformat()

    file_path = create_csv(tmp_path, [
        {"id": "1", "name": "Alice", "event_time": event_time},
        {"id": "1", "name": "Duplicate Alice", "event_time": event_time}
    ])

    result = run_pipeline(
        dataset_name="customers",
        file_path=file_path,
        required_fields=["id", "name", "event_time"],
        primary_key="id",
        timestamp_field="event_time",
        timestamp_fields=["event_time"],
        as_of=as_of,
        db_path=db_path
    )

    assert result["status"] == "PARTIAL"
    assert result["input_count"] == 2
    assert result["valid_count"] == 1
    assert result["rejected_count"] == 1

    connection = get_connection(db_path)

    rejected_count = connection.execute(
        "SELECT COUNT(*) FROM rejected_records"
    ).fetchone()[0]

    connection.close()

    assert rejected_count == 1


def test_pipeline_handles_empty_csv(tmp_path):
    db_path, as_of = setup_pipeline_test(tmp_path)

    file_path = create_csv(tmp_path, [])

    result = run_pipeline(
        dataset_name="customers",
        file_path=file_path,
        required_fields=["id", "name", "event_time"],
        primary_key="id",
        timestamp_field="event_time",
        timestamp_fields=["event_time"],
        as_of=as_of,
        db_path=db_path
    )

    assert result["input_count"] == 0
    assert result["valid_count"] == 0
    assert result["rejected_count"] == 0
    assert result["stored_count"] == 0


def test_pipeline_rejects_missing_file(tmp_path):
    db_path, as_of = setup_pipeline_test(tmp_path)

    missing_file = tmp_path / "missing_customers.csv"

    with pytest.raises(FileNotFoundError):
        run_pipeline(
            dataset_name="customers",
            file_path=missing_file,
            required_fields=["id", "name", "event_time"],
            primary_key="id",
            timestamp_field="event_time",
            timestamp_fields=["event_time"],
            as_of=as_of,
            db_path=db_path
        )


def test_pipeline_supports_multiple_datasets(tmp_path):
    db_path, as_of = setup_pipeline_test(tmp_path)

    order_schedule = {
        "dataset_name": "orders",
        "schedule_type": "interval",
        "timezone": "UTC",
        "interval_minutes": 30,
        "schedule_anchor": (
            as_of - timedelta(minutes=5)
        ).isoformat(),
        "arrival_grace_minutes": 15,
        "completion_sla_minutes": 60,
        "freshness_threshold_minutes": 180
    }

    upsert_dataset_config(order_schedule, db_path)

    event_time = (
        as_of - timedelta(minutes=1)
    ).isoformat()

    customer_file = create_csv(
        tmp_path,
        [
            {
                "id": "C001",
                "name": "Alice",
                "event_time": event_time
            }
        ],
        filename="customers.csv"
    )

    order_file = create_csv(
        tmp_path,
        [
            {
                "order_id": "O001",
                "customer_id": "C001",
                "amount": "1500.00",
                "event_time": event_time
            }
        ],
        fieldnames=[
            "order_id",
            "customer_id",
            "amount",
            "event_time"
        ],
        filename="orders.csv"
    )

    customer_result = run_pipeline(
        dataset_name="customers",
        file_path=customer_file,
        required_fields=["id", "name", "event_time"],
        primary_key="id",
        timestamp_field="event_time",
        timestamp_fields=["event_time"],
        as_of=as_of,
        db_path=db_path
    )

    order_result = run_pipeline(
        dataset_name="orders",
        file_path=order_file,
        required_fields=[
            "order_id",
            "customer_id",
            "amount",
            "event_time"
        ],
        primary_key="order_id",
        timestamp_field="event_time",
        timestamp_fields=["event_time"],
        as_of=as_of,
        db_path=db_path
    )

    assert customer_result["status"] == "SUCCESS"
    assert order_result["status"] == "SUCCESS"

    connection = get_connection(db_path)

    dataset_counts = dict(
        connection.execute(
            """
            SELECT dataset_name, COUNT(*)
            FROM processed_records
            GROUP BY dataset_name
            """
        ).fetchall()
    )

    connection.close()

    assert dataset_counts == {
        "customers": 1,
        "orders": 1
    }


def test_pipeline_supports_historical_backfill(tmp_path):
    historical_as_of = datetime(
        2025, 1, 15, 12, 0, tzinfo=timezone.utc
    )

    db_path, as_of = setup_pipeline_test(
        tmp_path,
        historical_as_of
    )

    event_time = (
        as_of - timedelta(minutes=1)
    ).isoformat()

    file_path = create_csv(tmp_path, [
        {
            "id": "BACKFILL001",
            "name": "Historical Customer",
            "event_time": event_time
        }
    ])

    result = run_pipeline(
        dataset_name="customers",
        file_path=file_path,
        required_fields=["id", "name", "event_time"],
        primary_key="id",
        timestamp_field="event_time",
        timestamp_fields=["event_time"],
        as_of=historical_as_of,
        db_path=db_path
    )

    expected_arrival = (
        historical_as_of - timedelta(minutes=5)
    ).isoformat()

    assert result["status"] == "SUCCESS"
    assert result["input_count"] == 1
    assert result["valid_count"] == 1
    assert result["rejected_count"] == 0
    assert result["stored_count"] == 1
    assert result["expected_arrival"] == expected_arrival

    connection = get_connection(db_path)

    stored_record = connection.execute(
        """
        SELECT record_id
        FROM processed_records
        WHERE dataset_name = ?
        """,
        ("customers",)
    ).fetchone()

    connection.close()

    assert stored_record[0] == "BACKFILL001"
