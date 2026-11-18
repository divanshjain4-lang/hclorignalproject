"""Reusable Tailwind-styled UI helpers for Gender Diversity Analysis.

All iframe HTML is static project markup plus HTML-escaped display strings.
Do not pass uploaded, database, query-string, or LLM-produced HTML to iframe().
"""
from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st

# Okabe-Ito inspired, colorblind-friendly grouping palette shared with Plotly.
GENDER_COLORS = {
    "Female": "#0072B2",
    "Male": "#E69F00",
    "Other": "#009E73",
}
THEME = {
    "ink": "#172B4D",
    "muted": "#53657D",
    "blue": "#0072B2",
    "teal": "#009E73",
    "amber": "#E69F00",
    "coral": "#D55E00",
    "surface": "#FFFFFF",
    "page": "#F5F7FA",
}
TAILWIND_CDN = "https://cdn.tailwindcss.com"


def _shell(content: str, *, title: str, extra_styles: str = "") -> str:
    """Return trusted static HTML with Tailwind and readable fallback styles."""
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="{TAILWIND_CDN}"></script>
<style>
  html,body{{margin:0;background:transparent;color:{THEME['ink']};font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}}
  .fallback-card{{background:#fff;border:1px solid #d8e1eb;border-radius:14px;padding:16px 18px;box-shadow:0 2px 8px rgba(23,43,77,.06)}}
  .fallback-muted{{color:{THEME['muted']}}}
  {extra_styles}
</style><title>{safe_title}</title></head><body>{content}</body></html>"""


def _iframe(html: str, *, height: int, alt: str) -> None:
    """Embed a small, self-contained HTML component in Streamlit."""
    st.iframe(html, width="stretch", height=height, alt=alt)


def render_header(title: str, subtitle: str, *, eyebrow: str = "GENDER DIVERSITY ANALYSIS") -> None:
    """Render the application header and context label."""
    safe_title, safe_subtitle, safe_eyebrow = map(escape, (title, subtitle, eyebrow))
    body = f"""<header class="fallback-card flex flex-col gap-1 border-l-4" style="border-left-color:{THEME['blue']}">
      <div class="text-xs font-bold tracking-[.14em] text-sky-700">{safe_eyebrow}</div>
      <h1 class="m-0 text-2xl font-bold tracking-tight text-slate-900">{safe_title}</h1>
      <p class="m-0 text-sm fallback-muted">{safe_subtitle}</p>
    </header>"""
    _iframe(_shell(body, title=title), height=142, alt=f"Page header: {title}")


def render_kpi_card(label: str, value: str, *, delta: str = "", note: str = "") -> None:
    """Render one responsive metric card; values are escaped before embedding."""
    safe_label, safe_value, safe_delta, safe_note = map(escape, (label, value, delta, note))
    delta_html = f'<p class="mt-2 text-xs font-semibold text-teal-700">{safe_delta}</p>' if safe_delta else ""
    note_html = f'<p class="mt-1 text-xs fallback-muted">{safe_note}</p>' if safe_note else ""
    body = f"""<article class="fallback-card min-h-28">
      <p class="m-0 text-xs font-semibold uppercase tracking-wide fallback-muted">{safe_label}</p>
      <p class="mb-0 mt-2 text-3xl font-bold tracking-tight text-slate-900">{safe_value}</p>
      {delta_html}{note_html}
    </article>"""
    _iframe(_shell(body, title=label), height=154, alt=f"KPI card: {label}, {value}")


def render_kpi_row(metrics: Iterable[dict[str, str]]) -> None:
    """Render a row of native Streamlit columns, one iframe card per metric."""
    metric_list = list(metrics)
    if not metric_list:
        return
    cols = st.columns(len(metric_list), gap="small")
    for col, metric in zip(cols, metric_list):
        with col:
            render_kpi_card(
                metric.get("label", "Metric"),
                metric.get("value", "—"),
                delta=metric.get("delta", ""),
                note=metric.get("note", ""),
            )


def render_insight_box(title: str, message: str, *, evidence: str = "", tone: str = "blue") -> None:
    """Render a compact narrative insight with its evidence and caveat."""
    accents = {"blue": THEME["blue"], "teal": THEME["teal"], "amber": THEME["amber"], "coral": THEME["coral"]}
    accent = accents.get(tone, THEME["blue"])
    safe_title, safe_message, safe_evidence = map(escape, (title, message, evidence))
    evidence_html = f'<p class="mb-0 mt-2 text-xs fallback-muted">{safe_evidence}</p>' if safe_evidence else ""
    body = f"""<aside class="fallback-card" style="border-left:4px solid {accent}">
      <h3 class="m-0 text-base font-bold text-slate-900">{safe_title}</h3>
      <p class="mb-0 mt-2 text-sm text-slate-700">{safe_message}</p>{evidence_html}
    </aside>"""
    _iframe(_shell(body, title=title), height=170, alt=f"Insight: {title}")


def render_shared_filters(
    *, years: Iterable[int], departments: Iterable[str], levels: Iterable[str], tenure_bands: Iterable[str]
) -> dict[str, object]:
    """Build shared filter widgets with stable session-state keys.

    Call once from each analysis page, after the page title is set. Streamlit
    retains these keyed selections when a user moves between multipage screens.
    """
    year_options = list(years)
    dept_options = sorted(set(departments))
    level_options = list(levels)
    tenure_options = list(tenure_bands)
    with st.sidebar:
        st.header("Shared filters")
        year = st.selectbox("Reporting year", year_options, index=len(year_options) - 1 if year_options else 0,
                            key="ui_reporting_year") if year_options else None
        selected_departments = st.multiselect("Department", dept_options, default=dept_options,
                                              key="ui_departments")
        selected_levels = st.multiselect("Job level", level_options, default=level_options,
                                         key="ui_job_levels")
        selected_tenure = st.multiselect("Tenure band", tenure_options, default=tenure_options,
                                         key="ui_tenure_bands")
        st.caption("Selections are shared across analysis pages for this session.")
    return {
        "reporting_year": year,
        "departments": selected_departments,
        "job_levels": selected_levels,
        "tenure_bands": selected_tenure,
    }
