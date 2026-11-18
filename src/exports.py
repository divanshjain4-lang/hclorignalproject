"""Aggregate-only CSV export builders used by the Streamlit download page."""
from __future__ import annotations

import pandas as pd

from .analytics import tenure_band


def build_aggregate_exports(facts: pd.DataFrame, cohort: pd.DataFrame, year: int,
                            departments: list[str], levels: list[str], tenure_bands: list[str]) -> dict[str, pd.DataFrame]:
    """Build filtered representation, salary and opening-outcome summaries.

    The outputs intentionally contain no employee or applicant identifiers.
    """
    cohort = cohort.copy()
    cohort = cohort.loc[cohort.department_name.isin(departments)]
    cohort = cohort.loc[cohort.level_name.isin(levels)]
    if "tenure_band" not in cohort:
        cohort["tenure_band"] = tenure_band(cohort.tenure_years_end)
    cohort = cohort.loc[cohort.tenure_band.isin(tenure_bands)]
    representation = cohort.groupby(["department_name", "level_name", "gender"], as_index=False).size()
    representation = representation.rename(columns={"size": "headcount"})
    pay = cohort.dropna(subset=["annual_salary"]).groupby(
        ["department_name", "level_name", "gender"], as_index=False).annual_salary.agg(
            salary_n="count", mean_salary_inr="mean", median_salary_inr="median")
    outcomes = facts.loc[facts.reporting_year.eq(year)].copy()
    outcomes["tenure_band"] = tenure_band(outcomes.tenure_years_start)
    outcomes = outcomes.loc[outcomes.department_name.isin(departments)]
    outcomes = outcomes.loc[outcomes.level_name.isin(levels)]
    outcomes = outcomes.loc[outcomes.tenure_band.isin(tenure_bands)]
    outcomes = outcomes.loc[outcomes.active_at_year_start.eq(1)].groupby(
        ["department_name", "gender", "tenure_band"], as_index=False).agg(
            at_risk=("active_at_year_start", "sum"), exits=("exit_in_year", "sum"),
            promotion_eligible=("promotion_eligible", "sum"), promotions=("promoted", "sum"))
    outcomes["attrition_rate"] = outcomes.exits.div(outcomes.at_risk.where(outcomes.at_risk.ne(0)))
    outcomes["promotion_rate"] = outcomes.promotions.div(
        outcomes.promotion_eligible.where(outcomes.promotion_eligible.ne(0)))
    return {"Representation aggregate": representation, "Pay aggregate": pay, "Outcome aggregate": outcomes}
