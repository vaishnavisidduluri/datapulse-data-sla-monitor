
from src.validation import validate_records


def test_valid_records():
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]

    valid, rejected = validate_records(
        records, ["id", "name"], "id"
    )

    assert len(valid) == 2
    assert len(rejected) == 0


def test_missing_required_field():
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2}
    ]

    valid, rejected = validate_records(
        records, ["id", "name"], "id"
    )

    assert len(valid) == 1
    assert len(rejected) == 1


def test_null_required_field():
    records = [
        {"id": 1, "name": None}
    ]

    valid, rejected = validate_records(
        records, ["id", "name"], "id"
    )

    assert len(valid) == 0
    assert len(rejected) == 1


def test_duplicate_records():
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 1, "name": "Bob"}
    ]

    valid, rejected = validate_records(
        records, ["id", "name"], "id"
    )

    assert len(valid) == 1
    assert len(rejected) == 1


def test_malformed_record():
    records = [
        {"id": 1, "name": "Alice"},
        "invalid_record"
    ]

    valid, rejected = validate_records(
        records, ["id", "name"], "id"
    )

    assert len(valid) == 1
    assert len(rejected) == 1


def test_empty_batch():
    valid, rejected = validate_records(
        [], ["id", "name"], "id"
    )

    assert valid == []
    assert rejected == []
