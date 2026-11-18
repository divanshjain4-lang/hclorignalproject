"""UI-05: evidence-backed summaries for the current filtered cohort."""
import numpy as np
import streamlit as st

from src.analytics import leadership_comparison, tenure_band
from src.metrics import outcome_chi_square, pay_gap_percent, target_gap_table
from src.page_data import page_context
from src.ui import render_header, render_insight_box

st.set_page_config(page_title="Insights · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("Evidence Summary", "Current-cohort measures with supporting counts and limitations")
st.info("The data are synthetic. The figures below summarize this filtered cohort and do not establish cause or justify individual employment decisions.")
tables, facts, cohort, filters = page_context()
year = int(filters["reporting_year"])
if cohort.empty:
    st.warning("No evidence can be summarized because the selected cohort is empty.")
    st.stop()

women = int(cohort.gender.eq("Female").sum())
share = women / len(cohort)
leadership = leadership_comparison(cohort)
st.subheader("Representation")
render_insight_box("Women’s workforce share", f"Women represent {share:.1%} of the selected cohort.",
                   evidence=f"{women} of {len(cohort)} active employees at year end {year}.", tone="blue")
render_insight_box("Leadership comparison",
                   f"Women’s L5+ share is {leadership['percentage_point_gap']:+.1f} percentage points compared with their workforce share.",
                   evidence=f"L5+: {leadership['leadership_women']}/{leadership['leadership_headcount']}; workforce: {women}/{len(cohort)}.", tone="teal")

pay = cohort.dropna(subset=["annual_salary"])
gap = pay_gap_percent(pay)
st.subheader("Pay and outcomes")
render_insight_box("Unadjusted pay comparison",
                   f"The male-versus-female mean salary gap is {gap:.1f}%." if np.isfinite(gap) else "A male/female mean salary gap is unavailable for this cohort.",
                   evidence=f"Salary records available: {len(pay)} of {len(cohort)} active employees. The metric is not adjusted for role, level or experience.", tone="amber")

current = facts.loc[facts.reporting_year.eq(year)].copy()
current = current.loc[current.department_name.isin(filters["departments"])]
current = current.loc[current.level_name.isin(filters["job_levels"])]
current["tenure_band"] = tenure_band(current.tenure_years_start)
current = current.loc[current.tenure_band.isin(filters["tenure_bands"])]
risk = current.loc[current.active_at_year_start.eq(1)].copy()
risk["outcome"] = risk.exit_in_year.map({1: "Yes", 0: "No"})
if len(risk):
    exit_n = int(risk.exit_in_year.sum())
    render_insight_box("Opening-cohort exits", f"{exit_n / len(risk):.1%} of employees at risk at the start of {year} exited during the year.",
                       evidence=f"{exit_n} exits / {len(risk)} active-at-start employees.", tone="coral")
    result = outcome_chi_square(risk, "outcome", {"Yes"})
    if np.isfinite(result["p_value"]):
        st.caption(f"Female/Male chi-square: χ²={result['statistic']:.3f}, p={result['p_value']:.4g}. {result['interpretation']}")
    else:
        st.caption(result["interpretation"])
else:
    st.info("No opening-cohort records are available for the selected filters.")

target = st.slider("Illustrative women representation target", 0, 80, 40, 5) / 100
scenario = target_gap_table(cohort, target)
additional = int(scenario.additional_women.sum()) if not scenario.empty else 0
render_insight_box("Fixed-headcount target arithmetic",
                   f"The selected cohort would require {additional} additional women to meet the selected target under the stated assumption.",
                   evidence=f"Target {target:.0%}; department-level and job-level estimates summed. Assumes other headcount stays fixed; not a hiring recommendation.", tone="blue")
st.caption("When subgroup counts are small or a test is unavailable, use the descriptive counts as context and avoid broad conclusions. Ask whether the same pattern appears in other years and comparable roles.")
