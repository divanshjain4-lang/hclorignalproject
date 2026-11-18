# System Design

## Purpose

This academic Streamlit application demonstrates aggregate analysis of gender representation, hiring, salary, promotion, attrition and performance. All checked-in records are fictional and synthetic. Designed patterns do not describe a real employer.

## Runtime flow

1. `src/database.py` loads the checked-in SQLite database read-only and validates its schema.
2. `src/cleaning.py` creates normalized analysis copies and an audit without dropping source rows.
3. `src/analytics.py` joins annual snapshots with employee, department and job-level context and calculates cohorts and funnels.
4. `src/metrics.py` computes summary rates, rank-based tests, sparse-cell-guarded chi-square results and HC3-robust salary OLS.
5. `app.py` is the primary Streamlit experience; `pages/` contains the eight dedicated analysis screens.
6. `src/generate_data.py` regenerates only when explicitly run; normal application startup never writes to the database.

## Canonical SQLite schema

| Table | Grain and key | Purpose |
|---|---|---|
| `Department` | One row per department; `dept_id` PK | Department names and optional women targets |
| `JobLevel` | One row per level; `level_id` PK | Ordered level, display title, leadership flag and target |
| `Employee` | One row per employee; `emp_id` PK | Gender, join/exit dates, total experience and education |
| `EmployeeYear` | One row per employee-year; `(emp_id, reporting_year)` PK; department/level FKs | Snapshot status, tenure, salary, promotion eligibility/outcome and performance rating |
| `ApplicantEvent` | One row per applicant; `applicant_id` PK; department FK | Gender, application date and highest stage reached |

The SQLite view `vw_employee_analysis` joins employee-year, employee, department and level information for analysis. The normalized source tables remain the source of truth.

## Important formulas and denominators

- Representation share = group headcount ÷ selected year-end headcount.
- Attrition rate = exits during year ÷ employees active at the start of that year.
- Promotion rate = promotions ÷ source-flagged eligible employees active at the start, with at least one year tenure and below L7.
- Hiring funnel stage count = applicants whose recorded highest stage is that stage or later. This is a cumulative funnel; actual stage transitions are unavailable.
- Unadjusted pay gap = (male mean annual salary − female mean annual salary) ÷ male mean annual salary.
- Adjusted pay analysis models log annual salary against gender, tenure, categorical level, department, education and rating with HC3 robust errors.
- Tenure bands use completed years: 0–2, 3–4 and 5+.
- Target scenario estimates added women at fixed other headcount: `ceil(max(0, (target * headcount - women) / (1 - target)))`.

## Safeguards and limitations

Missing salary and rating values, near-duplicate profiles and outliers are seeded for quality review. The cleaning layer reports them and preserves row counts. Small `Other` gender groups remain in descriptive views; tests comparing Female/Male are labeled and sparse chi-square results are flagged. Statistical associations are not causal claims. No individual-level prediction or employment recommendation is made.

The approved Step 2 HMW and Step 6 PRD were unavailable during the build. The OQ wording and project ID are marked provisional in the About screen. Real employee data require explicit governance, privacy controls, stakeholder approval and independent validation before use.
