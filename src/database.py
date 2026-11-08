
import sqlite3
from pathlib import Path

from src.config import DB_PATH, timestamp_to_string


# --------------------------------------------------
# DATABASE SCHEMA
# --------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS dataset_config (
    dataset_name TEXT PRIMARY KEY,

    schedule_type TEXT NOT NULL
        CHECK(schedule_type IN ('interval', 'daily', 'weekly')),

    timezone TEXT NOT NULL,

    expected_time TEXT,
    expected_weekday INTEGER,
    interval_minutes INTEGER,
    schedule_anchor TEXT,

    arrival_grace_minutes INTEGER NOT NULL DEFAULT 15
        CHECK(arrival_grace_minutes >= 0),

    completion_sla_minutes INTEGER NOT NULL DEFAULT 60
        CHECK(completion_sla_minutes >= 0),

    freshness_threshold_minutes INTEGER NOT NULL DEFAULT 120
        CHECK(freshness_threshold_minutes >= 0),

    enabled INTEGER NOT NULL DEFAULT 1
        CHECK(enabled IN (0, 1)),

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    CHECK(
        schedule_type != 'interval'
        OR (interval_minutes > 0 AND schedule_anchor IS NOT NULL)
    ),

    CHECK(
        schedule_type != 'weekly'
        OR (expected_weekday BETWEEN 0 AND 6)
    ),

    CHECK(
        schedule_type != 'daily'
        OR expected_time IS NOT NULL
    )
);


CREATE TABLE IF NOT EXISTS dataset_runs (
    run_id TEXT PRIMARY KEY,

    started_at TEXT NOT NULL,
    finished_at TEXT,

    status TEXT NOT NULL
        CHECK(status IN ('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL')),

    trigger_type TEXT DEFAULT 'MANUAL',

    input_count INTEGER DEFAULT 0,
    valid_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,

    error_message TEXT
);


CREATE TABLE IF NOT EXISTS dataset_loads (
    load_id TEXT PRIMARY KEY,

    dataset_name TEXT NOT NULL,
    run_id TEXT,

    expected_arrival_at TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    source_file TEXT,

    status TEXT NOT NULL
        CHECK(status IN ('RUNNING', 'SUCCESS', 'FAILED')),

    started_at TEXT NOT NULL,
    completed_at TEXT,

    input_count INTEGER DEFAULT 0,
    valid_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,

    FOREIGN KEY(dataset_name)
        REFERENCES dataset_config(dataset_name),

    FOREIGN KEY(run_id)
        REFERENCES dataset_runs(run_id),

    UNIQUE(dataset_name, expected_arrival_at, source_fingerprint)
);


CREATE TABLE IF NOT EXISTS rejected_records (
    rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,

    dataset_name TEXT NOT NULL,
    run_id TEXT,
    source_file TEXT,

    raw_record TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,

    rejected_at TEXT NOT NULL,

    FOREIGN KEY(dataset_name)
        REFERENCES dataset_config(dataset_name),

    FOREIGN KEY(run_id)
        REFERENCES dataset_runs(run_id)
);


CREATE TABLE IF NOT EXISTS alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,

    dataset_name TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,

    expected_arrival_at TEXT,
    message TEXT NOT NULL,
    recommended_action TEXT,

    status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK(status IN ('OPEN', 'RESOLVED')),

    created_at TEXT NOT NULL,
    resolved_at TEXT,

    FOREIGN KEY(dataset_name)
        REFERENCES dataset_config(dataset_name)
);


-- DATABASE INDEXES

CREATE INDEX IF NOT EXISTS idx_loads_dataset
ON dataset_loads(dataset_name);

CREATE INDEX IF NOT EXISTS idx_loads_status
ON dataset_loads(status);

CREATE INDEX IF NOT EXISTS idx_runs_status
ON dataset_runs(status);

CREATE INDEX IF NOT EXISTS idx_alerts_status
ON alerts(status);

CREATE INDEX IF NOT EXISTS idx_alerts_dataset
ON alerts(dataset_name);
"""


# --------------------------------------------------
# DATABASE PATH RESOLUTION
# --------------------------------------------------

def _resolve_db_path(db_path=None):
    """
    Resolve the database path at runtime.

    If a custom path is provided, use it.
    Otherwise, use the current module-level DB_PATH.

    Resolving at runtime allows tests to temporarily replace DB_PATH.
    """

    if db_path is None:
        db_path = DB_PATH

    return Path(db_path)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection(db_path=None):
    """
    Create a SQLite database connection.

    Uses the current default database path when no path is supplied.
    Supports custom database paths for testing.
    """

    resolved_path = _resolve_db_path(db_path)

    resolved_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        resolved_path,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")

    return connection


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------

def initialize_database(db_path=None):
    """
    Create all database tables and indexes.

    Safe to execute multiple times.
    """

    connection = get_connection(db_path)

    try:
        connection.executescript(SCHEMA)
        connection.commit()

        print("Database initialized successfully.")

    finally:
        connection.close()


# --------------------------------------------------
# INSERT OR UPDATE DATASET CONFIGURATION
# --------------------------------------------------

def upsert_dataset_config(schedule, db_path=None):
    """
    Insert a new dataset configuration.

    If the dataset already exists, update its configuration.
    """

    from src.scheduling import validate_schedule

    validate_schedule(schedule)

    now = timestamp_to_string()

    query = """
    INSERT INTO dataset_config (
        dataset_name,
        schedule_type,
        timezone,
        expected_time,
        expected_weekday,
        interval_minutes,
        schedule_anchor,
        arrival_grace_minutes,
        completion_sla_minutes,
        freshness_threshold_minutes,
        enabled,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    ON CONFLICT(dataset_name) DO UPDATE SET

        schedule_type = excluded.schedule_type,
        timezone = excluded.timezone,
        expected_time = excluded.expected_time,
        expected_weekday = excluded.expected_weekday,
        interval_minutes = excluded.interval_minutes,
        schedule_anchor = excluded.schedule_anchor,
        arrival_grace_minutes = excluded.arrival_grace_minutes,
        completion_sla_minutes = excluded.completion_sla_minutes,
        freshness_threshold_minutes = excluded.freshness_threshold_minutes,
        enabled = excluded.enabled,
        updated_at = excluded.updated_at
    """

    values = (
        schedule["dataset_name"],
        schedule["schedule_type"],
        schedule["timezone"],
        schedule.get("expected_time"),
        schedule.get("expected_weekday"),
        schedule.get("interval_minutes"),
        schedule.get("schedule_anchor"),
        schedule.get("arrival_grace_minutes", 15),
        schedule.get("completion_sla_minutes", 60),
        schedule.get("freshness_threshold_minutes", 120),
        schedule.get("enabled", 1),
        now,
        now
    )

    connection = get_connection(db_path)

    try:
        connection.execute(query, values)
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# --------------------------------------------------
# GET ENABLED DATASET CONFIGURATIONS
# --------------------------------------------------

def get_dataset_configs(db_path=None):
    """
    Retrieve all enabled dataset configurations.
    """

    connection = get_connection(db_path)

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM dataset_config
            WHERE enabled = 1
            ORDER BY dataset_name
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# --------------------------------------------------
# GET ONE DATASET CONFIGURATION
# --------------------------------------------------

def get_dataset_config(dataset_name, db_path=None):
    """
    Retrieve configuration for a particular dataset.
    """

    connection = get_connection(db_path)

    try:
        row = connection.execute(
            """
            SELECT *
            FROM dataset_config
            WHERE dataset_name = ?
            """,
            (dataset_name,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()
