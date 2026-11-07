
from src.ingestion import ingest_csv


def test_ingest_valid_csv(tmp_path):
    file_path = tmp_path / "valid.csv"
    file_path.write_text(
        "id,name\n1,Alice\n2,Bob\n",
        encoding="utf-8"
    )

    valid, rejected = ingest_csv(
        file_path, ["id", "name"], "id"
    )

    assert len(valid) == 2
    assert len(rejected) == 0


def test_ingest_csv_with_missing_field(tmp_path):
    file_path = tmp_path / "missing.csv"
    file_path.write_text(
        "id,name\n1,Alice\n2,\n",
        encoding="utf-8"
    )

    valid, rejected = ingest_csv(
        file_path, ["id", "name"], "id"
    )

    assert len(valid) == 1
    assert len(rejected) == 1


def test_ingest_csv_with_duplicates(tmp_path):
    file_path = tmp_path / "duplicates.csv"
    file_path.write_text(
        "id,name\n1,Alice\n1,Bob\n",
        encoding="utf-8"
    )

    valid, rejected = ingest_csv(
        file_path, ["id", "name"], "id"
    )

    assert len(valid) == 1
    assert len(rejected) == 1


def test_ingest_malformed_csv(tmp_path):
    file_path = tmp_path / "malformed.csv"
    file_path.write_text(
        'id,name\n1,"Alice\n',
        encoding="utf-8"
    )

    valid, rejected = ingest_csv(
        file_path, ["id", "name"], "id"
    )

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "Malformed CSV" in rejected[0]["reason"]


def test_ingest_empty_csv(tmp_path):
    file_path = tmp_path / "empty.csv"
    file_path.write_text("", encoding="utf-8")

    valid, rejected = ingest_csv(
        file_path, ["id", "name"], "id"
    )

    assert valid == []
    assert len(rejected) == 1
