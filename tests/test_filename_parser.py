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
