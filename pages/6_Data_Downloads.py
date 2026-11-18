"""UI-06: preview and download filtered aggregate summaries."""
import streamlit as st

from src.exports import build_aggregate_exports
from src.page_data import page_context
from src.ui import render_header

st.set_page_config(page_title="Data & Downloads · Gender Diversity", page_icon="⚖️", layout="wide")
render_header("Data & Downloads", "Export aggregate summaries for the selected period and shared filters")
st.info("The included records are synthetic. Downloads contain grouped summaries and omit employee identifiers.")
tables, facts, cohort, filters = page_context()
year = int(filters["reporting_year"])

exports = build_aggregate_exports(facts, cohort, year, filters["departments"], filters["job_levels"], filters["tenure_bands"])
choice = st.selectbox("Aggregate to preview and download", list(exports))
preview = exports[choice]
st.caption(f"Reporting year: {year} · aggregate rows: {len(preview)} · scope follows shared sidebar filters.")
st.dataframe(preview, hide_index=True, width="stretch")
filename = {"Representation aggregate": "representation_aggregate.csv", "Pay aggregate": "pay_aggregate.csv",
            "Outcome aggregate": "outcome_aggregate.csv"}[choice]
st.download_button("Download preview as CSV", preview.to_csv(index=False).encode("utf-8-sig"),
                   file_name=filename, mime="text/csv", disabled=preview.empty)
if preview.empty:
    st.info("No rows match the current filters; the download is disabled.")
