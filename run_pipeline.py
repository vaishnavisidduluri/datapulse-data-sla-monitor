
import csv
from datetime import datetime, timedelta, timezone

from src.config import RAW_DIR, timestamp_to_string
from src.database import (
    initialize_database,
    get_dataset_config,
    upsert_dataset_config
)
from src.pipeline import run_pipeline


def register_dataset_config(
    dataset_name,
    interval_minutes,
    freshness_threshold_minutes
):
    """Register a dataset configuration if it does not exist."""

    schedule = get_dataset_config(dataset_name)

    if schedule is None:
        schedule = {
            "dataset_name": dataset_name,
            "schedule_type": "interval",
            "timezone": "UTC",
            "interval_minutes": interval_minutes,
            "schedule_anchor": timestamp_to_string(
                datetime.now(timezone.utc) - timedelta(minutes=5)
            ),
            "arrival_grace_minutes": 15,
            "completion_sla_minutes": 60,
            "freshness_threshold_minutes": freshness_threshold_minutes,
            "enabled": 1
        }

        upsert_dataset_config(schedule)
        print(f"{dataset_name} dataset configuration created.")

    else:
        print(f"{dataset_name} dataset configuration already exists.")


def create_customer_data():
    """Generate sample customer records."""

    file_path = RAW_DIR / "customers.csv"
    now = datetime.now(timezone.utc)

    records = [
        {"id": "C001", "name": "Alice", "event_time": timestamp_to_string(now)},
        {"id": "C002", "name": "Bob", "event_time": timestamp_to_string(now - timedelta(minutes=2))},
        {"id": "C003", "name": "Charlie", "event_time": timestamp_to_string(now - timedelta(minutes=5))},
        {"id": "C004", "name": "David", "event_time": timestamp_to_string(now - timedelta(minutes=10))}
    ]

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["id", "name", "event_time"]
        )
        writer.writeheader()
        writer.writerows(records)

    return file_path


def create_order_data():
    """Generate sample order records."""

    file_path = RAW_DIR / "orders.csv"
    now = datetime.now(timezone.utc)

    records = [
        {
            "order_id": "O001",
            "customer_id": "C001",
            "amount": "1500.00",
            "event_time": timestamp_to_string(now)
        },
        {
            "order_id": "O002",
            "customer_id": "C002",
            "amount": "2500.50",
            "event_time": timestamp_to_string(now - timedelta(minutes=3))
        },
        {
            "order_id": "O003",
            "customer_id": "C003",
            "amount": "750.00",
            "event_time": timestamp_to_string(now - timedelta(minutes=8))
        },
        {
            "order_id": "O004",
            "customer_id": "C004",
            "amount": "3200.00",
            "event_time": timestamp_to_string(now - timedelta(minutes=12))
        }
    ]

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "order_id",
                "customer_id",
                "amount",
                "event_time"
            ]
        )
        writer.writeheader()
        writer.writerows(records)

    return file_path


def execute_dataset(
    dataset_name,
    file_path,
    required_fields,
    primary_key,
    lowercase_fields=None
):
    """Execute and display the result for one dataset."""

    result = run_pipeline(
        dataset_name=dataset_name,
        file_path=file_path,
        required_fields=required_fields,
        primary_key=primary_key,
        timestamp_field="event_time",
        lowercase_fields=lowercase_fields,
        timestamp_fields=["event_time"]
    )

    print(f"\n========== {dataset_name.upper()} PIPELINE RESULT ==========")

    for key, value in result.items():
        print(f"{key}: {value}")

    return result


def main():

    print("\n========== DATAPULSE ==========")

    # 1. Initialize database
    initialize_database()

    # 2. Register independent dataset configurations
    register_dataset_config(
        dataset_name="customers",
        interval_minutes=15,
        freshness_threshold_minutes=120
    )

    register_dataset_config(
        dataset_name="orders",
        interval_minutes=30,
        freshness_threshold_minutes=180
    )

    # 3. Generate sample data
    customer_file = create_customer_data()
    order_file = create_order_data()

    print(f"\nCustomer sample data: {customer_file}")
    print(f"Order sample data: {order_file}")

    # 4. Execute customer pipeline
    customer_result = execute_dataset(
        dataset_name="customers",
        file_path=customer_file,
        required_fields=["id", "name", "event_time"],
        primary_key="id",
        lowercase_fields=["name"]
    )

    # 5. Execute order pipeline
    order_result = execute_dataset(
        dataset_name="orders",
        file_path=order_file,
        required_fields=[
            "order_id",
            "customer_id",
            "amount",
            "event_time"
        ],
        primary_key="order_id"
    )

    # 6. Overall execution summary
    print("\n========== DATAPULSE SUMMARY ==========")

    print(f"Datasets processed: 2")
    print(
        f"Total input records: "
        f"{customer_result['input_count'] + order_result['input_count']}"
    )
    print(
        f"Total stored records: "
        f"{customer_result['stored_count'] + order_result['stored_count']}"
    )
    print(
        f"Total rejected records: "
        f"{customer_result['rejected_count'] + order_result['rejected_count']}"
    )

    print("\nDataPulse execution completed.")


if __name__ == "__main__":
    main()
