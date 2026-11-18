"""Generate deterministic synthetic data matching docs/08_Database_Design.xlsx.

Run from the project root with: python src/generate_data.py
All people, identifiers, events, and salaries are fictional. The Step 8
schema intentionally has no name or location columns, so none are added.
"""
from __future__ import annotations

import csv
import json
import random
import sqlite3
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DESIGN_FILE = ROOT / "docs" / "08_Database_Design.xlsx"
SEED = 42
YEARS = range(2021, 2026)
GENDERS = ("Female", "Male", "Other")
DEPARTMENTS = (
    "Engineering", "Quality Assurance", "Data & Analytics", "DevOps",
    "Human Resources", "Finance", "Sales", "Customer Support",
)
LEVEL_TITLES = (
    "Trainee / Associate", "Analyst", "Senior", "Lead", "Manager",
    "Senior Manager", "Director and above",
)
EDUCATION = ("Diploma", "Bachelor's", "Master's", "Doctorate")
ROLES = {
    "Engineering": ("Software Engineer", "Engineering Manager", "Architect"),
    "Quality Assurance": ("QA Analyst", "QA Engineer", "QA Manager"),
    "Data & Analytics": ("Data Analyst", "Data Engineer", "Analytics Manager"),
    "DevOps": ("DevOps Engineer", "Site Reliability Engineer", "Platform Manager"),
    "Human Resources": ("Recruiter", "HR Partner", "People Manager"),
    "Finance": ("Financial Analyst", "Accountant", "Finance Manager"),
    "Sales": ("Account Executive", "Sales Analyst", "Sales Manager"),
    "Customer Support": ("Support Specialist", "Support Lead", "Support Manager"),
}
TABLE_COLUMNS = {
    "Department": ["dept_id", "department_name", "target_women_pct"],
    "JobLevel": ["level_id", "level_name", "level_rank", "display_title", "is_leadership", "target_women_pct"],
    "Employee": ["emp_id", "gender", "join_date", "exit_date", "total_experience_years", "education_level"],
    "EmployeeYear": ["emp_id", "reporting_year", "snapshot_date", "dept_id", "level_id", "job_role",
                     "active_at_year_start", "active_at_year_end", "hired_in_year", "exit_in_year",
                     "tenure_years_start", "tenure_years_end", "annual_salary_inr", "promotion_eligible",
                     "promoted", "promotion_date", "performance_rating"],
    "ApplicantEvent": ["applicant_id", "gender", "dept_id", "applied_date", "stage_reached"],
}


def schema_from_design() -> str:
    """Use the exact DDL documented in Step 8 rather than a second schema."""
    from openpyxl import load_workbook

    wb = load_workbook(DESIGN_FILE, data_only=True, read_only=True)
    try:
        ddl = wb["SQLite_DDL"]["B2"].value
    finally:
        wb.close()
    if not isinstance(ddl, str) or "CREATE TABLE Department" not in ddl:
        raise ValueError(f"Could not read the Step 8 DDL from {DESIGN_FILE}")
    return ddl


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 February
        return d.replace(month=2, day=28, year=d.year + years)


def make_tables(rng: random.Random) -> dict[str, list[dict]]:
    departments = [
        {"dept_id": i, "department_name": name,
         "target_women_pct": round(rng.uniform(.36, .48), 2)}
        for i, name in enumerate(DEPARTMENTS, 1)
    ]
    levels = [
        {"level_id": i, "level_name": f"L{i}", "level_rank": i,
         "display_title": LEVEL_TITLES[i - 1], "is_leadership": int(i >= 5),
         "target_women_pct": round(max(.25, .48 - .025 * (i - 1)), 2)}
        for i in range(1, 8)
    ]

    employees: list[dict] = []
    employee_years: list[dict] = []
    active_ids: list[str] = []
    # Predetermine exactly 500 active and 300 exited employees.
    # Keep the first three active so two records can be seeded as exact
    # employee-profile lookalikes (their unique IDs are the only difference).
    exit_ids = set(rng.sample(range(4, 801), 300))
    outlier_employee = next(n for n in range(1, 801) if n not in exit_ids)
    # The first two repeated demographic profiles are intentional review flags:
    # unique synthetic IDs mean primary keys remain valid.
    near_duplicate_profile: dict | None = None
    for n in range(1, 801):
        emp_id = f"E{n:04d}"
        exited = n in exit_ids
        join = date(rng.randint(2015, 2024 if exited else 2025), rng.randint(1, 12), 1)
        if n in (2, 3) and near_duplicate_profile:
            join = near_duplicate_profile["join"]
        if exited:
            # Step 8's CHECK rule requires a leaver to be active on Jan 1;
            # keep exit later than the first full anniversary to satisfy it.
            earliest = max(join + timedelta(days=366), date(2022, 1, 1))
            latest = max(date(2025, 11, 30), earliest)
            exit_day = earliest + timedelta(days=rng.randint(0, (latest - earliest).days))
        else:
            exit_day = None
            active_ids.append(emp_id)

        # Leadership representation declines by level; other genders are retained.
        level = rng.choices(range(1, 8), weights=(25, 22, 18, 14, 10, 7, 4))[0]
        if level <= 2:
            gender_weights = (0.51, 0.47, 0.02)
        elif level <= 4:
            gender_weights = (0.45, 0.53, 0.02)
        else:
            gender_weights = (0.34, 0.64, 0.02)
        gender = rng.choices(GENDERS, weights=gender_weights)[0]
        prior = round(rng.uniform(0, 32), 1)
        education = rng.choices(EDUCATION, weights=(.08, .56, .32, .04))[0]
        # A few realistic look-alike records aid duplicate-review demonstrations.
        if n in (2, 3) and near_duplicate_profile:
            gender, prior, education = (near_duplicate_profile[k] for k in ("gender", "prior", "education"))
        elif n == 1:
            near_duplicate_profile = {"gender": gender, "prior": prior, "education": education, "join": join}
        if n == 799:
            prior = 48.0  # Intentional high-experience outlier, inside the schema's >= 0 rule.
        employees.append({
            "emp_id": emp_id, "gender": gender, "join_date": join.isoformat(),
            "exit_date": exit_day.isoformat() if exit_day else None,
            "total_experience_years": prior, "education_level": education,
        })

        # Level progression is monotonic, with a modestly lower promotion chance
        # for women at the same eligibility stage (synthetic signal to discover).
        current_level = level
        for year in YEARS:
            year_start, year_end = date(year, 1, 1), date(year, 12, 31)
            if join > year_end or (exit_day and exit_day < year_start):
                continue
            start_active = int(join <= year_start and (exit_day is None or exit_day >= year_start))
            end_active = int(join <= year_end and (exit_day is None or exit_day >= year_end))
            hired = int(join.year == year)
            exited_this_year = int(exit_day is not None and exit_day.year == year)
            elapsed_start = max(0, (year_start - join).days / 365.25)
            elapsed_end = max(0, (year_end - join).days / 365.25)
            if join.year < year and current_level < 7:
                rating_for_promo = rng.choices((1, 2, 3, 4, 5), weights=(.03, .12, .45, .32, .08))[0]
            else:
                rating_for_promo = rng.choices((1, 2, 3, 4, 5), weights=(.03, .12, .45, .32, .08))[0]
            eligible = int(start_active and elapsed_start >= 1 and current_level < 7)
            promo_probability = .075 if gender == "Female" else (.105 if gender == "Male" else .09)
            promoted = int(bool(eligible and rating_for_promo >= 3 and rng.random() < promo_probability))
            promo_date = None
            if promoted:
                promo_date = (date(year, rng.randint(3, 11), rng.randint(1, 25))).isoformat()
            department = rng.choice(DEPARTMENTS)
            # Keep role seniority broadly aligned to the reporting level.
            if current_level < 5:
                junior_roles = tuple(role_name for role_name in ROLES[department]
                                    if "Manager" not in role_name and "Architect" not in role_name)
                role = rng.choice(junior_roles)
            else:
                senior_roles = tuple(role_name for role_name in ROLES[department]
                                     if "Manager" in role_name or "Architect" in role_name)
                role = rng.choice(senior_roles or ROLES[department][-1:])
            # Level-based salary scale includes a small structural gender gap.
            base_salary = 380_000 + current_level * 190_000 + prior * 15_000
            gap = -.045 if gender == "Female" else (-.01 if gender == "Other" else 0)
            salary = round(max(300_000, base_salary * (1 + gap + rng.gauss(0, .06))) / 1000) * 1000
            rating = rating_for_promo
            annual_salary = salary
            # Positive but extreme allowed values create transparent outlier checks.
            employee_years.append({
                "emp_id": emp_id, "reporting_year": year, "snapshot_date": f"{year}-12-31",
                "dept_id": DEPARTMENTS.index(department) + 1, "level_id": current_level,
                "job_role": role, "active_at_year_start": start_active, "active_at_year_end": end_active,
                "hired_in_year": hired, "exit_in_year": exited_this_year,
                "tenure_years_start": round(elapsed_start, 2) if start_active else None,
                "tenure_years_end": round(elapsed_end, 2) if end_active else None,
                "annual_salary_inr": annual_salary, "promotion_eligible": eligible,
                "promoted": promoted, "promotion_date": promo_date,
                "performance_rating": rating,
            })
            if promoted:
                current_level = min(7, current_level + 1)

    # Set a reproducible exact 2.5% missing rate in two nullable analysis fields.
    salary_indices = rng.sample(range(len(employee_years)), round(.025 * len(employee_years)))
    rating_indices = rng.sample(range(len(employee_years)), round(.025 * len(employee_years)))
    for idx in salary_indices:
        employee_years[idx]["annual_salary_inr"] = None
    for idx in rating_indices:
        employee_years[idx]["performance_rating"] = None
    # One high but schema-valid salary outlier is retained for review.
    outlier_row = next(r for r in employee_years
                       if r["emp_id"] == f"E{outlier_employee:04d}" and r["reporting_year"] == 2025)
    outlier_row["annual_salary_inr"] = 8_500_000.0

    applicants: list[dict] = []
    for n in range(1, 5001):
        gender = rng.choices(GENDERS, weights=(.47, .51, .02))[0]
        # Stage reached, with a synthetic women drop-off through later funnel stages.
        weights = ((.49, .27, .15, .09) if gender == "Female"
                   else ((.43, .27, .18, .12) if gender == "Male" else (.46, .27, .17, .10)))
        stage = rng.choices(("Applied", "Shortlisted", "Offered", "Joined"), weights=weights)[0]
        applied = date(2021, 1, 1) + timedelta(days=rng.randint(0, (date(2025, 12, 31) - date(2021, 1, 1)).days))
        applicants.append({"applicant_id": f"A{n:05d}", "gender": gender,
                           "dept_id": rng.randint(1, len(DEPARTMENTS)),
                           "applied_date": applied.isoformat(), "stage_reached": stage})
    return {"Department": departments, "JobLevel": levels, "Employee": employees,
            "EmployeeYear": employee_years, "ApplicantEvent": applicants}


def materialize_sqlite(tables: dict[str, list[dict]], path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_from_design())
        for table, rows in tables.items():
            cols = TABLE_COLUMNS[table]
            marks = ",".join("?" for _ in cols)
            sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({marks})"
            conn.executemany(sql, [tuple(row[c] for c in cols) for row in rows])
        conn.commit()
    finally:
        conn.close()


def materialize_exports(tables: dict[str, list[dict]], db_path: Path) -> None:
    # One CSV per base table, using the exact Step 8 column order.
    for table, rows in tables.items():
        with (DATA_DIR / f"{table}.csv").open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=TABLE_COLUMNS[table])
            writer.writeheader()
            writer.writerows(rows)
    # Add the documented 33-column analytical view as an extra workbook sheet.
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        view_rows = [dict(row) for row in conn.execute("SELECT * FROM vw_employee_analysis").fetchall()]
        view_columns = [r[1] for r in conn.execute("PRAGMA table_info(vw_employee_analysis)")]
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows, cols in [*( (n, tables[n], TABLE_COLUMNS[n]) for n in TABLE_COLUMNS ),
                             ("vw_employee_analysis", view_rows, view_columns)]:
        ws = wb.create_sheet(name[:31])
        ws.append(cols)
        for row in rows:
            ws.append([row.get(c) for c in cols])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="24476B")
            cell.alignment = Alignment(wrap_text=True)
        for col_idx, col in enumerate(cols, 1):
            max_len = min(38, max(len(str(col)), *(len(str(ws.cell(r, col_idx).value or ""))
                                                    for r in range(2, min(ws.max_row, 80) + 1))))
            ws.column_dimensions[get_column_letter(col_idx)].width = max(12, max_len + 2)
    wb.save(DATA_DIR / "Gender_Diversity_Analysis_data.xlsx")


def validation_report(tables: dict[str, list[dict]], db_path: Path) -> dict:
    expected = {"Department": 8, "JobLevel": 7, "Employee": 800,
                "ApplicantEvent": 5000}
    counts = {name: len(rows) for name, rows in tables.items()}
    fk_violations = []
    range_issues = []
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        fk_violations.extend(conn.execute("PRAGMA foreign_key_check").fetchall())
        view_columns = [r[1] for r in conn.execute("PRAGMA table_info(vw_employee_analysis)")]
        view_count = conn.execute("SELECT COUNT(*) FROM vw_employee_analysis").fetchone()[0]
        if len(view_columns) < 30 or len(view_columns) > 40:
            range_issues.append(f"Analytical view has {len(view_columns)} columns; expected 30-40")
    if counts["EmployeeYear"] < 150:
        range_issues.append("EmployeeYear has fewer than 150 rows")
    if not 2500 <= counts["EmployeeYear"] <= 4000:
        range_issues.append(f"EmployeeYear: expected 2,500-4,000 project-scale rows, got {counts['EmployeeYear']}")
    for table, expected_count in expected.items():
        if counts[table] != expected_count:
            range_issues.append(f"{table}: expected {expected_count}, got {counts[table]}")
    for row in tables["Department"]:
        if row["dept_id"] <= 0 or row["target_women_pct"] is not None and not 0 <= row["target_women_pct"] <= 1:
            range_issues.append(f"Department range violation: {row['dept_id']}")
    for row in tables["JobLevel"]:
        if row["level_rank"] not in range(1, 8) or row["is_leadership"] not in (0, 1):
            range_issues.append(f"JobLevel range violation: {row['level_id']}")
    for row in tables["Employee"]:
        if row["gender"] not in GENDERS or row["total_experience_years"] < 0:
            range_issues.append(f"Employee range/category violation: {row['emp_id']}")
        if row["exit_date"] and row["exit_date"] < row["join_date"]:
            range_issues.append(f"Employee exit precedes join: {row['emp_id']}")
    for row in tables["EmployeeYear"]:
        if row["reporting_year"] not in YEARS or row["level_id"] not in range(1, 8):
            range_issues.append(f"EmployeeYear period/level violation: {row['emp_id']}/{row['reporting_year']}")
        if any(row[k] not in (0, 1) for k in ("active_at_year_start", "active_at_year_end", "hired_in_year",
                                                "exit_in_year", "promotion_eligible", "promoted")):
            range_issues.append(f"EmployeeYear boolean violation: {row['emp_id']}/{row['reporting_year']}")
        if row["annual_salary_inr"] is not None and row["annual_salary_inr"] <= 0:
            range_issues.append(f"EmployeeYear salary violation: {row['emp_id']}/{row['reporting_year']}")
        if row["performance_rating"] is not None and row["performance_rating"] not in range(1, 6):
            range_issues.append(f"EmployeeYear rating violation: {row['emp_id']}/{row['reporting_year']}")
    for row in tables["ApplicantEvent"]:
        if row["gender"] not in GENDERS or row["stage_reached"] not in ("Applied", "Shortlisted", "Offered", "Joined"):
            range_issues.append(f"ApplicantEvent category violation: {row['applicant_id']}")
    # Report intentionally seeded data-quality review issues separately from SQL constraints.
    missing_salary = sum(r["annual_salary_inr"] is None for r in tables["EmployeeYear"])
    missing_rating = sum(r["performance_rating"] is None for r in tables["EmployeeYear"])
    lookalikes = 2
    outliers = {"annual_salary_inr": [r["emp_id"] for r in tables["EmployeeYear"]
                                      if r["annual_salary_inr"] and r["annual_salary_inr"] > 5_000_000],
                "total_experience_years": [r["emp_id"] for r in tables["Employee"]
                                           if r["total_experience_years"] > 40]}
    report = {
        "seed": SEED,
        "row_counts": counts,
        "active_employee_id_count": 500,
        "exited_employee_id_count": 300,
        "sqlite_foreign_key_check": "PASS" if not fk_violations else f"FAIL: {fk_violations}",
        "range_and_design_checks": "PASS" if not range_issues else range_issues,
        "joined_view": {"name": "vw_employee_analysis", "rows": view_count, "columns": len(view_columns)},
        "quality_review_flags": {
            "missing_salary_values": {"count": missing_salary, "pct_of_employee_year": round(100 * missing_salary / counts["EmployeeYear"], 2)},
            "missing_performance_ratings": {"count": missing_rating, "pct_of_employee_year": round(100 * missing_rating / counts["EmployeeYear"], 2)},
            "near_duplicate_employee_profiles": lookalikes,
            "outlier_ids": outliers,
        },
        "schema_note": "Step 8 has no employee/applicant name or location columns; no such columns were added.",
        "patterns_to_find": [
            "Women are less represented at L5-L7 than at L1-L2 (leadership pipeline narrowing).",
            "Synthetic female salaries average modestly lower than male salaries within comparable roles/levels.",
            "Female promotion probability is modestly lower among eligible, rated employees.",
            "Female applicants reach Joined at a lower rate than male applicants.",
        ],
    }
    (DATA_DIR / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Human-readable Markdown version for quick review.
    lines = ["# Synthetic dataset validation report", "", f"Seed: {SEED}", "", "## Row counts"]
    lines += [f"- {name}: {count:,}" for name, count in counts.items()]
    lines += [f"- vw_employee_analysis: {view_count:,} rows x {len(view_columns)} columns",
              "", f"Foreign keys: {report['sqlite_foreign_key_check']}",
              f"Design/range checks: {report['range_and_design_checks']}", "",
              "## Seeded analysis patterns"]
    lines += [f"- {x}" for x in report["patterns_to_find"]]
    lines += ["", "## Data quality review flags",
              f"- Missing annual salaries: {missing_salary} ({report['quality_review_flags']['missing_salary_values']['pct_of_employee_year']}%)",
              f"- Missing performance ratings: {missing_rating} ({report['quality_review_flags']['missing_performance_ratings']['pct_of_employee_year']}%)",
              f"- Near-duplicate employee profiles: {lookalikes} (unique emp_id retained for PK integrity)",
              f"- Outlier records: {outliers}",
              "- SQLite remains valid: missing values occur only in nullable columns; duplicate-looking profiles use unique primary keys.",
              "- Names/places are not fields in the approved Step 8 schema."]
    (DATA_DIR / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tables = make_tables(random.Random(SEED))
    db_path = DATA_DIR / "app.db"
    materialize_sqlite(tables, db_path)
    materialize_exports(tables, db_path)
    report = validation_report(tables, db_path)
    if report["sqlite_foreign_key_check"] != "PASS" or report["range_and_design_checks"] != "PASS":
        raise SystemExit(f"Generated data failed validation; see {DATA_DIR / 'validation_report.json'}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
