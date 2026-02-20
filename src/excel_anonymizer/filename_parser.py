"""
Filename date parser for extracting dates from Excel filenames.

Supports various formats:
- Month-YY (Dec-24, Nov-24)
- Full month name (December 2024)
- YYYY-MM (2024-12)
- Quarter (Q1, Q2, Q3, Q4, 2024-Q3)
- YYYYMMDD (20241201)
- Year only (2024)

All dates default to **first of month** to avoid leap year issues.
Quarters default to first day of the quarter's last month (Q3 = Jul 1).
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class DateParseResult:
    """Result of parsing a date from a filename."""

    date: Optional[date]
    confidence: str  # "High", "Medium", "Low", "None"
    pattern: str     # Description of pattern matched
    original_text: Optional[str] = None  # The text that was matched


def parse_date_from_filename(filename: str) -> DateParseResult:
    """
    Parse date from filename using pattern matching.

    Args:
        filename: Filename to parse

    Returns:
        DateParseResult with parsed date, confidence, and pattern info

    Examples:
        >>> parse_date_from_filename("Dec-24 Report.xlsx")
        DateParseResult(date=date(2024, 12, 1), confidence="High", ...)

        >>> parse_date_from_filename("2024-Q3-Final.xlsx")
        DateParseResult(date=date(2024, 7, 1), confidence="High", ...)
    """
    # Try patterns in order of confidence (high to low)

    # Pattern 1: Month-YY (Dec-24, Nov-24) - HIGH CONFIDENCE
    result = _try_month_dash_year_short(filename)
    if result:
        return result

    # Pattern 2: YYYY-MM or MM-YYYY - HIGH CONFIDENCE
    result = _try_year_month_dash(filename)
    if result:
        return result

    # Pattern 3: Full month name (December 2024) - HIGH CONFIDENCE
    result = _try_full_month_name(filename)
    if result:
        return result

    # Pattern 4: Quarter (Q1, Q2, Q3, Q4) - HIGH CONFIDENCE
    result = _try_quarter(filename)
    if result:
        return result

    # Pattern 5: YYYYMMDD (20241201) - HIGH CONFIDENCE
    result = _try_yyyymmdd(filename)
    if result:
        return result

    # Pattern 6: MM-DD-YYYY or DD-MM-YYYY - MEDIUM/LOW CONFIDENCE (ambiguous)
    result = _try_slash_or_dash_date(filename)
    if result:
        return result

    # Pattern 7: Year only (2024) - LOW CONFIDENCE
    result = _try_year_only(filename)
    if result:
        return result

    # No date found
    return DateParseResult(
        date=None,
        confidence="None",
        pattern="No date found in filename",
        original_text=None
    )


def _try_month_dash_year_short(filename: str) -> Optional[DateParseResult]:
    """Try Month-YY format (Dec-24, Nov-24)"""
    # Pattern: 3-letter month abbreviation followed by -YY
    pattern = r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2})\b'
    match = re.search(pattern, filename, re.IGNORECASE)

    if match:
        month_abbr = match.group(1).capitalize()
        year_short = int(match.group(2))

        # Convert 2-digit year to 4-digit (assume 20xx for now)
        year = 2000 + year_short

        # Month name to number
        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
            "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
            "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        month = month_map[month_abbr]

        return DateParseResult(
            date=date(year, month, 1),  # First of month
            confidence="High",
            pattern="Month-YY",
            original_text=match.group(0)
        )

    return None


def _try_year_month_dash(filename: str) -> Optional[DateParseResult]:
    """Try YYYY-MM or MM-YYYY format"""
    # Try YYYY-MM first.
    # Use negative lookaround instead of \b so that underscore-delimited dates
    # (e.g. "report_2024-03.xlsx") are matched. \b treats _ as a word character
    # and would fail between '_' and '2'.
    pattern1 = r'(?<![a-zA-Z0-9])(20\d{2})-(0[1-9]|1[0-2])(?![a-zA-Z0-9])'
    match = re.search(pattern1, filename)

    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        return DateParseResult(
            date=date(year, month, 1),
            confidence="High",
            pattern="YYYY-MM",
            original_text=match.group(0)
        )

    # Try MM-YYYY
    pattern2 = r'(?<![a-zA-Z0-9])(0[1-9]|1[0-2])-(20\d{2})(?![a-zA-Z0-9])'
    match = re.search(pattern2, filename)

    if match:
        month = int(match.group(1))
        year = int(match.group(2))

        return DateParseResult(
            date=date(year, month, 1),
            confidence="High",
            pattern="MM-YYYY",
            original_text=match.group(0)
        )

    return None


def _try_full_month_name(filename: str) -> Optional[DateParseResult]:
    """Try full month name (December 2024, 2024 December)"""
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }

    # Try "Month YYYY"
    for month_name, month_num in months.items():
        pattern = rf'\b{month_name}\s+(20\d{{2}})\b'
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            return DateParseResult(
                date=date(year, month_num, 1),
                confidence="High",
                pattern="Full Month YYYY",
                original_text=match.group(0)
            )

    # Try "YYYY Month"
    for month_name, month_num in months.items():
        pattern = rf'\b(20\d{{2}})\s+{month_name}\b'
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            return DateParseResult(
                date=date(year, month_num, 1),
                confidence="High",
                pattern="YYYY Full Month",
                original_text=match.group(0)
            )

    return None


def _try_quarter(filename: str) -> Optional[DateParseResult]:
    """
    Try quarter format (Q1, Q2, Q3, Q4).

    Returns first day of the quarter's LAST month:
    - Q1 = Jan 1 (Jan is last month of Q1: Jan-Mar)
    - Q2 = Apr 1 (Apr is last month of Q2: Apr-Jun)
    - Q3 = Jul 1 (Jul is last month of Q3: Jul-Sep)
    - Q4 = Oct 1 (Oct is last month of Q4: Oct-Dec)
    """
    # Pattern: Q1, Q2, Q3, Q4 with optional year
    # Try YYYY-Q# first
    pattern1 = r'\b(20\d{2})-Q([1-4])\b'
    match = re.search(pattern1, filename, re.IGNORECASE)

    if match:
        year = int(match.group(1))
        quarter = int(match.group(2))

        # Quarter to first month of quarter
        quarter_months = {1: 1, 2: 4, 3: 7, 4: 10}
        month = quarter_months[quarter]

        return DateParseResult(
            date=date(year, month, 1),
            confidence="High",
            pattern="YYYY-Q#",
            original_text=match.group(0)
        )

    # Try Q#-YYYY
    pattern2 = r'\bQ([1-4])-(20\d{2})\b'
    match = re.search(pattern2, filename, re.IGNORECASE)

    if match:
        quarter = int(match.group(1))
        year = int(match.group(2))

        quarter_months = {1: 1, 2: 4, 3: 7, 4: 10}
        month = quarter_months[quarter]

        return DateParseResult(
            date=date(year, month, 1),
            confidence="Medium",
            pattern="Q#-YYYY",
            original_text=match.group(0)
        )

    return None


def _try_yyyymmdd(filename: str) -> Optional[DateParseResult]:
    """Try YYYYMMDD format (20241201)"""
    # Allow word boundaries or underscores around the date
    pattern = r'(?:^|[_\s])(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])(?:[_\s]|$|\.)'
    match = re.search(pattern, filename)

    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        try:
            # Use day 1 always (per requirements)
            parsed_date = date(year, month, 1)
            return DateParseResult(
                date=parsed_date,
                confidence="High",
                pattern="YYYYMMDD",
                original_text=match.group(0)
            )
        except ValueError:
            # Invalid date (e.g., Feb 31)
            return None

    return None


def _try_slash_or_dash_date(filename: str) -> Optional[DateParseResult]:
    """
    Try MM-DD-YYYY or DD-MM-YYYY format (ambiguous).

    Returns medium/low confidence since format is ambiguous.
    """
    # Pattern: ##-##-#### or ##/##/####
    pattern = r'\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b'
    match = re.search(pattern, filename)

    if match:
        first = int(match.group(1))
        second = int(match.group(2))
        year = int(match.group(3))

        # Assume MM-DD-YYYY if first number is <= 12
        if first <= 12:
            month = first
            confidence = "Medium"
        # Otherwise assume DD-MM-YYYY
        elif second <= 12:
            month = second
            confidence = "Low"
        else:
            # Can't determine
            return None

        try:
            return DateParseResult(
                date=date(year, month, 1),  # Use first of month
                confidence=confidence,
                pattern="MM-DD-YYYY or DD-MM-YYYY (ambiguous)",
                original_text=match.group(0)
            )
        except ValueError:
            return None

    return None


def _try_year_only(filename: str) -> Optional[DateParseResult]:
    """Try year-only format (2024) - returns Jan 1"""
    pattern = r'\b(20\d{2})\b'
    match = re.search(pattern, filename)

    if match:
        year = int(match.group(1))

        return DateParseResult(
            date=date(year, 1, 1),  # Jan 1 of that year
            confidence="Low",
            pattern="Year only",
            original_text=match.group(0)
        )

    return None
