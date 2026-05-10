"""Unit tests for web/helpers.py rendering helper functions."""

import pytest

from web.helpers import (
    classify_health_zone,
    compute_trend_arrow,
    format_financial_value,
    should_emphasize_yoy,
)


class TestClassifyHealthZone:
    """Tests for classify_health_zone()."""

    def test_none_value_returns_unknown(self):
        assert classify_health_zone(None, 1.0, 2.0) == "unknown"

    def test_normal_concern_below_low(self):
        assert classify_health_zone(0.5, 1.0, 2.0) == "concern"

    def test_normal_adequate_at_low_boundary(self):
        assert classify_health_zone(1.0, 1.0, 2.0) == "adequate"

    def test_normal_adequate_between_boundaries(self):
        assert classify_health_zone(1.5, 1.0, 2.0) == "adequate"

    def test_normal_adequate_at_high_boundary(self):
        assert classify_health_zone(2.0, 1.0, 2.0) == "adequate"

    def test_normal_strong_above_high(self):
        assert classify_health_zone(2.5, 1.0, 2.0) == "strong"

    def test_inverted_strong_below_low(self):
        assert classify_health_zone(0.5, 1.0, 2.0, inverted=True) == "strong"

    def test_inverted_adequate_at_low_boundary(self):
        assert classify_health_zone(1.0, 1.0, 2.0, inverted=True) == "adequate"

    def test_inverted_adequate_between_boundaries(self):
        assert classify_health_zone(1.5, 1.0, 2.0, inverted=True) == "adequate"

    def test_inverted_adequate_at_high_boundary(self):
        assert classify_health_zone(2.0, 1.0, 2.0, inverted=True) == "adequate"

    def test_inverted_concern_above_high(self):
        assert classify_health_zone(2.5, 1.0, 2.0, inverted=True) == "concern"

    def test_current_ratio_thresholds(self):
        """Current Ratio: thresholds 1.0/2.0, not inverted."""
        assert classify_health_zone(0.8, 1.0, 2.0) == "concern"
        assert classify_health_zone(1.5, 1.0, 2.0) == "adequate"
        assert classify_health_zone(3.0, 1.0, 2.0) == "strong"

    def test_debt_to_equity_thresholds(self):
        """Debt-to-Equity: thresholds 1.0/2.0, inverted (lower is better)."""
        assert classify_health_zone(0.5, 1.0, 2.0, inverted=True) == "strong"
        assert classify_health_zone(1.5, 1.0, 2.0, inverted=True) == "adequate"
        assert classify_health_zone(3.0, 1.0, 2.0, inverted=True) == "concern"

    def test_net_margin_thresholds(self):
        """Net Margin: thresholds 5%/15%, not inverted."""
        assert classify_health_zone(3.0, 5.0, 15.0) == "concern"
        assert classify_health_zone(10.0, 5.0, 15.0) == "adequate"
        assert classify_health_zone(20.0, 5.0, 15.0) == "strong"


class TestComputeTrendArrow:
    """Tests for compute_trend_arrow()."""

    def test_none_returns_flat_gray(self):
        result = compute_trend_arrow(None)
        assert result == {"direction": "flat", "color": "gray"}

    def test_zero_returns_flat_gray(self):
        result = compute_trend_arrow(0.0)
        assert result == {"direction": "flat", "color": "gray"}

    def test_positive_higher_is_better_green(self):
        result = compute_trend_arrow(5.0, higher_is_better=True)
        assert result == {"direction": "up", "color": "green"}

    def test_negative_higher_is_better_red(self):
        result = compute_trend_arrow(-5.0, higher_is_better=True)
        assert result == {"direction": "down", "color": "red"}

    def test_positive_lower_is_better_red(self):
        result = compute_trend_arrow(5.0, higher_is_better=False)
        assert result == {"direction": "up", "color": "red"}

    def test_negative_lower_is_better_green(self):
        result = compute_trend_arrow(-5.0, higher_is_better=False)
        assert result == {"direction": "down", "color": "green"}

    def test_none_with_higher_is_better_false(self):
        result = compute_trend_arrow(None, higher_is_better=False)
        assert result == {"direction": "flat", "color": "gray"}


class TestFormatFinancialValue:
    """Tests for format_financial_value()."""

    def test_none_returns_na(self):
        assert format_financial_value(None) == "N/A"

    def test_large_number_with_separators(self):
        assert format_financial_value(1234567.89) == "1,234,567.89"

    def test_zero(self):
        assert format_financial_value(0) == "0.00"

    def test_small_number(self):
        assert format_financial_value(0.5) == "0.50"

    def test_negative_number(self):
        assert format_financial_value(-1234.5) == "-1,234.50"

    def test_integer_gets_decimals(self):
        assert format_financial_value(1000) == "1,000.00"

    def test_rounding(self):
        assert format_financial_value(1.999) == "2.00"

    def test_three_decimal_places_rounded(self):
        assert format_financial_value(1234.567) == "1,234.57"


class TestShouldEmphasizeYoy:
    """Tests for should_emphasize_yoy()."""

    def test_none_returns_false(self):
        assert should_emphasize_yoy(None) is False

    def test_zero_returns_false(self):
        assert should_emphasize_yoy(0.0) is False

    def test_within_threshold_positive(self):
        assert should_emphasize_yoy(5.0) is False

    def test_within_threshold_negative(self):
        assert should_emphasize_yoy(-5.0) is False

    def test_at_threshold_returns_false(self):
        assert should_emphasize_yoy(10.0) is False

    def test_at_negative_threshold_returns_false(self):
        assert should_emphasize_yoy(-10.0) is False

    def test_above_threshold_returns_true(self):
        assert should_emphasize_yoy(10.1) is True

    def test_below_negative_threshold_returns_true(self):
        assert should_emphasize_yoy(-10.1) is True

    def test_large_positive_returns_true(self):
        assert should_emphasize_yoy(50.0) is True

    def test_large_negative_returns_true(self):
        assert should_emphasize_yoy(-50.0) is True
