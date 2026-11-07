
import csv
from datetime import datetime, timedelta, timezone

from src.database import (
    initialize_database,
    upsert_dataset_config,
    get_connection
)
from src.pipeline import run_pipeline


def setup_pipeline_test(tmp_path):
    db_path = tmp_path / "pipeline_test.db"
    initialize_database(db_path)

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


def create_csv(tmp_path, records):
    file_path = tmp_path / "customers.csv"

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["id", "name", "event_time"]
        )
        writer.writeheader()
        writer.writerows(records)

    return file_path


def test_pipeline_success(tmp_path):
    db_path, as_of = setup_pipeline_test(tmp_path)

    event_time = (
        as_of - timedelta(minutes=1)
    ).isoformat()

    file_path = create_csv(tmp_path, [
        {
            "id": "1",
            "name": " Alice ",
            "event_time": event_time
        },
        {
            "id": "2",
            "name": " Bob ",
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
        {
            "id": "1",
            "name": "Alice",
            "event_time": event_time
        },
        {
            "id": "1",
            "name": "Duplicate Alice",
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
