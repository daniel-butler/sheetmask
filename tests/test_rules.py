import random

import pandas as pd
import pytest
from sheetmask.rules import PercentageVarianceRule, PreserveRelationshipRule


def test_percentage_variance_changes_values():
    random.seed(0)
    rule = PercentageVarianceRule(variance_pct=0.3)
    series = pd.Series([100.0, 200.0, 300.0])
    result = rule.apply(series, {})
    # Each value should shift by at least 1% (30% variance applied)
    assert all(abs(result - series) >= 1.0)


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


def test_percentage_variance_is_reproducible_with_seed():
    import random as stdlib_random

    rng = stdlib_random.Random(42)
    rule = PercentageVarianceRule(variance_pct=0.3, rng=rng)
    series = pd.Series([100.0, 200.0, 300.0])
    result1 = rule.apply(series, {})

    rng2 = stdlib_random.Random(42)
    rule2 = PercentageVarianceRule(variance_pct=0.3, rng=rng2)
    result2 = rule2.apply(series, {})

    pd.testing.assert_series_equal(result1, result2)
