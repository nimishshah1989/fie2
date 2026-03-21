"""
Tests for Sector Compass — RS engine, portfolio rules, and API router.
"""

import pytest
from datetime import datetime, timedelta

from models import (
    CompassAction,
    CompassETFPrice,
    CompassModelNAV,
    CompassModelState,
    CompassModelTrade,
    CompassQuadrant,
    CompassRSScore,
    CompassStockPrice,
    CompassVolumeSignal,
    IndexConstituent,
    IndexPrice,
)
from services.compass_rs import (
    _classify_quadrant,
    _compute_relative_return,
    _compute_volume_signal,
    _derive_action,
    _get_sector_category,
)


# ─── Unit Tests: RS Engine Core Functions ─────────────────


class TestClassifyQuadrant:
    def test_leading(self):
        assert _classify_quadrant(70, 10) == CompassQuadrant.LEADING

    def test_weakening(self):
        assert _classify_quadrant(60, -5) == CompassQuadrant.WEAKENING

    def test_improving(self):
        assert _classify_quadrant(30, 15) == CompassQuadrant.IMPROVING

    def test_lagging(self):
        assert _classify_quadrant(40, -10) == CompassQuadrant.LAGGING

    def test_boundary_score_50_momentum_0(self):
        # Score=50 and momentum=0 → LAGGING (≤50, ≤0)
        assert _classify_quadrant(50, 0) == CompassQuadrant.LAGGING

    def test_score_exactly_50_positive_momentum(self):
        assert _classify_quadrant(50, 5) == CompassQuadrant.IMPROVING

    def test_high_score_zero_momentum(self):
        assert _classify_quadrant(80, 0) == CompassQuadrant.WEAKENING


class TestDeriveAction:
    def test_leading_accumulation_is_buy(self):
        assert _derive_action(CompassQuadrant.LEADING, CompassVolumeSignal.ACCUMULATION) == CompassAction.BUY

    def test_leading_weak_rally_is_accumulate(self):
        assert _derive_action(CompassQuadrant.LEADING, CompassVolumeSignal.WEAK_RALLY) == CompassAction.ACCUMULATE

    def test_leading_no_volume_is_accumulate(self):
        assert _derive_action(CompassQuadrant.LEADING, None) == CompassAction.ACCUMULATE

    def test_improving_is_watch(self):
        assert _derive_action(CompassQuadrant.IMPROVING, CompassVolumeSignal.ACCUMULATION) == CompassAction.WATCH

    def test_weakening_distribution_is_sell(self):
        assert _derive_action(CompassQuadrant.WEAKENING, CompassVolumeSignal.DISTRIBUTION) == CompassAction.SELL

    def test_weakening_weak_decline_is_hold(self):
        assert _derive_action(CompassQuadrant.WEAKENING, CompassVolumeSignal.WEAK_DECLINE) == CompassAction.HOLD

    def test_weakening_no_volume_is_hold(self):
        assert _derive_action(CompassQuadrant.WEAKENING, None) == CompassAction.HOLD

    def test_lagging_is_avoid(self):
        assert _derive_action(CompassQuadrant.LAGGING, CompassVolumeSignal.DISTRIBUTION) == CompassAction.AVOID

    def test_lagging_no_volume_is_avoid(self):
        assert _derive_action(CompassQuadrant.LAGGING, None) == CompassAction.AVOID


class TestComputeRelativeReturn:
    def test_outperformance(self):
        # Asset doubles, benchmark flat → +100% excess
        asset = {f"2025-{i:02d}-01": 100 + i * 10 for i in range(1, 7)}
        bench = {f"2025-{i:02d}-01": 100 for i in range(1, 7)}
        result = _compute_relative_return(asset, bench, period_days=5)
        assert result is not None
        assert result > 0

    def test_underperformance(self):
        # Asset flat, benchmark rises → negative excess
        asset = {f"2025-{i:02d}-01": 100 for i in range(1, 7)}
        bench = {f"2025-{i:02d}-01": 100 + i * 10 for i in range(1, 7)}
        result = _compute_relative_return(asset, bench, period_days=5)
        assert result is not None
        assert result < 0

    def test_equal_performance(self):
        dates = {f"2025-{i:02d}-01": 100 + i * 5 for i in range(1, 7)}
        result = _compute_relative_return(dates, dates, period_days=5)
        assert result is not None
        assert abs(result) < 0.01

    def test_insufficient_data(self):
        asset = {"2025-01-01": 100}
        bench = {"2025-01-01": 100}
        result = _compute_relative_return(asset, bench, period_days=63)
        assert result is None

    def test_zero_starting_price(self):
        # When both start at 0, the function returns None due to zero division guard
        asset = {"2025-01-01": 0, "2025-02-01": 0, "2025-06-01": 100}
        bench = {"2025-01-01": 0, "2025-02-01": 0, "2025-06-01": 110}
        result = _compute_relative_return(asset, bench, period_days=2)
        assert result is None


class TestComputeVolumeSignal:
    def _make_series(self, prices: list, volumes: list) -> list[dict]:
        return [
            {"date": f"2025-01-{i+1:02d}", "close": p, "volume": v}
            for i, (p, v) in enumerate(zip(prices, volumes))
        ]

    def test_accumulation(self):
        # Price rising + volume rising (recent > older)
        prices = [100 + i * 0.5 for i in range(70)]
        volumes = [1000] * 40 + [2000] * 30  # recent volume higher
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result == CompassVolumeSignal.ACCUMULATION

    def test_distribution(self):
        # Price falling + volume rising
        prices = [200 - i * 0.5 for i in range(70)]
        volumes = [1000] * 40 + [2000] * 30
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result == CompassVolumeSignal.DISTRIBUTION

    def test_weak_rally(self):
        # Price rising + volume falling
        prices = [100 + i * 0.5 for i in range(70)]
        volumes = [2000] * 40 + [1000] * 30
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result == CompassVolumeSignal.WEAK_RALLY

    def test_weak_decline(self):
        # Price falling + volume falling
        prices = [200 - i * 0.5 for i in range(70)]
        volumes = [2000] * 40 + [1000] * 30
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result == CompassVolumeSignal.WEAK_DECLINE

    def test_insufficient_data(self):
        series = [{"date": "2025-01-01", "close": 100, "volume": 1000}] * 10
        result = _compute_volume_signal(series)
        assert result is None

    def test_none_volumes_handled(self):
        prices = [100 + i for i in range(70)]
        volumes = [None] * 70
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result is None


class TestGetSectorCategory:
    def test_sectoral(self):
        assert _get_sector_category("BANKNIFTY") == "sectoral"

    def test_thematic(self):
        assert _get_sector_category("NIFTYHEALTHCARE") == "thematic"

    def test_unknown_defaults_thematic(self):
        assert _get_sector_category("UNKNOWN_INDEX") == "thematic"


# ─── Integration Tests: DB + API ──────────────────────────


def _seed_index_prices(db, index_name: str, days: int = 100, start_price: float = 100):
    """Seed IndexPrice data for testing."""
    base_date = datetime.now() - timedelta(days=days)
    for i in range(days):
        date = base_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        price = start_price + i * 0.5
        db.add(IndexPrice(
            date=date_str,
            index_name=index_name,
            close_price=price,
            open_price=price - 1,
            high_price=price + 1,
            low_price=price - 2,
            volume=100000 + i * 1000,
        ))
    db.commit()


def _seed_stock_prices(db, ticker: str, days: int = 100, start_price: float = 50):
    """Seed CompassStockPrice data for testing."""
    base_date = datetime.now() - timedelta(days=days)
    for i in range(days):
        date = base_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        price = start_price + i * 0.3
        db.add(CompassStockPrice(
            date=date_str,
            ticker=ticker,
            close=price,
            open=price - 0.5,
            high=price + 0.5,
            low=price - 1,
            volume=50000 + i * 500,
        ))
    db.commit()


def _seed_etf_prices(db, ticker: str, days: int = 100, start_price: float = 30):
    """Seed CompassETFPrice data for testing."""
    base_date = datetime.now() - timedelta(days=days)
    for i in range(days):
        date = base_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        price = start_price + i * 0.2
        db.add(CompassETFPrice(
            date=date_str,
            ticker=ticker,
            close=price,
            open=price - 0.3,
            high=price + 0.3,
            low=price - 0.5,
            volume=20000 + i * 200,
        ))
    db.commit()


class TestCompassModels:
    def test_compass_stock_price_creation(self, db_session):
        db_session.add(CompassStockPrice(
            date="2025-01-01", ticker="TCS", close=3800.0, volume=100000,
        ))
        db_session.commit()
        row = db_session.query(CompassStockPrice).filter_by(ticker="TCS").first()
        assert row is not None
        assert row.close == 3800.0

    def test_compass_etf_price_creation(self, db_session):
        db_session.add(CompassETFPrice(
            date="2025-01-01", ticker="ITBEES", close=38.5, volume=50000,
        ))
        db_session.commit()
        row = db_session.query(CompassETFPrice).filter_by(ticker="ITBEES").first()
        assert row is not None
        assert row.close == 38.5

    def test_compass_rs_score_creation(self, db_session):
        db_session.add(CompassRSScore(
            date="2025-01-01",
            instrument_id="NIFTYIT",
            instrument_type="index",
            rs_score=72.5,
            rs_momentum=14.2,
            quadrant=CompassQuadrant.LEADING,
            action=CompassAction.BUY,
            volume_signal=CompassVolumeSignal.ACCUMULATION,
        ))
        db_session.commit()
        row = db_session.query(CompassRSScore).filter_by(instrument_id="NIFTYIT").first()
        assert row.rs_score == 72.5
        assert row.quadrant == CompassQuadrant.LEADING
        assert row.action == CompassAction.BUY

    def test_compass_model_state(self, db_session):
        db_session.add(CompassModelState(
            sector_key="NIFTYIT",
            instrument_id="ITBEES",
            instrument_type="etf",
            entry_date="2025-01-15",
            entry_price=38.5,
            stop_loss=35.42,
            status="OPEN",
        ))
        db_session.commit()
        row = db_session.query(CompassModelState).filter_by(sector_key="NIFTYIT").first()
        assert row.status == "OPEN"
        assert row.stop_loss == 35.42

    def test_compass_model_trade(self, db_session):
        db_session.add(CompassModelTrade(
            trade_date="2025-01-15",
            sector_key="NIFTYIT",
            instrument_id="ITBEES",
            instrument_type="etf",
            side="BUY",
            price=38.5,
            reason="LEADING+ACCUMULATION",
            quadrant=CompassQuadrant.LEADING,
        ))
        db_session.commit()
        row = db_session.query(CompassModelTrade).first()
        assert row.side == "BUY"
        assert row.quadrant == CompassQuadrant.LEADING

    def test_compass_model_nav(self, db_session):
        db_session.add(CompassModelNAV(
            date="2025-01-15",
            nav=102.5,
            benchmark_nav=101.2,
            num_positions=3,
        ))
        db_session.commit()
        row = db_session.query(CompassModelNAV).first()
        assert row.nav == 102.5


class TestCompassAPI:
    def test_sectors_endpoint(self, client):
        resp = client.get("/api/compass/sectors?base=NIFTY&period=3M")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_sectors_invalid_period(self, client):
        resp = client.get("/api/compass/sectors?period=2M")
        assert resp.status_code == 400

    def test_stocks_endpoint_404(self, client):
        resp = client.get("/api/compass/sectors/FAKESECTOR/stocks?period=3M")
        assert resp.status_code == 404

    def test_etfs_endpoint(self, client):
        resp = client.get("/api/compass/etfs?base=NIFTY&period=3M")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_model_portfolio_endpoint(self, client):
        resp = client.get("/api/compass/model-portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert "positions" in data
        assert "max_positions" in data

    def test_model_trades_endpoint(self, client):
        resp = client.get("/api/compass/model-portfolio/trades")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_model_nav_endpoint(self, client):
        resp = client.get("/api/compass/model-portfolio/nav")
        assert resp.status_code == 200

    def test_model_performance_endpoint(self, client):
        resp = client.get("/api/compass/model-portfolio/performance")
        assert resp.status_code == 200

    def test_history_endpoint(self, client):
        resp = client.get("/api/compass/history/NIFTYIT?instrument_type=index")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_refresh_endpoint(self, client):
        resp = client.post("/api/compass/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert "sectors_computed" in data


class TestCompassPortfolioRules:
    def test_empty_portfolio_state(self, db_session):
        from services.compass_portfolio import get_model_portfolio_state
        state = get_model_portfolio_state(db_session)
        assert state["num_open"] == 0
        assert state["positions"] == []
        assert state["max_positions"] == 6

    def test_empty_trade_history(self, db_session):
        from services.compass_portfolio import get_trade_history
        trades = get_trade_history(db_session)
        assert trades == []

    def test_no_data_performance(self, db_session):
        from services.compass_portfolio import get_performance_metrics
        metrics = get_performance_metrics(db_session)
        assert metrics["status"] == "no_data"

    def test_rebalance_no_data(self, db_session):
        from services.compass_portfolio import run_weekly_rebalance
        result = run_weekly_rebalance(db_session, [])
        assert result["entries"] == []
        assert result["exits"] == []

    def test_rebalance_with_buy_signal(self, db_session):
        from services.compass_portfolio import run_weekly_rebalance

        # Seed ETF price so entry can get a price
        _seed_etf_prices(db_session, "ITBEES", days=10)

        scores = [{
            "sector_key": "NIFTYIT",
            "display_name": "NIFTY IT",
            "rs_score": 75,
            "rs_momentum": 12,
            "relative_return": 5.2,
            "volume_signal": "ACCUMULATION",
            "quadrant": "LEADING",
            "action": "BUY",
            "etfs": ["ITBEES"],
            "category": "sectoral",
        }]
        result = run_weekly_rebalance(db_session, scores)
        assert len(result["entries"]) == 1
        assert result["entries"][0]["sector"] == "NIFTYIT"

        # Verify position was created
        pos = db_session.query(CompassModelState).filter_by(sector_key="NIFTYIT").first()
        assert pos is not None
        assert pos.status == "OPEN"
        assert pos.instrument_id == "ITBEES"

    def test_max_positions_respected(self, db_session):
        from services.compass_portfolio import run_weekly_rebalance

        # Fill 6 positions
        for i in range(6):
            db_session.add(CompassModelState(
                sector_key=f"SECTOR{i}",
                instrument_id=f"ETF{i}",
                instrument_type="etf",
                entry_date="2025-01-01",
                entry_price=100,
                status="OPEN",
            ))
        db_session.commit()

        scores = [{
            "sector_key": "NEWSECTOR",
            "rs_score": 90,
            "rs_momentum": 20,
            "quadrant": "LEADING",
            "action": "BUY",
            "etfs": ["NEWETF"],
            "volume_signal": "ACCUMULATION",
        }]
        result = run_weekly_rebalance(db_session, scores)
        assert len(result["entries"]) == 0  # no room


class TestCompassRSComputation:
    def test_sector_scores_with_data(self, db_session):
        from services.compass_rs import compute_sector_rs_scores

        # Seed NIFTY benchmark
        _seed_index_prices(db_session, "NIFTY", days=100, start_price=22000)

        # Seed a few sector indices
        _seed_index_prices(db_session, "NIFTYIT", days=100, start_price=33000)
        _seed_index_prices(db_session, "BANKNIFTY", days=100, start_price=48000)
        _seed_index_prices(db_session, "NIFTYPHARMA", days=100, start_price=16000)

        # Seed ETF data for volume signal
        _seed_etf_prices(db_session, "ITBEES", days=100)
        _seed_etf_prices(db_session, "BANKBEES", days=100)

        scores = compute_sector_rs_scores(db_session, base_index="NIFTY", period_key="1M")
        # Should get scores for tracked sectors that have data
        assert len(scores) >= 3

        for s in scores:
            assert 0 <= s["rs_score"] <= 100
            assert s["quadrant"] in ("LEADING", "WEAKENING", "IMPROVING", "LAGGING")
            assert s["action"] in ("BUY", "ACCUMULATE", "WATCH", "HOLD", "SELL", "AVOID")

    def test_stock_scores_with_data(self, db_session):
        from services.compass_rs import compute_stock_rs_scores

        # Seed sector index
        _seed_index_prices(db_session, "NIFTYIT", days=100, start_price=33000)

        # Seed constituents
        db_session.add(IndexConstituent(index_name="NIFTY IT", ticker="TCS", company_name="TCS Ltd"))
        db_session.add(IndexConstituent(index_name="NIFTY IT", ticker="INFY", company_name="Infosys Ltd"))
        db_session.commit()

        # Seed stock prices
        _seed_stock_prices(db_session, "TCS", days=100, start_price=3500)
        _seed_stock_prices(db_session, "INFY", days=100, start_price=1400)

        scores = compute_stock_rs_scores(db_session, sector_key="NIFTYIT", period_key="1M")
        assert len(scores) == 2
        for s in scores:
            assert "ticker" in s
            assert "rs_score" in s
            assert "quadrant" in s
            assert "action" in s

    def test_persist_rs_scores(self, db_session):
        from services.compass_rs import persist_rs_scores

        scores = [
            {
                "sector_key": "NIFTYIT",
                "rs_score": 72,
                "rs_momentum": 14,
                "volume_signal": "ACCUMULATION",
                "quadrant": "LEADING",
                "action": "BUY",
                "relative_return": 5.2,
            }
        ]
        count = persist_rs_scores(db_session, scores, instrument_type="index", date_str="2025-06-01")
        assert count == 1

        row = db_session.query(CompassRSScore).filter_by(instrument_id="NIFTYIT").first()
        assert row is not None
        assert row.rs_score == 72
        assert row.quadrant == CompassQuadrant.LEADING
