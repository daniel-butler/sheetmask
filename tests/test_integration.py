"""
Integration tests using realistic Excel fixtures.

These tests run the full anonymization pipeline on complex,
multi-sheet Excel files to catch issues that unit tests miss.
"""

import pandas as pd
from pathlib import Path
from typer.testing import CliRunner
from sheetmask.cli import app
from sheetmask.executor import AnonymizationExecutor

runner = CliRunner()

FIXTURES = Path(__file__).parent / "fixtures"
REVENUE_REPORT = FIXTURES / "Dec-24 Revenue Report.xlsx"
TEAM_ROSTER = FIXTURES / "2024-Q4 Team Roster.xlsx"
REVENUE_CONFIG = FIXTURES / "revenue_report_config.py"
TEAM_CONFIG = FIXTURES / "team_roster_config.py"


# --- Revenue Report: multi-sheet, financial relationships ---


class TestRevenueReport:
    def test_all_three_sheets_processed(self, tmp_path):
        output = tmp_path / "output.xlsx"
        result = runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        assert result.exit_code == 0, result.output
        xls = pd.ExcelFile(output)
        assert set(xls.sheet_names) == {"Summary", "Details", "Team"}

    def test_client_names_anonymized(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        df = pd.read_excel(output, sheet_name="Summary")
        original_clients = {
            "Northgate Industries",
            "Apex Solutions LLC",
            "Riverfront Corp",
            "Pinnacle Group",
            "Coastal Dynamics",
            "Summit Partners",
            "Meridian Tech",
            "Harborview Systems",
            "Irongate Ventures",
            "Clearwater Group",
        }
        anonymized_clients = set(df["Client"].dropna())
        assert not original_clients.intersection(
            anonymized_clients
        ), "Some original client names were not anonymized"

    def test_person_names_anonymized(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        df = pd.read_excel(output, sheet_name="Summary")
        original_managers = {"Sarah Chen", "Marcus Webb", "Jordan Hayes"}
        anonymized_managers = set(df["Account Manager"].dropna())
        assert not original_managers.intersection(anonymized_managers)

    def test_gross_margin_equals_revenue_minus_cost(self, tmp_path):
        """GM = Revenue - Cost must hold after anonymization."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        df = pd.read_excel(output, sheet_name="Summary")
        # Exclude the totals row (empty Account Manager)
        data = df[df["Account Manager"].notna()].copy()
        expected_gm = (data["Revenue"] - data["Cost"]).round(2)
        pd.testing.assert_series_equal(
            data["Gross Margin"].round(2),
            expected_gm,
            check_names=False,
        )

    def test_gm_percent_derived_from_anonymized_values(self, tmp_path):
        """GM% = (GM / Revenue) * 100 must hold after anonymization."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        df = pd.read_excel(output, sheet_name="Summary")
        data = df[df["Account Manager"].notna()].copy()
        expected_pct = (data["Gross Margin"] / data["Revenue"] * 100).round(2)
        pd.testing.assert_series_equal(
            data["GM%"].round(2),
            expected_pct,
            check_names=False,
        )

    def test_entity_consistent_across_sheets(self, tmp_path):
        """Same person in Summary and Team sheets should map to the same fake name."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        summary_df = pd.read_excel(output, sheet_name="Summary")
        team_df = pd.read_excel(output, sheet_name="Team")

        summary_managers = set(summary_df["Account Manager"].dropna())
        team_names = set(team_df["Name"].dropna())

        # Every manager in Summary must appear in Team (same entity -> same fake name)
        assert summary_managers.issubset(team_names), (
            f"Manager names in Summary not found in Team: "
            f"{summary_managers - team_names}"
        )

    def test_null_descriptions_preserved(self, tmp_path):
        """Null values in Description column should remain null."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(REVENUE_REPORT, sheet_name="Details")
        output_df = pd.read_excel(output, sheet_name="Details")

        original_nulls = original_df["Description"].isna()
        output_nulls = output_df["Description"].isna()
        pd.testing.assert_series_equal(original_nulls, output_nulls, check_names=False)

    def test_dates_preserved(self, tmp_path):
        """Start Date and End Date columns must not be modified."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(REVENUE_REPORT, sheet_name="Details")
        output_df = pd.read_excel(output, sheet_name="Details")
        pd.testing.assert_series_equal(
            original_df["Start Date"], output_df["Start Date"], check_names=False
        )

    def test_output_is_reproducible(self, tmp_path):
        """Two runs with same seed must produce identical output."""
        out1 = tmp_path / "out1.xlsx"
        out2 = tmp_path / "out2.xlsx"
        for out in [out1, out2]:
            runner.invoke(
                app,
                [
                    "process",
                    str(REVENUE_REPORT),
                    str(out),
                    "--config",
                    str(REVENUE_CONFIG),
                    "--seed",
                    "99",
                ],
            )
        df1 = pd.read_excel(out1, sheet_name="Summary")
        df2 = pd.read_excel(out2, sheet_name="Summary")
        pd.testing.assert_frame_equal(df1, df2)

    def test_revenue_values_changed(self, tmp_path):
        """Revenue values must differ from originals after anonymization."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(REVENUE_REPORT, sheet_name="Summary")
        output_df = pd.read_excel(output, sheet_name="Summary")
        data_rows = original_df[original_df["Account Manager"].notna()]
        out_rows = output_df[output_df["Account Manager"].notna()]
        assert not data_rows["Revenue"].equals(out_rows["Revenue"])

    def test_emails_anonymized_in_team_sheet(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(REVENUE_REPORT),
                str(output),
                "--config",
                str(REVENUE_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(REVENUE_REPORT, sheet_name="Team")
        output_df = pd.read_excel(output, sheet_name="Team")
        original_emails = set(original_df["Email"])
        output_emails = set(output_df["Email"])
        assert not original_emails.intersection(output_emails)


# --- Team Roster: single-sheet, multiple entity types, nulls ---


class TestTeamRoster:
    def test_single_sheet_processed(self, tmp_path):
        output = tmp_path / "output.xlsx"
        result = runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        assert result.exit_code == 0, result.output
        xls = pd.ExcelFile(output)
        assert xls.sheet_names == ["Roster"]

    def test_first_and_last_names_anonymized_separately(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(TEAM_ROSTER, sheet_name="Roster")
        output_df = pd.read_excel(output, sheet_name="Roster")

        # The output columns must not be identical to the originals row-by-row.
        # (Common first/last names can collide between Faker output and the fixture,
        # so we only assert that the column as a whole has changed, not that every
        # individual name is absent from the original pool.)
        assert not original_df["First Name"].equals(
            output_df["First Name"]
        ), "First Name column was not changed by anonymization"
        assert not original_df["Last Name"].equals(
            output_df["Last Name"]
        ), "Last Name column was not changed by anonymization"

    def test_null_phones_remain_null(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(TEAM_ROSTER, sheet_name="Roster")
        output_df = pd.read_excel(output, sheet_name="Roster")
        original_nulls = original_df["Phone"].isna()
        output_nulls = output_df["Phone"].isna()
        pd.testing.assert_series_equal(original_nulls, output_nulls, check_names=False)

    def test_annual_bonus_derived_from_anonymized_salary(self, tmp_path):
        """Annual Bonus = Base Salary * Bonus % / 100 after anonymization."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        df = pd.read_excel(output, sheet_name="Roster")
        expected = (df["Base Salary"] * df["Bonus %"] / 100).round(0)
        pd.testing.assert_series_equal(
            df["Annual Bonus"].round(0), expected, check_names=False, check_dtype=False
        )

    def test_employee_ids_preserved(self, tmp_path):
        """Employee ID is a preserve_column -- must not change."""
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(TEAM_ROSTER, sheet_name="Roster")
        output_df = pd.read_excel(output, sheet_name="Roster")
        pd.testing.assert_series_equal(
            original_df["Employee ID"], output_df["Employee ID"]
        )

    def test_departments_preserved(self, tmp_path):
        original_df = pd.read_excel(TEAM_ROSTER, sheet_name="Roster")
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        output_df = pd.read_excel(output, sheet_name="Roster")
        pd.testing.assert_series_equal(
            original_df["Department"], output_df["Department"]
        )

    def test_salaries_changed_but_in_range(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(TEAM_ROSTER, sheet_name="Roster")
        output_df = pd.read_excel(output, sheet_name="Roster")
        # Values changed
        assert not original_df["Base Salary"].equals(output_df["Base Salary"])
        # But within 15% variance bounds
        assert all(output_df["Base Salary"] >= original_df["Base Salary"] * 0.85)
        assert all(output_df["Base Salary"] <= original_df["Base Salary"] * 1.15)

    def test_hire_dates_preserved(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(TEAM_ROSTER, sheet_name="Roster")
        output_df = pd.read_excel(output, sheet_name="Roster")
        pd.testing.assert_series_equal(original_df["Hire Date"], output_df["Hire Date"])

    def test_locations_anonymized(self, tmp_path):
        output = tmp_path / "output.xlsx"
        runner.invoke(
            app,
            [
                "process",
                str(TEAM_ROSTER),
                str(output),
                "--config",
                str(TEAM_CONFIG),
                "--seed",
                "42",
            ],
        )
        original_df = pd.read_excel(TEAM_ROSTER, sheet_name="Roster")
        output_df = pd.read_excel(output, sheet_name="Roster")
        original_locs = set(original_df["Location"])
        output_locs = set(output_df["Location"])
        assert not original_locs.intersection(output_locs)


# --- Multi-analyzer tests ---


class TestMultiAnalyzer:
    def test_analyze_two_files_returns_prompt(self):
        from sheetmask.multi_analyzer import analyze_multiple_files

        result = analyze_multiple_files([REVENUE_REPORT, TEAM_ROSTER])
        assert isinstance(result, str)
        assert "Multi-Month Excel Analysis" in result
        assert "Schema Stability Report" in result

    def test_stable_columns_detected(self):
        from sheetmask.multi_analyzer import compare_schemas

        # Revenue report has consistent sheets; use same file twice to guarantee stable columns
        result = compare_schemas([REVENUE_REPORT, REVENUE_REPORT])
        assert len(result["stable_columns"]) > 0
        assert result["total_files"] == 2

    def test_data_patterns_computed(self):
        from sheetmask.multi_analyzer import compare_data_patterns

        result = compare_data_patterns([REVENUE_REPORT, REVENUE_REPORT])
        assert len(result) > 0
        for col, stats in result.items():
            assert "null_pct_range" in stats
            assert "type_consistent" in stats

    def test_cli_analyze_multi_runs(self):
        result = runner.invoke(
            app,
            [
                "analyze-multi",
                str(REVENUE_REPORT),
                str(TEAM_ROSTER),
            ],
        )
        assert result.exit_code == 0
        assert "Multi-Month" in result.output


# --- Additional date format tests ---


class TestDateFormats:
    """Cover all date formats supported by filename_parser."""

    def test_quarter_with_year_prefix(self):
        from sheetmask.filename_parser import parse_date_from_filename
        from datetime import date

        result = parse_date_from_filename("2024-Q3 Report.xlsx")
        assert result.date == date(2024, 7, 1)
        assert result.confidence == "High"

    def test_quarter_only(self):
        from sheetmask.filename_parser import parse_date_from_filename
        from datetime import date

        result = parse_date_from_filename("Q4-2024 Summary.xlsx")
        assert result.date == date(2024, 10, 1)

    def test_yyyymmdd(self):
        from sheetmask.filename_parser import parse_date_from_filename
        from datetime import date

        result = parse_date_from_filename("report_20241201.xlsx")
        assert result.date == date(2024, 12, 1)
        assert result.confidence == "High"

    def test_year_only(self):
        from sheetmask.filename_parser import parse_date_from_filename
        from datetime import date

        result = parse_date_from_filename("Annual Report 2024.xlsx")
        assert result.date == date(2024, 1, 1)
        assert result.confidence == "Low"

    def test_fixture_filenames_parsed_correctly(self):
        from sheetmask.filename_parser import parse_date_from_filename
        from datetime import date

        r1 = parse_date_from_filename("Dec-24 Revenue Report.xlsx")
        assert r1.date == date(2024, 12, 1)

        r2 = parse_date_from_filename("2024-Q4 Team Roster.xlsx")
        assert r2.date == date(2024, 10, 1)


# --- Executor unit tests ---


class TestExecutor:
    def test_anonymize_file_returns_stats(self, tmp_path):
        import importlib.util

        spec = importlib.util.spec_from_file_location("cfg", TEAM_CONFIG)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        executor = AnonymizationExecutor(mod.config, seed=42)
        output = tmp_path / "out.xlsx"
        stats = executor.anonymize_file(TEAM_ROSTER, output, auto_suffix=False)

        assert stats["sheets_processed"] == 1
        assert stats["total_rows"] == 15
        assert stats["entity_mappings"]["total_mappings"] > 0

    def test_export_mapping_report(self, tmp_path):
        import json
        import importlib.util

        spec = importlib.util.spec_from_file_location("cfg", TEAM_CONFIG)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        executor = AnonymizationExecutor(mod.config, seed=42)
        output = tmp_path / "out.xlsx"
        executor.anonymize_file(TEAM_ROSTER, output, auto_suffix=False)

        mapping_file = tmp_path / "mappings.json"
        executor.export_mapping_report(mapping_file)

        assert mapping_file.exists()
        data = json.loads(mapping_file.read_text())
        assert "entity_types" in data
        assert "total_mappings" in data
        assert data["total_mappings"] > 0
