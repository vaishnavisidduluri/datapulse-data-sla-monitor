from src.database import (
    initialize_database,
    upsert_dataset_config,
    get_connection,
    get_dataset_configs
)


def test_database_creation(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    connection = get_connection(db_path)

    tables = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    table_names = [row["name"] for row in tables]

    connection.close()

    assert "dataset_config" in table_names
    assert "dataset_runs" in table_names
    assert "dataset_loads" in table_names
    assert "alerts" in table_names


def test_dataset_configuration(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    schedule = {
        "dataset_name": "customers",
        "schedule_type": "daily",
        "timezone": "Asia/Kolkata",
        "expected_time": "09:00",
        "arrival_grace_minutes": 15,
        "completion_sla_minutes": 60,
        "freshness_threshold_minutes": 120
    }

    # Temporarily replace the default database path
    from src import database

    original_path = database.DB_PATH
    database.DB_PATH = db_path

    try:
        upsert_dataset_config(schedule)

        configs = get_dataset_configs()

        assert len(configs) == 1
        assert configs[0]["dataset_name"] == "customers"
        assert configs[0]["expected_time"] == "09:00"

        # Running the same configuration again must not
        # create another dataset configuration.
        upsert_dataset_config(schedule)

        assert len(get_dataset_configs()) == 1

    finally:
        database.DB_PATH = original_path