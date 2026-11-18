"""Multipage entry point for the synthetic Gender Diversity Analysis dashboard."""
import numpy as np
import plotly.express as px
import streamlit as st

from src.analytics import tenure_band
from src.metrics import pay_gap_percent, safe_rate
from src.page_data import page_context
from src.ui import GENDER_COLORS, render_header

st.set_page_config(page_title="Gender Diversity Analysis", page_icon="⚖️", layout="wide")
render_header("Gender Diversity Analysis", "Aggregate representation and pay equity analysis")
st.info("This academic dashboard uses designed synthetic data. Results do not describe a real employer and should not guide individual employment decisions.")
tables, facts, cohort, filters = page_context()
year = int(filters["reporting_year"])

# Headcount and pay describe the selected year-end active cohort.
salary = cohort.dropna(subset=["annual_salary"])
gap = pay_gap_percent(salary) if not salary.empty else float("nan")

# Attrition is measured against the opening cohort, with the same shared scope.
opening = facts.loc[facts.reporting_year.eq(year)].copy()
opening["tenure_band"] = tenure_band(opening.tenure_years_start)
opening = opening.loc[opening.department_name.isin(filters["departments"])]
opening = opening.loc[opening.level_name.isin(filters["job_levels"])]
opening = opening.loc[opening.tenure_band.isin(filters["tenure_bands"])]
opening = opening.loc[opening.active_at_year_start.eq(1)]
exits, at_risk = int(opening.exit_in_year.sum()), len(opening)

kpis = st.columns(4)
kpis[0].metric("Active headcount", f"{len(cohort):,}", help=f"Selected year-end cohort: {year}.")
women = int(cohort.gender.eq("Female").sum())
kpis[1].metric("Women representation", f"{safe_rate(women, len(cohort)):.1%}", help=f"{women} / {len(cohort)} active employees.")
kpis[2].metric("Unadjusted pay gap", f"{gap:.1f}%" if np.isfinite(gap) else "N/A",
               help="(Male mean salary − Female mean salary) / Male mean salary. Not adjusted.")
kpis[3].metric("Overall attrition rate", f"{safe_rate(exits, at_risk):.1%}", help=f"{exits} exits / {at_risk} at-risk employees at year start.")

st.subheader("Explore the dashboard")
links = [
    ("Overview", "pages/1_Overview.py", "Year-end KPIs and cohort summary"),
    ("Representation", "pages/2_Representation.py", "Career pipeline, trends and target scenarios"),
    ("Department Compare", "pages/3_Department_Compare.py", "Department and job-level comparisons"),
    ("EDA & Statistics", "pages/4_EDA_Statistics.py", "Hiring, pay, promotion, attrition and performance"),
    ("Insights", "pages/5_Insights.py", "Evidence summaries for current filters"),
    ("Data & Downloads", "pages/6_Data_Downloads.py", "Preview and export aggregate data"),
    ("Data Quality", "pages/7_Data_Quality.py", "Schema and source validation status"),
    ("About & Definitions", "pages/8_About.py", "Project questions, methods and limits"),
]
cols = st.columns(3)
for index, (label, page, description) in enumerate(links):
    with cols[index % 3]:
        st.page_link(page, label=label, help=description)

if cohort.empty:
    st.warning("No employees match these filters. Expand the shared sidebar selections.")
else:
    distribution = cohort.groupby("gender", as_index=False).size().rename(columns={"size": "Headcount"})
    st.plotly_chart(px.pie(distribution, names="gender", values="Headcount", hole=.5,
                           title=f"Selected cohort · {year}", color="gender", color_discrete_map=GENDER_COLORS), width="stretch")
st.caption("Shared sidebar filters use stable session-state keys and carry between analysis screens. Empty selections return an empty cohort.")
