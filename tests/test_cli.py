import pandas as pd
import pytest
from typer.testing import CliRunner
from sheetmask.cli import app

runner = CliRunner()


@pytest.fixture
def sample_excel(tmp_path):
    """Create a minimal Excel file for testing."""
    df = pd.DataFrame(
        {
            "Name": ["Alice Smith", "Bob Jones"],
            "Revenue": [1000.0, 2000.0],
            "Date": ["2024-01-01", "2024-01-02"],
        }
    )
    path = tmp_path / "sample.xlsx"
    df.to_excel(path, index=False)
    return path


@pytest.fixture
def sample_config(tmp_path):
    """Create a minimal config.py for testing."""
    config_content = """\
from sheetmask import PercentageVarianceRule

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
    result = runner.invoke(
        app,
        [
            "process",
            str(sample_excel),
            str(output),
            "--config",
            str(sample_config),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()

    df = pd.read_excel(output)
    assert list(df.columns) == ["Name", "Revenue", "Date"]
    # Names should be anonymized (different from originals)
    assert df["Name"].iloc[0] != "Alice Smith"


def test_process_auto_output_path(sample_excel, sample_config):
    result = runner.invoke(
        app,
        [
            "process",
            str(sample_excel),
            "--config",
            str(sample_config),
        ],
    )
    assert result.exit_code == 0, result.output
    expected_output = sample_excel.parent / "sample_SYNTHETIC.xlsx"
    assert expected_output.exists()


def test_process_missing_config(sample_excel, tmp_path):
    result = runner.invoke(
        app,
        [
            "process",
            str(sample_excel),
            "--config",
            str(tmp_path / "nonexistent.py"),
        ],
    )
    assert result.exit_code != 0


def test_process_config_missing_config_dict(sample_excel, tmp_path):
    """Config file exists but does not define a 'config' dict."""
    bad_config = tmp_path / "bad_config.py"
    bad_config.write_text("# no config dict here\n")
    result = runner.invoke(
        app,
        [
            "process",
            str(sample_excel),
            "--config",
            str(bad_config),
        ],
    )
    assert result.exit_code != 0
    assert "must define a 'config'" in result.output
    assert "dict" in result.output


def test_process_invalid_sheet_name_gives_clear_error(sample_excel, tmp_path):
    """Config with nonexistent sheet_to_keep should give a clear error, not crash."""
    bad_config = tmp_path / "bad_sheet_config.py"
    bad_config.write_text("""\
config = {
    "version": "1.0.0",
    "sheets_to_keep": ["NonExistentSheet"],
    "entity_columns": {},
    "numeric_rules": {},
    "preserve_columns": [],
}
""")
    output = tmp_path / "output.xlsx"
    result = runner.invoke(
        app,
        [
            "process",
            str(sample_excel),
            str(output),
            "--config",
            str(bad_config),
        ],
    )
    assert result.exit_code != 0
    assert "sheet" in result.output.lower()
    # Must name the missing sheet so the user knows what to fix
    assert "NonExistentSheet" in result.output
