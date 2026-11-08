# DataPulse – Data Dictionary

## 1. Overview

DataPulse uses SQLite to store dataset configurations, pipeline execution history, incoming load details, processed records, rejected records, and monitoring alerts.

Database location: `database/datapulse.db`

## 2. Database Tables

### 2.1 `dataset_config`

Stores configuration for each monitored dataset.

| Column | Description |
|---|---|
| dataset_name | Unique dataset identifier |
| schedule_type | Schedule type: interval, daily, or weekly |
| timezone | Timezone used for schedule evaluation |
| expected_time | Expected time for daily or weekly schedules |
| expected_weekday | Expected weekday for weekly schedules |
| interval_minutes | Interval duration in minutes |
| schedule_anchor | Reference timestamp for interval schedules |
| arrival_grace_minutes | Allowed arrival delay |
| completion_sla_minutes | Maximum allowed processing duration |
| freshness_threshold_minutes | Maximum acceptable data age |
| enabled | Indicates whether monitoring is enabled |
| created_at | Configuration creation timestamp |
| updated_at | Last configuration update timestamp |

### 2.2 `dataset_runs`

Stores pipeline execution history.

| Column | Description |
|---|---|
| run_id | Unique pipeline execution identifier |
| started_at | Pipeline start timestamp |
| finished_at | Pipeline completion timestamp |
| status | RUNNING, SUCCESS, FAILED, or PARTIAL |
| trigger_type | Type of execution trigger |
| input_count | Total input records |
| valid_count | Number of valid records |
| rejected_count | Number of rejected records |
| error_message | Error details, if execution fails |

### 2.3 `dataset_loads`

Tracks individual dataset load attempts.

| Column | Description |
|---|---|
| load_id | Unique load identifier |
| dataset_name | Name of the dataset |
| run_id | Associated pipeline execution |
| expected_arrival_at | Expected dataset arrival timestamp |
| source_fingerprint | Source file fingerprint used for duplicate-load detection |
| source_file | Input file path |
| status | RUNNING, SUCCESS, or FAILED |
| started_at | Load start timestamp |
| completed_at | Load completion timestamp |
| input_count | Total input records |
| valid_count | Number of valid records |
| rejected_count | Number of rejected records |

### 2.4 `processed_records`

Stores successfully transformed records.

Records are identified using the dataset name and record identifier. An UPSERT operation updates existing records instead of creating duplicates during reruns.

### 2.5 `rejected_records`

Stores records that fail validation.

| Column | Description |
|---|---|
| rejection_id | Unique rejection identifier |
| dataset_name | Dataset associated with the rejected record |
| run_id | Pipeline execution identifier |
| source_file | Original input file |
| raw_record | Original rejected record |
| rejection_reason | Reason for rejection |
| rejected_at | Rejection timestamp |

### 2.6 `alerts`

Stores monitoring issues detected by DataPulse.

| Column | Description |
|---|---|
| alert_id | Unique alert identifier |
| dataset_name | Dataset associated with the alert |
| alert_type | Type of monitoring issue |
| severity | Alert severity |
| expected_arrival_at | Expected arrival associated with the alert, if applicable |
| message | Description of the issue |
| recommended_action | Suggested corrective action |
| status | OPEN or RESOLVED |
| created_at | Alert creation timestamp |
| resolved_at | Alert resolution timestamp |

## 3. Important Monitoring Statuses

**Arrival status**
- ON_TIME
- LATE
- MISSING
- PENDING
- NOT_DUE

**Completion status**
- MET
- BREACHED
- IN_PROGRESS

**Freshness status**
- FRESH
- STALE
- NO_DATA
- NO_VALID_TIMESTAMP
- FUTURE_TIMESTAMP

## 4. Data Reconciliation

DataPulse tracks input, valid, rejected, and stored record counts.

The following reconciliation rules are checked during pipeline execution:

- Input count = Valid count + Rejected count
- Stored count = Transformed record count

These checks help identify record loss or inconsistencies during processing.