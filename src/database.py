"""Read and validate the project’s canonical five-table SQLite dataset."""
from __future__ import annotations

from pathlib import Path
import random
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "app.db"
TABLE_COLUMNS = {
    "Department": ["dept_id", "department_name", "target_women_pct"],
    "JobLevel": ["level_id", "level_name", "level_rank", "display_title", "is_leadership", "target_women_pct"],
    "Employee": ["emp_id", "gender", "join_date", "exit_date", "total_experience_years", "education_level"],
    "EmployeeYear": ["emp_id", "reporting_year", "snapshot_date", "dept_id", "level_id", "job_role",
                     "active_at_year_start", "active_at_year_end", "hired_in_year", "exit_in_year",
                     "tenure_years_start", "tenure_years_end", "annual_salary_inr", "promotion_eligible",
                     "promoted", "promotion_date", "performance_rating"],
    "ApplicantEvent": ["applicant_id", "gender", "dept_id", "applied_date", "stage_reached"],
}
TABLE_NAMES = tuple(TABLE_COLUMNS)
READABLE_NAMES = frozenset((*TABLE_NAMES, "vw_employee_analysis"))


@contextmanager
def _connect_read_only(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open an existing SQLite file in read-only mode; never create it implicitly."""
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Synthetic database not found: {path}")
    uri = f"{path.as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    try:
        yield connection
    finally:
        connection.close()


def validate_schema(connection: sqlite3.Connection) -> list[str]:
    """Return schema errors for missing tables, views or required columns."""
    objects = {row["name"]: row["type"] for row in connection.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')")}
    errors: list[str] = []
    for table, expected in TABLE_COLUMNS.items():
        if objects.get(table) != "table":
            errors.append(f"Required table is missing: {table}")
            continue
        actual = [row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')]
        missing = [column for column in expected if column not in actual]
        if missing:
            errors.append(f"{table} is missing required columns: {', '.join(missing)}")
    if objects.get("vw_employee_analysis") != "view":
        errors.append("Required analytical view is missing: vw_employee_analysis")
    return errors


def read_table(db_path: str | Path, table: str) -> pd.DataFrame:
    """Read one approved source table or the documented joined analysis view."""
    if table not in READABLE_NAMES:
        raise ValueError(f"Unsupported table: {table}")
    with _connect_read_only(db_path) as connection:
        errors = validate_schema(connection)
        if errors:
            raise ValueError("Invalid project database schema: " + "; ".join(errors))
        return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)


def _compatibility_frames(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Adapt the five normalized sources into analysis-ready frames.

    The lowercase aliases are in-memory DataFrames only; they do not create
    extra SQLite tables or alter the Step 8 schema.
    """
    department = raw["Department"].rename(columns={"department_name": "department_name"}).copy()
    levels = raw["JobLevel"].rename(columns={"level_rank": "rank", "display_title": "title"}).copy()
    years = raw["EmployeeYear"].copy()
    years["year"] = years["reporting_year"]
    years["annual_salary"] = years["annual_salary_inr"]
    years["rating"] = years["performance_rating"]

    latest = (years.sort_values(["emp_id", "reporting_year"])
              .drop_duplicates("emp_id", keep="last"))
    employees = raw["Employee"].merge(
        latest[["emp_id", "dept_id", "level_id", "job_role", "tenure_years_end"]],
        on="emp_id", how="left", validate="one_to_one")
    employees = employees.rename(columns={"job_role": "role", "education_level": "education"})
    education_rank = {"Diploma": 1, "Bachelor's": 2, "Master's": 3, "Doctorate": 4}
    employees["education"] = employees["education"].map(education_rank)

    applicants = raw["ApplicantEvent"].rename(columns={"stage_reached": "stage"}).copy()
    salaries = years[["emp_id", "year", "annual_salary"]].dropna(subset=["annual_salary"]).copy()
    appraisals = years.loc[years["rating"].notna(), ["emp_id", "year", "rating"]].copy()
    promotion_rows = years.loc[years["promoted"].eq(1),
                               ["emp_id", "year", "level_id", "promotion_date"]].copy()
    promotion_rows = promotion_rows.rename(columns={"level_id": "from_level"})
    promotion_rows["to_level"] = promotion_rows["from_level"] + 1
    promotion_rows["promotion_id"] = range(1, len(promotion_rows) + 1)
    promotions = promotion_rows[["promotion_id", "emp_id", "year", "from_level", "to_level", "promotion_date"]]

    return {
        "departments": department,
        "job_levels": levels,
        "employees": employees,
        "employee_years": years,
        "salaries": salaries,
        "applicants": applicants,
        "promotions": promotions,
        "appraisals": appraisals,
    }


def load_dataset(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, pd.DataFrame]:
    """Load the five canonical tables, joined view and analysis adapters.

    One read-only connection is used for the complete load. The returned
    canonical table keys retain the exact Step 8 names; lowercase keys are
    DataFrame adapters to keep analytical modules focused on tidy inputs.
    """
    with _connect_read_only(db_path) as connection:
        errors = validate_schema(connection)
        if errors:
            raise ValueError("Invalid project database schema: " + "; ".join(errors))
        result = {table: pd.read_sql_query(f'SELECT * FROM "{table}"', connection)
                  for table in TABLE_NAMES}
        result["vw_employee_analysis"] = pd.read_sql_query(
            'SELECT * FROM "vw_employee_analysis"', connection)
    from .cleaning import clean_tables

    cleaned, audit = clean_tables({name: result[name] for name in TABLE_NAMES})
    result.update(cleaned)
    result["cleaning_audit"] = audit
    result.update(_compatibility_frames(result))
    return result


def generate_synthetic_db(db_path: str | Path, seed: int = 42) -> dict[str, int]:
    """Generate a temporary/test database using the same Step 8 schema.

    Normal dashboard startup never calls this helper. Use the explicit
    project-root command ``python generate_data.py`` to regenerate exports.
    """
    from .generate_data import make_tables, materialize_sqlite

    path = Path(db_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tables = make_tables(random.Random(seed))
    materialize_sqlite(tables, path)
    return {name: len(rows) for name, rows in tables.items()}
