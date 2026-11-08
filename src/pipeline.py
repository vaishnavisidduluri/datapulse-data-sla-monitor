
import hashlib
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from src.config import timestamp_to_string, parse_timestamp
from src.database import get_connection, get_dataset_config
from src.ingestion import ingest_csv
from src.transformation import transform_records
from src.storage import store_records
from src.freshness import calculate_freshness
from src.sla_monitor import (
    evaluate_arrival_sla,
    evaluate_completion_sla
)
from src.scheduling import latest_expected_arrival
from src.alert_engine import generate_alerts, save_alerts


def calculate_file_fingerprint(file_path):
    """Generate a SHA-256 fingerprint for the input file."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def run_pipeline(
    dataset_name,
    file_path,
    required_fields,
    primary_key,
    timestamp_field,
    lowercase_fields=None,
    timestamp_fields=None,
    as_of=None,
    db_path=None,
    arrival_at=None
):
    """
    Execute the complete DataPulse pipeline.

    Parameters:
        dataset_name: Name of the dataset.
        file_path: Input CSV file path.
        required_fields: Required CSV columns.
        primary_key: Unique record identifier.
        timestamp_field: Field used for freshness monitoring.
        lowercase_fields: Fields to convert to lowercase.
        timestamp_fields: Fields to convert to UTC timestamps.
        as_of: Optional timezone-aware evaluation timestamp.
        db_path: Optional custom SQLite database path.
        arrival_at: Optional actual data arrival timestamp.

    If arrival_at is not supplied, evaluation_time is used as a
    backward-compatible fallback. For accurate arrival SLA tracking,
    provide the actual arrival timestamp.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {file_path}"
        )

    # 1. Load saved dataset configuration
    if db_path is not None:
        schedule = get_dataset_config(dataset_name, db_path)
    else:
        schedule = get_dataset_config(dataset_name)

    if schedule is None:
        raise ValueError(
            f"No configuration found for dataset: {dataset_name}"
        )

    if not schedule["enabled"]:
        raise ValueError(
            f"Dataset {dataset_name} is disabled."
        )

    # 2. Capture pipeline execution and evaluation timestamps
    started_at = datetime.now(timezone.utc)
    started_at_string = timestamp_to_string(started_at)

    if as_of is not None:
        evaluation_time = parse_timestamp(as_of)
    else:
        evaluation_time = started_at

    evaluation_time = evaluation_time.astimezone(timezone.utc)

    # Use actual arrival time when provided.
    # Otherwise, preserve compatibility with existing callers.
    if arrival_at is not None:
        actual_arrival = parse_timestamp(arrival_at)
    else:
        actual_arrival = evaluation_time

    actual_arrival = actual_arrival.astimezone(timezone.utc)

    if actual_arrival > evaluation_time:
        raise ValueError(
            "Arrival timestamp cannot be later than evaluation time."
        )

    actual_arrival_string = timestamp_to_string(actual_arrival)

    run_id = str(uuid.uuid4())
    load_id = str(uuid.uuid4())

    connection = (
        get_connection(db_path)
        if db_path is not None
        else get_connection()
    )

    load_created = False

    try:
        # 3. Create pipeline run
        connection.execute(
            """
            INSERT INTO dataset_runs (
                run_id, started_at, status, trigger_type
            )
            VALUES (?, ?, 'RUNNING', 'MANUAL')
            """,
            (run_id, started_at_string)
        )

        connection.commit()

        # 4. Determine expected arrival from saved schedule
        expected_arrival = latest_expected_arrival(
            schedule,
            evaluation_time
        )

        if expected_arrival is None:
            raise ValueError(
                "No expected arrival is available for this schedule."
            )

        expected_arrival_string = timestamp_to_string(
            expected_arrival
        )

        # 5. Calculate input fingerprint
        fingerprint = calculate_file_fingerprint(file_path)

        # 6. Create or reuse dataset load
        connection.execute(
            """
            INSERT INTO dataset_loads (
                load_id,
                dataset_name,
                run_id,
                expected_arrival_at,
                source_fingerprint,
                source_file,
                status,
                started_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'RUNNING', ?)
            ON CONFLICT(
                dataset_name,
                expected_arrival_at,
                source_fingerprint
            )
            DO UPDATE SET
                run_id = excluded.run_id,
                status = 'RUNNING',
                started_at = excluded.started_at,
                completed_at = NULL
            """,
            (
                load_id,
                dataset_name,
                run_id,
                expected_arrival_string,
                fingerprint,
                str(file_path),
                started_at_string
            )
        )

        connection.commit()
        load_created = True

        # 7. Ingest and validate CSV
        valid_records, rejected_records = ingest_csv(
            file_path,
            required_fields,
            primary_key
        )

        input_count = len(valid_records) + len(rejected_records)

        # 8. Transform valid records
        transformed_records = transform_records(
            valid_records,
            lowercase_fields=lowercase_fields,
            timestamp_fields=timestamp_fields
        )

        # 9. Store processed records
        stored_count = store_records(
            dataset_name,
            transformed_records,
            primary_key,
            db_path
        )

        # 10. Data reconciliation checks
        if input_count != (
            len(transformed_records) + len(rejected_records)
        ):
            raise ValueError(
                "Data reconciliation failed: input count does not "
                "match valid and rejected record counts."
            )

        if stored_count != len(transformed_records):
            raise ValueError(
                "Data reconciliation failed: stored count does not "
                "match transformed record count."
            )

        # 11. Save rejected records
        for rejected in rejected_records:
            connection.execute(
                """
                INSERT INTO rejected_records (
                    dataset_name,
                    run_id,
                    source_file,
                    raw_record,
                    rejection_reason,
                    rejected_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_name,
                    run_id,
                    str(file_path),
                    json.dumps(
                        rejected.get("record"),
                        default=str
                    ),
                    rejected.get("reason", "Invalid record"),
                    timestamp_to_string()
                )
            )

        connection.commit()

        # 12. Calculate data freshness
        freshness_result = calculate_freshness(
            transformed_records,
            timestamp_field,
            schedule["freshness_threshold_minutes"],
            as_of=evaluation_time
        )

        # 13. Evaluate arrival SLA using actual arrival time
        arrival_result = evaluate_arrival_sla(
            schedule,
            arrivals=[
                {
                    "expected_arrival": expected_arrival_string,
                    "arrived_at": actual_arrival_string
                }
            ],
            as_of=evaluation_time
        )

        # 14. Evaluate pipeline completion SLA
        finished_at = datetime.now(timezone.utc)
        finished_at_string = timestamp_to_string(finished_at)

        completion_result = evaluate_completion_sla(
            started_at_string,
            finished_at_string,
            schedule["completion_sla_minutes"],
            as_of=evaluation_time
        )

        # 15. Generate and save alerts
        alerts = generate_alerts(
            dataset_name,
            arrival_result=arrival_result,
            completion_result=completion_result,
            freshness_result=freshness_result
        )

        saved_alert_count = save_alerts(
            alerts,
            expected_arrival_at=expected_arrival_string,
            db_path=db_path
        )

        # 16. Determine final run status
        final_status = (
            "PARTIAL" if rejected_records else "SUCCESS"
        )

        connection.execute(
            """
            UPDATE dataset_runs
            SET finished_at = ?,
                status = ?,
                input_count = ?,
                valid_count = ?,
                rejected_count = ?
            WHERE run_id = ?
            """,
            (
                finished_at_string,
                final_status,
                input_count,
                len(transformed_records),
                len(rejected_records),
                run_id
            )
        )

        connection.execute(
            """
            UPDATE dataset_loads
            SET status = 'SUCCESS',
                completed_at = ?,
                input_count = ?,
                valid_count = ?,
                rejected_count = ?
            WHERE dataset_name = ?
              AND expected_arrival_at = ?
              AND source_fingerprint = ?
            """,
            (
                finished_at_string,
                input_count,
                len(transformed_records),
                len(rejected_records),
                dataset_name,
                expected_arrival_string,
                fingerprint
            )
        )

        connection.commit()

        # 17. Return pipeline summary
        return {
            "run_id": run_id,
            "dataset_name": dataset_name,
            "status": final_status,
            "input_count": input_count,
            "valid_count": len(transformed_records),
            "rejected_count": len(rejected_records),
            "stored_count": stored_count,
            "alert_count": saved_alert_count,
            "arrival_status": arrival_result["status"],
            "expected_arrival": expected_arrival_string,
            "actual_arrival": actual_arrival_string,
            "completion_status": completion_result["status"],
            "freshness_status": freshness_result["status"]
        }

    except Exception as error:
        connection.rollback()

        connection.execute(
            """
            UPDATE dataset_runs
            SET status = 'FAILED',
                finished_at = ?,
                error_message = ?
            WHERE run_id = ?
            """,
            (
                timestamp_to_string(),
                str(error),
                run_id
            )
        )

        if load_created:
            connection.execute(
                """
                UPDATE dataset_loads
                SET status = 'FAILED',
                    completed_at = ?
                WHERE run_id = ?
                """,
                (
                    timestamp_to_string(),
                    run_id
                )
            )

        connection.commit()
        raise

    finally:
        connection.close()
