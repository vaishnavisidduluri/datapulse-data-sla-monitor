
import json

from src.config import timestamp_to_string
from src.database import get_connection


def store_records(dataset_name, records, primary_key, db_path=None):
    """
    Store processed records in SQLite.

    A record is uniquely identified by:
        dataset_name + primary_key

    Reprocessing the same record updates it instead of
    creating a duplicate.
    """

    if not dataset_name:
        raise ValueError("Dataset name is required.")

    if not primary_key:
        raise ValueError("Primary key is required.")

    connection = (
        get_connection(db_path)
        if db_path is not None
        else get_connection()
    )

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS processed_records (
                dataset_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (dataset_name, record_id)
            )
        """)

        now = timestamp_to_string()

        rows = []

        for record in records:
            record_id = record.get(primary_key)

            if record_id is None or str(record_id).strip() == "":
                raise ValueError(
                    f"Missing primary key: {primary_key}"
                )

            rows.append((
                dataset_name,
                str(record_id),
                json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str
                ),
                now,
                now
            ))

        connection.executemany("""
            INSERT INTO processed_records (
                dataset_name,
                record_id,
                record_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(dataset_name, record_id)
            DO UPDATE SET
                record_json = excluded.record_json,
                updated_at = excluded.updated_at
        """, rows)

        connection.commit()
        return len(rows)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
