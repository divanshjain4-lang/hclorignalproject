"""Run validation and core statistical summaries from the synthetic SQLite database."""
from pathlib import Path
import json
import pandas as pd

from src.analytics import employee_dimension, yearly_outcomes
from src.database import generate_synthetic_db, load_dataset
from src.metrics import adjusted_pay_model, outcome_chi_square, salary_tests

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "app.db"
REPORTS = ROOT / "reports"

if not DB.exists():
    print("Generating database:", generate_synthetic_db(DB))
tables = load_dataset(DB)
employees = employee_dimension(tables)
REPORTS.mkdir(exist_ok=True)
quality = {"employee_rows": len(tables["employees"]), "applicant_rows": len(tables["applicants"]),
           "duplicate_employee_ids": int(tables["employees"].emp_id.duplicated().sum()),
           "missing_mandatory_employee_cells": int(tables["employees"][
               ["emp_id", "gender", "dept_id", "role", "level_id", "join_date", "total_experience_years", "education"]
           ].isna().sum().sum())}
(REPORTS / "data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
salary = tables["salaries"].query("year == 2025").merge(employees, on="emp_id").merge(tables["appraisals"].query("year == 2025")[["emp_id", "rating"]], on="emp_id", how="left")
salary.to_csv(REPORTS / "salary_2025_analysis.csv", index=False)
pd.DataFrame(salary_tests(salary)).to_csv(REPORTS / "salary_tests_by_level.csv", index=False)
model = adjusted_pay_model(salary.rename(columns={"department_name": "department"}))
with (REPORTS / "statistical_summary.txt").open("w", encoding="utf-8") as file:
    file.write("Adjusted log-salary OLS with HC3 robust standard errors\n")
    file.write(model.summary().as_text())
    file.write("\n\nGender terms:\n")
    for term in [name for name in model.params.index if "gender" in name.casefold()]:
        file.write(f"{term}: coefficient={model.params[term]:.6f}, p={model.pvalues[term]:.6g}\n")
attrition, promotions = yearly_outcomes(employees, tables["promotions"])
attrition.to_csv(REPORTS / "attrition_rates.csv", index=False)
promotions.to_csv(REPORTS / "promotion_rates.csv", index=False)
print(json.dumps(quality, indent=2))
print(f"Wrote analysis outputs to {REPORTS}")
