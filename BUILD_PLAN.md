# BUILD PLAN — Gender Diversity Analysis

**Project ID:** DA-GDA-01 (placeholder; replace with ABES-issued ID)  
**Author:** Divansh Jain · Roll No. 2500320140050  
**Mentor:** Alpna Lodhi · **Baseline:** Python 3.12, Streamlit, SQLite, pandas, NumPy, SciPy/statsmodels, Plotly, pytest/AppTest

## Project summary (10 lines)

1. This is a local, read-only Streamlit dashboard for the fictional NexaTech Solutions workforce.
2. All employee, applicant, pay, promotion and performance records are synthetic.
3. The project covers calendar years 2021–2025 and uses year-end workforce cohorts.
4. Its approved data design has five tables: Department, JobLevel, Employee, EmployeeYear and ApplicantEvent.
5. Twelve BRs map to ten OQs, 17 user stories, ten functional requirements and eight UI screens.
6. The analyses cover representation, hiring, pay, promotion, attrition and performance.
7. Rates must show their counts and denominators; association does not establish causation.
8. The target interface is Streamlit multipage with shared filters, Plotly charts and aggregate CSV downloads.
9. The checked-in SQLite schema is the five-table Step 8 design and app startup reads it read-only.
10. Current automated verification has 78 passing tests on Python 3.14.6; detailed manual UI scenarios remain Not run.

## Project documents

Treat these as the requirements and design authority. The approved Step 2 HMW artifact and Step 6 PRD were not present when this plan was prepared. Step 3 HMW wording is provisional and must be reconciled when the approved source is available.

- [01 Project Understanding (source)](C:/Users/DELL/Downloads/01_divansh_project_understanding%20(1).docx)
- [03 Needs Analysis](docs/03_Needs_Analysis.docx)
- [04 Traceability Matrix](docs/04_Traceability_Matrix.xlsx)
- [05 Business Requirements Document](docs/05_BRD.docx)
- [07 Technical Requirements Document](docs/07_TRD.docx)
- [08 Database Design](docs/08_Database_Design.xlsx)
- [09 ER Diagram Document](docs/09_ER_Diagram.docx) · [ER Diagram PNG](docs/09_ER_Diagram.png)
- [11 User Stories](docs/11_User_Stories.docx)
- [12 UI Framework](docs/12_UI_Framework.docx)
- [13 Test Cases](docs/13_Test_Cases.docx)
- [System Design](docs/system_design.md) · [Test Plan](docs/test_plan.md)

## Final folder structure

```text
gender-diversity-analysis/
├── app.py                         # Streamlit entry point and shared navigation
├── pages/
│   ├── 1_Overview.py
│   ├── 2_Representation.py
│   ├── 3_Department_Compare.py
│   ├── 4_EDA_Statistics.py
│   ├── 5_Insights.py
│   ├── 6_Data_Downloads.py
│   ├── 7_Data_Quality.py
│   └── 8_About.py
├── src/ database.py, validation.py, cleaning.py, analytics.py, metrics.py, ui.py
├── data/ app.db and synthetic CSV/XLSX source files
├── tests/ test_data.py, test_analysis.py, test_app.py
├── docs/ requirements and design artifacts
├── reports/ reproducible generated summaries
├── .streamlit/config.toml · .gitignore · requirements.txt · README.md
└── BUILD_PLAN.md
```

## Build sequence

Follow the tasks in order. Give the AI only the exact prompt and files listed for that task. Do not start dependent work until the check and required tests pass. Record observed results in the RTM and commit every completed task.

### BUILD-01 — Set up the supported environment and pinned dependencies

**Files:** requirements.txt, .gitignore, README.md, docs/07_TRD.docx  
**Stories / features:** US-01, US-02 · FR-01, FR-02

**Exact prompt for the AI:**
> Act as the project’s Python build engineer. Review requirements.txt, the TRD stack and current tests. Establish a reproducible Python 3.12 environment. Verify each dependency pin has a compatible wheel for Python 3.12 and Streamlit Community Cloud; change only incompatible pins and record each change in README. Ensure .venv, caches, secrets and scratch files are ignored. Do not alter the business schema or weaken test expectations. Return changed files, setup commands and dependency verification output.

**How to check:** Create a clean Python 3.12 venv, install requirements, run `python -m pip check`, and confirm imports/versions.  
**Tests that must pass:** dependency setup prerequisite; app smoke test must be runnable.  
**Commit:** `git add . && git commit -m "BUILD-01: establish supported Python environment"`

### BUILD-02 — Align loader, validation and cleaning to the five-table design

**Files:** app.py, src/database.py, src/validation.py, src/cleaning.py, src/generate_data.py, generate_data.py, data/app.db, tests/test_data.py, tests/test_project.py
**Stories / features:** US-01, US-02 · FR-01, FR-02

**Exact prompt for the AI:**
> Act as a senior data engineer. Make the Step 8 schema the single source of truth: Department, JobLevel, Employee, EmployeeYear and ApplicantEvent, with documented columns, keys, checks and foreign keys. Refactor loading to read data/app.db safely using paths relative to the project root, validate table/column contracts and expose consistent DataFrames to the app. Do not silently replace the database or introduce a second schema. Add cleaning that trims and standardizes categories, parses dates, reports missing/duplicate/outlier counts, preserves unknowns for quality reporting, and never silently drops rows. Keep synthetic generation reproducible with seed 42 and valid foreign keys. Update stale tests to the Step 8 schema rather than weakening expected behavior. Keep database generation separate from normal dashboard startup. Show schema/count validation results.

**How to check:** Compare all five table names/columns with Step 8; verify row counts, key uniqueness, FKs, dates/ranges and that loading does not modify data/app.db.  
**Tests that must pass:** TC-T-01–TC-T-06; TC-T-12 must advance beyond the current loader crash.  
**Commit:** `git add . && git commit -m "BUILD-02: align loader and validation to Step 8 schema"`

### BUILD-03 — Implement shared analysis and statistical functions

**Files:** src/analytics.py, src/metrics.py, tests/test_analysis.py, tests/test_project.py
**Stories / features:** US-04–US-14 · FR-03–FR-08

**Exact prompt for the AI:**
> Act as a statistician and senior Python analyst. Implement reusable functions for OQ-01–OQ-10: annual active cohorts and gender shares; department/level and L5+ leadership comparisons; target gap estimate with fixed-other-headcount assumption; hiring stage counts and prior-stage conversion; salary mean/median/count/gap by comparable group; log-salary OLS with gender, level, department, experience, education and rating plus robust uncertainty; eligible-population promotion rates and guarded association test; attrition using the opening at-risk denominator and tenure bands; and rating distributions with a suitable ordinal test. Return structured results with numerator, denominator, sample size, method, p-value, confidence interval where applicable and plain-English caveat. Handle empty groups, zero denominators, sparse cells and singular models. Test formulas on tiny deterministic fixtures. Association is not causation. Keep all IDs unchanged.

**How to check:** Independently calculate fixture results and compare 2021–2025 metrics with direct aggregation; inspect sparse groups and model diagnostics.  
**Tests that must pass:** TC-T-07–TC-T-11 and existing metric tests.  
**Commit:** `git add . && git commit -m "BUILD-03: implement validated analysis functions"`

### BUILD-04 — Create reusable UI components and shared filters

**Files:** src/ui.py, .streamlit/config.toml, tests/test_app.py  
**Stories / features:** US-03, US-15, US-17 · FR-03, FR-09

**Exact prompt for the AI:**
> Act as a Streamlit UI developer. Implement reusable header, KPI card/row, chart card, insight box, synthetic-data notice and shared sidebar filters from docs/12_UI_Framework.docx. Keep charts, controls, tables and buttons native Streamlit/Plotly. Use st.iframe only for isolated header/card markup with safe HTML escaping and readable fallback styling if Tailwind CDN is unavailable. Define stable session-state keys for year, department, job level and tenure band; default to the full cohort. Apply Female #0072B2, Male #E69F00, Other #009E73 and the approved theme. Ensure responsive layout and labels do not rely on color alone. Do not claim pages are complete.

**How to check:** AppTest checks component render, widget labels, stable defaults and no exceptions.  
**Tests that must pass:** TC-T-12–TC-T-14.  
**Commit:** `git add . && git commit -m "BUILD-04: add shared UI components"`

### BUILD-05 — Build app shell and Overview screen

**Files:** app.py, pages/1_Overview.py, src/ui.py, tests/test_app.py  
**Stories / features:** US-03, US-04, US-15, US-17 · FR-03, FR-09 · UI-01

**Exact prompt for the AI:**
> Act as a Streamlit application developer. Create app.py as the multipage entry point and implement UI-01 Overview and KPIs from docs/12_UI_Framework.docx. Reuse shared filters/components. Show active headcount, women representation, unadjusted pay gap and attrition rate with year/cohort definitions, counts and denominators. Include synthetic-data and no-causality notices, plus a clear empty-cohort state. Use validated data and shared metric functions; do not duplicate formulas in the page. Preserve all IDs.

**How to check:** AppTest starts without exceptions; filters recalculate KPIs; results reconcile independently; no-match filters show a clear empty state.  
**Tests that must pass:** TC-F-02, -03, -08, -17, -20, -22; TC-T-12–TC-T-14.  
**Commit:** `git add . && git commit -m "BUILD-05: implement app shell and overview"`

### BUILD-06 — Build Representation Trend and Department Compare screens

**Files:** pages/2_Representation.py, pages/3_Department_Compare.py, src/analytics.py, tests/test_app.py  
**Stories / features:** US-03–US-06 · FR-03, FR-08, FR-09 · UI-02, UI-03

**Exact prompt for the AI:**
> Act as a data visualization developer. Implement UI-02 and UI-03 for OQ-01, OQ-02, OQ-03 and OQ-10. Show the year-end 100% gender pipeline by job level, annual representation line, department-by-level heatmap and grouped comparisons, leadership versus workforce share with percentage-point difference, and actual-versus-target/added-headcount estimate. Every rate shows count/denominator or an accessible companion table. Apply shared filters, ordered levels, responsive Plotly charts, labels/hover details, small-group notes and empty states. Keep formulas in shared analysis modules and check all visuals against hand calculations.

**How to check:** Populated departments/levels are present; shares reconcile; target changes update estimates; filters produce no stale chart.  
**Tests that must pass:** TC-F-02–08, -22; TC-T-07, -11, -16.  
**Commit:** `git add . && git commit -m "BUILD-06: build representation and comparison screens"`

### BUILD-07 — Build EDA and Statistics screen

**Files:** pages/4_EDA_Statistics.py, src/analytics.py, src/metrics.py, tests/test_app.py  
**Stories / features:** US-07–US-14, US-15, US-17 · FR-04–FR-07, FR-09 · UI-04

**Exact prompt for the AI:**
> Act as an HR analytics app developer. Implement UI-04 with gendered hiring funnel and prior-stage conversion; salary distribution by gender/job level with mean, median, n and stated gap; adjusted OLS coefficient, interval, p-value and diagnostics; eligible-population promotion counts/rates and guarded chi-square; attrition by year/gender/department/tenure using the opening at-risk denominator; and rating distribution/median/test. Apply shared filters. Show counts, assumptions and accessible table summaries. Use colorblind-friendly charts, clear empty states and no causal or individual-level claims. Use shared metric functions only.

**How to check:** Verify every OQ view and statistic against independent calculations; test sparse groups and empty filters.  
**Tests that must pass:** TC-F-09–16, -21, -23; TC-T-07–11, -16.  
**Commit:** `git add . && git commit -m "BUILD-07: build EDA and statistics screen"`

### BUILD-08 — Build evidence-backed Insights screen

**Files:** pages/5_Insights.py, src/ui.py, src/analytics.py, tests/test_app.py  
**Stories / features:** US-06, US-12, US-15, US-17 · FR-08, FR-09 · UI-05

**Exact prompt for the AI:**
> Act as a responsible analytics product developer. Implement UI-05 as an evidence summary derived only from current filtered results. Each finding must name its supporting KPI/table, numerator/denominator, period/cohort, valid statistical evidence and caveat or next question. Explain target scenarios under the fixed-other-headcount assumption. If evidence is absent, say so; never invent findings, claim causation, describe synthetic patterns as real, or recommend individual employment action. Reuse the insight component and ensure values update with filters.

**How to check:** Compare each insight to known fixture metrics; test empty/insufficient-evidence states and safe-use caveats.  
**Tests that must pass:** TC-F-05, -14, -17, -20; TC-T-16.  
**Commit:** `git add . && git commit -m "BUILD-08: implement Insights screen"`

### BUILD-09 — Build Data and Downloads screen

**Files:** pages/6_Data_Downloads.py, src/database.py, src/analytics.py, tests/test_app.py  
**Stories / features:** US-01, US-03, US-16, US-17 · FR-01, FR-03, FR-10 · UI-06

**Exact prompt for the AI:**
> Act as a Streamlit export developer. Implement UI-06 with filtered aggregate previews and CSV downloads for supported representation, pay and outcome summaries. Use active shared filters; include labels, units, period and aggregate scope. Downloads must match preview totals and must not expose unnecessary employee IDs. Show row count and synthetic-data notice. Test headers, filtered scope, repeated downloads after filter changes and empty export behavior.

**How to check:** Compare downloaded files with filtered preview tables and verify no unintended employee identifiers.  
**Tests that must pass:** TC-F-18, -19, -24; TC-T-17.  
**Commit:** `git add . && git commit -m "BUILD-09: add aggregate data downloads"`

### BUILD-10 — Build Data Quality page and validation report

**Files:** pages/7_Data_Quality.py, src/validation.py, src/cleaning.py, data/validation_report.json, tests/test_data.py, tests/test_app.py  
**Stories / features:** US-02, US-17 · FR-02, FR-09, FR-10 · UI-07

**Exact prompt for the AI:**
> Act as a data-quality engineer. Implement UI-07 from src/validation.py. Show table row/column counts, required-column status, missingness, duplicate-key candidates, key/FK integrity, category/range/date checks and flagged outliers. Distinguish designed synthetic patterns from defects. Show PASS/WARN/FAIL, affected counts, seed/version and synthetic notice. Provide a validation report download without unnecessary personal identifiers. Never show PASS for a missing or failed check. Test malformed temporary fixtures and the valid checked-in SQLite database.

**How to check:** Inject missing values, duplicate keys, invalid FK/range and empty inputs in temporary fixtures; validate the actual DB.  
**Tests that must pass:** TC-F-19, -25; TC-T-01–06, -17.  
**Commit:** `git add . && git commit -m "BUILD-10: add data-quality checks and page"`

### BUILD-11 — Build About and Definitions screen

**Files:** pages/8_About.py, docs/system_design.md, src/ui.py, tests/test_app.py  
**Stories / features:** US-15, US-17 · FR-09 · UI-08

**Exact prompt for the AI:**
> Act as a documentation-focused Streamlit developer. Implement UI-08 with project purpose, synthetic-data provenance/limits, glossary, all ten OQ definitions, year-end active rule, leadership threshold, target assumption, pay-gap formula, promotion eligibility, attrition denominator, hiring-conversion denominator, statistical methods and safe-use cautions. Mark assumptions awaiting approval. Make no legal, causal or real-company claims. Use clear language and ensure navigation reaches the page.

**How to check:** Compare every definition with BRD/TRD/system_design and confirm notice/navigation.  
**Tests that must pass:** TC-F-17, -20; TC-T-16.  
**Commit:** `git add . && git commit -m "BUILD-11: add About and Definitions page"`

### BUILD-12 — Integrate navigation and persistent filters

**Files:** app.py, pages/*.py, src/ui.py, tests/test_app.py  
**Stories / features:** US-03, US-15–17 · FR-03, FR-09 · UI-01–UI-08

**Exact prompt for the AI:**
> Act as a Streamlit integration engineer. Wire all eight UI screens into navigation. Keep stable session-state keys for year, department, job level and tenure band, and apply them consistently where relevant. Explain non-applicable filters. Verify titles, active screen, empty states and synthetic notices. Do not change approved formulas. Add AppTest navigation and filter-persistence checks, including no-match and restored-default cohorts.

**How to check:** Visit all eight screens; change filters, verify persistence/results, test no-match and reset.  
**Tests that must pass:** TC-F-02–08, -17, -20, TC-T-12–16.  
**Commit:** `git add . && git commit -m "BUILD-12: integrate multipage navigation"`

### BUILD-13 — Complete and run the test suite

**Files:** tests/test_data.py, tests/test_analysis.py, tests/test_app.py, tests/test_project.py, docs/13_Test_Cases.docx, docs/04_Traceability_Matrix.xlsx  
**Stories / features:** US-01–17 · FR-01–10 · UI-01–08

**Exact prompt for the AI:**
> Act as a test engineer. Reconcile pytest/AppTest with all 25 functional and 17 technical cases and every BR row in the RTM. Add the missing per-page render, empty-filter and filtered-download tests; do not weaken tests to hide defects. Check DB schema/counts/keys/FKs, cleaning, known KPI formulas, statistics, model outputs, app startup, all eight pages, navigation/filter persistence, export scope and performance. Run the complete suite in a clean supported Python 3.12 environment. Target first render under 3 seconds and each page under 5 seconds on the recorded machine. Update statuses only with observed results and report failures precisely.

**How to check:** Clean install, `python -m pytest -q`, all-page AppTest and timed render; require every test pass.  
**Tests that must pass:** TC-F-01–25 and TC-T-01–17.  
**Commit:** `git add . && git commit -m "BUILD-13: finish tests and traceability"`

### BUILD-14 — Finalize README and delivery documentation

**Files:** README.md, docs/system_design.md, docs/test_plan.md, docs/04_Traceability_Matrix.xlsx, docs/13_Test_Cases.docx  
**Stories / features:** US-01–17 · FR-01–10

**Exact prompt for the AI:**
> Act as a technical writer. Update README and supporting docs to match verified implementation and test results. Include Python version, exact setup/run/test commands, folder structure, database tables, regeneration behavior, synthetic-only warning, metric definitions/denominators, page guide, assumptions, test outcome and deployment URL if available. Verify links and schema. Do not claim tests, approvals or deployment without evidence. Keep IDs/priorities unchanged; flag provisional HMW wording and project-ID placeholder.

**How to check:** Follow README in a clean clone; verify links, commands, schema, results and URL.  
**Tests that must pass:** TC-T-01–17 green before claiming release readiness.  
**Commit:** `git add . && git commit -m "BUILD-14: finalize README and docs"`

### BUILD-15 — Deploy and verify Streamlit Community Cloud

**Files:** app.py, requirements.txt, data/app.db, .gitignore, .streamlit/config.toml, README.md, pages/, src/  
**Stories / features:** US-01–17 · FR-01–10

**Exact prompt for the AI:**
> Act as a deployment engineer. Verify root app.py and pinned requirements, approved synthetic five-table data/app.db, relative paths, ignored secrets/venv/caches and no real personal data. Confirm clean Python 3.12 install and passing tests. Prepare the GitHub main branch and Streamlit Community Cloud configuration for app.py. Do not invent a repository or URL; use only the repository/destination supplied by the project owner. After deployment, inspect logs and smoke-test all eight screens, filters, charts, empty states and downloads. Record live URL and evidence in README and project documents.

**How to check:** Confirm repository/deploy logs; visit live URL and smoke-test all pages; record verified URL.  
**Tests that must pass:** All TC-F and TC-T cases locally; repeat critical smoke tests in Cloud.  
**Commit:** `git add . && git commit -m "BUILD-15: deploy and verify hosted app"`

## Definition of Done

- Must BR-01, BR-02, BR-03, BR-05, BR-07, BR-09 and BR-11 meet their acceptance criteria. Deferred Should/Could items have rationale and owner.
- All 25 functional and 17 technical cases have current results and automated tests pass without weakened expectations.
- All ten OQs map to implemented analysis and evidence; all 12 BRs have source HMW, story, UI and test traceability.
- The five-table Step 8 SQLite design is the single validated schema; its keys, FKs, ranges and categories pass.
- All eight screens render; shared filters persist/recalculate; empty states are clear; aggregate downloads match filtered results.
- First render is under 3 seconds and each page under 5 seconds on the recorded environment.
- Clean Python 3.12 install and README commands work; dependencies are pinned.
- Streamlit Community Cloud URL and smoke-test evidence are recorded. Deployment contains synthetic data only and no secrets.
- Provisional HMW wording, business assumptions and project-ID placeholder are reconciled or marked pending.

## Commands (Windows PowerShell)

Run at the repository root. Regenerate SQLite only after BUILD-02 aligns the generator with the Step 8 five-table contract.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
streamlit run app.py --server.port 8502
```

Open `http://localhost:8502`. Optional deterministic data regeneration after BUILD-02: `python generate_data.py`.

## Viva notes — 10 likely questions

1. **Why synthetic data?** Safe to share/test; designed patterns do not describe an actual employer.
2. **How is year-end headcount defined?** Joined by December 31 and not exited on or before the snapshot date.
3. **What is a broken rung?** Compare gender representation by ordered job levels and leadership, showing counts.
4. **What is the unadjusted pay gap?** (Male mean − Female mean) / Male mean; show medians and sample sizes too.
5. **Why log salary in OLS?** Salary can be right-skewed; the coefficient is an adjusted percentage association under the model.
6. **Why Mann–Whitney U?** It compares independent distributions without requiring normally distributed salaries; assumptions still matter.
7. **What is the attrition denominator?** Opening workforce at risk for the year; show exits and denominator.
8. **How is promotion rate calculated?** Promotions divided by the explicitly eligible population, not all employees.
9. **What does a significant p-value prove?** Evidence against the null under assumptions, not causation or discrimination.
10. **What remains before public deployment?** Reconcile provisional HMW/PRD and project ID, confirm public disclosure of student identifiers, validate on Python 3.12, and complete the cloud deployment checks.

## Current handoff status

Latest full run: **78 passed in 18.03 seconds** using Python 3.14.6; first-render timing passed on this machine and `pip check` reported no broken requirements. Python 3.12 is the supported target but was unavailable for runtime verification. AppTest renders all eight pages and exercises shared filter changes, no-match states and aggregate export scope. Remaining manual functional scenarios are marked Not run in the test-case register. Approved Step 2 HMW wording, Step 6 PRD and issued project ID were unavailable. The supplied GitHub repository is public; the project has not been pushed because its documents contain student identifiers and explicit approval to publish those details was not given. No cloud URL is claimed.
