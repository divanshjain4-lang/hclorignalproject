"""UI-04: hiring, pay, promotion, attrition and performance analyses."""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import hiring_funnel, tenure_band
from src.metrics import adjusted_pay_model, gender_effect, outcome_chi_square, performance_test, salary_tests
from src.page_data import page_context
from src.ui import GENDER_COLORS, render_header

st.set_page_config(page_title="EDA & Statistics · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("EDA & Statistics", "Descriptive comparisons and guarded statistical tests")
st.info("Statistical associations do not establish causation. Small subgroup results may be unstable.")
tables, facts, cohort, filters = page_context()
year = int(filters["reporting_year"])
departments, levels, bands = filters["departments"], filters["job_levels"], filters["tenure_bands"]
if cohort.empty:
    st.warning("No employees match these filters. Expand the shared sidebar selections.")

# Hiring funnel counts are grouped by application year and destination department.
funnel = hiring_funnel(tables["applicants"], tables["departments"])
funnel = funnel.loc[funnel.year.eq(year) & funnel.department.isin(departments)]
if funnel.empty:
    st.warning("No applicants match the selected year and departments.")
else:
    st.plotly_chart(px.bar(funnel, x="stage", y="applicants", color="gender", barmode="group", text_auto=True,
                           title=f"Hiring stage counts · {year}", color_discrete_map=GENDER_COLORS), width="stretch")
    conv = funnel.groupby(["stage", "gender"], as_index=False).agg(
        reached=("applicants", "sum"), applied=("applied_applicants", "sum"),
        prior=("previous_stage_applicants", "sum"))
    conv["from_applied"] = conv.reached.div(conv.applied.replace(0, np.nan))
    conv["from_prior_stage"] = conv.reached.div(conv.prior.replace(0, np.nan)).fillna(1)
    st.dataframe(conv, hide_index=True, width="stretch")

pay = cohort.dropna(subset=["annual_salary"]).copy()
if pay.empty:
    st.warning("No salary observations are available for this cohort.")
else:
    st.plotly_chart(px.violin(pay, x="level_name", y="annual_salary", color="gender", box=True, points="outliers",
                              title=f"Annual salary distribution by level · {year}", color_discrete_map=GENDER_COLORS,
                              labels={"annual_salary": "Annual salary (INR)", "level_name": "Job level"}), width="stretch")
    salary_summary = pay.groupby(["level_name", "gender"], as_index=False).annual_salary.agg(
        headcount="count", mean_salary="mean", median_salary="median")
    st.dataframe(salary_summary, hide_index=True, width="stretch")
    st.subheader("Within-level unadjusted tests")
    tests = pd.DataFrame(salary_tests(pay.rename(columns={"annual_salary": "annual_salary"})))
    if tests.empty:
        st.caption("Each job level requires at least two Female and two Male salary observations for these tests.")
    else:
        st.dataframe(tests, hide_index=True, width="stretch")
        st.caption("Mann–Whitney U compares distributions; Welch’s t-test compares means. Neither adjusts for tenure or other factors.")

# Outcome analyses use the opening workforce and the source-provided eligibility flags.
outcomes = facts.loc[facts.reporting_year.eq(year)].copy()
outcomes["tenure_band"] = tenure_band(outcomes.tenure_years_start)
for col, allowed in (("department_name", departments), ("level_name", levels), ("tenure_band", bands)):
    outcomes = outcomes.loc[outcomes[col].isin(allowed)]
at_risk = outcomes.loc[outcomes.active_at_year_start.eq(1)].copy()
eligible = at_risk.loc[at_risk.promotion_eligible.eq(1)].copy()
at_risk["outcome"] = at_risk.exit_in_year.map({1: "Yes", 0: "No"})
eligible["outcome"] = eligible.promoted.map({1: "Yes", 0: "No"})
for heading, frame, flag, numerator, denominator in (
    ("Attrition", at_risk, "exit_in_year", "exits", "at-risk employees"),
    ("Promotion among eligible employees", eligible, "promoted", "promotions", "eligible employees"),
):
    st.subheader(f"{heading} · {year}")
    summary = frame.groupby("gender", as_index=False).agg(**{numerator: (flag, "sum"), denominator: (flag, "size")})
    summary["rate"] = summary[numerator].div(summary[denominator].replace(0, np.nan))
    st.dataframe(summary, hide_index=True, width="stretch")
    test = outcome_chi_square(frame, "outcome", {"Yes"})
    st.caption(f"{test['interpretation']} χ²={test['statistic']:.3f}; p={test['p_value']:.4g}." if np.isfinite(test["p_value"]) else test["interpretation"])

# Adjusted OLS is fitted on the annual sample, with categorical education and HC3 uncertainty.
model_data = facts.loc[facts.reporting_year.eq(year)].copy()
for col, allowed in (("department_name", departments), ("level_name", levels),):
    model_data = model_data.loc[model_data[col].isin(allowed)]
model_data = model_data.rename(columns={"education_level": "education"})
st.subheader("Adjusted log-salary regression")
try:
    model = adjusted_pay_model(model_data)
    effect = gender_effect(model)
    st.dataframe(pd.DataFrame([effect]), hide_index=True, width="stretch")
    st.caption(f"OLS with HC3 robust standard errors; n={effect['n']}. Coefficient is a model association, not causal evidence.")
except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
    st.warning(f"Adjusted model is unavailable for this filtered sample: {exc}")

ratings = cohort.dropna(subset=["rating"])
if ratings.empty:
    st.info("No performance ratings are available for this cohort.")
else:
    rating_counts = ratings.groupby(["rating", "gender"], as_index=False).size().rename(columns={"size": "Employees"})
    st.plotly_chart(px.bar(rating_counts, x="rating", y="Employees", color="gender", barmode="group",
                           title="Performance rating distribution", color_discrete_map=GENDER_COLORS), width="stretch")
    st.write("Mann–Whitney U p-value:", f"{performance_test(ratings)['mann_whitney_p']:.4g}")
