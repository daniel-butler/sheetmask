# excel-anonymizer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract the FDP anonymization CLI into a standalone Python package that anyone can install and use to create PII-safe Excel test fixtures.

**Architecture:** New package `excel-anonymizer` in `/Users/danielbutler/code/excel-anon`. Copies six modules from FDP's `src/fdp/tools/anonymization/`, fixes their internal imports, and provides a new CLI (`excel-anon`) that replaces `--processor MyProcessor` with `--config config.py`. FDP keeps its own copy — no cross-dependency.

**Tech Stack:** Python 3.13+, pandas, openpyxl, pyxlsb, typer, rich, faker, pytest, uv

**Source to copy from:** `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/`

---

## Workflow the tool enables

```
1. excel-anon analyze input.xlsx          → generates LLM prompt
2. paste into Claude/ChatGPT              → LLM returns config dict
3. save dict to config.py
4. excel-anon process input.xlsx \
       --config config.py                 → anonymized output file
```

---

## Task 1: Initialize repo and package scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/excel_anonymizer/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Step 1: Initialize git repo**

```bash
cd /Users/danielbutler/code/excel-anon
git init
```

Expected: `Initialized empty Git repository in /Users/danielbutler/code/excel-anon/.git/`

**Step 2: Create `pyproject.toml`**

```toml
[project]
name = "excel-anonymizer"
version = "0.1.0"
description = "CLI for creating PII-safe Excel test fixtures"
requires-python = ">=3.13"
dependencies = [
    "pandas>=2.0.0",
    "openpyxl>=3.1.0",
    "pyxlsb>=1.0.10",
    "typer>=0.15.0",
    "rich>=13.0.0",
    "faker>=20.0.0",
]

[project.scripts]
excel-anon = "excel_anonymizer.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = ["-v", "--tb=short"]
```

**Step 3: Create directory structure**

```bash
mkdir -p src/excel_anonymizer tests
```

**Step 4: Create `src/excel_anonymizer/__init__.py`**

Exports the two rule classes so user configs can do `from excel_anonymizer import PercentageVarianceRule`:

```python
from excel_anonymizer.rules import PercentageVarianceRule, PreserveRelationshipRule

__all__ = ["PercentageVarianceRule", "PreserveRelationshipRule"]
```

**Step 5: Create `tests/__init__.py`**

Empty file:
```python
```

**Step 6: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/
.pytest_cache/
```

**Step 7: Install dependencies**

```bash
cd /Users/danielbutler/code/excel-anon
uv sync
```

Expected: lock file created, dependencies installed.

**Step 8: Commit**

```bash
git add .
git commit -m "feat: initialize excel-anonymizer package scaffold"
```

---

## Task 2: Copy and adapt the six core modules

These six files are copied from FDP's `src/fdp/tools/anonymization/` with minimal changes (import paths only).

**Files:**
- Create: `src/excel_anonymizer/rules.py`
- Create: `src/excel_anonymizer/entity_mapper.py`
- Create: `src/excel_anonymizer/filename_parser.py`
- Create: `src/excel_anonymizer/executor.py`
- Create: `src/excel_anonymizer/analyzer.py`
- Create: `src/excel_anonymizer/multi_analyzer.py`
- Create: `tests/test_rules.py`
- Create: `tests/test_entity_mapper.py`
- Create: `tests/test_filename_parser.py`

### `rules.py` — copy verbatim

No import changes needed. Copy the full content of `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/rules.py` as-is.

The file defines `NumericAnonymizationRule`, `PercentageVarianceRule`, `PreserveRelationshipRule`. No internal imports.

### `entity_mapper.py` — copy verbatim

No import changes needed. Copy the full content of `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/entity_mapper.py` as-is.

### `filename_parser.py` — copy verbatim

No import changes needed. Copy the full content of `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/filename_parser.py` as-is.

### `multi_analyzer.py` — one import change

Copy the full content of `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/multi_analyzer.py` but change line 13:

```python
# BEFORE (FDP relative import — works in both, but be explicit)
from .filename_parser import parse_date_from_filename

# AFTER (same relative import — no change needed)
from .filename_parser import parse_date_from_filename
```

No change required — relative import already works. Copy verbatim.

### `executor.py` — two import changes

Copy the full content of `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/executor.py` but change:

```python
# BEFORE
from fdp.tools.anonymization.entity_mapper import EntityMapper
from fdp.tools.anonymization.rules import NumericAnonymizationRule
```

```python
# AFTER
from excel_anonymizer.entity_mapper import EntityMapper
from excel_anonymizer.rules import NumericAnonymizationRule
```

Also inside `_apply_numeric_rules`, change the local import:

```python
# BEFORE
from fdp.tools.anonymization.rules import PercentageVarianceRule, PreserveRelationshipRule

# AFTER
from excel_anonymizer.rules import PercentageVarianceRule, PreserveRelationshipRule
```

### `analyzer.py` — two changes

Copy the full content of `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/analyzer.py` but:

**Change 1:** Fix the import on line 12:
```python
# BEFORE
from fdp.tools.anonymization.filename_parser import parse_date_from_filename

# AFTER
from excel_anonymizer.filename_parser import parse_date_from_filename
```

**Change 2:** Remove the `--processor` context section from `analyze_excel_for_anonymization`. The `processor` parameter stays (it's optional and defaults to None) but remove the call to `_get_processor_context` and the related `## Processor Context` section from the prompt template. Replace the `{processor_context}` placeholder with an empty string or remove it.

Specifically, in the prompt string near the bottom of `analyze_excel_for_anonymization`, remove:
```python
{processor_context}
```
And remove the entire `_get_processor_context` and `_describe_rule` functions at the bottom of the file (lines 229–293 in FDP), since they reference FDP processor attributes (`processor.processor_name`, `processor.schema_definition`, `processor.validation_rules`).

Also update the **Output Format** section of the prompt to show the standalone `config.py` format instead of the FDP processor format. Replace the output format block with:

```python
prompt += """
## Output Format

Save the recommended config as a Python file (e.g., `my_config.py`):

```python
from excel_anonymizer import PercentageVarianceRule, PreserveRelationshipRule

config = {
    "version": "1.0.0",

    # Only keep sheets with data to process
    "sheets_to_keep": """ + sheets_example + """,

    # Entity columns that need fake names/companies
    "entity_columns": {
        # Column name -> Entity type
        # "Project Manager": "PERSON",
        # "Client Name": "ORGANIZATION",
    },

    # Numeric columns that need anonymization
    "numeric_rules": {
        # Base values - add random variance
        # "Month Revenue Actuals": PercentageVarianceRule(variance_pct=0.3),

        # Derived values - recompute from anonymized sources
        # "Month GM Actuals": PreserveRelationshipRule(
        #     formula="context['Month Revenue Actuals'] - context['Month Exp Actuals']",
        #     dependent_columns=["Month Revenue Actuals", "Month Exp Actuals"]
        # ),
    },

    # Columns to preserve as-is (not sensitive)
    "preserve_columns": [
        # "Period End Date",
        # "Project Type",
    ],
}
```

Then run:
```bash
excel-anon process your_file.xlsx --config my_config.py
```
"""
```

**Step 1: Write test for rules**

Create `tests/test_rules.py`:

```python
import pandas as pd
import pytest
from excel_anonymizer.rules import PercentageVarianceRule, PreserveRelationshipRule


def test_percentage_variance_changes_values():
    rule = PercentageVarianceRule(variance_pct=0.3)
    series = pd.Series([100.0, 200.0, 300.0])
    result = rule.apply(series, {})
    assert len(result) == 3
    assert not result.equals(series)


def test_percentage_variance_preserves_zero():
    rule = PercentageVarianceRule(variance_pct=0.3)
    series = pd.Series([0.0, 100.0])
    result = rule.apply(series, {})
    assert result.iloc[0] == 0.0


def test_percentage_variance_preserves_nulls():
    rule = PercentageVarianceRule(variance_pct=0.3)
    series = pd.Series([100.0, None, 300.0])
    result = rule.apply(series, {})
    assert pd.isna(result.iloc[1])


def test_percentage_variance_stays_within_range():
    rule = PercentageVarianceRule(variance_pct=0.1)
    series = pd.Series([1000.0] * 100)
    result = rule.apply(series, {})
    assert all(result >= 900.0)
    assert all(result <= 1100.0)


def test_preserve_relationship_recomputes_from_context():
    rule = PreserveRelationshipRule(
        formula="context['Revenue'] - context['Cost']",
        dependent_columns=["Revenue", "Cost"],
    )
    context = {
        "Revenue": pd.Series([100.0, 200.0]),
        "Cost": pd.Series([30.0, 50.0]),
    }
    result = rule.apply(pd.Series([70.0, 150.0]), context)
    assert result.iloc[0] == pytest.approx(70.0)
    assert result.iloc[1] == pytest.approx(150.0)


def test_preserve_relationship_raises_on_missing_column():
    rule = PreserveRelationshipRule(
        formula="context['Revenue'] - context['Cost']",
        dependent_columns=["Revenue", "Cost"],
    )
    with pytest.raises(ValueError, match="Missing dependent columns"):
        rule.apply(pd.Series([1.0]), {"Revenue": pd.Series([100.0])})
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/danielbutler/code/excel-anon
uv run pytest tests/test_rules.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'excel_anonymizer'`

**Step 3: Create `src/excel_anonymizer/rules.py`**

Copy verbatim from `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/rules.py`.

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_rules.py -v
```

Expected: 6 PASSED.

**Step 5: Write test for entity_mapper**

Create `tests/test_entity_mapper.py`:

```python
from excel_anonymizer.entity_mapper import EntityMapper


def test_same_entity_maps_to_same_fake():
    mapper = EntityMapper(seed=42)
    fake1 = mapper.get_or_create("PERSON", "John Smith")
    fake2 = mapper.get_or_create("PERSON", "John Smith")
    assert fake1 == fake2


def test_different_entities_map_differently():
    mapper = EntityMapper(seed=42)
    fake1 = mapper.get_or_create("PERSON", "John Smith")
    fake2 = mapper.get_or_create("PERSON", "Jane Doe")
    assert fake1 != fake2


def test_seed_produces_reproducible_output():
    mapper1 = EntityMapper(seed=42)
    mapper2 = EntityMapper(seed=42)
    fake1 = mapper1.get_or_create("ORGANIZATION", "Acme Corp")
    fake2 = mapper2.get_or_create("ORGANIZATION", "Acme Corp")
    assert fake1 == fake2


def test_all_entity_types_generate_without_error():
    mapper = EntityMapper(seed=42)
    types = [
        "PERSON", "PERSON_FIRST_NAME", "PERSON_LAST_NAME",
        "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER",
        "PROJECT_NAME", "PROJECT_DESCRIPTION", "LOCATION",
    ]
    for t in types:
        result = mapper.get_or_create(t, "test_value")
        assert isinstance(result, str)
        assert len(result) > 0


def test_to_dict_counts_mappings():
    mapper = EntityMapper(seed=42)
    mapper.get_or_create("PERSON", "Alice")
    mapper.get_or_create("PERSON", "Bob")
    mapper.get_or_create("ORGANIZATION", "Acme")
    report = mapper.to_dict()
    assert report["total_mappings"] == 3
```

**Step 6: Create `src/excel_anonymizer/entity_mapper.py`**

Copy verbatim from `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/entity_mapper.py`.

**Step 7: Write test for filename_parser**

Create `tests/test_filename_parser.py`:

```python
from datetime import date
from excel_anonymizer.filename_parser import parse_date_from_filename


def test_parses_month_dash_year_short():
    result = parse_date_from_filename("Dec-24 Report.xlsx")
    assert result.date == date(2024, 12, 1)
    assert result.confidence == "High"


def test_parses_full_month_name():
    result = parse_date_from_filename("December 2024 Summary.xlsx")
    assert result.date == date(2024, 12, 1)
    assert result.confidence == "High"


def test_parses_yyyy_mm():
    result = parse_date_from_filename("report_2024-03.xlsx")
    assert result.date == date(2024, 3, 1)


def test_no_date_returns_none():
    result = parse_date_from_filename("my_report.xlsx")
    assert result.date is None
    assert result.confidence == "None"
```

**Step 8: Create remaining source files**

Create `src/excel_anonymizer/filename_parser.py` — copy verbatim.
Create `src/excel_anonymizer/multi_analyzer.py` — copy verbatim (relative imports already correct).

**Step 9: Create `src/excel_anonymizer/executor.py`**

Copy from FDP but change three imports:

```python
# Lines to change at top of file:
from excel_anonymizer.entity_mapper import EntityMapper
from excel_anonymizer.rules import NumericAnonymizationRule

# Line to change inside _apply_numeric_rules method:
from excel_anonymizer.rules import PercentageVarianceRule, PreserveRelationshipRule
```

All other content is identical to `/Users/danielbutler/code/financial-data-pipeline/src/fdp/tools/anonymization/executor.py`.

**Step 10: Create `src/excel_anonymizer/analyzer.py`**

Copy from FDP with two changes:

1. Line 12 — change import:
   ```python
   # BEFORE
   from fdp.tools.anonymization.filename_parser import parse_date_from_filename
   # AFTER
   from excel_anonymizer.filename_parser import parse_date_from_filename
   ```

2. Remove `processor` parameter handling and the `_get_processor_context`/`_describe_rule` functions. The `processor` parameter in `analyze_excel_for_anonymization` should remain but be ignored (or remove it). Remove the `{processor_context}` interpolation from the prompt and the call to `_get_processor_context`.

3. Update the Output Format section to show the standalone `config.py` pattern (see description in the introduction to Task 2 above).

**Step 11: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass.

**Step 12: Commit**

```bash
git add src/ tests/
git commit -m "feat: add core anonymization modules"
```

---

## Task 3: Build the CLI

**Files:**
- Create: `src/excel_anonymizer/cli.py`
- Create: `tests/test_cli.py`

The CLI provides three commands: `analyze`, `analyze-multi`, `process`.

Key difference from FDP's `src/fdp/cli/anonymize.py`:
- `process` uses `--config config.py` instead of `--processor MyProcessor`
- Config is loaded dynamically with `importlib.util`
- Output path: no auto-placement in `tests/fixtures/` — either use the provided `output` arg or default to `{input_stem}_SYNTHETIC.xlsx` in the same directory

**Step 1: Write failing test**

Create `tests/test_cli.py`:

```python
import json
from pathlib import Path
import pandas as pd
import pytest
from typer.testing import CliRunner
from excel_anonymizer.cli import app


runner = CliRunner()


@pytest.fixture
def sample_excel(tmp_path):
    """Create a minimal Excel file for testing."""
    df = pd.DataFrame({
        "Name": ["Alice Smith", "Bob Jones"],
        "Revenue": [1000.0, 2000.0],
        "Date": ["2024-01-01", "2024-01-02"],
    })
    path = tmp_path / "sample.xlsx"
    df.to_excel(path, index=False)
    return path


@pytest.fixture
def sample_config(tmp_path):
    """Create a minimal config.py for testing."""
    config_content = """
from excel_anonymizer import PercentageVarianceRule

config = {
    "version": "1.0.0",
    "sheets_to_keep": None,
    "entity_columns": {"Name": "PERSON"},
    "numeric_rules": {
        "Revenue": PercentageVarianceRule(variance_pct=0.1),
    },
    "preserve_columns": ["Date"],
}
"""
    path = tmp_path / "config.py"
    path.write_text(config_content)
    return path


def test_analyze_command_runs(sample_excel):
    result = runner.invoke(app, ["analyze", str(sample_excel)])
    assert result.exit_code == 0
    assert "Excel Column Analysis" in result.output


def test_analyze_saves_to_file(sample_excel, tmp_path):
    output = tmp_path / "prompt.txt"
    result = runner.invoke(app, ["analyze", str(sample_excel), "--output", str(output)])
    assert result.exit_code == 0
    assert output.exists()
    assert "Excel Column Analysis" in output.read_text()


def test_process_command_anonymizes(sample_excel, sample_config, tmp_path):
    output = tmp_path / "output.xlsx"
    result = runner.invoke(app, [
        "process", str(sample_excel),
        str(output),
        "--config", str(sample_config),
    ])
    assert result.exit_code == 0, result.output
    assert output.exists()

    df = pd.read_excel(output)
    assert list(df.columns) == ["Name", "Revenue", "Date"]
    # Names should be anonymized (different from originals)
    assert df["Name"].iloc[0] != "Alice Smith"


def test_process_auto_output_path(sample_excel, sample_config):
    result = runner.invoke(app, [
        "process", str(sample_excel),
        "--config", str(sample_config),
    ])
    assert result.exit_code == 0, result.output
    expected_output = sample_excel.parent / "sample_SYNTHETIC.xlsx"
    assert expected_output.exists()


def test_process_missing_config(sample_excel, tmp_path):
    result = runner.invoke(app, [
        "process", str(sample_excel),
        "--config", str(tmp_path / "nonexistent.py"),
    ])
    assert result.exit_code != 0
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'excel_anonymizer.cli'`

**Step 3: Create `src/excel_anonymizer/cli.py`**

```python
"""
CLI for excel-anonymizer.

Commands:
    analyze       - Analyze an Excel file, generate LLM prompt
    analyze-multi - Analyze multiple Excel files for schema patterns
    process       - Anonymize an Excel file using a config file
"""
import importlib.util
import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer(
    name="excel-anon",
    help="Create PII-safe Excel test fixtures",
    no_args_is_help=True,
)

console = Console()


@app.command()
def analyze(
    input_file: Path = typer.Argument(
        ...,
        help="Excel file to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    sheet: str = typer.Option(
        None,
        "--sheet",
        "-s",
        help="Sheet name to analyze (default: all sheets)",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Save prompt to file (default: print to console)",
    ),
):
    """
    Generate LLM prompt for analyzing Excel columns.

    Analyzes column names, types, and sample values. Paste the output into
    Claude or ChatGPT to get anonymization config recommendations.

    Workflow:
        1. excel-anon analyze input.xlsx
        2. Copy the prompt into Claude or ChatGPT
        3. Save the recommended config dict to config.py
        4. excel-anon process input.xlsx --config config.py
    """
    from excel_anonymizer.analyzer import analyze_excel_for_anonymization

    try:
        console.print("[cyan]Analyzing Excel file...[/cyan]\n")
        prompt = analyze_excel_for_anonymization(input_file, sheet_name=sheet)

        if output:
            output.write_text(prompt)
            console.print(f"[green]Prompt saved to:[/green] {output}")
            console.print("\n[bold]Next steps:[/bold]")
            console.print(f"1. Open {output}")
            console.print("2. Copy the entire prompt")
            console.print("3. Paste into Claude or ChatGPT")
            console.print("4. Save the config dict to config.py")
            console.print("5. Run: excel-anon process input.xlsx --config config.py\n")
        else:
            console.print(prompt)
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("1. Copy the prompt above into Claude or ChatGPT")
            console.print("2. Save the config dict to config.py")
            console.print("3. Run: excel-anon process input.xlsx --config config.py\n")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="analyze-multi")
def analyze_multi(
    input_files: list[Path] = typer.Argument(
        ...,
        help="Excel files to analyze (space-separated)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Save prompt to file (default: print to console)",
    ),
):
    """
    Analyze multiple Excel files to detect schema patterns.

    Useful for building processors that handle real-world data variance
    across multiple months or versions of the same report.
    """
    from excel_anonymizer.multi_analyzer import analyze_multiple_files

    try:
        if len(input_files) < 2:
            console.print("[yellow]Warning: Only 1 file provided. Works best with 2+ files.[/yellow]\n")

        console.print(f"[cyan]Analyzing {len(input_files)} files...[/cyan]\n")
        prompt = analyze_multiple_files(input_files)

        if output:
            output.write_text(prompt)
            console.print(f"[green]Analysis saved to:[/green] {output}")
        else:
            console.print(prompt)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def process(
    input_file: Path = typer.Argument(
        ...,
        help="Excel file to anonymize",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output_file: Path = typer.Argument(
        None,
        help="Output path (default: {input_stem}_SYNTHETIC.xlsx in same directory)",
    ),
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Python config file containing a 'config' dict",
        exists=True,
        file_okay=True,
        readable=True,
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        "-s",
        help="Random seed for reproducible anonymization",
    ),
    export_mapping: Path = typer.Option(
        None,
        "--export-mapping",
        "-m",
        help="Export entity mapping report to JSON",
    ),
):
    """
    Anonymize an Excel file using a config file.

    The config file must be a Python file containing a 'config' dict.
    Get a config by running 'excel-anon analyze' first, then pasting
    the prompt into Claude or ChatGPT.

    Examples:
        excel-anon process input.xlsx --config my_config.py
        excel-anon process input.xlsx output.xlsx --config my_config.py
        excel-anon process input.xlsx --config config.py --seed 123
    """
    from excel_anonymizer.executor import AnonymizationExecutor

    try:
        # Load config from Python file
        anon_config = _load_config(config)

        # Resolve output path
        output_path = _resolve_output_path(input_file, output_file)
        console.print(f"[cyan]Output:[/cyan] {output_path}")
        console.print(f"[cyan]Config:[/cyan] {config}")
        console.print(f"[cyan]Seed:[/cyan] {seed}\n")

        # Run anonymization
        executor = AnonymizationExecutor(anon_config, seed=seed)
        stats = executor.anonymize_file(input_file, output_path, auto_suffix=False)

        if export_mapping:
            executor.export_mapping_report(export_mapping)

        console.print("\n[bold green]Anonymization complete![/bold green]")
        console.print(f"  Input:    {input_file}")
        console.print(f"  Output:   {output_path}")
        console.print(f"  Sheets:   {stats['sheets_processed']}")
        console.print(f"  Rows:     {stats['total_rows']}")
        console.print(f"  Entities: {stats['entity_mappings']['total_mappings']}")

        if export_mapping:
            console.print(f"  Mapping:  {export_mapping}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


def _load_config(config_path: Path) -> dict:
    """Load anonymization config from a Python file."""
    spec = importlib.util.spec_from_file_location("_anon_config", config_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load config file: {config_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "config"):
        raise ValueError(
            f"{config_path} must define a 'config' dict. "
            "Run 'excel-anon analyze' to generate a starter config."
        )
    return module.config


def _resolve_output_path(input_file: Path, output_file: Path | None) -> Path:
    """Resolve output path. Defaults to {stem}_SYNTHETIC.xlsx in the same directory."""
    if output_file is not None:
        return output_file
    return input_file.parent / f"{input_file.stem}_SYNTHETIC.xlsx"
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: All 5 tests PASS.

**Step 5: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests pass.

**Step 6: Smoke test the installed CLI**

```bash
uv run excel-anon --help
```

Expected: help text showing `analyze`, `analyze-multi`, `process` commands.

**Step 7: Commit**

```bash
git add src/excel_anonymizer/cli.py tests/test_cli.py
git commit -m "feat: add CLI with analyze and process commands"
```

---

## Task 4: README

**Files:**
- Create: `README.md`

**Step 1: Create `README.md`**

```markdown
# excel-anonymizer

CLI for creating PII-safe Excel test fixtures.

Analyzes Excel files and anonymizes sensitive data (names, organizations, financials)
while preserving structure and statistical properties.

## Install

```bash
pip install git+https://github.com/your-org/excel-anonymizer.git
```

Or with uv:
```bash
uv add git+https://github.com/your-org/excel-anonymizer.git
```

## Workflow

### Step 1: Analyze your file

```bash
excel-anon analyze "My Report.xlsx"
```

This prints a prompt. Copy it into Claude or ChatGPT.

### Step 2: Save the config

The LLM returns a config dict. Save it to a Python file:

```python
# my_config.py
from excel_anonymizer import PercentageVarianceRule, PreserveRelationshipRule

config = {
    "version": "1.0.0",
    "sheets_to_keep": ["Sheet1"],
    "entity_columns": {
        "Manager": "PERSON",
        "Client": "ORGANIZATION",
    },
    "numeric_rules": {
        "Revenue": PercentageVarianceRule(variance_pct=0.3),
        "Margin": PreserveRelationshipRule(
            formula="context['Revenue'] - context['Cost']",
            dependent_columns=["Revenue", "Cost"],
        ),
    },
    "preserve_columns": ["Date", "Project Type"],
}
```

### Step 3: Anonymize

```bash
excel-anon process "My Report.xlsx" --config my_config.py
# Output: My Report_SYNTHETIC.xlsx
```

## Entity Types

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

## Commands

```
excel-anon analyze <file>             Analyze file, print LLM prompt
excel-anon analyze <file> -o out.txt  Save prompt to file
excel-anon analyze-multi f1 f2 f3     Analyze multiple files for schema patterns
excel-anon process <file> --config c  Anonymize file using config
excel-anon process <file> out.xlsx --config c --seed 123
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install and workflow instructions"
```

---

## Done

Verify the full suite passes and the CLI works end-to-end:

```bash
uv run pytest -v
uv run excel-anon --help
uv run excel-anon analyze --help
uv run excel-anon process --help
```
