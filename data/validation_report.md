# Synthetic dataset validation report

Seed: 42

## Row counts
- Department: 8
- JobLevel: 7
- Employee: 800
- EmployeeYear: 3,019
- ApplicantEvent: 5,000
- vw_employee_analysis: 3,019 rows x 33 columns

Foreign keys: PASS
Design/range checks: PASS

## Seeded analysis patterns
- Women are less represented at L5-L7 than at L1-L2 (leadership pipeline narrowing).
- Synthetic female salaries average modestly lower than male salaries within comparable roles/levels.
- Female promotion probability is modestly lower among eligible, rated employees.
- Female applicants reach Joined at a lower rate than male applicants.

## Data quality review flags
- Missing annual salaries: 75 (2.48%)
- Missing performance ratings: 75 (2.48%)
- Near-duplicate employee profiles: 2 (unique emp_id retained for PK integrity)
- Outlier records: {'annual_salary_inr': ['E0001'], 'total_experience_years': ['E0799']}
- SQLite remains valid: missing values occur only in nullable columns; duplicate-looking profiles use unique primary keys.
- Names/places are not fields in the approved Step 8 schema.
