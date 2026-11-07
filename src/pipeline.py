
import hashlib
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from src.config import timestamp_to_string
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
    db_path=None
):
    """
    Execute the complete DataPulse pipeline.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

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

    started_at = datetime.now(timezone.utc)
    started_at_string = timestamp_to_string(started_at)

    evaluation_time = as_of if as_of is not None else started_at

    run_id = str(uuid.uuid4())
    load_id = str(uuid.uuid4())

    connection = (
        get_connection(db_path)
        if db_path is not None
        else get_connection()
    )

    load_created = False

    try:
        # 2. Create pipeline run
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

        # 3. Determine expected arrival
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

        # 4. Calculate input fingerprint
        fingerprint = calculate_file_fingerprint(file_path)

        # 5. Create or reuse dataset load
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

        # 6. Ingest and validate CSV
        valid_records, rejected_records = ingest_csv(
            file_path,
            required_fields,
            primary_key
        )

        input_count = len(valid_records) + len(rejected_records)

        # 7. Transform valid records
        transformed_records = transform_records(
            valid_records,
            lowercase_fields=lowercase_fields,
            timestamp_fields=timestamp_fields
        )

        # 8. Store processed records
        stored_count = store_records(
            dataset_name,
            transformed_records,
            primary_key,
            db_path
        )

        # 9. Save rejected records
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

        # 10. Calculate data freshness
        freshness_result = calculate_freshness(
            transformed_records,
            timestamp_field,
            schedule["freshness_threshold_minutes"],
            as_of=evaluation_time
        )

        # 11. Evaluate arrival SLA
        arrival_result = evaluate_arrival_sla(
            schedule,
            arrivals=[
                {
                    "expected_arrival": expected_arrival_string,
                    "arrived_at": started_at_string
                }
            ],
            as_of=evaluation_time
        )

        # 12. Evaluate completion SLA
        finished_at = datetime.now(timezone.utc)
        finished_at_string = timestamp_to_string(finished_at)

        completion_result = evaluate_completion_sla(
            started_at_string,
            finished_at_string,
            schedule["completion_sla_minutes"],
            as_of=evaluation_time
        )

        # 13. Generate and save alerts
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

        # 14. Determine final run status
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

        # 15. Return pipeline summary
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
            "completion_status": completion_result["status"],
            "freshness_status": freshness_result["status"],
            "expected_arrival": expected_arrival_string
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
                (timestamp_to_string(), run_id)
            )

        connection.commit()
        raise

    finally:
        connection.close()
