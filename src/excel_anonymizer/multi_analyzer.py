"""
Multi-month analyzer for comparing Excel files across time periods.

Detects schema stability, data patterns, and quality issues by analyzing
multiple files representing different time periods.
"""

import pandas as pd
from pathlib import Path
from typing import List
from collections import defaultdict

from .filename_parser import parse_date_from_filename


def analyze_multiple_files(file_paths: List[Path]) -> str:
    """
    Generate comprehensive multi-month analysis prompt for LLM.

    Args:
        file_paths: List of Excel file paths to analyze

    Returns:
        LLM prompt with multi-month analysis
    """
    if not file_paths:
        raise ValueError("No files provided for analysis")

    # Parse filename dates
    file_info = []
    for path in file_paths:
        date_result = parse_date_from_filename(path.name)
        file_info.append({
            "path": path,
            "name": path.name,
            "date": date_result.date,
            "date_confidence": date_result.confidence,
            "date_pattern": date_result.pattern,
        })

    # Sort by date (None dates go to end)
    file_info.sort(key=lambda x: (x["date"] is None, x["date"]))

    # Compare schemas
    schema_comparison = compare_schemas(file_paths)

    # Compare data patterns
    data_patterns = compare_data_patterns(file_paths)

    # Build prompt
    prompt = _build_multi_month_prompt(file_info, schema_comparison, data_patterns)

    return prompt


def compare_schemas(file_paths: List[Path]) -> dict:
    """
    Compare schemas across multiple files.

    Returns dict with:
    - stable_columns: Columns present in ALL files
    - variable_columns: Columns not in all files
    - schema_changes: Added/removed columns
    """
    if not file_paths:
        raise ValueError("No files provided for schema comparison")

    # Read first sheet from each file
    file_schemas = []
    for path in file_paths:
        df = pd.read_excel(path)
        file_schemas.append({
            "path": path,
            "columns": set(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        })

    # Find stable columns (in all files)
    all_columns = set.intersection(*[s["columns"] for s in file_schemas])
    stable_columns = list(all_columns)

    # Find variable columns (not in all files)
    all_possible_columns = set.union(*[s["columns"] for s in file_schemas])
    variable_columns = {}

    for col in all_possible_columns:
        if col not in all_columns:
            present_count = sum(1 for s in file_schemas if col in s["columns"])
            variable_columns[col] = {
                "present_in": present_count,
                "total_files": len(file_schemas),
            }

    return {
        "stable_columns": stable_columns,
        "variable_columns": variable_columns,
        "total_files": len(file_paths),
    }


def compare_data_patterns(file_paths: List[Path]) -> dict:
    """
    Compare data patterns across files.

    Returns dict with column-level statistics:
    - null_pct_range: (min, max) null percentage across files
    - types: Set of data types seen
    - type_consistent: Boolean if types are consistent
    - unique_count_range: (min, max) unique value counts
    """
    patterns = defaultdict(lambda: {
        "null_pcts": [],
        "types": set(),
        "unique_counts": [],
    })

    # Analyze each file
    for path in file_paths:
        df = pd.read_excel(path)

        for col in df.columns:
            null_pct = (df[col].isna().sum() / len(df)) * 100
            dtype = str(df[col].dtype)
            unique_count = df[col].nunique()

            patterns[col]["null_pcts"].append(null_pct)
            patterns[col]["types"].add(dtype)
            patterns[col]["unique_counts"].append(unique_count)

    # Calculate summary statistics
    result = {}
    for col, data in patterns.items():
        null_pcts = data["null_pcts"]
        result[col] = {
            "null_pct_range": (min(null_pcts), max(null_pcts)) if null_pcts else (0, 0),
            "types": data["types"],
            "type_consistent": len(data["types"]) == 1,
            "unique_count_range": (min(data["unique_counts"]), max(data["unique_counts"])) if data["unique_counts"] else (0, 0),
        }

    return result


def _build_multi_month_prompt(file_info: List[dict], schema_comparison: dict, data_patterns: dict) -> str:
    """Build the comprehensive multi-month analysis prompt"""

    prompt = """# Multi-Month Excel Analysis for Anonymization

## Task
Analyze multiple Excel files across time periods to identify:
- Schema stability (which columns are consistent)
- Data quality issues (format changes, null patterns)
- Validation rule candidates (based on multi-month patterns)
- Sheet selection guidance (which sheets are essential)

## Files Analyzed

"""

    # List all files with parsed dates
    for i, info in enumerate(file_info, 1):
        date_str = info["date"].strftime("%Y-%m-%d") if info["date"] else "Unknown"
        prompt += f"{i}. **{info['name']}**\n"
        prompt += f"   - Parsed Date: {date_str} (Confidence: {info['date_confidence']})\n"
        prompt += f"   - Pattern: {info['date_pattern']}\n\n"

    # Filename pattern analysis
    prompt += """## Filename Pattern Analysis

"""
    # Detect if all files follow same pattern
    patterns = [info["date_pattern"] for info in file_info]
    unique_patterns = set(patterns)

    if len(unique_patterns) == 1 and "No date found" not in patterns[0]:
        prompt += f"- **Detected Pattern**: {patterns[0]}\n"
        prompt += f"- **Date Parsing**: {len([p for p in patterns if 'No date' not in p])}/{len(patterns)} successful\n"
        prompt += "- **Consistency**: High (all files follow same pattern)\n"
        prompt += "- **Recommendation**: This pattern is reliable for date extraction\n\n"
    else:
        prompt += "- **Consistency**: Low (multiple patterns detected)\n"
        prompt += "- **Patterns Found**:\n"
        for pattern in unique_patterns:
            count = patterns.count(pattern)
            prompt += f"  - {pattern} ({count} file{'s' if count > 1 else ''})\n"
        prompt += "\n"

    # Schema stability
    prompt += """## Schema Stability Report

### Stable Columns (present in all files)

"""

    stable_cols = schema_comparison["stable_columns"]
    if stable_cols:
        prompt += "The following columns appear in ALL files:\n\n"
        for col in sorted(stable_cols):
            # Add data pattern info
            pattern = data_patterns.get(col, {})
            null_range = pattern.get("null_pct_range", (0, 0))
            type_consistent = pattern.get("type_consistent", True)

            status = "✅" if type_consistent and null_range[1] < 100 else "⚠️"
            prompt += f"- {status} **{col}**\n"

            if null_range[0] == null_range[1]:
                prompt += f"  - Null: {null_range[0]:.1f}%\n"
            else:
                prompt += f"  - Null range: {null_range[0]:.1f}% - {null_range[1]:.1f}%\n"

            if not type_consistent:
                types_str = ", ".join(pattern.get("types", set()))
                prompt += f"  - ⚠️ Type inconsistency: {types_str}\n"

            # Flag always-null columns
            if null_range[0] == 100 and null_range[1] == 100:
                prompt += "  - ⚠️ **ALWAYS NULL** - candidate for removal\n"

            prompt += "\n"
    else:
        prompt += "No columns are present in all files.\n\n"

    # Variable columns
    var_cols = schema_comparison["variable_columns"]
    if var_cols:
        prompt += """### Variable Columns (not in all files)

"""
        for col, info in sorted(var_cols.items()):
            prompt += f"- **{col}**: Present in {info['present_in']}/{info['total_files']} files\n"

    # Validation recommendations
    prompt += """


## Validation Rule Recommendations

Based on multi-month stability analysis:

### High Confidence Rules
✅ **NotNullRule candidates**: Columns with 0% null across ALL files
"""

    # Find columns with 0% null in all files
    not_null_candidates = [
        col for col in stable_cols
        if data_patterns.get(col, {}).get("null_pct_range", (100, 100))[1] == 0
    ]

    if not_null_candidates:
        prompt += "\n```python\nNotNullRule(columns=[\n"
        for col in sorted(not_null_candidates):
            prompt += f'    "{col}",\n'
        prompt += "])\n```\n"
    else:
        prompt += "\n(No columns with 0% null in all files)\n"

    # Flag always-null columns
    always_null_cols = [
        col for col in stable_cols
        if data_patterns.get(col, {}).get("null_pct_range", (0, 0))[0] == 100
    ]

    if always_null_cols:
        prompt += """
### ❌ DO NOT use NotNullRule on these columns
The following columns are 100% null in ALL files (candidates for removal):

"""
        for col in sorted(always_null_cols):
            prompt += f"- **{col}**\n"

    # Data quality issues
    prompt += """


## Data Quality Issues Detected

"""

    # Find type inconsistencies
    type_issues = [
        (col, pattern) for col, pattern in data_patterns.items()
        if not pattern.get("type_consistent", True) and col in stable_cols
    ]

    if type_issues:
        for col, pattern in type_issues:
            types_str = ", ".join(pattern["types"])
            prompt += f"1. **Type inconsistency in {col}**: {types_str}\n"
            prompt += "   - Recommendation: Add type coercion in transform()\n\n"

    # Find null percentage changes
    null_variance = [
        (col, pattern) for col, pattern in data_patterns.items()
        if col in stable_cols and abs(pattern["null_pct_range"][1] - pattern["null_pct_range"][0]) > 30
    ]

    if null_variance:
        for col, pattern in null_variance:
            null_min, null_max = pattern["null_pct_range"]
            prompt += f"2. **Null percentage variance in {col}**: {null_min:.1f}% to {null_max:.1f}%\n"
            prompt += "   - Recommendation: Column population is inconsistent\n\n"

    if not type_issues and not null_variance:
        prompt += "No major data quality issues detected.\n"

    prompt += """


## Summary

**✅ Stable (safe to rely on):**
"""
    for col in sorted(stable_cols)[:5]:  # Show top 5
        prompt += f"\n- {col}"

    if len(stable_cols) > 5:
        prompt += f"\n- ... and {len(stable_cols) - 5} more stable columns"

    if var_cols:
        prompt += """

**⚠️ Variable (need flexible handling):**
"""
        for col in sorted(var_cols.keys())[:3]:  # Show top 3
            prompt += f"\n- {col}"

    if always_null_cols:
        prompt += """

**❌ Never Used (candidates for removal):**
"""
        for col in sorted(always_null_cols):
            prompt += f"\n- {col}"

    prompt += """

## Recommendation

Build processor with flexible validation:
- Use strict NotNullRule only for columns that are ALWAYS populated
- Allow for schema variations in variable columns
- Transform step to normalize format inconsistencies
- Warning (not error) for columns that vary in population
"""

    return prompt
