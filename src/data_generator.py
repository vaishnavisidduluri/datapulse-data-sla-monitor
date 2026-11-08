
import csv
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone


def generate_customer_data(
    record_count=1000,
    output_path="data/raw/customers_large.csv",
    generated_at=None
):
    """
    Generate configurable synthetic customer records.

    Args:
        record_count: Number of records to generate.
        output_path: Destination CSV file.
        generated_at: Optional timezone-aware reference timestamp.

    Returns:
        Path to the generated CSV file.
    """

    if record_count <= 0:
        raise ValueError("Record count must be greater than zero.")

    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    if generated_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware.")

    generated_at = generated_at.astimezone(timezone.utc)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=["id", "name", "event_time"]
        )

        writer.writeheader()

        for index in range(1, record_count + 1):

            event_time = generated_at - timedelta(
                seconds=(index - 1) % 1800
            )

            writer.writerow({
                "id": f"C{index:06d}",
                "name": f"Customer {index:06d}",
                "event_time": event_time.isoformat()
            })

    print(f"Generated {record_count} customer records.")
    print(f"Output file: {output_file.resolve()}")

    return output_file


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate synthetic customer CSV data."
    )

    parser.add_argument(
        "--records",
        type=int,
        default=1000,
        help="Number of records to generate."
    )

    parser.add_argument(
        "--output",
        default="data/raw/customers_large.csv",
        help="Output CSV file path."
    )

    args = parser.parse_args()

    generate_customer_data(
        record_count=args.records,
        output_path=args.output
    )
