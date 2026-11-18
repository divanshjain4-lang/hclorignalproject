"""Reusable diversity metrics and statistical tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu, ttest_ind
import math


def safe_rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def active_on(employees: pd.DataFrame, as_of: str | pd.Timestamp) -> pd.Series:
    day = pd.Timestamp(as_of)
    joined = pd.to_datetime(employees["join_date"])
    exited = pd.to_datetime(employees["exit_date"], errors="coerce")
    return joined.le(day) & (exited.isna() | exited.gt(day))


def representation_table(employees: pd.DataFrame) -> pd.DataFrame:
    summary = employees.groupby("gender", dropna=False).size().rename("headcount").reset_index()
    total = int(summary["headcount"].sum())
    summary["share"] = summary["headcount"].div(total) if total else 0.0
    return summary


def pay_gap_percent(salaries: pd.DataFrame, female: str = "Female", male: str = "Male") -> float:
    means = salaries.groupby("gender")["annual_salary"].mean()
    if male not in means or female not in means or not means[male]:
        return float("nan")
    return float((means[male] - means[female]) / means[male] * 100)


def outcome_chi_square(data: pd.DataFrame, outcome: str, positive_values: set[str]) -> dict[str, float | str]:
    pair = data.loc[data["gender"].isin(["Female", "Male"]), ["gender", outcome]].dropna()
    if pair["gender"].nunique() < 2 or pair[outcome].nunique() < 2:
        return {"statistic": float("nan"), "p_value": float("nan"), "interpretation": "Insufficient variation for a chi-square test."}
    positive = pair[outcome].astype(str).str.casefold().isin({x.casefold() for x in positive_values})
    table = pd.crosstab(pair["gender"], positive)
    stat, p_value, _, expected = chi2_contingency(table)
    if (expected < 5).any():
        return {"statistic": float(stat), "p_value": float(p_value),
                "interpretation": "Chi-square assumptions are weak (an expected cell is below 5); treat this result as exploratory."}
    decision = "evidence of an association" if p_value < .05 else "no statistically significant association detected"
    return {"statistic": float(stat), "p_value": float(p_value), "interpretation": f"At α=0.05, {decision} between gender and {outcome}. This is not evidence of causation."}


def salary_tests(salaries: pd.DataFrame) -> list[dict[str, float | str | int]]:
    results = []
    for level, group in salaries.groupby("level_name"):
        women = group.loc[group.gender.eq("Female"), "annual_salary"].dropna()
        men = group.loc[group.gender.eq("Male"), "annual_salary"].dropna()
        if min(len(women), len(men)) < 2:
            continue
        results.append({"job_level": str(level), "female_n": len(women), "male_n": len(men),
                        "female_mean": float(women.mean()), "male_mean": float(men.mean()),
                        "female_median": float(women.median()), "male_median": float(men.median()),
                        "mean_gap_percent": float((men.mean() - women.mean()) / men.mean() * 100) if men.mean() else float("nan"),
                        "mann_whitney_p": float(mannwhitneyu(women, men, alternative="two-sided").pvalue),
                        "welch_t_p": float(ttest_ind(women, men, equal_var=False).pvalue)})
    return results


def performance_test(data: pd.DataFrame) -> dict[str, float | int]:
    women = data.loc[data.gender.eq("Female"), "rating"].dropna()
    men = data.loc[data.gender.eq("Male"), "rating"].dropna()
    if min(len(women), len(men)) < 2:
        return {"female_n": len(women), "male_n": len(men), "mann_whitney_p": float("nan"), "welch_t_p": float("nan")}
    return {"female_n": len(women), "male_n": len(men),
            "mann_whitney_p": float(mannwhitneyu(women, men, alternative="two-sided").pvalue),
            "welch_t_p": float(ttest_ind(women, men, equal_var=False).pvalue)}


def target_gap_table(employees: pd.DataFrame, target: float = .40) -> pd.DataFrame:
    """Estimate extra women needed to reach a share target if other headcount stays fixed."""
    if not 0 <= target <= 1:
        raise ValueError("target must be between 0 and 1")
    rows = []
    for (department, level), group in employees.groupby(["department_name", "level_name"], observed=True):
        headcount = len(group)
        women = int(group.gender.eq("Female").sum())
        share = women / headcount if headcount else 0.0
        if target == 1:
            needed = max(0, headcount - women)
        else:
            needed = math.ceil(max(0.0, (target * headcount - women) / (1 - target)))
        rows.append({"department": department, "job_level": level, "headcount": headcount,
                     "women": women, "women_share": share, "target": target, "additional_women": needed})
    return pd.DataFrame(rows)


def adjusted_pay_model(data: pd.DataFrame):
    """Fit log salary with job and experience controls using HC3 robust standard errors."""
    import statsmodels.formula.api as smf
    # Accept either source-schema or analysis-frame column names.
    data = data.copy()
    aliases = {"annual_salary_inr": "annual_salary", "performance_rating": "rating",
               "level_name": "level_rank", "department_name": "department", "education_level": "education"}
    for source, target in aliases.items():
        if target not in data and source in data:
            data[target] = data[source]
    needed = ["annual_salary", "gender", "tenure_years", "level_rank", "department", "education", "rating"]
    model_data = data[needed].dropna().copy()
    model_data = model_data.loc[model_data.annual_salary.gt(0)]
    model_data["log_salary"] = np.log(model_data["annual_salary"])
    if len(model_data) < 8 or model_data.gender.nunique() < 2:
        raise ValueError("At least 8 complete observations across two gender groups are required")
    formula = "log_salary ~ C(gender) + tenure_years + C(level_rank) + C(department) + C(education) + rating"
    ordinary = smf.ols(formula, data=model_data)
    if np.linalg.matrix_rank(ordinary.exog) < ordinary.exog.shape[1]:
        raise ValueError("Adjusted pay model is singular because predictors are redundant in this sample")
    model = ordinary.fit(cov_type="HC3")
    if model.df_resid <= 0 or not np.isfinite(model.params).all():
        raise ValueError("Adjusted pay model is singular or has no residual degrees of freedom")
    return model


def gender_effect(model, reference: str = "Female") -> dict[str, float | str | int]:
    """Extract the male-vs-reference log-pay effect with robust CI and sample size."""
    terms = [term for term in model.params.index if term.startswith("C(gender)[T.")]
    if not terms:
        return {"term": "", "coefficient": float("nan"), "p_value": float("nan"),
                "ci_low": float("nan"), "ci_high": float("nan"), "n": int(model.nobs),
                "interpretation": "No estimable gender coefficient; check group variation and model rank."}
    term = next((t for t in terms if reference not in t), terms[0])
    coef = float(model.params[term]); p = float(model.pvalues[term]); low, high = model.conf_int().loc[term]
    direction = "higher" if coef > 0 else "lower"
    decision = "statistically significant" if p < .05 else "not statistically significant"
    return {"term": term, "coefficient": coef, "p_value": p, "ci_low": float(low),
            "ci_high": float(high), "n": int(model.nobs),
            "interpretation": f"The modeled gender association is {direction} log salary and is {decision} (95% CI; not causal)."}
