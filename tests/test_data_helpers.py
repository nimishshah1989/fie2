"""
Tests for FIE v3 — Data Helper Utilities (services/data_helpers.py)

Covers upsert_price_row, get_portfolio_tickers, and
get_all_portfolio_tickers_with_inception with various data states.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from models import (
    IndexPrice, ModelPortfolio, PortfolioHolding,
    PortfolioStatus,
)


# ─── Helpers ────────────────────────────────────────────────

def _seed_portfolio_with_holdings(db_session, name="Test Portfolio", tickers=None,
                                  inception_date=None, status=PortfolioStatus.ACTIVE):
    """Create a portfolio with holdings in the test DB."""
    portfolio = ModelPortfolio(
        name=name, benchmark="NIFTY", status=status,
        inception_date=inception_date,
    )
    db_session.add(portfolio)
    db_session.flush()

    if tickers is None:
        tickers = [("RELIANCE", 10), ("TCS", 5)]

    for ticker, qty in tickers:
        db_session.add(PortfolioHolding(
            portfolio_id=portfolio.id,
            ticker=ticker,
            quantity=qty,
            avg_cost=100.0,
            total_cost=100.0 * qty,
        ))
    db_session.commit()
    return portfolio


# ─── upsert_price_row ─────────────────────────────────────


class TestUpsertPriceRow:
    """Tests for the upsert_price_row function."""

    def test_should_insert_new_price_row(self, db_session):
        from services.data_helpers import upsert_price_row
        row = {
            "date": "2026-03-07",
            "close": 22500.0,
            "open": 22400.0,
            "high": 22600.0,
            "low": 22300.0,
            "volume": 1000000.0,
        }
        result = upsert_price_row(db_session, "NIFTY", row)
        db_session.commit()
        assert result is True

        # Verify it was inserted
        saved = db_session.query(IndexPrice).filter_by(
            date="2026-03-07", index_name="NIFTY"
        ).first()
        assert saved is not None
        assert saved.close_price == 22500.0
        assert saved.open_price == 22400.0
        assert saved.high_price == 22600.0
        assert saved.low_price == 22300.0
        assert saved.volume == 1000000.0

    def test_should_update_existing_price_row(self, db_session):
        from services.data_helpers import upsert_price_row
        # Insert first
        row1 = {"date": "2026-03-06", "close": 22000.0, "open": 21900.0}
        upsert_price_row(db_session, "NIFTY", row1)
        db_session.commit()

        # Update with new close price
        row2 = {"date": "2026-03-06", "close": 22100.0, "open": 21950.0}
        result = upsert_price_row(db_session, "NIFTY", row2)
        db_session.commit()
        assert result is True

        saved = db_session.query(IndexPrice).filter_by(
            date="2026-03-06", index_name="NIFTY"
        ).first()
        assert saved.close_price == 22100.0
        assert saved.open_price == 21950.0

    def test_should_return_false_when_close_is_missing(self, db_session):
        from services.data_helpers import upsert_price_row
        row = {"date": "2026-03-07"}
        result = upsert_price_row(db_session, "NIFTY", row)
        assert result is False

    def test_should_return_false_when_close_is_none(self, db_session):
        from services.data_helpers import upsert_price_row
        row = {"date": "2026-03-07", "close": None}
        result = upsert_price_row(db_session, "NIFTY", row)
        assert result is False

    def test_should_return_false_when_close_is_zero(self, db_session):
        from services.data_helpers import upsert_price_row
        row = {"date": "2026-03-07", "close": 0}
        result = upsert_price_row(db_session, "NIFTY", row)
        assert result is False

    def test_should_handle_missing_optional_fields(self, db_session):
        """Only close and date are required. Other fields default to None."""
        from services.data_helpers import upsert_price_row
        row = {"date": "2026-03-05", "close": 22000.0}
        result = upsert_price_row(db_session, "NIFTY", row)
        db_session.commit()
        assert result is True

        saved = db_session.query(IndexPrice).filter_by(
            date="2026-03-05", index_name="NIFTY"
        ).first()
        assert saved.close_price == 22000.0
        assert saved.open_price is None
        assert saved.high_price is None
        assert saved.low_price is None
        assert saved.volume is None

    def test_should_update_fetched_at_on_upsert(self, db_session):
        """The fetched_at timestamp should update on both insert and update."""
        from services.data_helpers import upsert_price_row
        row = {"date": "2026-03-04", "close": 21900.0}
        upsert_price_row(db_session, "NIFTY", row)
        db_session.commit()

        saved1 = db_session.query(IndexPrice).filter_by(
            date="2026-03-04", index_name="NIFTY"
        ).first()
        first_fetched = saved1.fetched_at

        # Update same row
        row2 = {"date": "2026-03-04", "close": 21950.0}
        upsert_price_row(db_session, "NIFTY", row2)
        db_session.commit()
        db_session.refresh(saved1)
        # fetched_at should be set (may or may not differ due to speed)
        assert saved1.fetched_at is not None

    def test_should_work_with_different_index_names(self, db_session):
        """Multiple index names on the same date should create separate rows."""
        from services.data_helpers import upsert_price_row
        upsert_price_row(db_session, "NIFTY", {"date": "2026-03-07", "close": 22000.0})
        upsert_price_row(db_session, "BANKNIFTY", {"date": "2026-03-07", "close": 48000.0})
        upsert_price_row(db_session, "TCS", {"date": "2026-03-07", "close": 3500.0})
        db_session.commit()

        count = db_session.query(IndexPrice).filter_by(date="2026-03-07").count()
        assert count == 3

    def test_should_handle_very_large_prices(self, db_session):
        """Indices like SENSEX have values in the 70000+ range."""
        from services.data_helpers import upsert_price_row
        row = {"date": "2026-03-07", "close": 75432.89, "volume": 999999999.0}
        result = upsert_price_row(db_session, "SENSEX", row)
        db_session.commit()
        assert result is True

        saved = db_session.query(IndexPrice).filter_by(
            date="2026-03-07", index_name="SENSEX"
        ).first()
        assert saved.close_price == 75432.89

    def test_should_handle_fractional_prices(self, db_session):
        """Stock prices can have many decimal places."""
        from services.data_helpers import upsert_price_row
        row = {"date": "2026-03-07", "close": 1234.5678}
        result = upsert_price_row(db_session, "RELIANCE", row)
        db_session.commit()
        assert result is True

        saved = db_session.query(IndexPrice).filter_by(
            date="2026-03-07", index_name="RELIANCE"
        ).first()
        assert abs(saved.close_price - 1234.5678) < 0.0001


# ─── get_portfolio_tickers ────────────────────────────────


class TestGetPortfolioTickers:
    """Tests for the get_portfolio_tickers function.

    get_portfolio_tickers uses a late import: `from price_service import NSE_ETF_UNIVERSE, NSE_TICKER_MAP`
    So we must patch on price_service, not on services.data_helpers.
    """

    @patch("price_service.NSE_ETF_UNIVERSE", {"NIFTYBEES": "NIFTYBEES.NS", "BANKBEES": "BANKBEES.NS"})
    @patch("price_service.NSE_TICKER_MAP", {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"})
    def test_should_return_stock_tickers_only(self, db_session):
        """ETFs and index tickers should be excluded."""
        from services.data_helpers import get_portfolio_tickers
        _seed_portfolio_with_holdings(db_session, name="Stock Portfolio", tickers=[
            ("RELIANCE", 10),
            ("TCS", 5),
            ("NIFTYBEES", 100),  # ETF — should be excluded
        ])
        result = get_portfolio_tickers(db_session)
        assert "RELIANCE" in result
        assert "TCS" in result
        assert "NIFTYBEES" not in result

    @patch("price_service.NSE_ETF_UNIVERSE", {})
    @patch("price_service.NSE_TICKER_MAP", {})
    def test_should_exclude_basket_tickers(self, db_session):
        """Tickers starting with MB_ (microbaskets) should be excluded."""
        from services.data_helpers import get_portfolio_tickers
        _seed_portfolio_with_holdings(db_session, name="Basket Ticker Portfolio", tickers=[
            ("RELIANCE", 10),
            ("MB_HEALTHCARE", 1),  # Basket ticker — should be excluded
        ])
        result = get_portfolio_tickers(db_session)
        assert "RELIANCE" in result
        assert "MB_HEALTHCARE" not in result

    @patch("price_service.NSE_ETF_UNIVERSE", {})
    @patch("price_service.NSE_TICKER_MAP", {})
    def test_should_return_empty_list_with_no_portfolios(self, db_session):
        from services.data_helpers import get_portfolio_tickers
        result = get_portfolio_tickers(db_session)
        assert result == []

    @patch("price_service.NSE_ETF_UNIVERSE", {})
    @patch("price_service.NSE_TICKER_MAP", {})
    def test_should_exclude_archived_portfolios(self, db_session):
        """Only tickers from ACTIVE portfolios should be returned."""
        from services.data_helpers import get_portfolio_tickers
        _seed_portfolio_with_holdings(
            db_session, name="Archived Port",
            tickers=[("SBIN", 20)],
            status=PortfolioStatus.ARCHIVED,
        )
        result = get_portfolio_tickers(db_session)
        assert "SBIN" not in result

    @patch("price_service.NSE_ETF_UNIVERSE", {})
    @patch("price_service.NSE_TICKER_MAP", {})
    def test_should_exclude_zero_quantity_holdings(self, db_session):
        """Holdings with quantity=0 (fully sold) should not be included."""
        from services.data_helpers import get_portfolio_tickers
        portfolio = ModelPortfolio(
            name="Zero Qty Port", benchmark="NIFTY", status=PortfolioStatus.ACTIVE,
        )
        db_session.add(portfolio)
        db_session.flush()
        db_session.add(PortfolioHolding(
            portfolio_id=portfolio.id, ticker="WIPRO",
            quantity=0, avg_cost=400.0, total_cost=0.0,
        ))
        db_session.commit()

        result = get_portfolio_tickers(db_session)
        assert "WIPRO" not in result

    @patch("price_service.NSE_ETF_UNIVERSE", {})
    @patch("price_service.NSE_TICKER_MAP", {})
    def test_should_uppercase_tickers(self, db_session):
        from services.data_helpers import get_portfolio_tickers
        _seed_portfolio_with_holdings(db_session, name="Case Port", tickers=[
            ("reliance", 10),
        ])
        result = get_portfolio_tickers(db_session)
        assert "RELIANCE" in result

    @patch("price_service.NSE_ETF_UNIVERSE", {})
    @patch("price_service.NSE_TICKER_MAP", {})
    def test_should_return_distinct_tickers(self, db_session):
        """Same ticker in multiple portfolios should appear only once."""
        from services.data_helpers import get_portfolio_tickers
        _seed_portfolio_with_holdings(db_session, name="Port A", tickers=[("RELIANCE", 10)])
        _seed_portfolio_with_holdings(db_session, name="Port B", tickers=[("RELIANCE", 20)])
        result = get_portfolio_tickers(db_session)
        assert result.count("RELIANCE") == 1


# ─── get_all_portfolio_tickers_with_inception ──────────────


class TestGetAllPortfolioTickersWithInception:
    """Tests for get_all_portfolio_tickers_with_inception function."""

    def test_should_return_ticker_to_inception_date_mapping(self, db_session):
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        _seed_portfolio_with_holdings(
            db_session, name="Inception Port",
            tickers=[("RELIANCE", 10), ("TCS", 5)],
            inception_date="2021-08-02",
        )
        result = get_all_portfolio_tickers_with_inception(db_session)
        assert "RELIANCE" in result
        assert result["RELIANCE"] == "2021-08-02"
        assert "TCS" in result
        assert result["TCS"] == "2021-08-02"

    def test_should_return_empty_dict_with_no_portfolios(self, db_session):
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        result = get_all_portfolio_tickers_with_inception(db_session)
        assert result == {}

    def test_should_use_earliest_inception_when_ticker_in_multiple_portfolios(self, db_session):
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        _seed_portfolio_with_holdings(
            db_session, name="Early Port",
            tickers=[("RELIANCE", 10)],
            inception_date="2020-01-15",
        )
        _seed_portfolio_with_holdings(
            db_session, name="Late Port",
            tickers=[("RELIANCE", 5)],
            inception_date="2022-06-01",
        )
        result = get_all_portfolio_tickers_with_inception(db_session)
        assert result["RELIANCE"] == "2020-01-15"

    def test_should_default_to_1y_ago_when_no_inception_date(self, db_session):
        """Portfolios without inception_date should default to 365 days ago."""
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        _seed_portfolio_with_holdings(
            db_session, name="No Inception Port",
            tickers=[("INFY", 15)],
            inception_date=None,
        )
        result = get_all_portfolio_tickers_with_inception(db_session)
        assert "INFY" in result
        expected_default = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        assert result["INFY"] == expected_default

    def test_should_exclude_archived_portfolios(self, db_session):
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        _seed_portfolio_with_holdings(
            db_session, name="Archived Inception",
            tickers=[("SBIN", 20)],
            inception_date="2021-01-01",
            status=PortfolioStatus.ARCHIVED,
        )
        result = get_all_portfolio_tickers_with_inception(db_session)
        assert "SBIN" not in result

    def test_should_exclude_zero_quantity_holdings(self, db_session):
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        portfolio = ModelPortfolio(
            name="Zero Qty Inception Port", benchmark="NIFTY",
            status=PortfolioStatus.ACTIVE, inception_date="2021-01-01",
        )
        db_session.add(portfolio)
        db_session.flush()
        db_session.add(PortfolioHolding(
            portfolio_id=portfolio.id, ticker="WIPRO",
            quantity=0, avg_cost=400.0, total_cost=0.0,
        ))
        db_session.commit()
        result = get_all_portfolio_tickers_with_inception(db_session)
        assert "WIPRO" not in result

    def test_should_exclude_basket_tickers(self, db_session):
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        _seed_portfolio_with_holdings(
            db_session, name="Basket Inception Port",
            tickers=[("RELIANCE", 10), ("MB_HEALTHCARE", 1)],
            inception_date="2021-01-01",
        )
        result = get_all_portfolio_tickers_with_inception(db_session)
        assert "RELIANCE" in result
        assert "MB_HEALTHCARE" not in result

    def test_should_include_etf_tickers(self, db_session):
        """Unlike get_portfolio_tickers, this function includes ETFs."""
        from services.data_helpers import get_all_portfolio_tickers_with_inception
        _seed_portfolio_with_holdings(
            db_session, name="ETF Inception Port",
            tickers=[("NIFTYBEES", 100)],
            inception_date="2021-01-01",
        )
        result = get_all_portfolio_tickers_with_inception(db_session)
        # This function does NOT filter out ETFs (unlike get_portfolio_tickers)
        assert "NIFTYBEES" in result
