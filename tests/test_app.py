from pathlib import Path
import time

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_streamlit_app_starts_and_main_navigation_renders():
    app = AppTest.from_file(str(APP), default_timeout=30).run(timeout=30)
    assert not app.exception
    assert len(app.get("page_link")) >= 7
    assert len(app.metric) == 4


def test_streamlit_app_load_time_is_under_three_seconds():
    started = time.perf_counter()
    app = AppTest.from_file(str(APP), default_timeout=30).run(timeout=30)
    elapsed = time.perf_counter() - started
    assert not app.exception
    assert elapsed < 3.0, f"First render took {elapsed:.2f}s (target <3s)"


def test_dashboard_filter_controls_are_present():
    app = AppTest.from_file(str(APP), default_timeout=30).run(timeout=30)
    labels = {str(widget.label) for widget in app.multiselect}
    assert {"Department", "Job level", "Tenure band"} <= labels
    assert any(str(widget.label) == "Reporting year" for widget in app.selectbox)


def test_dashboard_displays_four_kpis():
    app = AppTest.from_file(str(APP), default_timeout=30).run(timeout=30)
    labels = {str(metric.label) for metric in app.metric}
    assert {"Active headcount", "Women representation", "Unadjusted pay gap", "Overall attrition rate"} <= labels


def test_shared_ui_components_escape_content_and_render_defaults():
    from src.ui import _shell, render_header, render_insight_box, render_kpi_row, render_shared_filters
    script = '''
from src.ui import render_header, render_insight_box, render_kpi_row, render_shared_filters
render_header("Overview <script>", "Synthetic workforce")
render_kpi_row([{"label": "Headcount", "value": "500"}])
render_insight_box("Evidence", "Counts are descriptive")
render_shared_filters(years=[2024, 2025], departments=["Sales"], levels=["L1"], tenure_bands=["0-2 yrs"])
'''
    app = AppTest.from_string(script, default_timeout=20).run(timeout=20)
    assert not app.exception
    assert len(app.selectbox) == 1 and app.selectbox[0].key == "ui_reporting_year"
    assert {widget.key for widget in app.multiselect} == {"ui_departments", "ui_job_levels", "ui_tenure_bands"}
    # The HTML lives in iframe output; source strings must be escaped before embed.
    assert "&lt;script&gt;" in _shell("", title="<script>")


def test_overview_page_renders_kpis_and_charts():
    page = APP.parent / "pages" / "1_Overview.py"
    app = AppTest.from_file(str(page), default_timeout=30).run(timeout=30)
    assert not app.exception
    assert len(app.metric) == 4
    assert len(app.get("plotly_chart")) == 3


def test_representation_and_department_pages_render():
    for name in ("2_Representation.py", "3_Department_Compare.py"):
        app = AppTest.from_file(str(APP.parent / "pages" / name), default_timeout=30).run(timeout=30)
        assert not app.exception, name
        assert len(app.get("plotly_chart")) >= 2, name
        if name == "2_Representation.py":
            assert len(app.metric) == 3


def test_eda_statistics_page_renders_without_exceptions():
    app = AppTest.from_file(str(APP.parent / "pages" / "4_EDA_Statistics.py"), default_timeout=40).run(timeout=40)
    assert not app.exception
    assert len(app.get("plotly_chart")) >= 2


def test_insights_page_renders_evidence_cards():
    app = AppTest.from_file(str(APP.parent / "pages" / "5_Insights.py"), default_timeout=35).run(timeout=35)
    assert not app.exception
    assert len(app.slider) == 1
    assert len(app.get("iframe")) >= 3


def test_aggregate_download_preview_excludes_employee_identifiers():
    page = APP.parent / "pages" / "6_Data_Downloads.py"
    app = AppTest.from_file(str(page), default_timeout=30).run(timeout=30)
    assert not app.exception
    app.selectbox[0].select("Pay aggregate").run()
    assert not app.exception
    assert "emp_id" not in app.dataframe[0].value.columns
    assert app.get("download_button")[0].proto.disabled is False


def test_empty_department_filter_shows_empty_state_on_overview():
    page = APP.parent / "pages" / "1_Overview.py"
    app = AppTest.from_file(str(page), default_timeout=30).run(timeout=30)
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("No employees match" in str(item.value) for item in app.warning)


def test_reporting_year_filter_recalculates_overview_headcount():
    page = APP.parent / "pages" / "1_Overview.py"
    app = AppTest.from_file(str(page), default_timeout=30).run(timeout=30)
    before = app.metric[0].value
    app.selectbox[0].select(2024).run()
    assert not app.exception
    after = app.metric[0].value
    assert before != after


def test_department_and_level_filters_recalculate_overview_headcount():
    page = APP.parent / "pages" / "1_Overview.py"
    app = AppTest.from_file(str(page), default_timeout=30).run(timeout=30)
    original = int(app.metric[0].value.replace(",", ""))
    departments = app.multiselect[0].options
    app.multiselect[0].set_value([departments[0]]).run()
    department_count = int(app.metric[0].value.replace(",", ""))
    assert 0 < department_count < original
    levels = app.multiselect[1].options
    app.multiselect[1].set_value([levels[0]]).run()
    assert int(app.metric[0].value.replace(",", "")) <= department_count


def test_default_overview_headcount_reconciles_to_database():
    from src.analytics import active_cohort_for_year
    from src.database import load_dataset
    tables = load_dataset()
    expected = len(active_cohort_for_year(tables, 2025))
    app = AppTest.from_file(str(APP.parent / "pages" / "1_Overview.py"), default_timeout=30).run(timeout=30)
    assert int(app.metric[0].value.replace(",", "")) == expected


def test_empty_shared_filters_show_empty_state_in_analysis_page():
    page = APP.parent / "pages" / "4_EDA_Statistics.py"
    app = AppTest.from_file(str(page), default_timeout=35).run(timeout=35)
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("No employees match" in str(item.value) for item in app.warning)
    assert any("No applicants match" in str(item.value) for item in app.warning)


def test_data_quality_page_shows_live_status_without_ids():
    page = APP.parent / "pages" / "7_Data_Quality.py"
    app = AppTest.from_file(str(page), default_timeout=35).run(timeout=35)
    assert not app.exception
    assert any(str(metric.value) == "PASS" for metric in app.metric)
    assert any("Foreign-key integrity" in str(item.value) for item in app.markdown)


def test_about_page_defines_all_ten_analysis_questions():
    page = APP.parent / "pages" / "8_About.py"
    app = AppTest.from_file(str(page), default_timeout=25).run(timeout=25)
    assert not app.exception
    assert any("OQ-10" in str(frame.value.to_string()) for frame in app.dataframe)
    assert any("provisional" in str(item.value).casefold() for item in app.warning)


def test_all_eight_pages_render_and_use_shared_filter_keys():
    pages = sorted((APP.parent / "pages").glob("*.py"))
    assert len(pages) == 8
    for page in pages:
        app = AppTest.from_file(str(page), default_timeout=40).run(timeout=40)
        assert not app.exception, page.name
        if page.name not in {"7_Data_Quality.py", "8_About.py"}:
            keys = {widget.key for widget in app.multiselect}
            assert {"ui_departments", "ui_job_levels", "ui_tenure_bands"} <= keys, page.name
