# Test Plan

The pytest suite covers all five canonical database tables and counts, schema and foreign keys, cleaning and validation, cohort and rate formulas, sparse contingency tests, salary and performance comparisons, robust adjusted OLS, target calculations, hiring funnel conversions, aggregate CSV exports, all eight Streamlit pages, shared filters, empty states, and core KPI behavior.

Run with:

```powershell
python -m pytest -q
```

The checked-in synthetic database is reproducible from `generate_data.py`. Tests create a separate temporary database and do not overwrite `data/app.db`.

Latest observed run: **78 passed in 17.73 seconds** using Python 3.14.6. The project targets Python 3.12; that interpreter was not available for this run. The run includes an AppTest timing assertion for first render under 3 seconds on this machine. Manual browser acceptance cases remain Not run in `docs/13_Test_Cases.docx`.
