
import csv
from datetime import datetime, timedelta, timezone

from src.config import RAW_DIR, timestamp_to_string
from src.database import (
    initialize_database,
    get_dataset_config,
    upsert_dataset_config
)
from src.pipeline import run_pipeline


def create_sample_data():
    """Generate sample customer records with current timestamps."""

    file_path = RAW_DIR / "customers.csv"

    now = datetime.now(timezone.utc)

    records = [
        {
            "id": "C001",
            "name": "Alice",
            "event_time": timestamp_to_string(now)
        },
        {
            "id": "C002",
            "name": "Bob",
            "event_time": timestamp_to_string(
                now - timedelta(minutes=2)
            )
        },
        {
            "id": "C003",
            "name": "Charlie",
            "event_time": timestamp_to_string(
                now - timedelta(minutes=5)
            )
        },
        {
            "id": "C004",
            "name": "David",
            "event_time": timestamp_to_string(
                now - timedelta(minutes=10)
            )
        }
    ]

    with open(
        file_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=["id", "name", "event_time"]
        )

        writer.writeheader()
        writer.writerows(records)

    return file_path


def main():

    print("\n========== DATAPULSE ==========")

    # 1. Initialize database
    initialize_database()

    # 2. Register dataset configuration if needed
    schedule = get_dataset_config("customers")

    if schedule is None:

        schedule = {
            "dataset_name": "customers",
            "schedule_type": "interval",
            "timezone": "UTC",
            "interval_minutes": 15,
            "schedule_anchor": timestamp_to_string(
                datetime.now(timezone.utc) - timedelta(minutes=5)
            ),
            "arrival_grace_minutes": 15,
            "completion_sla_minutes": 60,
            "freshness_threshold_minutes": 120,
            "enabled": 1
        }

        upsert_dataset_config(schedule)

        print("Customer dataset configuration created.")

    # 3. Generate sample CSV
    file_path = create_sample_data()

    print(f"Sample data created: {file_path}")

    # 4. Execute pipeline
    result = run_pipeline(
        dataset_name="customers",
        file_path=file_path,
        required_fields=["id", "name", "event_time"],
        primary_key="id",
        timestamp_field="event_time",
        lowercase_fields=["name"],
        timestamp_fields=["event_time"]
    )

    # 5. Display results
    print("\n========== PIPELINE RESULT ==========")

    for key, value in result.items():
        print(f"{key}: {value}")

    print("\nDataPulse execution completed.")


if __name__ == "__main__":
    main()
