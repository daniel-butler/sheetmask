# sheetmask

Turn a real Excel file into a safe test fixture — fake names, fake numbers, real structure.

## Install

```bash
pip install git+https://github.com/daniel-butler/sheetmask.git
```

```bash
uv add git+https://github.com/daniel-butler/sheetmask.git
```

## Quickstart

1. Run `analyze` on your file. It prints a prompt describing the columns and sample data — copy it.

```bash
sheetmask analyze "Q4 Expense Report.xlsx"
```

2. Paste the prompt into Claude or ChatGPT. Save the config it returns:

```python
# q4_expense_config.py
from sheetmask import PercentageVarianceRule, PreserveRelationshipRule

config = {
    "version": "1.0.0",
    "sheets_to_keep": ["Expenses"],
    "entity_columns": {
        "Employee Name": "PERSON",
        "Department": "ORGANIZATION",
        "Manager": "PERSON",
    },
    "numeric_rules": {
        "Reimbursement": PercentageVarianceRule(variance_pct=0.2),
        "Net Amount": PreserveRelationshipRule(
            formula="context['Reimbursement'] - context['Deduction']",
            dependent_columns=["Reimbursement", "Deduction"],
        ),
    },
    "preserve_columns": ["Date", "Category"],
}
```

3. Run `process`. The output lands beside the original.

```bash
sheetmask process "Q4 Expense Report.xlsx" --config q4_expense_config.py
# Output: Q4 Expense Report_SYNTHETIC.xlsx
```

## Reference

### Entity types

Each unique value maps to the same fake value throughout the file, so relationships between rows stay intact.

| Type | Generates |
|------|-----------|
| `PERSON` | Full name |
| `PERSON_FIRST_NAME` | First name only |
| `PERSON_LAST_NAME` | Last name only |
| `ORGANIZATION` | Company name |
| `EMAIL_ADDRESS` | Email address |
| `PHONE_NUMBER` | Phone number |
| `PROJECT_NAME` | Project name |
| `LOCATION` | City, State |

### Numeric rules

**`PercentageVarianceRule`** replaces each value with a random number within a band of the original. Use it for independent figures.

```python
"Headcount": PercentageVarianceRule(variance_pct=0.15)
# 100 becomes a random number between 85 and 115.
```

**`PreserveRelationshipRule`** derives a value from other already-anonymized columns. Use it wherever one column is computed from others, so the arithmetic stays consistent.

```python
"Gross Margin": PreserveRelationshipRule(
    formula="context['Revenue'] - context['Cost']",
    dependent_columns=["Revenue", "Cost"],
)
# Gross Margin will always equal anonymized Revenue minus anonymized Cost.
```

### All commands

| Command | Description |
|---------|-------------|
| `sheetmask analyze <file>` | Analyze file and print LLM prompt |
| `sheetmask analyze <file> -o prompt.txt` | Save LLM prompt to a file |
| `sheetmask analyze-multi f1 f2 f3` | Analyze multiple files for shared schema patterns |
| `sheetmask process <file> --config config.py` | Anonymize file using config |
| `sheetmask process <file> out.xlsx --config config.py --seed 42` | Write to named output with fixed random seed |
