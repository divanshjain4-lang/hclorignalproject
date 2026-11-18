# Gender Diversity Analysis

An eight-page Streamlit dashboard for aggregate analysis of representation, recruitment, pay, promotion, attrition and performance in a fictional workforce. All checked-in records are synthetic.

## Requirements and setup

The project’s supported baseline is Python 3.12. Dependency pins were checked for Windows CPython 3.12 wheels. The available verification environment was Python 3.14.6; the complete suite passed there. Python 3.12 itself was not available for the recorded run.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
streamlit run app.py --server.port 8502
```

Open `http://localhost:8502`. `run_dashboard.bat` performs the setup, runs the tests, and starts the app on port 8502. Normal app startup reads `data/app.db` in read-only mode. Regenerate synthetic sources explicitly with `python generate_data.py`.

## Pages

| Page | Contents |
|---|---|
| Overview | Headcount, women representation, unadjusted pay gap, attrition and cohort charts |
| Representation | Pipeline by level, trend, leadership comparison and target scenario |
| Department Compare | Department/level representation and salary comparisons |
| EDA & Statistics | Hiring funnel, salary tests, adjusted OLS, promotion, attrition and performance |
| Insights | Filtered measures with counts, periods and caveats |
| Data & Downloads | Preview and download aggregate representation, pay and outcome CSVs |
| Data Quality | Live schema, key, foreign-key, range and cleaning checks |
| About & Definitions | Analysis questions, formulas, methods and limitations |

Year, department, job-level and tenure-band selections are shared across analysis pages. Empty selections produce empty-result states.

## Project structure

```text
app.py                 Streamlit landing page
pages/                 Eight analysis and documentation pages
src/                   Data loading, cleaning, analytics, metrics, exports and UI
data/app.db            Checked-in synthetic SQLite source
data/*.csv             Synthetic source exports and validation report
tests/                 Pytest and Streamlit AppTest checks
docs/                  Project requirements and design artifacts
reports/               Reproducible analysis outputs
requirements.txt       Pinned Python dependencies
BUILD_PLAN.md           Build sequence and deployment checklist
```

## Data design

The normalized SQLite source contains `Department` (8 rows), `JobLevel` (7), `Employee` (800), `EmployeeYear` (3,019), and `ApplicantEvent` (5,000), plus `vw_employee_analysis`. Annual salaries, ratings, promotion eligibility and promotion outcomes live in employee-year snapshots. Source paths are relative to the project root.

The generator uses seed 42 and intentionally includes missing salary/rating values, near-duplicate profiles and outliers for quality review. Cleaning preserves rows and records an audit. No real employee data is included.

## Definitions and limitations

- Year-end representation uses the annual snapshot’s active flag. Attrition uses exits divided by the opening workforce at risk.
- Promotion rates use employees flagged eligible at year start, with at least one year tenure and below L7.
- Unadjusted pay gap is `(male mean salary - female mean salary) / male mean salary`.
- Adjusted salary analysis models log salary using gender, tenure, categorical job level, department, education and performance rating with HC3 robust uncertainty.
- Hiring counts are cumulative by highest stage reached; the source does not contain stage transition dates.
- Tenure bands use completed years: 0–2, 3–4 and 5+. Target scenarios assume other headcount remains fixed.

All patterns are designed synthetic examples, not findings about a real organization. Statistical association does not establish causation. Do not use this dashboard for individual employment decisions or legal conclusions. The approved HMW wording and PRD were unavailable during the build; those source requirements and the project ID remain provisional.

## Test and deployment status

Latest recorded run: **78 passed in 17.73 seconds** using Python 3.14.6. All eight pages render under Streamlit AppTest. Detailed manual browser scenarios remain marked Not run in `docs/13_Test_Cases.docx`.

The public GitHub destination was supplied, but this local repository has not been pushed. The project documents contain student identifiers, so public disclosure has not been approved. No Streamlit Community Cloud URL is available yet.

