"""Validation tests for the generated SQLite workforce analytics project."""
import sqlite3
import pandas as pd
import pytest

from src.analytics import active_for_year, employee_dimension, employee_outcomes, hiring_funnel, yearly_outcomes
from src.database import generate_synthetic_db, load_dataset, read_table
from src.metrics import active_on, adjusted_pay_model, outcome_chi_square, pay_gap_percent, performance_test, representation_table, safe_rate, salary_tests, target_gap_table


@pytest.fixture(scope="module")
def db_bundle(tmp_path_factory):
    path = tmp_path_factory.mktemp("hrdb") / "app.db"
    counts = generate_synthetic_db(path, seed=321)
    tables = load_dataset(path)
    employees = employee_dimension(tables)
    return path, counts, tables, employees


def test_dataset_has_800_employees(db_bundle):
    assert db_bundle[1]["Employee"] == 800


def test_dataset_has_exactly_500_active_employees(db_bundle):
    assert active_for_year(db_bundle[3], 2025).shape[0] == 500


def test_dataset_has_exactly_300_exit_records(db_bundle):
    assert db_bundle[3].exit_date.notna().sum() == 300


def test_dataset_has_5000_applicants(db_bundle):
    assert db_bundle[1]["ApplicantEvent"] == 5000


def test_database_contains_the_five_step8_tables(db_bundle):
    with sqlite3.connect(db_bundle[0]) as conn:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"Department", "JobLevel", "Employee", "EmployeeYear", "ApplicantEvent"} <= names


def test_database_foreign_keys_are_valid(db_bundle):
    with sqlite3.connect(db_bundle[0]) as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_gender_categories_are_consistent(db_bundle):
    assert set(db_bundle[2]["employees"].gender) == {"Female", "Male", "Other"}


def test_job_levels_are_l1_through_l7(db_bundle):
    assert db_bundle[2]["job_levels"]["rank"].tolist() == list(range(1, 8))


def test_active_as_of_excludes_future_joiners():
    frame = pd.DataFrame({"join_date": ["2025-01-01", "2026-01-01"], "exit_date": [None, None]})
    assert active_on(frame, "2025-12-31").tolist() == [True, False]


def test_active_as_of_excludes_employees_exited_before_date():
    frame = pd.DataFrame({"join_date": ["2020-01-01"], "exit_date": ["2024-12-31"]})
    assert active_on(frame, "2025-01-01").tolist() == [False]


@pytest.mark.parametrize("numerator,denominator,expected", [(0, 5, 0), (2, 4, .5), (8, 4, 2), (0, 0, 0), (4, 0, 0)])
def test_safe_rate(numerator, denominator, expected):
    assert safe_rate(numerator, denominator) == pytest.approx(expected)


def test_representation_sums_to_one():
    result = representation_table(pd.DataFrame({"gender": ["Female", "Female", "Male", "Other"]}))
    assert result.share.sum() == pytest.approx(1.0)


def test_representation_headcount_is_counted():
    result = representation_table(pd.DataFrame({"gender": ["Female", "Female", "Male"]}))
    assert result.set_index("gender").loc["Female", "headcount"] == 2


def test_empty_representation_is_empty():
    result = representation_table(pd.DataFrame({"gender": pd.Series(dtype=str)}))
    assert result.empty


def test_pay_gap_zero_when_means_equal():
    data = pd.DataFrame({"gender": ["Female", "Female", "Male", "Male"], "annual_salary": [100, 100, 100, 100]})
    assert pay_gap_percent(data) == pytest.approx(0)


def test_pay_gap_positive_when_female_mean_is_lower():
    data = pd.DataFrame({"gender": ["Female", "Male"], "annual_salary": [80, 100]})
    assert pay_gap_percent(data) == pytest.approx(20)


def test_pay_gap_nan_without_male_group():
    data = pd.DataFrame({"gender": ["Female"], "annual_salary": [100]})
    assert pd.isna(pay_gap_percent(data))


def test_hiring_funnel_contains_four_stages(db_bundle):
    result = hiring_funnel(db_bundle[2]["applicants"])
    assert set(result.stage) == {"Applied", "Shortlisted", "Offered", "Joined"}


def test_hiring_funnel_conversion_is_bounded(db_bundle):
    result = hiring_funnel(db_bundle[2]["applicants"])
    assert result.conversion_from_applied.between(0, 1).all()


def test_hiring_funnel_decreases_or_stays_flat_by_stage(db_bundle):
    result = hiring_funnel(db_bundle[2]["applicants"])
    checks = result.groupby(["year", "department", "gender"], observed=True).apply(
        lambda g: g.sort_values("stage_rank").applicants.diff().dropna().le(0).all(), include_groups=False)
    assert checks.all()


def test_annual_outcome_metrics_cover_five_years(db_bundle):
    attrition, promotions = yearly_outcomes(db_bundle[3], db_bundle[2]["promotions"])
    assert set(attrition.year) == set(range(2021, 2026))
    assert set(promotions.year) == set(range(2021, 2026))


def test_annual_rates_are_between_zero_and_one(db_bundle):
    attrition, promotions = yearly_outcomes(db_bundle[3], db_bundle[2]["promotions"])
    assert attrition.attrition_rate.between(0, 1).all()
    assert promotions.promotion_rate.between(0, 1).all()


def test_employee_outcomes_are_binary(db_bundle):
    attrition, promotion = employee_outcomes(db_bundle[3], db_bundle[2]["promotions"], 2025)
    assert set(attrition.outcome) <= {"Yes", "No"}
    assert set(promotion.outcome) <= {"Yes", "No"}


def test_chi_square_reports_p_value_in_range():
    data = pd.DataFrame({"gender": ["Female"] * 20 + ["Male"] * 20, "outcome": ["Yes"] * 10 + ["No"] * 10 + ["Yes"] * 10 + ["No"] * 10})
    result = outcome_chi_square(data, "outcome", {"Yes"})
    assert result["statistic"] >= 0
    assert 0 <= result["p_value"] <= 1


def test_chi_square_handles_insufficient_variation():
    data = pd.DataFrame({"gender": ["Female", "Male"], "outcome": ["No", "No"]})
    assert "Insufficient" in outcome_chi_square(data, "outcome", {"Yes"})["interpretation"]


def test_salary_tests_have_valid_p_values(db_bundle):
    tables = db_bundle[2]
    pay = tables["salaries"].query("year == 2025").merge(db_bundle[3], on="emp_id")
    results = salary_tests(pay)
    assert results
    assert all(0 <= row["mann_whitney_p"] <= 1 for row in results)


def test_adjusted_ols_includes_gender_coefficient(db_bundle):
    tables = db_bundle[2]
    pay = tables["salaries"].query("year == 2025").merge(db_bundle[3], on="emp_id")
    pay = pay.merge(tables["appraisals"].query("year == 2025")[["emp_id", "rating"]], on="emp_id", how="left")
    model = adjusted_pay_model(pay.rename(columns={"department_name": "department"}))
    assert any("gender" in term.casefold() for term in model.params.index)


def test_read_table_rejects_unapproved_table(db_bundle):
    with pytest.raises(ValueError, match="Unsupported table"):
        read_table(db_bundle[0], "sqlite_master; DROP TABLE employees")


def test_target_gap_calculates_additions_needed():
    employees = pd.DataFrame({"department_name": ["Engineering"] * 10, "level_name": ["L1"] * 10,
                              "gender": ["Female"] * 2 + ["Male"] * 8})
    result = target_gap_table(employees, .40).iloc[0]
    assert result.additional_women == 4
    assert (result.women + result.additional_women) / (result.headcount + result.additional_women) >= .40


def test_target_gap_rejects_invalid_target():
    with pytest.raises(ValueError, match="between 0 and 1"):
        target_gap_table(pd.DataFrame(columns=["department_name", "level_name", "gender"]), 1.2)


def test_performance_test_returns_p_values():
    data = pd.DataFrame({"gender": ["Female"] * 4 + ["Male"] * 4, "rating": [2, 3, 3, 4, 3, 3, 4, 5]})
    result = performance_test(data)
    assert 0 <= result["mann_whitney_p"] <= 1
    assert 0 <= result["welch_t_p"] <= 1
