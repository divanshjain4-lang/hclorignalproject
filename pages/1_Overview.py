"""UI-01: year-end overview and headline cohort measures."""
import plotly.express as px
import streamlit as st

from src.metrics import pay_gap_percent, safe_rate
from src.page_data import page_context
from src.ui import GENDER_COLORS, render_header

st.set_page_config(page_title="Overview · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("Overview", "Year-end representation, pay and workforce outcomes")
st.info("All records are synthetic. Aggregate patterns are descriptive and do not establish causation or guide individual employment decisions.")

tables, facts, cohort, filters = page_context()
year = int(filters["reporting_year"])
if cohort.empty:
    st.warning("No employees match these filters. Expand the department, job-level or tenure selections.")
    st.stop()

salary = cohort.dropna(subset=["annual_salary"]).copy()
female_share = float(cohort.gender.eq("Female").mean())
pay_gap = pay_gap_percent(salary.rename(columns={"annual_salary": "annual_salary"})) if not salary.empty else float("nan")
year_fact = facts.loc[facts.reporting_year.eq(year)]
if filters["departments"]:
    year_fact = year_fact.loc[year_fact.department_name.isin(filters["departments"])]
attrition_num = int(year_fact.exit_in_year.sum())
attrition_den = int(year_fact.active_at_year_start.sum())
cards = st.columns(4)
cards[0].metric("Active headcount", f"{len(cohort):,}", help=f"Year-end active employees in {year}.")
cards[1].metric("Women representation", f"{female_share:.1%}", help=f"{int(cohort.gender.eq('Female').sum())} women / {len(cohort)} employees.")
cards[2].metric("Unadjusted pay gap", f"{pay_gap:.1f}%" if pay_gap == pay_gap else "N/A",
                help="(Male mean salary − Female mean salary) / Male mean salary; descriptive and unadjusted.")
cards[3].metric("Attrition rate", f"{safe_rate(attrition_num, attrition_den):.1%}",
                help=f"{attrition_num} exits / {attrition_den} employees active at year start in the selected departments.")

left, right = st.columns(2)
with left:
    gender = cohort.groupby("gender", as_index=False).size().rename(columns={"size": "Headcount"})
    st.plotly_chart(px.pie(gender, names="gender", values="Headcount", hole=.48,
                           title=f"Gender distribution · {year}", color="gender", color_discrete_map=GENDER_COLORS),
                    width="stretch")
with right:
    dept = cohort.groupby(["department_name", "gender"], as_index=False).size().rename(columns={"size": "Headcount"})
    st.plotly_chart(px.bar(dept, x="department_name", y="Headcount", color="gender", barmode="stack",
                           title="Departmental representation", text_auto=True, color_discrete_map=GENDER_COLORS,
                           labels={"department_name": "Department"}), width="stretch")

pipeline = cohort.groupby(["level_name", "level_rank", "gender"], as_index=False).size().rename(columns={"size": "Headcount"})
pipeline["Share"] = pipeline["Headcount"] / pipeline.groupby("level_name")["Headcount"].transform("sum")
pipeline = pipeline.sort_values("level_rank")
st.plotly_chart(px.bar(pipeline, x="level_name", y="Share", color="gender", barmode="stack",
                       title="Gender representation across the career pipeline", text=pipeline.Share.map(lambda v: f"{v:.0%}"),
                       color_discrete_map=GENDER_COLORS, labels={"level_name": "Job level", "Share": "Employees (%)"}),
                width="stretch")
st.caption("Pay gap uses the selected year-end cohort with an available annual salary. Rates display numerator and denominator in metric help text.")
