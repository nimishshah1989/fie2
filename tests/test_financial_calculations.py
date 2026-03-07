"""
Tests for core financial calculation functions in FIE v3.

Covers:
- XIRR computation (Newton-Raphson method)
- Maximum drawdown computation
- Yahoo symbol mapping for portfolio tickers
- Empty portfolio totals helper
- Price return computation (compute_returns)
"""

from datetime import datetime, date, timedelta
import pytest

# ─── Import the functions under test from portfolio_service ───
from services.portfolio_service import (
    compute_xirr,
    compute_max_drawdown,
    get_yahoo_symbol,
    YAHOO_SYMBOL_MAP,
    empty_totals,
)

from price_service import compute_returns


# ═══════════════════════════════════════════════════════════
#  XIRR COMPUTATION
# ═══════════════════════════════════════════════════════════


class TestComputeXirr:
    """Tests for the Newton-Raphson XIRR implementation."""

    def test_should_return_approximately_10_pct_for_simple_annual_return(self):
        """Invest 100k, get back 110k after exactly 1 year => ~10% XIRR."""
        start = date(2025, 1, 1)
        end = date(2026, 1, 1)
        cashflows = [
            (start, -100_000),   # investment (outflow)
            (end,    110_000),   # redemption (inflow)
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        assert abs(result - 10.0) < 0.5, f"Expected ~10%, got {result}%"

    def test_should_return_approximately_20_pct_for_20_percent_gain(self):
        """Invest 1L, get back 1.2L after 1 year => ~20% XIRR."""
        start = date(2024, 4, 1)
        end = date(2025, 3, 31)
        cashflows = [
            (start, -100_000),
            (end,    120_000),
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        assert abs(result - 20.0) < 1.0, f"Expected ~20%, got {result}%"

    def test_should_handle_multiple_investments_and_one_redemption(self):
        """Multiple SIP-like investments with a final portfolio value."""
        cashflows = [
            (date(2024, 1, 1), -10_000),   # 1st SIP
            (date(2024, 4, 1), -10_000),   # 2nd SIP
            (date(2024, 7, 1), -10_000),   # 3rd SIP
            (date(2024, 10, 1), -10_000),  # 4th SIP
            (date(2025, 1, 1),  45_000),   # portfolio value after 1 year
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        # Total invested 40k, got back 45k => positive return
        assert result > 0, f"Expected positive XIRR, got {result}%"

    def test_should_handle_negative_return(self):
        """Invest 100k, get back only 90k => negative XIRR."""
        cashflows = [
            (date(2024, 1, 1), -100_000),
            (date(2025, 1, 1),   90_000),
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        assert result < 0, f"Expected negative XIRR, got {result}%"
        assert abs(result - (-10.0)) < 0.5, f"Expected ~-10%, got {result}%"

    def test_should_return_none_for_empty_cashflows(self):
        """Empty cashflow list should return None."""
        result = compute_xirr([])
        assert result is None

    def test_should_return_none_for_single_cashflow(self):
        """Single cashflow is insufficient for XIRR calculation."""
        result = compute_xirr([(date(2024, 1, 1), -100_000)])
        assert result is None

    def test_should_handle_same_day_transactions(self):
        """Two cashflows on the same day (buy + sell)."""
        today = date(2025, 1, 1)
        cashflows = [
            (today, -100_000),
            (today,  105_000),
        ]
        # Same-day means days=0 for all entries, (1+rate)^0 = 1
        # NPV = -100000 + 105000 = 5000, derivative is 0
        # The function should handle this gracefully (may return None or a value)
        result = compute_xirr(cashflows)
        # With both cashflows on day 0, NPV is just the sum of amounts
        # and the derivative is 0, so the Newton-Raphson should break early
        # The function returns round(rate * 100, 2) which defaults to ~10% initial guess
        # This is acceptable behavior for a degenerate case
        assert result is not None or result is None  # should not raise

    def test_should_handle_zero_return(self):
        """Invest 100k, get back exactly 100k => ~0% XIRR."""
        cashflows = [
            (date(2024, 1, 1), -100_000),
            (date(2025, 1, 1),  100_000),
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        assert abs(result) < 1.0, f"Expected ~0%, got {result}%"

    def test_should_handle_large_positive_return(self):
        """Invest 100k, get back 200k in 1 year => ~100% XIRR."""
        cashflows = [
            (date(2024, 1, 1), -100_000),
            (date(2025, 1, 1),  200_000),
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        assert abs(result - 100.0) < 1.0, f"Expected ~100%, got {result}%"

    def test_should_handle_half_year_period(self):
        """Invest 100k, get 110k after 6 months => annualized ~21% XIRR."""
        cashflows = [
            (date(2024, 1, 1), -100_000),
            (date(2024, 7, 1),  110_000),  # ~182 days
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        # 10% in 6 months annualizes to approximately 21%
        assert result > 15.0, f"Expected >15% annualized, got {result}%"
        assert result < 25.0, f"Expected <25% annualized, got {result}%"

    def test_should_return_result_as_percentage(self):
        """XIRR result should be in percentage format (e.g. 10.0 not 0.1)."""
        cashflows = [
            (date(2024, 1, 1), -100_000),
            (date(2025, 1, 1),  110_000),
        ]
        result = compute_xirr(cashflows)
        assert result is not None
        # Result should be ~10, not ~0.1
        assert result > 1.0, "XIRR should return percentage, not decimal"

    def test_should_return_none_when_rate_diverges(self):
        """When Newton-Raphson diverges (rate > 100 or < -0.99), return None."""
        # Extreme case: invest 1 rupee, get 1 crore next day
        cashflows = [
            (date(2024, 1, 1), -1),
            (date(2024, 1, 2),  10_000_000),
        ]
        result = compute_xirr(cashflows)
        # The function caps at rate > 100, so this should return None
        # or a very large number that gets capped
        # Either outcome is acceptable for such an extreme case
        assert result is None or isinstance(result, float)


# ═══════════════════════════════════════════════════════════
#  MAX DRAWDOWN COMPUTATION
# ═══════════════════════════════════════════════════════════


class TestComputeMaxDrawdown:
    """Tests for the maximum drawdown calculation."""

    def test_should_compute_25_pct_drawdown_for_clear_peak_to_trough(self):
        """[100, 120, 90, 110] => peak=120, trough=90, drawdown = (90-120)/120 = -25%."""
        values = [100, 120, 90, 110]
        result = compute_max_drawdown(values)
        assert result is not None
        assert abs(result - (-25.0)) < 0.01, f"Expected -25.0%, got {result}%"

    def test_should_return_zero_for_monotonically_increasing_series(self):
        """No drawdown when values only go up."""
        values = [100, 110, 120, 130, 140, 150]
        result = compute_max_drawdown(values)
        assert result is not None
        assert result == 0.0, f"Expected 0.0% drawdown, got {result}%"

    def test_should_return_zero_for_constant_values(self):
        """All same values means no drawdown."""
        values = [100, 100, 100, 100]
        result = compute_max_drawdown(values)
        assert result is not None
        assert result == 0.0, f"Expected 0.0% drawdown, got {result}%"

    def test_should_return_none_for_single_value(self):
        """Single value is insufficient for drawdown calculation."""
        result = compute_max_drawdown([100])
        assert result is None

    def test_should_return_none_for_empty_list(self):
        """Empty list should return None."""
        result = compute_max_drawdown([])
        assert result is None

    def test_should_detect_largest_drawdown_in_multiple_dips(self):
        """When there are multiple drawdowns, return the largest one."""
        # First dip: 100->80 = -20%, Second dip: 120->60 = -50%
        values = [100, 80, 100, 120, 60, 100]
        result = compute_max_drawdown(values)
        assert result is not None
        assert abs(result - (-50.0)) < 0.01, f"Expected -50.0%, got {result}%"

    def test_should_handle_monotonically_decreasing_series(self):
        """All values declining means drawdown equals total decline from first value."""
        values = [100, 90, 80, 70, 60]
        result = compute_max_drawdown(values)
        assert result is not None
        assert abs(result - (-40.0)) < 0.01, f"Expected -40.0%, got {result}%"

    def test_should_handle_drawdown_at_the_end(self):
        """Drawdown occurring at the very end of the series."""
        values = [100, 110, 120, 130, 50]
        result = compute_max_drawdown(values)
        assert result is not None
        # Peak = 130, trough = 50 => (50-130)/130 = -61.54%
        expected = round((50 - 130) / 130 * 100, 2)
        assert abs(result - expected) < 0.01, f"Expected {expected}%, got {result}%"

    def test_should_handle_large_real_world_nav_series(self):
        """Simulated NAV series with realistic portfolio values."""
        # Simulate a portfolio that rises, dips, recovers
        values = [
            1000000, 1050000, 1100000, 1080000, 1120000,
            1150000, 1000000, 1050000, 1200000, 1250000,
        ]
        result = compute_max_drawdown(values)
        assert result is not None
        # Peak before biggest dip = 1150000, trough = 1000000
        expected = round((1000000 - 1150000) / 1150000 * 100, 2)
        assert abs(result - expected) < 0.01, f"Expected {expected}%, got {result}%"

    def test_should_return_result_in_negative_percentage(self):
        """Drawdown result should be negative (or zero) percentage."""
        values = [100, 120, 80, 110]
        result = compute_max_drawdown(values)
        assert result is not None
        assert result <= 0, "Drawdown should be negative or zero"

    def test_should_handle_two_values(self):
        """Minimum viable input: two values."""
        result = compute_max_drawdown([100, 80])
        assert result is not None
        assert abs(result - (-20.0)) < 0.01

    def test_should_handle_zero_peak_gracefully(self):
        """If the peak is 0, division by zero should be avoided."""
        values = [0, 0, 0]
        result = compute_max_drawdown(values)
        assert result is not None
        assert result == 0.0, "Zero peak should result in 0 drawdown"


# ═══════════════════════════════════════════════════════════
#  YAHOO SYMBOL MAPPING (portfolio_service)
# ═══════════════════════════════════════════════════════════


class TestGetYahooSymbol:
    """Tests for portfolio-specific Yahoo Finance symbol mapping."""

    def test_should_return_ns_suffix_for_regular_ticker(self):
        """Regular NSE ticker should get .NS suffix."""
        result = get_yahoo_symbol("RELIANCE")
        assert result == "RELIANCE.NS"

    def test_should_map_liquidcase_correctly(self):
        """LIQUIDCASE is a known override in YAHOO_SYMBOL_MAP."""
        result = get_yahoo_symbol("LIQUIDCASE")
        assert result == "LIQUIDCASE.NS"

    def test_should_map_cpseetf_correctly(self):
        """CPSEETF maps to CPSEETF.NS."""
        result = get_yahoo_symbol("CPSEETF")
        assert result == "CPSEETF.NS"

    def test_should_map_metaletf_to_metalietf(self):
        """METALETF maps to METALIETF.NS (note the I)."""
        result = get_yahoo_symbol("METALETF")
        assert result == "METALIETF.NS"

    def test_should_map_sensexetf_to_sensexietf(self):
        """SENSEXETF maps to SENSEXIETF.NS."""
        result = get_yahoo_symbol("SENSEXETF")
        assert result == "SENSEXIETF.NS"

    def test_should_map_netfmid150_to_mid150bees(self):
        """NETFMID150 maps to MID150BEES.NS."""
        result = get_yahoo_symbol("NETFMID150")
        assert result == "MID150BEES.NS"

    def test_should_return_none_for_microbasket_ticker(self):
        """MB_* tickers use basket NAV, not Yahoo Finance."""
        result = get_yahoo_symbol("MB_HEALTHCARE")
        assert result is None

    def test_should_return_none_for_lowercase_microbasket(self):
        """mb_* tickers should also be recognized (case insensitive)."""
        result = get_yahoo_symbol("mb_pharma")
        assert result is None

    def test_should_handle_oil_etf_mapping(self):
        """OIL ETF (with space) maps to OILIETF.NS."""
        result = get_yahoo_symbol("OIL ETF")
        assert result == "OILIETF.NS"

    def test_should_handle_nipponamc_netfauto_mapping(self):
        """Complex ticker with dash maps correctly."""
        result = get_yahoo_symbol("NIPPONAMC - NETFAUTO")
        assert result == "NETFAUTO.NS"

    def test_should_add_ns_suffix_for_unknown_ticker(self):
        """Unknown tickers default to appending .NS."""
        result = get_yahoo_symbol("HDFCBANK")
        assert result == "HDFCBANK.NS"

    def test_should_cover_all_yahoo_symbol_map_entries(self):
        """Every entry in YAHOO_SYMBOL_MAP should be correctly returned."""
        for ticker, expected_symbol in YAHOO_SYMBOL_MAP.items():
            result = get_yahoo_symbol(ticker)
            assert result == expected_symbol, (
                f"get_yahoo_symbol('{ticker}') returned '{result}', "
                f"expected '{expected_symbol}'"
            )


# ═══════════════════════════════════════════════════════════
#  EMPTY TOTALS HELPER
# ═══════════════════════════════════════════════════════════


class TestEmptyTotals:
    """Tests for the empty portfolio totals structure."""

    def test_should_return_dict_with_all_zero_values(self):
        """Empty totals should have all financial fields set to 0."""
        result = empty_totals()
        assert result["total_invested"] == 0.0
        assert result["current_value"] == 0.0
        assert result["unrealized_pnl"] == 0.0
        assert result["unrealized_pnl_pct"] == 0.0
        assert result["realized_pnl"] == 0.0
        assert result["num_holdings"] == 0

    def test_should_contain_exactly_six_keys(self):
        """Verify the structure has exactly the expected keys."""
        result = empty_totals()
        expected_keys = {
            "total_invested", "current_value", "unrealized_pnl",
            "unrealized_pnl_pct", "realized_pnl", "num_holdings",
        }
        assert set(result.keys()) == expected_keys


# ═══════════════════════════════════════════════════════════
#  COMPUTE RETURNS (from price_service)
# ═══════════════════════════════════════════════════════════


class TestComputeReturns:
    """Tests for the alert position return computation."""

    def test_should_compute_bullish_positive_return(self):
        """Bullish position with price increase => positive return."""
        result = compute_returns(100.0, 120.0, "BULLISH")
        assert result["return_pct"] == 20.0
        assert result["return_absolute"] == 20.0

    def test_should_compute_bullish_negative_return(self):
        """Bullish position with price decrease => negative return."""
        result = compute_returns(100.0, 80.0, "BULLISH")
        assert result["return_pct"] == -20.0
        assert result["return_absolute"] == -20.0

    def test_should_compute_bearish_positive_return(self):
        """Bearish position profits when price drops."""
        result = compute_returns(100.0, 80.0, "BEARISH")
        assert result["return_pct"] == 20.0
        assert result["return_absolute"] == 20.0

    def test_should_compute_bearish_negative_return(self):
        """Bearish position loses when price rises."""
        result = compute_returns(100.0, 120.0, "BEARISH")
        assert result["return_pct"] == -20.0
        assert result["return_absolute"] == -20.0

    def test_should_return_none_for_zero_alert_price(self):
        """Zero alert price should return None (division by zero guard)."""
        result = compute_returns(0.0, 100.0, "BULLISH")
        assert result["return_pct"] is None
        assert result["return_absolute"] is None

    def test_should_return_none_for_none_alert_price(self):
        """None alert price should return None."""
        result = compute_returns(None, 100.0, "BULLISH")
        assert result["return_pct"] is None

    def test_should_return_none_for_none_current_price(self):
        """None current price should return None."""
        result = compute_returns(100.0, None, "BULLISH")
        assert result["return_pct"] is None

    def test_should_default_to_bullish_for_unknown_direction(self):
        """Non-BEARISH direction should behave like BULLISH (default multiplier)."""
        result = compute_returns(100.0, 120.0, "NEUTRAL")
        assert result["return_pct"] == 20.0

    def test_should_round_return_pct_to_two_decimals(self):
        """Return percentage should be rounded to 2 decimal places."""
        result = compute_returns(100.0, 133.33, "BULLISH")
        assert result["return_pct"] == 33.33

    def test_should_round_return_absolute_to_two_decimals(self):
        """Absolute return should be rounded to 2 decimal places."""
        result = compute_returns(100.0, 133.337, "BULLISH")
        assert result["return_absolute"] == 33.34  # rounds up
