from pathlib import Path
from datetime import datetime, timezone

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
QUARANTINE_DIR = DATA_DIR / "quarantine"

DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "datapulse.db"

REPORTS_DIR = BASE_DIR / "reports"

# Create required directories if they do not exist
for directory in [
    RAW_DIR,
    PROCESSED_DIR,
    QUARANTINE_DIR,
    DATABASE_DIR,
    REPORTS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


def utc_now():
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def timestamp_to_string(value=None):
    """Convert a datetime into an ISO-8601 UTC string."""
    value = value or utc_now()

    if value.tzinfo is None:
        raise ValueError("Timestamp must include timezone information.")

    return value.astimezone(timezone.utc).isoformat()


def parse_timestamp(value):
    """Parse an ISO-8601 timestamp and ensure it is timezone-aware."""
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

    if result.tzinfo is None:
        raise ValueError("Timestamp must include timezone information.")

    return result