"""Data preparation and annual cohort metrics used by the dashboard."""
from __future__ import annotations
import pandas as pd

from .metrics import active_on, safe_rate


def employee_dimension(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    employees = tables["employees"].merge(tables["departments"], on="dept_id").merge(tables["job_levels"], on="level_id")
    employees["join_date"] = pd.to_datetime(employees["join_date"])
    employees["exit_date"] = pd.to_datetime(employees["exit_date"], errors="coerce")
    employees["level_rank"] = employees["rank"]
    employees["tenure_years"] = ((pd.Timestamp("2025-12-31") - employees["join_date"]).dt.days / 365.25).clip(lower=0)
    return employees


def active_for_year(employees: pd.DataFrame, year: int) -> pd.DataFrame:
    cohort = employees.loc[active_on(employees, pd.Timestamp(year, 12, 31))].copy()
    cohort["tenure_years"] = ((pd.Timestamp(year, 12, 31) - cohort["join_date"]).dt.days / 365.25).clip(lower=0)
    return cohort


def annual_representation(employees: pd.DataFrame, years=range(2021, 2026)) -> pd.DataFrame:
    rows = []
    for year in years:
        cohort = active_for_year(employees, int(year))
        grouped = cohort.groupby("gender").size().rename("headcount").reset_index()
        total = int(grouped.headcount.sum())
        grouped["year"] = int(year)
        grouped["share"] = grouped.headcount / total if total else 0
        rows.append(grouped)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["gender", "headcount", "year", "share"])


def employee_year_frame(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join annual fact snapshots to employee, department and job-level context."""
    facts = tables.get("EmployeeYear", tables.get("employee_years"))
    people = tables.get("Employee", tables.get("employees"))
    departments = tables.get("Department", tables.get("departments"))
    levels = tables.get("JobLevel", tables.get("job_levels"))
    if any(frame is None for frame in (facts, people, departments, levels)):
        raise KeyError("EmployeeYear, Employee, Department and JobLevel data are required")
    data = facts.merge(people, on="emp_id", how="left", validate="many_to_one")
    data = data.merge(departments[["dept_id", "department_name"]], on="dept_id", how="left", validate="many_to_one")
    level_cols = ["level_id", "level_name", "level_rank", "is_leadership"]
    data = data.merge(levels[level_cols], on="level_id", how="left", validate="many_to_one")
    data["rank"] = data["level_rank"]
    data["role"] = data["job_role"]
    data["year"] = data["reporting_year"]
    data["annual_salary"] = data["annual_salary_inr"]
    data["rating"] = data["performance_rating"]
    data["tenure_years"] = data["tenure_years_end"].fillna(data["tenure_years_start"])
    return data


def active_cohort_for_year(tables: dict[str, pd.DataFrame], year: int,
                           departments: list[str] | None = None,
                           levels: list[str] | None = None,
                           tenure_bands: list[str] | None = None) -> pd.DataFrame:
    """Return the approved year-end active cohort with optional shared filters."""
    cohort = employee_year_frame(tables)
    cohort = cohort.loc[cohort.reporting_year.eq(int(year)) & cohort.active_at_year_end.eq(1)].copy()
    if departments is not None:
        cohort = cohort.loc[cohort.department_name.isin(departments)]
    if levels is not None:
        cohort = cohort.loc[cohort.level_name.isin(levels)]
    cohort["tenure_band"] = tenure_band(cohort["tenure_years_end"])
    if tenure_bands is not None:
        cohort = cohort.loc[cohort.tenure_band.isin(tenure_bands)]
    return cohort


def tenure_band(years: pd.Series) -> pd.Series:
    """Create mutually exclusive 0–2, 3–4 and 5+ year bands from completed tenure."""
    value = pd.to_numeric(years, errors="coerce").apply(lambda x: int(x) if pd.notna(x) and x >= 0 else float("nan"))
    return pd.cut(value, bins=[-0.001, 3, 5, float("inf")], right=False,
                  labels=["0-2 yrs", "3-4 yrs", "5+ yrs"]).astype("string")


def representation_by_department_level(cohort: pd.DataFrame) -> pd.DataFrame:
    """Return gender headcounts and within-department/level shares."""
    groups = ["department_name", "level_name", "gender"]
    result = cohort.groupby(groups, dropna=False, observed=True).size().rename("headcount").reset_index()
    totals = result.groupby(groups[:2], dropna=False, observed=True).headcount.transform("sum")
    result["share"] = result.headcount.div(totals.where(totals.ne(0), 1))
    return result


def leadership_comparison(cohort: pd.DataFrame) -> dict[str, float | int]:
    """Compare women’s leadership and workforce shares with counts and pp gap."""
    leadership = cohort.loc[cohort["is_leadership"].astype(bool)]
    workforce_n = int(len(cohort))
    leadership_n = int(len(leadership))
    workforce_women = int(cohort.gender.eq("Female").sum())
    leadership_women = int(leadership.gender.eq("Female").sum())
    workforce_share = workforce_women / workforce_n if workforce_n else 0.0
    leadership_share = leadership_women / leadership_n if leadership_n else 0.0
    return {"workforce_headcount": workforce_n, "workforce_women": workforce_women,
            "workforce_women_share": workforce_share, "leadership_headcount": leadership_n,
            "leadership_women": leadership_women, "leadership_women_share": leadership_share,
            "percentage_point_gap": (leadership_share - workforce_share) * 100}


def annual_snapshot_outcomes(tables: dict[str, pd.DataFrame], years=range(2021, 2026)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute exit and eligible-promotion rates using the designed annual fact flags."""
    data = employee_year_frame(tables)
    attrition = data.loc[data.reporting_year.isin(years)].groupby(
        ["reporting_year", "gender", "department_name"], dropna=False).agg(
            at_risk=("active_at_year_start", "sum"), exits=("exit_in_year", "sum")).reset_index()
    attrition = attrition.rename(columns={"reporting_year": "year"})
    attrition["attrition_rate"] = attrition.apply(lambda r: safe_rate(r.exits, r.at_risk), axis=1)
    promos = data.loc[data.reporting_year.isin(years)].groupby(
        ["reporting_year", "gender", "department_name"], dropna=False).agg(
            eligible=("promotion_eligible", "sum"), promotions=("promoted", "sum")).reset_index()
    promos = promos.rename(columns={"reporting_year": "year"})
    promos["promotion_rate"] = promos.apply(lambda r: safe_rate(r.promotions, r.eligible), axis=1)
    return attrition, promos


def hiring_funnel(applicants: pd.DataFrame, departments: pd.DataFrame | None = None) -> pd.DataFrame:
    stage_order = ["Applied", "Shortlisted", "Offered", "Joined"]
    ranks = {stage: rank for rank, stage in enumerate(stage_order)}
    data = applicants.copy()
    data["year"] = pd.to_datetime(data["applied_date"]).dt.year
    if departments is not None:
        data = data.merge(departments, on="dept_id", how="left")
        data["department"] = data["department_name"]
    else:
        data["department"] = data["dept_id"].astype(str)
    data["stage_rank"] = data.stage.map(ranks)
    # Applicants at a later stage are included in each preceding funnel step.
    expanded = []
    for target in stage_order:
        reached = data.loc[data.stage_rank.ge(ranks[target])].groupby(["gender", "year", "department"]).size().rename("applicants").reset_index()
        reached["stage"] = target
        reached["stage_rank"] = ranks[target]
        expanded.append(reached)
    result = pd.concat(expanded, ignore_index=True)
    group_cols = ["gender", "year", "department"]
    applied = result.loc[result.stage.eq("Applied"), group_cols + ["applicants"]].rename(
        columns={"applicants": "applied_applicants"})
    result = result.merge(applied, on=group_cols, how="left", validate="many_to_one")
    result["conversion_from_applied"] = result.applicants.div(result.applied_applicants.where(result.applied_applicants.ne(0), 1))
    previous = result[group_cols + ["stage_rank", "applicants"]].copy()
    previous["stage_rank"] += 1
    previous = previous.rename(columns={"applicants": "previous_stage_applicants"})
    result = result.merge(previous, on=group_cols + ["stage_rank"], how="left", validate="one_to_one")
    result["conversion_from_previous"] = result["applicants"].div(
        result["previous_stage_applicants"].where(result["previous_stage_applicants"].ne(0), 1))
    result.loc[result.stage.eq("Applied"), "conversion_from_previous"] = 1.0
    result["previous_stage_applicants"] = result["previous_stage_applicants"].fillna(0).astype(int)
    return result.sort_values(["year", "department", "gender", "stage_rank"])


def yearly_outcomes(employees: pd.DataFrame, promotions: pd.DataFrame, years=range(2021, 2026)) -> tuple[pd.DataFrame, pd.DataFrame]:
    attrition_rows, promotion_rows = [], []
    for year in years:
        start, end = pd.Timestamp(year, 1, 1), pd.Timestamp(year, 12, 31)
        at_risk = employees.loc[employees.join_date.le(start) & (employees.exit_date.isna() | employees.exit_date.ge(start))]
        exits = employees.loc[employees.exit_date.dt.year.eq(year)]
        for gender in ["Female", "Male", "Other"]:
            denominator = int(at_risk.gender.eq(gender).sum())
            numerator = int(exits.gender.eq(gender).sum())
            attrition_rows.append({"year": year, "gender": gender, "at_risk": denominator, "exits": numerator,
                                   "attrition_rate": safe_rate(numerator, denominator)})
        eligible = employees.loc[employees.join_date.le(start) & (employees.exit_date.isna() | employees.exit_date.ge(start)) & employees["rank"].lt(7) & ((start - employees.join_date).dt.days >= 365)]
        promoted_ids = set(promotions.loc[promotions.year.eq(year), "emp_id"])
        year_promotions = promotions.loc[promotions.year.eq(year)]
        for gender in ["Female", "Male", "Other"]:
            denominator = int(eligible.gender.eq(gender).sum())
            numerator = int(year_promotions.emp_id.isin(set(eligible.loc[eligible.gender.eq(gender), "emp_id"]) & promoted_ids).sum())
            promotion_rows.append({"year": year, "gender": gender, "eligible": denominator, "promotions": numerator,
                                   "promotion_rate": safe_rate(numerator, denominator)})
    return pd.DataFrame(attrition_rows), pd.DataFrame(promotion_rows)


def employee_outcomes(employees: pd.DataFrame, promotions: pd.DataFrame, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return person-level synthetic records for valid Female/Male contingency tests."""
    start = pd.Timestamp(year, 1, 1)
    at_risk = employees.loc[employees.join_date.le(start) & (employees.exit_date.isna() | employees.exit_date.ge(start))].copy()
    at_risk["outcome"] = at_risk.exit_date.dt.year.eq(year).map({True: "Yes", False: "No"})
    eligible = at_risk.loc[at_risk["rank"].lt(7) & ((start - at_risk.join_date).dt.days >= 365)].copy()
    promoted_ids = set(promotions.loc[promotions.year.eq(year), "emp_id"])
    eligible["outcome"] = eligible.emp_id.isin(promoted_ids).map({True: "Yes", False: "No"})
    return at_risk, eligible


def latest_pay_frame(tables: dict[str, pd.DataFrame], employees: pd.DataFrame, year: int = 2025) -> pd.DataFrame:
    pay = tables["salaries"].loc[tables["salaries"].year.eq(year)].merge(employees, on="emp_id", suffixes=("", "_employee"))
    appraisals = tables["appraisals"].loc[tables["appraisals"].year.eq(year), ["emp_id", "rating"]]
    return pay.merge(appraisals, on="emp_id", how="left")
