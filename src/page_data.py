"""Shared cached data and page filters for the eight dashboard screens."""
from pathlib import Path

import streamlit as st

from .analytics import active_cohort_for_year, employee_year_frame
from .database import DEFAULT_DB_PATH, load_dataset
from .ui import render_shared_filters


@st.cache_data(show_spinner="Loading synthetic workforce data…")
def _load_tables(path: str, modified: float):
    return load_dataset(path)


def page_context():
    """Load tables and return the shared-filtered annual active cohort."""
    path = Path(DEFAULT_DB_PATH)
    if not path.is_file():
        st.error("The project database is missing. Run `python generate_data.py` from the project folder.")
        st.stop()
    tables = _load_tables(str(path), path.stat().st_mtime)
    facts = employee_year_frame(tables)
    years = sorted(facts.reporting_year.dropna().astype(int).unique().tolist())
    departments = sorted(facts.department_name.dropna().unique().tolist())
    levels = (facts[["level_name", "level_rank"]].drop_duplicates()
              .sort_values("level_rank").level_name.tolist())
    filters = render_shared_filters(years=years, departments=departments, levels=levels,
                                   tenure_bands=["0-2 yrs", "3-4 yrs", "5+ yrs"])
    cohort = active_cohort_for_year(tables, filters["reporting_year"],
                                    filters["departments"], filters["job_levels"], filters["tenure_bands"])
    return tables, facts, cohort, filters
