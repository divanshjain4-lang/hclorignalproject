"""UI-08: project notes, metric definitions and safe-use limits."""
import streamlit as st

from src.ui import render_header

st.set_page_config(page_title="About · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("About & Definitions", "Scope, data provenance, questions and metric rules")
st.warning("The approved Step 2 HMW wording, Step 6 PRD and issued project ID were not available in the build workspace. The analysis questions and project ID remain provisional until reconciled.")
st.subheader("Purpose and data")
st.write("This academic dashboard demonstrates aggregate analysis of workforce representation, hiring, pay, promotion, attrition and performance.")
st.write("The data are synthetic and generated with a fixed seed. Designed patterns are teaching examples; they are not evidence about any real employer or group.")
st.write("The database contains Department, JobLevel, Employee, EmployeeYear and ApplicantEvent. Employee-year snapshots support trend measures; applicant events store the final stage reached.")

st.subheader("Analysis questions")
questions = [
    ("OQ-01", "How does year-end gender representation change from 2021 to 2025?"),
    ("OQ-02", "How is gender represented within each department and job level?"),
    ("OQ-03", "How does women’s share of L5+ leadership compare with their workforce share?"),
    ("OQ-04", "How many applicants of each gender reach each recorded hiring stage?"),
    ("OQ-05", "How do mean, median and distribution of annual salary compare by gender within level?"),
    ("OQ-06", "What gender association remains in log salary after controlling for level, department, tenure, education and rating?"),
    ("OQ-07", "What proportion of the eligible opening cohort is promoted, by gender?"),
    ("OQ-08", "What proportion of the opening at-risk cohort exits, by gender, department and tenure band?"),
    ("OQ-09", "How do annual performance rating distributions compare by gender?"),
    ("OQ-10", "What added women headcount would reach a selected representation target if other headcount stayed fixed?"),
]
st.dataframe(questions, column_config={0: "ID", 1: "Question"}, hide_index=True, width="stretch")

st.subheader("Metric definitions")
st.markdown("""
- **Year-end active:** active at the December 31 snapshot, using the EmployeeYear source flag.
- **Representation share:** gender headcount divided by selected year-end headcount.
- **Leadership:** levels marked leadership in the JobLevel master (L5 and above in this project).
- **Unadjusted pay gap:** (male mean annual salary − female mean annual salary) ÷ male mean annual salary. Missing salary rows are excluded and the remaining sample is shown.
- **Adjusted pay model:** OLS of log annual salary with gender, tenure, categorical job level, department, education and rating; HC3 robust standard errors and confidence intervals. The model is an association.
- **Promotion rate:** promoted employees divided by the source-flagged eligible population (active at year start, at least one year tenure, below L7).
- **Attrition rate:** exits during the year divided by employees active at the start of that year.
- **Hiring conversion:** final-stage count divided by applications; stage-to-stage conversion uses the preceding stage count. Applicant-level transition dates are not available.
- **Tenure bands:** completed years grouped as 0–2, 3–4 and 5+ years.
- **Target scenario:** ceil((target × current headcount − women) ÷ (1 − target)), floored at zero; assumes other headcount stays fixed.
""")
st.subheader("Methods and limitations")
st.write("Mann–Whitney U compares two independent distributions; Welch’s t-test compares means; chi-square tests are withheld as unreliable when expected counts are sparse. Model intervals and p-values depend on model assumptions.")
st.write("Small subgroups are volatile. `Other` gender is retained in descriptive views; Female/Male-only tests are clearly identified. Statistical significance does not prove causation, discrimination or a need for any individual employment action.")
st.caption("Pending approval: source HMW and PRD reconciliation, final project ID, business target approval, and any real-data governance/privacy review.")
