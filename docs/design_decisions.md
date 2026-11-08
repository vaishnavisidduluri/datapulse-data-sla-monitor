# DataPulse – Design Decisions

## 1. Project Architecture

DataPulse follows a modular architecture. Each component has a specific responsibility:

1. **Configuration:** Manages database paths, directories, and timestamp utilities.
2. **Scheduling:** Calculates expected dataset arrivals using configurable schedules.
3. **Ingestion:** Reads incoming CSV files.
4. **Validation:** Identifies missing fields, null values, duplicate identifiers, and malformed records.
5. **Transformation:** Cleans records and normalizes timestamps.
6. **Storage:** Persists processed records in SQLite.
7. **Freshness Monitoring:** Evaluates the age of the latest available data.
8. **SLA Monitoring:** Evaluates arrival and processing completion SLAs.
9. **Alert Engine:** Generates actionable alerts.
10. **Pipeline:** Coordinates the complete execution flow.

## 2. Technology Choices

| Technology | Reason |
|---|---|
| Python | Core processing and business logic |
| SQLite | Lightweight relational database with no separate server |
| CSV | Simple and portable input format |
| Pytest | Automated unit and integration testing |
| Streamlit | Interactive monitoring dashboard |

The synthetic data generator uses Python's standard library to avoid unnecessary dependencies.

## 3. Configurable Scheduling

Hardcoded arrival timestamps were avoided.

The system supports:
- Interval schedules, such as every 15 minutes.
- Daily schedules with configurable expected times.
- Weekly schedules with configurable weekdays.
- Configurable timezones and arrival grace periods.
- Explicit historical evaluation timestamps for backfills.

Schedule evaluation uses timezone-aware timestamps.

## 4. Data Quality and Validation

Incoming records are validated before transformation and storage.

Invalid records are tracked separately with their original content and rejection reasons. Valid records continue through the pipeline.

This allows partial processing instead of rejecting an entire dataset because of individual invalid records.

## 5. Idempotency

Repeated processing should not create duplicate processed records.

DataPulse uses:
- A composite record key based on dataset name and record identifier.
- SQLite UPSERT operations for processed records.
- Source fingerprints and unique load constraints for load tracking.

This supports safe reruns and prevents duplicate records.

## 6. Failure Handling and Recovery

Pipeline execution status and error details are recorded in the database.

A failed execution can be investigated and rerun after correcting the underlying issue. Historical data can also be evaluated using an explicit `as_of` timestamp.

The current implementation supports reruns and backfills; it does not claim automatic scheduling or automatic resumption of interrupted executions.

## 7. Monitoring Strategy

DataPulse evaluates three separate dimensions:

- **Arrival SLA:** Did the dataset arrive within its configured grace period?
- **Completion SLA:** Did processing finish within the configured duration?
- **Data freshness:** Is the latest event timestamp within the configured freshness threshold?

Separating these checks makes it easier to identify the actual source of a data reliability issue.

## 8. Alert Design

Alerts contain:
- Alert type
- Severity
- Dataset name
- Description
- Recommended corrective action

Duplicate open alerts for the same dataset, alert type, and expected arrival are prevented.

## 9. Performance and Scalability

The pipeline was tested with a synthetic dataset containing 10,000 records.

A local execution completed in approximately 3.92 seconds during testing. This is an observed benchmark, not a guaranteed performance target.

SQLite and the modular processing design keep the implementation lightweight while allowing individual components to be extended.

## 10. Testing Strategy

The test suite covers:
- CSV ingestion and malformed input.
- Data validation and transformation.
- Interval, daily, and weekly scheduling.
- Timezone-aware freshness calculations.
- Arrival and completion SLA evaluation.
- Alert generation and duplicate prevention.
- Database operations and idempotency.
- Pipeline success, rejected records, and historical backfills.

The complete test suite currently contains 59 passing tests.