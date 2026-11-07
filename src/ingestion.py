
import csv

from src.validation import validate_records


def ingest_csv(file_path, required_fields, primary_key):
    """
    Read a CSV file and separate valid and rejected records.
    """

    records = []
    source_rows = []
    rejected_records = []

    try:
        with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, strict=True)

            if reader.fieldnames is None:
                return [], [{
                    "record": None,
                    "row_number": 1,
                    "reason": "CSV file is empty or missing headers"
                }]

            for row in reader:
                row_number = reader.line_num

                # Detect rows containing extra columns
                if None in row:
                    rejected_records.append({
                        "record": row,
                        "row_number": row_number,
                        "reason": "Row contains extra columns"
                    })
                    continue

                records.append(row)
                source_rows.append(row_number)

    except csv.Error as error:
        rejected_records.append({
            "record": None,
            "row_number": reader.line_num,
            "reason": f"Malformed CSV: {error}"
        })

    # Validate all successfully read records
    valid_records, validation_rejections = validate_records(
        records,
        required_fields,
        primary_key
    )

    # Preserve original CSV row numbers
    for rejected in validation_rejections:
        rejected["row_number"] = source_rows[
            rejected["row_number"] - 1
        ]
        rejected_records.append(rejected)

    return valid_records, rejected_records
