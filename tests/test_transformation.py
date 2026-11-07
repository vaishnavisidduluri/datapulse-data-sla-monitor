from src.transformation import transform_records


def test_remove_extra_spaces():
    records = [{"name": " Alice "}]

    result = transform_records(records)

    assert result == [{"name": "Alice"}]


def test_empty_string_becomes_none():
    records = [{"name": ""}]

    result = transform_records(records)

    assert result == [{"name": None}]


def test_lowercase_email():
    records = [{"email": "ALICE@GMAIL.COM"}]

    result = transform_records(
        records,
        lowercase_fields=["email"]
    )

    assert result[0]["email"] == "alice@gmail.com"


def test_timestamp_converted_to_utc():
    records = [
        {"created_at": "2026-11-07T09:00:00+05:30"}
    ]

    result = transform_records(
        records,
        timestamp_fields=["created_at"]
    )

    assert result[0]["created_at"] == "2026-11-07T03:30:00+00:00"


def test_transformation_is_deterministic():
    records = [{"name": " Alice ", "email": "ALICE@GMAIL.COM"}]

    first = transform_records(records, lowercase_fields=["email"])
    second = transform_records(records, lowercase_fields=["email"])

    assert first == second
