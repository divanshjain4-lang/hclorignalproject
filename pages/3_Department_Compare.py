"""UI-03: compare department and job-level representation and pay."""
import plotly.express as px
import streamlit as st

from src.page_data import page_context
from src.ui import GENDER_COLORS, render_header

st.set_page_config(page_title="Department Compare · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("Department Comparison", "Compare representation and salary across filtered departments and levels")
tables, facts, cohort, filters = page_context()
year = int(filters["reporting_year"])
if cohort.empty:
    st.warning("No employees match these filters.")
    st.stop()

counts = cohort.groupby(["department_name", "gender"], as_index=False).size().rename(columns={"size": "Headcount"})
st.plotly_chart(px.bar(counts, x="department_name", y="Headcount", color="gender", barmode="group", text_auto=True,
                       title=f"Department headcount by gender · {year}", color_discrete_map=GENDER_COLORS,
                       labels={"department_name": "Department"}), width="stretch")

level_share = cohort.groupby(["department_name", "level_name", "level_rank", "gender"], as_index=False).size().rename(columns={"size": "Headcount"})
level_share["share"] = level_share.Headcount / level_share.groupby(["department_name", "level_name"]).Headcount.transform("sum")
women = level_share.loc[level_share.gender.eq("Female")]
st.plotly_chart(px.density_heatmap(women, x="level_name", y="department_name", z="share", histfunc="avg",
                                  title="Women’s share within department and job level", color_continuous_scale="Blues",
                                  labels={"share": "Women’s share", "level_name": "Job level", "department_name": "Department"}),
                width="stretch")
st.dataframe(women[["department_name", "level_name", "Headcount", "share"]].rename(columns={"share": "Women share"}),
             hide_index=True, width="stretch")

pay = cohort.dropna(subset=["annual_salary"])
if pay.empty:
    st.info("No salary observations are available for these filters.")
else:
    st.plotly_chart(px.box(pay, x="level_name", y="annual_salary", color="gender", points="outliers",
                           title=f"Annual salary distributions by level · {year}", color_discrete_map=GENDER_COLORS,
                           labels={"annual_salary": "Annual salary (INR)", "level_name": "Job level"}), width="stretch")
    pay_summary = pay.groupby(["department_name", "level_name", "gender"]).annual_salary.agg(
        headcount="count", mean_salary="mean", median_salary="median").reset_index()
    st.dataframe(pay_summary, hide_index=True, width="stretch")
st.caption("Department and level comparisons are descriptive. Salary observations may be missing; headcount and salary sample size are shown separately.")
