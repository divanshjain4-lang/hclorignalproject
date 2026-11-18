"""UI-02: representation pipeline, trend and target scenarios."""
import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import leadership_comparison, tenure_band
from src.metrics import target_gap_table
from src.page_data import page_context
from src.ui import GENDER_COLORS, render_header

st.set_page_config(page_title="Representation · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("Representation & Career Pipeline", "Year-end gender shares by level, with a trend and target scenario")
tables, facts, cohort, filters = page_context()
year = int(filters["reporting_year"])
if cohort.empty:
    st.warning("No employees match these filters.")
    st.stop()

pipeline = cohort.groupby(["level_name", "level_rank", "gender"], as_index=False).size().rename(columns={"size": "Headcount"})
pipeline["Share"] = pipeline.Headcount / pipeline.groupby("level_name").Headcount.transform("sum")
pipeline = pipeline.sort_values("level_rank")
st.plotly_chart(px.bar(pipeline, x="level_name", y="Share", color="gender", barmode="stack", text=pipeline.Share.map(lambda v: f"{v:.0%}"),
                       title=f"Year-end workforce pipeline · {year}", color_discrete_map=GENDER_COLORS,
                       labels={"level_name": "Job level", "Share": "Employees (%)"}), width="stretch")

trends = facts.loc[facts.active_at_year_end.eq(1)].copy()
trends["tenure_band"] = tenure_band(trends.tenure_years_end)
trends = trends.loc[trends.department_name.isin(filters["departments"])]
trends = trends.loc[trends.level_name.isin(filters["job_levels"])]
trends = trends.loc[trends.tenure_band.isin(filters["tenure_bands"])]
trend = trends.groupby(["reporting_year", "gender"]).size().rename("headcount").reset_index()
trend["share"] = trend.headcount / trend.groupby("reporting_year").headcount.transform("sum")
st.plotly_chart(px.line(trend, x="reporting_year", y="share", color="gender", markers=True,
                        title="Gender representation trend", color_discrete_map=GENDER_COLORS,
                        labels={"reporting_year": "Year", "share": "Workforce share"}), width="stretch")

summary = leadership_comparison(cohort)
c1, c2, c3 = st.columns(3)
c1.metric("Women in selected workforce", f"{summary['workforce_women_share']:.1%}",
          help=f"{summary['workforce_women']} / {summary['workforce_headcount']} active employees")
c2.metric("Women in L5+ leadership", f"{summary['leadership_women_share']:.1%}",
          help=f"{summary['leadership_women']} / {summary['leadership_headcount']} active L5+ employees")
c3.metric("Leadership minus workforce", f"{summary['percentage_point_gap']:+.1f} pp")

target = st.slider("Women representation target", 0, 80, 40, 5) / 100
gaps = target_gap_table(cohort, target).sort_values("additional_women", ascending=False)
st.subheader("Illustrative added-headcount scenario")
st.dataframe(gaps, hide_index=True, width="stretch")
st.caption("Scenario assumes existing headcount remains fixed and added hires are women; it is arithmetic, not a hiring recommendation. Small groups can produce volatile shares.")
