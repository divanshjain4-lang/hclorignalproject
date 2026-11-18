from pathlib import Path
import sqlite3
import pandas as pd

from src.cleaning import clean_tables
from src.validation import validate_database

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"
EXPECTED_TABLES = {"Department", "JobLevel", "Employee", "EmployeeYear", "ApplicantEvent"}


def _load_tables():
    """Load each documented Step 8 table directly from the checked-in SQLite file."""
    with sqlite3.connect(DB_PATH) as connection:
        return {table: pd.read_sql_query(f'SELECT * FROM "{table}"', connection) for table in EXPECTED_TABLES}


def test_app_database_loads_all_documented_tables():
    tables = _load_tables()
    assert set(tables) == EXPECTED_TABLES
    assert all(isinstance(frame, pd.DataFrame) for frame in tables.values())


def test_database_table_counts_match_seeded_design():
    tables = _load_tables()
    assert len(tables["Department"]) == 8
    assert len(tables["JobLevel"]) == 7
    assert len(tables["Employee"]) == 800
    assert len(tables["EmployeeYear"]) >= 150
    assert len(tables["ApplicantEvent"]) == 5000


def test_database_columns_match_documented_design():
    expected = {"emp_id", "gender", "join_date", "exit_date", "total_experience_years", "education_level"}
    assert set(_load_tables()["Employee"].columns) == expected
    assert _load_tables()["EmployeeYear"].shape[1] == 17


def test_primary_keys_and_composite_keys_are_unique():
    keys = {"Department": ["dept_id"], "JobLevel": ["level_id"], "Employee": ["emp_id"],
            "EmployeeYear": ["emp_id", "reporting_year"], "ApplicantEvent": ["applicant_id"]}
    tables = _load_tables()
    for table, columns in keys.items():
        assert not tables[table].duplicated(columns).any(), f"Duplicate key in {table}: {columns}"


def test_foreign_keys_are_valid():
    with sqlite3.connect(DB_PATH) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_genders_are_standardized_and_salary_values_valid():
    tables = _load_tables()
    assert set(tables["Employee"].gender) <= {"Female", "Male", "Other"}
    assert set(tables["ApplicantEvent"].gender) <= {"Female", "Male", "Other"}
    salaries = tables["EmployeeYear"].annual_salary_inr.dropna()
    assert salaries.gt(0).all()


def test_data_has_no_duplicate_employee_primary_key():
    assert not _load_tables()["Employee"].emp_id.duplicated().any()


def test_cleaning_standardizes_gender_and_keeps_unknown_categories():
    source = {"Employee": pd.DataFrame({"emp_id": ["E1", "E2", "E3", "E4"],
                                        "gender": [" f ", "WOMEN", "Male ", "Agender"]})}
    cleaned, audit = clean_tables(source)
    assert cleaned["Employee"].gender.tolist() == ["Female", "Female", "Male", "Agender"]
    assert len(cleaned["Employee"]) == 4
    assert audit.loc[0, "rows_dropped"] == 0
    assert audit.loc[0, "unrecognized_gender_labels"] == 1


def test_cleaning_parses_dates_and_reports_invalid_values():
    source = {"Employee": pd.DataFrame({"emp_id": ["E1", "E2"], "gender": ["Female", "Male"],
                                        "join_date": ["2021-03-01", "not-a-date"]})}
    cleaned, audit = clean_tables(source)
    assert pd.notna(cleaned["Employee"].join_date.iloc[0])
    assert pd.isna(cleaned["Employee"].join_date.iloc[1])
    assert audit.loc[0, "invalid_dates_coerced"] == 1


def test_validation_report_passes_checked_in_database():
    result = validate_database(DB_PATH)
    assert result["status"] == "PASS"
    assert result["foreign_key_status"] == "PASS"
    assert result["row_counts"]["EmployeeYear"] == 3019
