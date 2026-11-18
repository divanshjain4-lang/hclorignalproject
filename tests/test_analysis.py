import pandas as pd
import pytest

from src.analytics import (active_cohort_for_year, active_for_year, annual_snapshot_outcomes, employee_dimension,
                           employee_outcomes, employee_year_frame, hiring_funnel, tenure_band, yearly_outcomes)
from src.metrics import (active_on, adjusted_pay_model, outcome_chi_square, pay_gap_percent,
                         performance_test, representation_table, safe_rate, salary_tests,
                         target_gap_table)


def test_clean_active_cohort_and_representation_metrics():
    employees = pd.DataFrame({"join_date": ["2020-01-01", "2022-01-01"], "exit_date": [None, "2024-06-01"],
                              "gender": ["Female", "Male"]})
    active = employees.loc[active_on(employees, "2023-12-31")]
    summary = representation_table(active)
    assert summary["headcount"].sum() == 2
    assert summary["share"].sum() == pytest.approx(1)


def test_safe_rate_handles_zero_denominator():
    assert safe_rate(2, 4) == pytest.approx(.5)
    assert safe_rate(1, 0) == 0


def test_pay_gap_known_values():
    pay = pd.DataFrame({"gender": ["Female", "Male"], "annual_salary": [80.0, 100.0]})
    assert pay_gap_percent(pay) == pytest.approx(20)


def test_target_gap_and_range_validation():
    staff = pd.DataFrame({"department_name": ["Engineering"] * 10, "level_name": ["L1"] * 10,
                          "gender": ["Female"] * 2 + ["Male"] * 8})
    result = target_gap_table(staff, .4).iloc[0]
    assert result.additional_women == 4
    with pytest.raises(ValueError):
        target_gap_table(staff, 1.1)


def test_hiring_funnel_counts_and_conversion_are_valid():
    from io import StringIO
    applicants = pd.DataFrame({"gender": ["Female", "Male", "Female"], "applied_date": ["2025-01-01"] * 3,
                               "dept_id": [1] * 3, "stage": ["Joined", "Shortlisted", "Applied"]})
    funnel = hiring_funnel(applicants)
    assert set(funnel.stage) == {"Applied", "Shortlisted", "Offered", "Joined"}
    assert funnel.conversion_from_applied.between(0, 1).all()
    short = funnel.loc[funnel.stage.eq("Shortlisted")].iloc[0]
    assert short.applicants == 1 and short.previous_stage_applicants == 2
    assert short.conversion_from_previous == pytest.approx(.5)


def test_outcome_chi_square_returns_interpretation_and_p_value():
    frame = pd.DataFrame({"gender": ["Female"] * 20 + ["Male"] * 20,
                          "outcome": ["Yes"] * 10 + ["No"] * 10 + ["Yes"] * 10 + ["No"] * 10})
    result = outcome_chi_square(frame, "outcome", {"Yes"})
    assert 0 <= result["p_value"] <= 1
    assert "α=0.05" in result["interpretation"]


def test_salary_tests_return_level_results():
    pay = pd.DataFrame({"level_name": ["L1"] * 8, "gender": ["Female"] * 4 + ["Male"] * 4,
                        "annual_salary": [80, 90, 100, 110, 100, 110, 120, 130]})
    result = salary_tests(pay)
    assert result and 0 <= result[0]["mann_whitney_p"] <= 1


def test_adjusted_pay_model_has_gender_term():
    import numpy as np
    rows = []
    rng = np.random.default_rng(42)
    for gender in ["Female", "Male"]:
        for i in range(30):
            rows.append({"annual_salary": 50000 + 1000 * i + (5000 if gender == "Male" else 0) + rng.normal(0, 1500),
                         "gender": gender, "tenure_years": float(rng.uniform(0, 15)),
                         "level_rank": int(rng.integers(1, 8)), "department": str(rng.choice(["A", "B", "C", "D"])),
                         "education": str(rng.choice(["Bachelor", "Master", "Doctorate"])),
                         "rating": int(rng.integers(1, 6))})
    model = adjusted_pay_model(pd.DataFrame(rows))
    assert any("gender" in str(term).casefold() for term in model.params.index)


def test_gender_effect_contains_robust_inference():
    import numpy as np
    from src.metrics import gender_effect
    rng = np.random.default_rng(17)
    rows = []
    for gender in ["Female", "Male"]:
        for _ in range(40):
            rows.append({"annual_salary": float(np.exp(10 + (.08 if gender == "Male" else 0) + rng.normal(0, .1))),
                         "gender": gender, "tenure_years": float(rng.uniform(0, 10)),
                         "level_rank": int(rng.integers(1, 7)), "department": str(rng.choice(["A", "B", "C"])),
                         "education": str(rng.choice(["Bachelor", "Master"])), "rating": int(rng.integers(1, 6))})
    effect = gender_effect(adjusted_pay_model(pd.DataFrame(rows)))
    assert effect["n"] == 80 and 0 <= effect["p_value"] <= 1
    assert effect["ci_low"] < effect["ci_high"]


def test_tenure_bands_use_completed_years_and_handle_missing():
    result = tenure_band(pd.Series([0.99, 2.99, 3.0, 4.99, 5.0, None])).tolist()
    assert result[:5] == ["0-2 yrs", "0-2 yrs", "3-4 yrs", "3-4 yrs", "5+ yrs"]
    assert pd.isna(result[-1])


def test_performance_test_returns_valid_probability():
    data = pd.DataFrame({"gender": ["Female"] * 4 + ["Male"] * 4,
                         "rating": [2, 3, 3, 4, 3, 3, 4, 5]})
    result = performance_test(data)
    assert 0 <= result["mann_whitney_p"] <= 1


def test_yearly_outcomes_are_defined_and_bounded(tmp_path):
    from src.database import generate_synthetic_db, load_dataset
    from src.analytics import employee_dimension
    path = tmp_path / "analytics_fixture.db"
    generate_synthetic_db(path, seed=9)
    bundle = load_dataset(path)
    employees = employee_dimension(bundle)
    attrition, promotion = yearly_outcomes(employees, bundle["promotions"], years=[2025])
    assert attrition.attrition_rate.between(0, 1).all()
    assert promotion.promotion_rate.between(0, 1).all()
    exits, eligible = employee_outcomes(employees, bundle["promotions"], 2025)
    assert set(exits.outcome) <= {"Yes", "No"}
    assert set(eligible.outcome) <= {"Yes", "No"}


def test_annual_snapshot_rates_reconcile_to_source_flags(tmp_path):
    from src.database import generate_synthetic_db, load_dataset
    path = tmp_path / "snapshot_fixture.db"
    generate_synthetic_db(path, seed=42)
    bundle = load_dataset(path)
    joined = employee_year_frame(bundle)
    attrition, promotions = annual_snapshot_outcomes(bundle, years=[2025])
    source = joined.loc[joined.reporting_year.eq(2025)]
    assert attrition.at_risk.sum() == source.active_at_year_start.sum()
    assert attrition.exits.sum() == source.exit_in_year.sum()
    assert promotions.eligible.sum() == source.promotion_eligible.sum()
    assert promotions.promotions.sum() == source.promoted.sum()
    assert attrition.attrition_rate.between(0, 1).all()
    assert promotions.promotion_rate.between(0, 1).all()


def test_explicitly_empty_shared_filters_return_empty_cohort(tmp_path):
    from src.database import generate_synthetic_db, load_dataset
    from src.analytics import active_cohort_for_year
    path = tmp_path / "empty_filter_fixture.db"
    generate_synthetic_db(path, seed=42)
    cohort = active_cohort_for_year(load_dataset(path), 2025, departments=[], levels=[], tenure_bands=[])
    assert cohort.empty


def test_aggregate_exports_match_filtered_preview_and_hide_ids(tmp_path):
    from io import StringIO
    from src.analytics import active_cohort_for_year, employee_year_frame
    from src.database import generate_synthetic_db, load_dataset
    from src.exports import build_aggregate_exports
    path = tmp_path / "export_fixture.db"
    generate_synthetic_db(path, seed=42)
    tables = load_dataset(path)
    facts = employee_year_frame(tables)
    depts = sorted(facts.department_name.dropna().unique())
    levels = sorted(facts.level_name.dropna().unique())
    bands = ["0-2 yrs", "3-4 yrs", "5+ yrs"]
    cohort = active_cohort_for_year(tables, 2025, depts, levels, bands)
    exports = build_aggregate_exports(facts, cohort, 2025, depts, levels, bands)
    assert exports["Representation aggregate"].headcount.sum() == len(cohort)
    assert "emp_id" not in exports["Pay aggregate"].columns
    csv_frame = pd.read_csv(StringIO(exports["Pay aggregate"].to_csv(index=False)))
    pd.testing.assert_frame_equal(csv_frame, exports["Pay aggregate"], check_dtype=False)
    scoped = build_aggregate_exports(facts, cohort, 2025, [depts[0]], levels, bands)
    assert set(scoped["Representation aggregate"].department_name) <= {depts[0]}
    assert scoped["Representation aggregate"].headcount.sum() < len(cohort)
