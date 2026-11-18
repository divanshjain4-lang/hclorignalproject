"""Schema and data-quality checks for the approved Step 8 database."""
from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

from .database import DEFAULT_DB_PATH, TABLE_COLUMNS, _connect_read_only, load_dataset, validate_schema

PRIMARY_KEYS = {
    "Department": ["dept_id"], "JobLevel": ["level_id"], "Employee": ["emp_id"],
    "EmployeeYear": ["emp_id", "reporting_year"], "ApplicantEvent": ["applicant_id"],
}


def validate_tables(tables: dict[str, pd.DataFrame]) -> dict:
    """Check required columns, row counts, key uniqueness, ranges and categories."""
    checks = []

    def record(name: str, passed: bool, detail: str, severity: str = "FAIL") -> None:
        checks.append({"check": name, "status": "PASS" if passed else severity, "detail": detail})

    for table, columns in TABLE_COLUMNS.items():
        frame = tables.get(table)
        if frame is None:
            record(f"{table} available", False, "Required table was not loaded.")
            continue
        missing = [column for column in columns if column not in frame.columns]
        record(f"{table} columns", not missing,
               "All required columns are present." if not missing else f"Missing: {', '.join(missing)}")
        if missing:
            continue
        record(f"{table} rows", len(frame) > 0, f"{len(frame):,} rows loaded.", severity="WARN")
        keys = PRIMARY_KEYS[table]
        duplicates = int(frame.duplicated(keys, keep=False).sum())
        record(f"{table} primary key", duplicates == 0,
               f"{duplicates:,} duplicate-key rows." if duplicates else "No duplicate keys.")

    for table in ("Employee", "ApplicantEvent"):
        frame = tables.get(table)
        if frame is not None and "gender" in frame:
            invalid = sorted(set(frame.gender.dropna().astype(str)) - {"Female", "Male", "Other"})
            record(f"{table} gender categories", not invalid,
                   "Gender labels are allowed." if not invalid else f"Review unknown labels: {invalid}", severity="WARN")
    employee_year = tables.get("EmployeeYear")
    if employee_year is not None:
        salary = employee_year.annual_salary_inr.dropna()
        rating = employee_year.performance_rating.dropna()
        record("Salary range", salary.gt(0).all(), "Non-missing annual salaries are positive.")
        record("Performance rating range", rating.between(1, 5).all(), "Ratings are within 1–5.")
        record("Reporting-year range", employee_year.reporting_year.between(2021, 2025).all(), "Years are 2021–2025.")
        record("Snapshot date rule", (employee_year.snapshot_date.astype(str) ==
                                       employee_year.reporting_year.astype(str) + "-12-31").all(),
               "Each snapshot is dated December 31 of its reporting year.")
    return {"status": "FAIL" if any(x["status"] == "FAIL" for x in checks) else "PASS",
            "checks": checks, "row_counts": {t: len(tables[t]) for t in TABLE_COLUMNS if t in tables}}


def validate_database(db_path: str | Path = DEFAULT_DB_PATH) -> dict:
    """Validate schema, source tables and SQLite foreign-key integrity."""
    with _connect_read_only(db_path) as connection:
        schema_errors = validate_schema(connection)
        fk_issues = connection.execute("PRAGMA foreign_key_check").fetchall()
        fk_issues = [tuple(row) for row in fk_issues]
    if schema_errors:
        return {"status": "FAIL", "schema_errors": schema_errors,
                "foreign_key_issues": fk_issues, "checks": []}
    loaded = load_dataset(db_path)
    tables = {name: loaded[name] for name in TABLE_COLUMNS}
    report = validate_tables(tables)
    report["schema_errors"] = []
    report["foreign_key_issues"] = fk_issues
    report["foreign_key_status"] = "PASS" if not fk_issues else "FAIL"
    if fk_issues:
        report["status"] = "FAIL"
    report["database_path"] = str(Path(db_path).resolve())
    return report
