"""
Tests for Sector Compass — Gate-based RS engine, portfolio rules, and API router.
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
    _classify_pe_zone,
    _compute_relative_return,
    _compute_volume_signal,
    _derive_action_gate,
    _get_sector_category,
)


# ─── Unit Tests: RS Engine Core Functions ─────────────────


class TestClassifyQuadrant:
    """RS Score is a ratio centered at 0 (not percentile 0-100).
    Positive = outperforming benchmark. Quadrant threshold is 0, not 50."""

    def test_leading(self):
        assert _classify_quadrant(5.2, 2.1) == CompassQuadrant.LEADING

    def test_weakening(self):
        assert _classify_quadrant(3.5, -1.8) == CompassQuadrant.WEAKENING

    def test_improving(self):
        assert _classify_quadrant(-2.0, 4.5) == CompassQuadrant.IMPROVING

    def test_lagging(self):
        assert _classify_quadrant(-5.0, -3.0) == CompassQuadrant.LAGGING

    def test_boundary_zero_zero(self):
        assert _classify_quadrant(0, 0) == CompassQuadrant.LAGGING

    def test_zero_score_positive_momentum(self):
        assert _classify_quadrant(0, 5) == CompassQuadrant.IMPROVING

    def test_positive_score_zero_momentum(self):
        assert _classify_quadrant(3.0, 0) == CompassQuadrant.WEAKENING


class TestDeriveActionGate:
    """Gate-based decision engine: 3 binary gates → deterministic actions."""

    # ── All 8 gate combinations ──────────────────────

    def test_all_pass_is_buy(self):
        """G1✓ G2✓ G3✓ → BUY"""
        action, reason = _derive_action_gate(
            absolute_return=5.0, rs_score=3.0, momentum=2.0,
            volume_signal=CompassVolumeSignal.ACCUMULATION,
            market_regime={"regime": "BULL"},
        )
        assert action == CompassAction.BUY
        assert "Rising" in reason

    def test_rising_outperforming_fading_is_hold(self):
        """G1✓ G2✓ G3✗ → HOLD"""
        action, _ = _derive_action_gate(
            absolute_return=3.0, rs_score=2.0, momentum=-1.0,
            volume_signal=None, market_regime={"regime": "BULL"},
        )
        assert action == CompassAction.HOLD

    def test_rising_lagging_strengthening_is_watch_emerging(self):
        """G1✓ G2✗ G3✓ → WATCH_EMERGING"""
        action, reason = _derive_action_gate(
            absolute_return=4.0, rs_score=-2.0, momentum=3.0,
            volume_signal=None, market_regime={"regime": "BULL"},
        )
        assert action == CompassAction.WATCH_EMERGING
        assert "RS crossing" in reason

    def test_rising_lagging_fading_is_avoid(self):
        """G1✓ G2✗ G3✗ → AVOID"""
        action, _ = _derive_action_gate(
            absolute_return=2.0, rs_score=-3.0, momentum=-1.0,
            volume_signal=None, market_regime={"regime": "BULL"},
        )
        assert action == CompassAction.AVOID

    def test_falling_outperforming_strengthening_is_watch_relative(self):
        """G1✗ G2✓ G3✓ → WATCH_RELATIVE"""
        action, reason = _derive_action_gate(
            absolute_return=-2.0, rs_score=5.0, momentum=2.0,
            volume_signal=None, market_regime={"regime": "CORRECTION"},
        )
        assert action == CompassAction.WATCH_RELATIVE
        assert "absolute return" in reason.lower()

    def test_falling_outperforming_fading_is_sell(self):
        """G1✗ G2✓ G3✗ → SELL"""
        action, _ = _derive_action_gate(
            absolute_return=-5.0, rs_score=2.0, momentum=-3.0,
            volume_signal=None, market_regime={"regime": "CORRECTION"},
        )
        assert action == CompassAction.SELL

    def test_falling_lagging_strengthening_is_watch_early(self):
        """G1✗ G2✗ G3✓ → WATCH_EARLY"""
        action, reason = _derive_action_gate(
            absolute_return=-3.0, rs_score=-2.0, momentum=1.5,
            volume_signal=None, market_regime={"regime": "BEAR"},
        )
        assert action == CompassAction.WATCH_EARLY
        assert "early" in reason.lower() or "Early" in reason

    def test_all_fail_is_sell(self):
        """G1✗ G2✗ G3✗ → SELL"""
        action, reason = _derive_action_gate(
            absolute_return=-8.0, rs_score=-5.0, momentum=-3.0,
            volume_signal=CompassVolumeSignal.DISTRIBUTION,
            market_regime={"regime": "BEAR"},
        )
        assert action == CompassAction.SELL
        assert "Falling" in reason

    # ── Volume overrides ─────────────────────────────

    def test_distribution_downgrades_buy_to_hold(self):
        """BUY + DISTRIBUTION volume → HOLD (smart money selling)"""
        action, reason = _derive_action_gate(
            absolute_return=5.0, rs_score=3.0, momentum=2.0,
            volume_signal=CompassVolumeSignal.DISTRIBUTION,
            market_regime={"regime": "BULL"},
        )
        assert action == CompassAction.HOLD
        assert "smart money" in reason.lower() or "distribution" in reason.lower()

    def test_accumulation_on_watch_adds_note(self):
        """WATCH + ACCUMULATION volume → still WATCH but reason mentions accumulation"""
        action, reason = _derive_action_gate(
            absolute_return=4.0, rs_score=-2.0, momentum=3.0,
            volume_signal=CompassVolumeSignal.ACCUMULATION,
            market_regime={"regime": "BULL"},
        )
        assert action == CompassAction.WATCH_EMERGING
        assert "accumulation" in reason.lower()

    # ── Market regime overrides ──────────────────────

    def test_bear_caps_buy_to_hold(self):
        """All gates pass but BEAR regime → HOLD"""
        action, reason = _derive_action_gate(
            absolute_return=5.0, rs_score=3.0, momentum=2.0,
            volume_signal=CompassVolumeSignal.ACCUMULATION,
            market_regime={"regime": "BEAR"},
        )
        assert action == CompassAction.HOLD
        assert "BEAR" in reason

    def test_correction_with_weak_volume_caps_buy(self):
        """All gates pass but CORRECTION + WEAK_RALLY → HOLD"""
        action, reason = _derive_action_gate(
            absolute_return=5.0, rs_score=3.0, momentum=2.0,
            volume_signal=CompassVolumeSignal.WEAK_RALLY,
            market_regime={"regime": "CORRECTION"},
        )
        assert action == CompassAction.HOLD
        assert "CORRECTION" in reason

    def test_correction_with_accumulation_allows_buy(self):
        """All gates pass + CORRECTION + ACCUMULATION → BUY allowed"""
        action, _ = _derive_action_gate(
            absolute_return=5.0, rs_score=3.0, momentum=2.0,
            volume_signal=CompassVolumeSignal.ACCUMULATION,
            market_regime={"regime": "CORRECTION"},
        )
        assert action == CompassAction.BUY

    def test_bull_regime_no_override(self):
        """BULL regime doesn't modify any action"""
        action, _ = _derive_action_gate(
            absolute_return=5.0, rs_score=3.0, momentum=2.0,
            volume_signal=None,
            market_regime={"regime": "BULL"},
        )
        assert action == CompassAction.BUY


class TestClassifyPEZone:
    def test_value(self):
        assert _classify_pe_zone(12.0) == "VALUE"

    def test_fair(self):
        assert _classify_pe_zone(20.0) == "FAIR"

    def test_stretched(self):
        assert _classify_pe_zone(30.0) == "STRETCHED"

    def test_expensive(self):
        assert _classify_pe_zone(50.0) == "EXPENSIVE"

    def test_none(self):
        assert _classify_pe_zone(None) is None

    def test_boundary_15(self):
        assert _classify_pe_zone(15.0) == "FAIR"

    def test_boundary_25(self):
        assert _classify_pe_zone(25.0) == "STRETCHED"

    def test_boundary_40(self):
        assert _classify_pe_zone(40.0) == "EXPENSIVE"


class TestComputeRelativeReturn:
    def test_outperformance(self):
        asset = {f"2025-{i:02d}-01": 100 + i * 10 for i in range(1, 7)}
        bench = {f"2025-{i:02d}-01": 100 for i in range(1, 7)}
        result = _compute_relative_return(asset, bench, period_days=5)
        assert result is not None
        assert result > 0

    def test_underperformance(self):
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
        prices = [100 + i * 0.5 for i in range(70)]
        volumes = [1000] * 40 + [2000] * 30
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result == CompassVolumeSignal.ACCUMULATION

    def test_distribution(self):
        prices = [200 - i * 0.5 for i in range(70)]
        volumes = [1000] * 40 + [2000] * 30
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result == CompassVolumeSignal.DISTRIBUTION

    def test_weak_rally(self):
        prices = [100 + i * 0.5 for i in range(70)]
        volumes = [2000] * 40 + [1000] * 30
        series = self._make_series(prices, volumes)
        result = _compute_volume_signal(series)
        assert result == CompassVolumeSignal.WEAK_RALLY

    def test_weak_decline(self):
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
        metrics = get_performance_metrics(db_session, portfolio_type="etf_only")
        assert metrics["status"] == "no_data"

    def test_rebalance_no_data(self, db_session):
        from services.compass_portfolio import run_weekly_rebalance
        result = run_weekly_rebalance(db_session, [])
        assert result["etf_only"]["entries"] == []
        assert result["etf_only"]["exits"] == []

    def test_rebalance_with_buy_signal(self, db_session):
        from services.compass_portfolio import run_weekly_rebalance

        _seed_etf_prices(db_session, "ITBEES", days=10)

        scores = [{
            "sector_key": "NIFTYIT",
            "display_name": "NIFTY IT",
            "rs_score": 5.2,
            "rs_momentum": 2.1,
            "relative_return": 5.2,
            "volume_signal": "ACCUMULATION",
            "quadrant": "LEADING",
            "action": "BUY",
            "etfs": ["ITBEES"],
            "category": "sectoral",
        }]
        result = run_weekly_rebalance(db_session, scores)
        etf_result = result["etf_only"]
        assert len(etf_result["entries"]) == 1
        assert etf_result["entries"][0]["sector"] == "NIFTYIT"

        pos = db_session.query(CompassModelState).filter_by(
            sector_key="NIFTYIT", portfolio_type="etf_only"
        ).first()
        assert pos is not None
        assert pos.status == "OPEN"
        assert pos.instrument_id == "ITBEES"

    def test_max_positions_respected(self, db_session):
        from services.compass_portfolio import run_weekly_rebalance

        for i in range(6):
            db_session.add(CompassModelState(
                portfolio_type="etf_only",
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
            "rs_score": 8.5,
            "rs_momentum": 3.0,
            "quadrant": "LEADING",
            "action": "BUY",
            "etfs": ["NEWETF"],
            "volume_signal": "ACCUMULATION",
        }]
        result = run_weekly_rebalance(db_session, scores)
        assert len(result["etf_only"]["entries"]) == 0


class TestCompassRSComputation:
    def test_sector_scores_with_data(self, db_session):
        from services.compass_rs import compute_sector_rs_scores

        _seed_index_prices(db_session, "NIFTY", days=100, start_price=22000)
        _seed_index_prices(db_session, "NIFTYIT", days=100, start_price=33000)
        _seed_index_prices(db_session, "BANKNIFTY", days=100, start_price=48000)
        _seed_index_prices(db_session, "NIFTYPHARMA", days=100, start_price=16000)
        _seed_etf_prices(db_session, "ITBEES", days=100)
        _seed_etf_prices(db_session, "BANKBEES", days=100)

        scores = compute_sector_rs_scores(db_session, base_index="NIFTY", period_key="1M")
        assert len(scores) >= 3

        valid_actions = {a.value for a in CompassAction}
        for s in scores:
            assert isinstance(s["rs_score"], float)
            assert s["quadrant"] in ("LEADING", "WEAKENING", "IMPROVING", "LAGGING")
            assert s["action"] in valid_actions
            assert "action_reason" in s

    def test_stock_scores_with_data(self, db_session):
        from services.compass_rs import compute_stock_rs_scores

        _seed_index_prices(db_session, "NIFTYIT", days=100, start_price=33000)

        db_session.add(IndexConstituent(index_name="NIFTY IT", ticker="TCS", company_name="TCS Ltd"))
        db_session.add(IndexConstituent(index_name="NIFTY IT", ticker="INFY", company_name="Infosys Ltd"))
        db_session.commit()

        _seed_stock_prices(db_session, "TCS", days=100, start_price=3500)
        _seed_stock_prices(db_session, "INFY", days=100, start_price=1400)

        scores = compute_stock_rs_scores(db_session, sector_key="NIFTYIT", period_key="1M")
        assert len(scores) == 2
        for s in scores:
            assert "ticker" in s
            assert "rs_score" in s
            assert "quadrant" in s
            assert "action" in s
            assert "action_reason" in s

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
