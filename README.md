# DataPulse – Configurable Data Freshness & SLA Monitoring System

DataPulse is a configurable data engineering solution that monitors dataset arrivals, processing SLAs, and data freshness. It detects missing or late data loads, identifies data quality issues, and generates actionable alerts.

## 1. Key Features

- **Configurable Scheduling:** Interval, daily, and weekly dataset schedules.
- **Timezone Awareness:** Timezone-aware timestamps and schedule evaluation.
- **Data Ingestion:** CSV ingestion with malformed input handling.
- **Data Validation:** Detects missing fields, null values, and duplicate identifiers.
- **Data Transformation:** Cleans records and converts configured timestamps to UTC.
- **Data Storage:** SQLite-based persistent storage.
- **Arrival SLA Monitoring:** Detects on-time, late, missing, and pending arrivals.
- **Completion SLA Monitoring:** Tracks processing duration against configured thresholds.
- **Freshness Monitoring:** Detects stale, missing, and future-dated data.
- **Actionable Alerts:** Generates alerts with severity and recommended actions.
- **Idempotent Processing:** Prevents duplicate records during reruns.
- **Historical Backfills:** Supports evaluation using an explicit historical timestamp.
- **Data Reconciliation:** Checks input, valid, rejected, and stored record counts.
- **Monitoring Dashboard:** Streamlit dashboard for pipeline runs, configurations, and alerts.

## 2. Technology Stack

- Python 3
- SQLite
- Pytest
- Streamlit
- Standard Python CSV library

## 3. Project Structure

```text
datapulse-data-sla-monitor/
│
├── data/
│   └── raw/
│       ├── customers.csv
│       └── customers_large.csv
│
├── database/
│   └── datapulse.db
│
├── dashboard/
│   └── app.py
│
├── docs/
│   ├── data_dictionary.md
│   └── design_decisions.md
│
├── src/
│   ├── config.py
│   ├── database.py
│   ├── data_generator.py
│   ├── ingestion.py
│   ├── validation.py
│   ├── transformation.py
│   ├── storage.py
│   ├── scheduling.py
│   ├── freshness.py
│   ├── sla_monitor.py
│   ├── alert_engine.py
│   └── pipeline.py
│
├── tests/
│   ├── test_alert_engine.py
│   ├── test_database.py
│   ├── test_freshness.py
│   ├── test_idempotency.py
│   ├── test_ingestion.py
│   ├── test_pipeline.py
│   ├── test_scheduling.py
│   ├── test_sla_monitor.py
│   ├── test_transformation.py
│   └── test_validation.py
│
├── run_pipeline.py
├── check_results.py
├── requirements.txt
├── README.md
└── .gitignore
```

## 4. Installation

Clone the repository:

```bash
git clone https://github.com/vaishnavisidduluri/datapulse-data-sla-monitor.git
cd datapulse-data-sla-monitor
```

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 5. Run the Pipeline

```bash
python run_pipeline.py
```

The pipeline initializes the database, prepares sample customer data, processes records, evaluates SLAs and freshness, and generates alerts.

## 6. Generate Synthetic Data

Generate 10,000 customer records:

```bash
python -m src.data_generator --records 10000
```

Specify a custom output path:

```bash
python -m src.data_generator --records 5000 --output data/raw/customers_test.csv
```

## 7. Run the Dashboard

```bash
streamlit run dashboard/app.py
```

Open the local URL displayed in the terminal, normally:

`http://localhost:8501`

The dashboard displays:
- Configured datasets
- Pipeline execution counts
- Processed record counts
- Recent pipeline executions
- Dataset configurations
- Open monitoring alerts

## 8. Run Tests

Run the complete test suite:

```bash
pytest -v
```

The current implementation has **59 passing tests** covering ingestion, validation, transformation, scheduling, freshness, SLAs, alerts, database operations, idempotency, and pipeline execution.

## 9. Dataset Configuration

Each dataset supports configurable properties:

- Dataset name
- Schedule type
- Timezone
- Expected arrival time
- Expected weekday
- Interval duration
- Arrival grace period
- Completion SLA threshold
- Freshness threshold
- Enabled/disabled status

This allows datasets with different delivery frequencies and SLA requirements to be monitored independently.

## 10. Monitoring and Alerts

DataPulse monitors the following conditions:

| Alert | Description |
|---|---|
| MISSING_ARRIVAL | Expected dataset has not arrived within its grace period |
| LATE_ARRIVAL | Dataset arrived after its expected deadline |
| COMPLETION_SLA_BREACH | Processing exceeded its configured SLA |
| STALE_DATA | Latest data is older than the freshness threshold |
| NO_DATA | No records are available |
| INVALID_FRESHNESS_TIMESTAMP | No valid timestamp is available |
| FUTURE_EVENT_TIMESTAMP | A record contains a future timestamp |

Each alert includes a description and recommended corrective action.

## 11. Performance Testing

A synthetic dataset containing 10,000 records was processed successfully.

Observed local execution time: approximately **3.92 seconds**.

This is a measured result from the development environment and may vary across systems.

## 12. Documentation

Additional technical documentation:

- `docs/data_dictionary.md` – database tables, fields, statuses, and reconciliation rules.
- `docs/design_decisions.md` – architecture, technology choices, idempotency, recovery, and testing strategy.

## 13. Project Objective

DataPulse demonstrates a configurable and testable approach to data reliability monitoring. It helps engineering teams identify data delivery issues, maintain freshness, monitor processing SLAs, and improve pipeline observability.