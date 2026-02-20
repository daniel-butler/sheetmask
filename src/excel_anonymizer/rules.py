"""
Numeric anonymization rules for domain-aware data anonymization.

These rules preserve statistical properties and business constraints
while anonymizing numeric data.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import random
import pandas as pd


@dataclass
class NumericAnonymizationRule(ABC):
    """Base class for numeric anonymization rules."""

    @abstractmethod
    def apply(self, series: pd.Series, context: dict[str, pd.Series]) -> pd.Series:
        """
        Apply anonymization to series.

        Args:
            series: Pandas series to anonymize
            context: Dict of all columns in DataFrame (for relationship rules)

        Returns:
            Anonymized series
        """
        pass


@dataclass
class PercentageVarianceRule(NumericAnonymizationRule):
    """
    Add random variance while preserving distribution.

    Example:
        rule = PercentageVarianceRule(variance_pct=0.3)  # ±30%
        anonymized = rule.apply(df["Revenue"], {})

        # Original: [100, 200, 300]
        # Anonymized: [87, 234, 281] (varies by ±30%, preserves distribution shape)
    """
    variance_pct: float = 0.3  # ±30% default

    def apply(self, series: pd.Series, context: dict[str, pd.Series]) -> pd.Series:
        """Add random noise ±variance_pct to each value"""

        def add_noise(value):
            if pd.isna(value):
                return value
            if value == 0:
                return 0.0  # Don't add noise to zero values
            noise = value * random.uniform(-self.variance_pct, self.variance_pct)
            return value + noise

        anonymized = series.apply(add_noise)

        # Round to 2 decimal places for financial data
        try:
            anonymized = anonymized.round(2)
        except (TypeError, AttributeError):
            pass

        return anonymized


@dataclass
class PreserveRelationshipRule(NumericAnonymizationRule):
    """
    Recompute derived columns from anonymized source columns.

    Use this for computed columns like:
    - Margin% = (Revenue - Expense) / Revenue
    - GM = Revenue - Expense
    - Ratio = Value1 / Value2

    Example:
        # GM should be Revenue - Expense
        rule = PreserveRelationshipRule(
            formula="context['Revenue'] - context['Expense']",
            dependent_columns=["Revenue", "Expense"]
        )

        # After anonymizing Revenue and Expense, GM is recomputed
        anonymized_gm = rule.apply(df["GM"], context)
    """
    formula: str  # Python expression using context dict
    dependent_columns: list[str]

    def apply(self, series: pd.Series, context: dict[str, pd.Series]) -> pd.Series:
        """Recompute from anonymized dependent columns"""

        # Verify dependent columns exist in context
        missing = [col for col in self.dependent_columns if col not in context]
        if missing:
            raise ValueError(f"Missing dependent columns: {missing}")

        # Evaluate formula
        result = eval(self.formula, {"__builtins__": {}}, {"context": context})

        # Convert to Series if needed
        if not isinstance(result, pd.Series):
            result = pd.Series(result, index=series.index)

        # Round to 2 decimal places
        try:
            result = result.round(2)
        except (TypeError, AttributeError):
            pass

        return result
