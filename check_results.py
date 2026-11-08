import sqlite3

conn = sqlite3.connect("database/datapulse.db")

processed = conn.execute(
    "SELECT COUNT(*) FROM processed_records WHERE dataset_name = ?",
    ("customers",)
).fetchone()[0]

latest_run = conn.execute(
    """
    SELECT status, input_count, valid_count, rejected_count
    FROM dataset_runs
    ORDER BY started_at DESC
    LIMIT 1
    """
).fetchone()

print("Processed records:", processed)
print("Latest run:", latest_run)

conn.close()