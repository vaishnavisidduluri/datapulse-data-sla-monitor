
from src.database import get_connection
from src.config import timestamp_to_string


def generate_alerts(
    dataset_name,
    arrival_result=None,
    completion_result=None,
    freshness_result=None
):
    """
    Generate actionable alerts from SLA and freshness results.

    Returns a list of alert dictionaries.
    """

    alerts = []

    def add_alert(alert_type, severity, message, recommended_action):
        alerts.append({
            "dataset_name": dataset_name,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "recommended_action": recommended_action
        })

    # 1. Arrival SLA alerts
    if arrival_result:
        status = arrival_result.get("status")

        if status == "MISSING":
            add_alert(
                "MISSING_ARRIVAL",
                "CRITICAL",
                f"Dataset {dataset_name} missed its expected arrival deadline.",
                "Check the source system and investigate the missing data load."
            )

        elif status == "LATE":
            add_alert(
                "LATE_ARRIVAL",
                "WARNING",
                f"Dataset {dataset_name} arrived after its expected deadline.",
                "Investigate the source delay and review the arrival schedule."
            )

    # 2. Processing completion SLA alerts
    if completion_result:
        status = completion_result.get("status")

        if status == "BREACHED":
            add_alert(
                "COMPLETION_SLA_BREACH",
                "CRITICAL",
                f"Dataset {dataset_name} exceeded its processing completion SLA.",
                "Inspect pipeline logs, identify the slow processing stage, and retry if safe."
            )

    # 3. Data freshness alerts
    if freshness_result:
        status = freshness_result.get("status")

        if status == "STALE":
            add_alert(
                "STALE_DATA",
                "WARNING",
                f"Dataset {dataset_name} has exceeded its freshness threshold.",
                "Check the latest source update and trigger a refresh if necessary."
            )

        elif status == "NO_DATA":
            add_alert(
                "NO_DATA",
                "CRITICAL",
                f"Dataset {dataset_name} contains no available records.",
                "Check whether the source load ran successfully and investigate missing data."
            )

        elif status == "NO_VALID_TIMESTAMP":
            add_alert(
                "INVALID_FRESHNESS_TIMESTAMP",
                "WARNING",
                f"Dataset {dataset_name} has no valid event timestamps for freshness calculation.",
                "Inspect the timestamp field and correct invalid or missing values."
            )

        elif status == "FUTURE_TIMESTAMP":
            add_alert(
                "FUTURE_EVENT_TIMESTAMP",
                "WARNING",
                f"Dataset {dataset_name} contains an event timestamp later than the evaluation time.",
                "Check source timezone settings and investigate incorrect event timestamps."
            )

    return alerts


def save_alerts(alerts, expected_arrival_at=None, db_path=None):
    """
    Save generated alerts in SQLite.

    Avoid duplicate OPEN alerts for the same:
    dataset, alert type, and expected arrival.

    Returns the number of newly inserted alerts.
    """

    connection = (
        get_connection(db_path)
        if db_path is not None
        else get_connection()
    )

    inserted_count = 0
    now = timestamp_to_string()

    try:
        for alert in alerts:

            dataset_name = alert["dataset_name"]
            alert_type = alert["alert_type"]

            expected = (
                alert.get("expected_arrival_at")
                or expected_arrival_at
            )

            # Check whether the same open alert already exists
            existing = connection.execute(
                """
                SELECT alert_id
                FROM alerts
                WHERE dataset_name = ?
                  AND alert_type = ?
                  AND expected_arrival_at IS ?
                  AND status = 'OPEN'
                LIMIT 1
                """,
                (
                    dataset_name,
                    alert_type,
                    expected
                )
            ).fetchone()

            if existing:
                continue

            # Insert a new alert
            connection.execute(
                """
                INSERT INTO alerts (
                    dataset_name,
                    alert_type,
                    severity,
                    expected_arrival_at,
                    message,
                    recommended_action,
                    status,
                    created_at,
                    resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, NULL)
                """,
                (
                    dataset_name,
                    alert_type,
                    alert["severity"],
                    expected,
                    alert["message"],
                    alert.get("recommended_action"),
                    now
                )
            )

            inserted_count += 1

        connection.commit()
        return inserted_count

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
