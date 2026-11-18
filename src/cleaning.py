"""Auditable, non-destructive normalization for the canonical HR tables."""
from __future__ import annotations

from collections.abc import Mapping
import pandas as pd

GENDER_MAP = {
    "female": "Female", "f": "Female", "woman": "Female", "women": "Female",
    "male": "Male", "m": "Male", "man": "Male", "men": "Male",
    "other": "Other", "non-binary": "Other", "nonbinary": "Other",
    "prefer not to say": "Other", "unknown": "Unknown",
}
DATE_COLUMNS = {
    "Employee": ("join_date", "exit_date"),
    "EmployeeYear": ("snapshot_date", "promotion_date"),
    "ApplicantEvent": ("applied_date",),
}
NUMERIC_COLUMNS = {
    "Department": ("dept_id", "target_women_pct"),
    "JobLevel": ("level_id", "level_rank", "is_leadership", "target_women_pct"),
    "Employee": ("total_experience_years",),
    "EmployeeYear": ("reporting_year", "dept_id", "level_id", "active_at_year_start",
                     "active_at_year_end", "hired_in_year", "exit_in_year", "tenure_years_start",
                     "tenure_years_end", "annual_salary_inr", "promotion_eligible", "promoted",
                     "performance_rating"),
    "ApplicantEvent": ("dept_id",),
}


def standardize_gender(value):
    """Map common gender variants; preserve unfamiliar non-empty labels for review."""
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if not text:
        return pd.NA
    return GENDER_MAP.get(text.casefold(), text)


def clean_tables(tables: Mapping[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Normalize whitespace, gender labels, dates and numeric types without dropping rows.

    Returns new DataFrames plus an audit table. Invalid numeric/date values become
    missing in the analysis copy and are counted in the audit; source SQLite data
    is never modified. Unrecognized gender values remain visible for validation.
    """
    cleaned: dict[str, pd.DataFrame] = {}
    audit_rows = []
    for table, frame in tables.items():
        result = frame.copy(deep=True)
        before_rows = len(result)
        for column in result.select_dtypes(include=["object", "string"]).columns:
            result[column] = result[column].map(
                lambda x: x.strip() if isinstance(x, str) else x)
        if "gender" in result.columns:
            original = result["gender"].copy()
            result["gender"] = result["gender"].map(standardize_gender).astype("string")
            changed = int((original.astype("string").fillna("") != result["gender"].fillna("")).sum())
            unknown = int((~result["gender"].isin(["Female", "Male", "Other"]) & result["gender"].notna()).sum())
        else:
            changed = unknown = 0
        invalid_dates = 0
        for column in DATE_COLUMNS.get(table, ()):
            if column in result.columns:
                original = result[column]
                parsed = pd.to_datetime(original, errors="coerce")
                invalid_dates += int((original.notna() & parsed.isna()).sum())
                result[column] = parsed
        invalid_numbers = 0
        for column in NUMERIC_COLUMNS.get(table, ()):
            if column in result.columns:
                original = result[column]
                parsed = pd.to_numeric(original, errors="coerce")
                invalid_numbers += int((original.notna() & parsed.isna()).sum())
                result[column] = parsed
        cleaned[table] = result
        audit_rows.append({
            "table": table, "rows_before": before_rows, "rows_after": len(result),
            "rows_dropped": before_rows - len(result), "gender_labels_standardized": changed,
            "unrecognized_gender_labels": unknown, "invalid_dates_coerced": invalid_dates,
            "invalid_numbers_coerced": invalid_numbers,
        })
    return cleaned, pd.DataFrame(audit_rows)
