"""UI-07: live source validation and cleaning audit."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.database import DEFAULT_DB_PATH, load_dataset
from src.validation import validate_database
from src.ui import render_header

st.set_page_config(page_title="Data Quality · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("Data Quality", "Schema, key, foreign-key, range and cleaning checks")
st.info("The checked-in dataset is synthetic. Seeded missing values, near-duplicate profiles and outliers are flagged for review, not silently removed.")

@st.cache_data(show_spinner="Validating the SQLite database…")
def run_validation(path: str, modified: float):
    return validate_database(path)

@st.cache_data(show_spinner=False)
def load_quality_tables(path: str, modified: float):
    return load_dataset(path)

if not Path(DEFAULT_DB_PATH).is_file():
    st.error("The project database is missing; validation cannot pass.")
    st.stop()
report = run_validation(str(DEFAULT_DB_PATH), Path(DEFAULT_DB_PATH).stat().st_mtime)
tables = load_quality_tables(str(DEFAULT_DB_PATH), Path(DEFAULT_DB_PATH).stat().st_mtime)
status = report.get("status", "FAIL")
st.metric("Overall validation status", status, help="FAIL indicates at least one required contract check failed.")
counts = pd.DataFrame([{"Table": name, "Rows": len(tables[name]), "Columns": len(tables[name].columns)}
                       for name in ("Department", "JobLevel", "Employee", "EmployeeYear", "ApplicantEvent")])
st.subheader("Table size")
st.dataframe(counts, hide_index=True, width="stretch")
checks = pd.DataFrame(report.get("checks", []))
if not checks.empty:
    st.subheader("Validation checks")
    st.dataframe(checks, hide_index=True, width="stretch")
fk = report.get("foreign_key_issues", [])
st.write(f"**Foreign-key integrity:** {report.get('foreign_key_status', 'FAIL')} · {len(fk)} violations")

st.subheader("Missingness and cleaning audit")
audit = tables["cleaning_audit"].copy()
missing_rows = []
for name in ("Department", "JobLevel", "Employee", "EmployeeYear", "ApplicantEvent"):
    frame = tables[name]
    for column in frame.columns:
        missing_rows.append({"Table": name, "Column": column, "Missing": int(frame[column].isna().sum()),
                             "Rows": len(frame)})
st.dataframe(pd.DataFrame(missing_rows).query("Missing > 0"), hide_index=True, width="stretch")
st.dataframe(audit, hide_index=True, width="stretch")

st.subheader("Synthetic review flags")
quality_file = Path(DEFAULT_DB_PATH).parent / "validation_report.json"
if quality_file.exists():
    seeded_report = json.loads(quality_file.read_text(encoding="utf-8"))
    flags = seeded_report.get("quality_review_flags", {})
    for label, value in flags.items():
        if isinstance(value, dict) and "count" in value:
            value = f"{value['count']} values ({value.get('pct_of_employee_year', 0):.2f}% of employee-year rows)"
        elif isinstance(value, list):
            value = f"{len(value)} flagged records"
        st.write(f"**{label.replace('_', ' ').title()}:** {value}")
    st.caption("Record identifiers are suppressed from this screen. These are synthetic quality flags, not hidden data changes.")
else:
    st.warning("The generator review report is missing; the live database checks above remain available.")

download = json.dumps(report, indent=2, default=str).encode("utf-8")
st.download_button("Download live validation report", download, "validation_report.json", "application/json")
if status != "PASS":
    st.error("At least one required validation failed. Do not describe this database as clean until the issue is corrected.")
