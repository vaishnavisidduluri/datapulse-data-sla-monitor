
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "datapulse.db"

st.set_page_config(
    page_title="DataPulse | SLA Monitor",
    page_icon="📊",
    layout="wide"
)

st.title("📊 DataPulse")
st.subheader("Data Freshness & SLA Monitoring Dashboard")
st.caption(
    "Monitor dataset arrivals, processing SLAs, freshness, and alerts."
)

if not DB_PATH.exists():
    st.error("Database not found. Run `python run_pipeline.py` first.")
    st.stop()


@st.cache_data(ttl=10)
def load_dashboard_data():
    connection = sqlite3.connect(DB_PATH)

    try:
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table'",
            connection
        )["name"].tolist()

        def read_table(query, table_name):
            if table_name not in tables:
                return pd.DataFrame()
            return pd.read_sql_query(query, connection)

        configs = read_table(
            "SELECT * FROM dataset_config ORDER BY dataset_name",
            "dataset_config"
        )

        runs = read_table(
            """
            SELECT * FROM dataset_runs
            ORDER BY started_at DESC
            LIMIT 10
            """,
            "dataset_runs"
        )

        alerts = read_table(
            """
            SELECT * FROM alerts
            WHERE status = 'OPEN'
            ORDER BY created_at DESC
            LIMIT 20
            """,
            "alerts"
        )

        if "processed_records" in tables:
            records = pd.read_sql_query(
                "SELECT COUNT(*) AS total FROM processed_records",
                connection
            )
            processed_count = int(records.iloc[0]["total"])
        else:
            processed_count = 0

        if "dataset_runs" in tables:
            total_runs = pd.read_sql_query(
                "SELECT COUNT(*) AS total FROM dataset_runs",
                connection
            ).iloc[0]["total"]
        else:
            total_runs = 0

        if "alerts" in tables:
            open_alert_count = pd.read_sql_query(
                "SELECT COUNT(*) AS total FROM alerts WHERE status = 'OPEN'",
                connection
            ).iloc[0]["total"]
        else:
            open_alert_count = 0

        return (
            configs,
            runs,
            alerts,
            processed_count,
            int(total_runs),
            int(open_alert_count)
        )

    finally:
        connection.close()


try:
    (
        configs,
        runs,
        alerts,
        processed_count,
        total_runs,
        open_alert_count
    ) = load_dashboard_data()

    total_datasets = len(configs)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Configured Datasets", total_datasets)
    col2.metric("Total Pipeline Runs", total_runs)
    col3.metric("Processed Records", processed_count)
    col4.metric("Open Alerts", open_alert_count)

    st.divider()

    st.subheader("Recent Pipeline Executions")

    if runs.empty:
        st.info("No pipeline executions available.")
    else:
        st.dataframe(
            runs,
            width="stretch",
            hide_index=True
        )

    st.subheader("Dataset Configurations")

    if configs.empty:
        st.info("No dataset configurations available.")
    else:
        st.dataframe(
            configs,
            width="stretch",
            hide_index=True
        )

    st.subheader("Open Alerts")

    if alerts.empty:
        st.success("No open alerts. All monitored conditions are clear.")
    else:
        st.dataframe(
            alerts,
            width="stretch",
            hide_index=True
        )

    st.caption("Dashboard data refreshes automatically every 10 seconds.")

except Exception as error:
    st.error(f"Unable to load dashboard data: {error}")
    st.info(
        "Make sure the database has been initialized by running "
        "`python run_pipeline.py`."
    )
