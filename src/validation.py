
def validate_records(records, required_fields, primary_key):
    """
    Validate incoming records.

    Returns:
        valid_records: Records that pass validation.
        rejected_records: Records with validation errors.
    """

    valid_records = []
    rejected_records = []
    seen_ids = set()

    for index, record in enumerate(records):

        errors = []

        # 1. Check whether the record is a dictionary
        if not isinstance(record, dict):
            rejected_records.append({
                "record": record,
                "row_number": index + 1,
                "reason": "Record must be a dictionary"
            })
            continue

        # 2. Check required fields
        for field in required_fields:
            if field not in record:
                errors.append(f"Missing required field: {field}")

            elif record[field] is None or (
                isinstance(record[field], str) and not record[field].strip()
            ):
                errors.append(f"Empty required field: {field}")

        # 3. Check duplicate primary key
        record_id = record.get(primary_key)

        if record_id is not None:
            if record_id in seen_ids:
                errors.append(f"Duplicate primary key: {record_id}")
            else:
                seen_ids.add(record_id)

        # 4. Separate valid and rejected records
        if errors:
            rejected_records.append({
                "record": record,
                "row_number": index + 1,
                "reason": "; ".join(errors)
            })
        else:
            valid_records.append(record)

    return valid_records, rejected_records
