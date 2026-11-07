
import json

import pytest

from src.database import get_connection, initialize_database
from src.storage import store_records


def get_record_count(db_path):
    connection = get_connection(db_path)

    try:
        result = connection.execute(
            "SELECT COUNT(*) FROM processed_records"
        ).fetchone()

        return result[0]
    finally:
        connection.close()


def test_store_records(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]

    store_records("customers", records, "id", db_path)

    assert get_record_count(db_path) == 2


def test_rerun_does_not_create_duplicates(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]

    store_records("customers", records, "id", db_path)
    store_records("customers", records, "id", db_path)

    assert get_record_count(db_path) == 2


def test_same_id_in_different_datasets(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    store_records(
        "customers", [{"id": 1, "name": "Alice"}], "id", db_path
    )

    store_records(
        "products", [{"id": 1, "name": "Laptop"}], "id", db_path
    )

    assert get_record_count(db_path) == 2


def test_existing_record_is_updated(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    store_records(
        "customers", [{"id": 1, "name": "Alice"}], "id", db_path
    )

    store_records(
        "customers", [{"id": 1, "name": "Alice Smith"}], "id", db_path
    )

    assert get_record_count(db_path) == 1

    connection = get_connection(db_path)

    try:
        row = connection.execute("""
            SELECT record_json
            FROM processed_records
            WHERE dataset_name = 'customers' AND record_id = '1'
        """).fetchone()

        saved_record = json.loads(row["record_json"])
        assert saved_record["name"] == "Alice Smith"
    finally:
        connection.close()


def test_empty_batch(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    result = store_records(
        "customers", [], "id", db_path
    )

    assert result == 0
    assert get_record_count(db_path) == 0


def test_missing_primary_key_rolls_back_batch(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    records = [
        {"id": 1, "name": "Alice"},
        {"name": "Missing ID"}
    ]

    with pytest.raises(ValueError):
        store_records("customers", records, "id", db_path)

    assert get_record_count(db_path) == 0
