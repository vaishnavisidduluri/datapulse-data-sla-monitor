
from src.config import parse_timestamp, timestamp_to_string


def transform_records(
    records,
    lowercase_fields=None,
    timestamp_fields=None
):
    lowercase_fields = lowercase_fields or []
    timestamp_fields = timestamp_fields or []

    transformed_records = []

    for record in records:
        transformed = {}

        for field, value in record.items():

            if isinstance(value, str):
                value = value.strip()

                if value == "":
                    value = None

            if value is not None and field in lowercase_fields:
                value = str(value).lower()

            if value is not None and field in timestamp_fields:
                value = timestamp_to_string(
                    parse_timestamp(value)
                )

            transformed[field] = value

        transformed_records.append(transformed)

    return transformed_records
