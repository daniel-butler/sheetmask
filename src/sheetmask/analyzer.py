"""
Excel column analyzer for generating LLM prompts.

This tool analyzes Excel files and generates prompts that can be pasted
into Claude/GPT to get anonymization config recommendations.
"""
import pandas as pd
from pathlib import Path
from rich.console import Console

from excel_anonymizer.filename_parser import parse_date_from_filename

console = Console()


def analyze_excel_for_anonymization(
    input_path: Path,
    sheet_name: str | None = None,
    sample_rows: int = 3,
) -> str:
    """
    Generate LLM prompt for analyzing Excel columns.

    Args:
        input_path: Path to Excel file
        sheet_name: Sheet to analyze (None = analyze ALL sheets)
        sample_rows: Number of sample values to show per column

    Returns:
        LLM prompt ready to paste into Claude/GPT
    """
    # Read Excel file - get all sheet names
    xls = pd.ExcelFile(input_path)

    if sheet_name:
        # Analyze single sheet
        sheets_to_analyze = {sheet_name: pd.read_excel(input_path, sheet_name=sheet_name)}
    else:
        # Analyze ALL sheets
        sheets_to_analyze = {name: pd.read_excel(input_path, sheet_name=name) for name in xls.sheet_names}

    # Parse date from filename
    date_result = parse_date_from_filename(input_path.name)

    # Build prompt header
    total_sheets = len(sheets_to_analyze)
    total_rows = sum(len(df) for df in sheets_to_analyze.values())

    prompt = f"""# Excel Column Analysis for Anonymization

## Task
Analyze the columns in this Excel file and recommend anonymization strategies.

## File Information
- **File**: {input_path.name}
"""

    # Add parsed date if found
    if date_result.date:
        prompt += f"- **Parsed Date**: {date_result.date.strftime('%Y-%m-%d')} (Confidence: {date_result.confidence})\n"
        prompt += f"- **Date Pattern**: {date_result.pattern}\n"

    prompt += f"""- **Total Sheets**: {total_sheets}
- **Total Rows**: {total_rows:,}

## Sheet Overview

"""

    # Add sheet overview
    for name, df in sheets_to_analyze.items():
        prompt += f"### {name}\n"
        prompt += f"- **Rows**: {len(df):,}\n"
        prompt += f"- **Columns**: {len(df.columns)}\n\n"

    # Analyze each sheet in detail
    for sheet_name, df in sheets_to_analyze.items():
        prompt += f"\n---\n\n## Sheet: {sheet_name}\n\n"
        prompt += f"**Rows**: {len(df):,} | **Columns**: {len(df.columns)}\n\n"
        prompt += "| Column Name | Data Type | Sample Values | Null % | Unique Count |\n"
        prompt += "|-------------|-----------|---------------|--------|--------------|\n"

        # Analyze each column
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_pct = (df[col].isna().sum() / len(df)) * 100
            unique_count = df[col].nunique()

            # Get sample values (truncate long strings)
            samples = df[col].dropna().head(sample_rows).tolist()
            sample_str = ", ".join(str(s)[:30] for s in samples)
            if not sample_str:
                sample_str = "(all null)"

            prompt += f"| {col} | {dtype} | {sample_str} | {null_pct:.1f}% | {unique_count} |\n"

    sheet_list = list(sheets_to_analyze.keys())
    sheets_example = f'["{sheet_list[0]}"]' if len(sheet_list) == 1 else f'["{sheet_list[0]}", "{sheet_list[1] if len(sheet_list) > 1 else sheet_list[0]}"]'

    prompt += f"""

---

## Questions to Answer

### 1. Sheet Selection
**Which sheets should be kept vs. discarded?**

Consider:
- Does this sheet contain the core data for processing?
- Does this sheet have PII that needs anonymization?
- Is this a lookup table, pivot, or derived summary that can be discarded?
- Are there duplicate/redundant sheets?

**Recommendation format:**
```
sheets_to_keep: ["SheetName1", "SheetName2"]  # Main data sheets only
sheets_to_discard: ["Sheet3", "Sheet4"]  # Explain why for each
```

### 2. Entity Type Analysis
For each sheet you're keeping, identify columns with entities.

**Supported entity types** (see `excel_anonymizer/entity_mapper.py`):
- **PERSON**: Full names (e.g., "John Doe")
- **PERSON_FIRST_NAME**: First names only (e.g., "John")
- **PERSON_LAST_NAME**: Last names only (e.g., "Doe")
- **ORGANIZATION**: Company names, client names, vendor names
- **EMAIL_ADDRESS**: Email addresses (generates fake emails)
- **PHONE_NUMBER**: Phone numbers
- **LOCATION**: Office locations, cities, addresses (if not just codes)
- **PROJECT_NAME**: Project titles
- **PROJECT_DESCRIPTION**: Project descriptions

**Important**: Use the exact entity type names above. The entity mapper does not support custom entity types.

### 3. Numeric Strategy
For each numeric column:

- **Add Variance**: `PercentageVarianceRule(variance_pct=X)` - For base financial values
- **Preserve Relationship**: `PreserveRelationshipRule(formula="...")` - For derived/calculated values
- **Preserve As-Is**: For IDs, codes, counts, percentages that don't reveal sensitive info

### 4. Financial Constraints
Identify any accounting rules that must be preserved:

- Debit = Credit balances?
- Margin% = (GM / Revenue) * 100?
- Running totals or cumulative calculations?
- Any other derived relationships?

### 5. Preserve Columns
Which columns should NOT be anonymized?

- Dates (usually needed for validation)
- Categories/Types (Project Type, Status, etc.)
- Codes/IDs (if not sensitive)
- Flags/Indicators

## Output Format

Save the recommended config as a Python file (e.g., `my_config.py`):

```python
from excel_anonymizer import PercentageVarianceRule, PreserveRelationshipRule

config = {{
    "version": "1.0.0",
    "sheets_to_keep": {sheets_example},
    "entity_columns": {{
        # "Project Manager": "PERSON",
        # "Client Name": "ORGANIZATION",
    }},
    "numeric_rules": {{
        # "Revenue": PercentageVarianceRule(variance_pct=0.3),
        # "Margin": PreserveRelationshipRule(
        #     formula="context['Revenue'] - context['Cost']",
        #     dependent_columns=["Revenue", "Cost"]
        # ),
    }},
    "preserve_columns": [
        # "Date",
        # "Project Type",
    ],
}}
```

Then run:
```bash
excel-anon process your_file.xlsx --config my_config.py
```

## Important Notes

- **Sheet Selection**: Only keep sheets with core data. Discard lookups, pivots, and summaries to reduce test fixture size.
- **Entity Consistency**: All occurrences of the same entity (e.g., "Acme Corp") will map to the same fake value across ALL sheets and columns.
- **Validation**: The anonymized data will be validated, so ensure numeric rules don't break constraints.
- **Dates**: Preserve dates as-is (needed for filename alignment and date-based validation).
- **Derived Columns**: Use `PreserveRelationshipRule` to recompute from anonymized source columns.

## Your Task

1. **Review all sheets above** - identify which are core data vs. lookup/pivot/summary sheets
2. **For sheets to keep**: Identify entities, numeric strategies, and preserve columns
3. **For sheets to discard**: Briefly explain why (e.g., "pivot table, can be regenerated")
4. **Provide complete config** in the format above

Please analyze and provide recommendations.
"""

    return prompt
