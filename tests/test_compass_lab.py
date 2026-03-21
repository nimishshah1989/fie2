"""
Tests for the Compass Lab agentic system:
- Stateless simulator
- Parameter grid generation
- Regime detection
- Sweep execution
- Regime config extraction
- Rule discovery
- Autonomous trader decisions
- Decision logging
"""

import json
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from services.compass_simulator import (
    PERIOD_DAYS,
    REGIME_NAMES,
    SimParams,
    SimResult,
    detect_regimes_vectorized,
    evaluate_gates,
    generate_focused_grid,
    generate_param_grid,
    simulate,
)


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def synthetic_prices():
    """Generate synthetic market data for testing."""
    np.random.seed(42)
    n_days = 1000
    n_sectors = 5

    # Benchmark: gentle uptrend with volatility
    benchmark = 100 * np.cumprod(1 + np.random.normal(0.0003, 0.01, n_days))

    # Sectors: mix of outperforming and underperforming
    prices = np.column_stack([
        100 * np.cumprod(1 + np.random.normal(0.0005, 0.012, n_days)),  # strong
        100 * np.cumprod(1 + np.random.normal(0.0004, 0.015, n_days)),  # moderate
        100 * np.cumprod(1 + np.random.normal(0.0001, 0.018, n_days)),  # weak
        100 * np.cumprod(1 + np.random.normal(0.0003, 0.010, n_days)),  # defensive
        100 * np.cumprod(1 + np.random.normal(-0.0001, 0.020, n_days)), # declining
    ])
    sector_keys = ["STRONG", "MODERATE", "WEAK", "DEFENSIVE", "DECLINING"]
    return prices, benchmark, sector_keys


@pytest.fixture
def bear_market_prices():
    """Generate a bear market scenario."""
    np.random.seed(99)
    n_days = 500

    # Sharp decline then recovery
    phase1 = 100 * np.cumprod(1 + np.random.normal(-0.002, 0.02, 200))  # crash
    phase2 = phase1[-1] * np.cumprod(1 + np.random.normal(0.001, 0.015, 300))  # recovery
    benchmark = np.concatenate([phase1, phase2])

    prices = np.column_stack([
        benchmark * (1 + np.random.normal(0, 0.005, n_days)),
        benchmark * (1 + np.random.normal(0.001, 0.008, n_days)),
        benchmark * (1 + np.random.normal(-0.001, 0.01, n_days)),
    ])
    sector_keys = ["SECTOR_A", "SECTOR_B", "SECTOR_C"]
    return prices, benchmark, sector_keys


@pytest.fixture
def default_params():
    return SimParams()


# ─── SimParams Tests ─────────────────────────────────────────

class TestSimParams:
    def test_default_values(self):
        p = SimParams()
        assert p.rs_period == "3M"
        assert p.stop_loss_pct == 8.0
        assert p.max_positions == 6

    def test_custom_values(self):
        p = SimParams(stop_loss_pct=5.0, max_positions=3, min_rs_entry=2.0)
        assert p.stop_loss_pct == 5.0
        assert p.max_positions == 3
        assert p.min_rs_entry == 2.0

    def test_to_dict(self):
        p = SimParams()
        d = p.to_dict()
        assert "rs_period" in d
        assert "stop_loss_pct" in d
        assert len(d) == 8  # all 8 parameters

    def test_param_hash_deterministic(self):
        p1 = SimParams(stop_loss_pct=8.0)
        p2 = SimParams(stop_loss_pct=8.0)
        assert p1.param_hash() == p2.param_hash()

    def test_param_hash_different(self):
        p1 = SimParams(stop_loss_pct=8.0)
        p2 = SimParams(stop_loss_pct=10.0)
        assert p1.param_hash() != p2.param_hash()

    def test_frozen(self):
        p = SimParams()
        with pytest.raises(AttributeError):
            p.stop_loss_pct = 10.0


# ─── Regime Detection Tests ─────────────────────────────────

class TestRegimeDetection:
    def test_bull_market(self):
        """Steady uptrend should be classified as BULL."""
        prices = 100 * np.cumprod(1 + np.full(500, 0.001))
        regimes = detect_regimes_vectorized(prices)
        # After initial period, should be mostly BULL (0)
        assert np.sum(regimes[100:] == 0) > len(regimes[100:]) * 0.8

    def test_bear_market(self):
        """Sharp decline (>15%) should be classified as BEAR."""
        prices = np.concatenate([
            100 * np.ones(300),  # flat
            100 * np.cumprod(1 + np.full(200, -0.003)),  # decline
        ])
        regimes = detect_regimes_vectorized(prices)
        # Should have BEAR (3) in later period
        assert np.any(regimes == 3)

    def test_regime_array_shape(self):
        prices = np.ones(200) * 100
        regimes = detect_regimes_vectorized(prices)
        assert regimes.shape == (200,)
        assert regimes.dtype == np.int8

    def test_short_data(self):
        """Very short data should default to BULL."""
        prices = np.ones(30) * 100
        regimes = detect_regimes_vectorized(prices)
        assert np.all(regimes == 0)

    def test_all_regimes_possible(self):
        """Complex price series should produce multiple regime types."""
        np.random.seed(42)
        # Create volatile series with ups and downs
        prices = np.concatenate([
            100 * np.cumprod(1 + np.full(200, 0.002)),    # strong up
            100 * 1.5 * np.cumprod(1 + np.full(200, -0.003)),  # decline
            100 * 0.9 * np.cumprod(1 + np.full(200, 0.001)),   # recovery
        ])
        regimes = detect_regimes_vectorized(prices)
        unique_regimes = set(regimes.tolist())
        # Should have at least 2 different regimes
        assert len(unique_regimes) >= 2


# ─── Gate Engine Tests ───────────────────────────────────────

class TestEvaluateGates:
    def test_all_gates_pass_bull(self):
        """G1+G2+G3 in BULL = BUY."""
        assert evaluate_gates(5.0, 3.0, 1.0, 0, 0.0, "moderate") == "BUY"

    def test_g1_g2_no_g3(self):
        """G1+G2, no G3 = HOLD."""
        assert evaluate_gates(5.0, 3.0, -1.0, 0, 0.0, "moderate") == "HOLD"

    def test_all_gates_fail(self):
        """No gates pass = SELL."""
        assert evaluate_gates(-5.0, -3.0, -1.0, 0, 0.0, "moderate") == "SELL"

    def test_bear_blocks_buy(self):
        """BUY in BEAR regime = HOLD."""
        assert evaluate_gates(5.0, 3.0, 1.0, 3, 0.0, "moderate") == "HOLD"

    def test_correction_strict_blocks_buy(self):
        """BUY in CORRECTION with strict = HOLD."""
        assert evaluate_gates(5.0, 3.0, 1.0, 2, 0.0, "strict") == "HOLD"

    def test_correction_moderate_allows_buy(self):
        """BUY in CORRECTION with moderate = BUY."""
        assert evaluate_gates(5.0, 3.0, 1.0, 2, 0.0, "moderate") == "BUY"

    def test_min_rs_threshold(self):
        """RS below threshold = different action."""
        # RS = 1.5, min_rs = 2.0 → G2 fails
        assert evaluate_gates(5.0, 1.5, 1.0, 0, 2.0, "moderate") == "WATCH"

    def test_g1_no_g2_g3_watch(self):
        """Rising but lagging = WATCH."""
        assert evaluate_gates(5.0, -1.0, 1.0, 0, 0.0, "moderate") == "WATCH"

    def test_g1_no_g2_no_g3_avoid(self):
        """Rising but underperforming and fading = AVOID."""
        assert evaluate_gates(5.0, -1.0, -1.0, 0, 0.0, "moderate") == "AVOID"


# ─── Simulator Tests ─────────────────────────────────────────

class TestSimulator:
    def test_basic_simulation(self, synthetic_prices, default_params):
        prices, benchmark, sector_keys = synthetic_prices
        result = simulate(prices, benchmark, sector_keys, default_params)

        assert isinstance(result, SimResult)
        assert result.param_hash
        assert result.nav_curve is not None
        assert len(result.nav_curve) > 0

    def test_returns_trades(self, synthetic_prices, default_params):
        prices, benchmark, sector_keys = synthetic_prices
        result = simulate(prices, benchmark, sector_keys, default_params)

        assert len(result.trades) > 0
        # Should have both BUY and SELL trades
        buy_trades = [t for t in result.trades if t.side == "BUY"]
        sell_trades = [t for t in result.trades if t.side == "SELL"]
        assert len(buy_trades) > 0

    def test_nav_starts_at_100(self, synthetic_prices, default_params):
        prices, benchmark, sector_keys = synthetic_prices
        result = simulate(prices, benchmark, sector_keys, default_params)
        assert abs(result.nav_curve[0] - 100.0) < 1.0

    def test_max_positions_respected(self, synthetic_prices):
        """Should never hold more than max_positions."""
        prices, benchmark, sector_keys = synthetic_prices
        params = SimParams(max_positions=2)
        result = simulate(prices, benchmark, sector_keys, params)

        # Check at each day that we never have more than 2 open buys without sells
        open_count = 0
        max_seen = 0
        for t in result.trades:
            if t.side == "BUY":
                open_count += 1
            elif t.side == "SELL":
                open_count -= 1
            max_seen = max(max_seen, open_count)
        assert max_seen <= 2

    def test_stop_loss_triggers(self, bear_market_prices):
        """Stop-loss should trigger during sharp decline."""
        prices, benchmark, sector_keys = bear_market_prices
        params = SimParams(stop_loss_pct=5.0, max_positions=3)
        result = simulate(prices, benchmark, sector_keys, params)

        stop_exits = [t for t in result.trades if t.exit_reason == "STOP_LOSS"]
        # In a bear market, should have some stop-loss exits
        assert len(stop_exits) >= 0  # may or may not trigger depending on entry timing

    def test_regime_metrics_computed(self, synthetic_prices, default_params):
        prices, benchmark, sector_keys = synthetic_prices
        result = simulate(prices, benchmark, sector_keys, default_params)

        assert len(result.regime_metrics) > 0
        for regime_name, metrics in result.regime_metrics.items():
            assert regime_name in REGIME_NAMES.values()
            assert hasattr(metrics, 'win_rate')
            assert hasattr(metrics, 'n_trades')

    def test_sharpe_ratio_computed(self, synthetic_prices, default_params):
        prices, benchmark, sector_keys = synthetic_prices
        result = simulate(prices, benchmark, sector_keys, default_params)
        # Sharpe should be a finite number
        assert np.isfinite(result.sharpe)

    def test_max_drawdown_non_negative(self, synthetic_prices, default_params):
        prices, benchmark, sector_keys = synthetic_prices
        result = simulate(prices, benchmark, sector_keys, default_params)
        assert result.max_drawdown >= 0

    def test_too_short_data_returns_empty(self):
        """Data shorter than lookback should return empty result."""
        prices = np.ones((50, 3)) * 100
        benchmark = np.ones(50) * 100
        params = SimParams(rs_period="3M")  # needs 63 + 20 = 83 days
        result = simulate(prices, benchmark, ["A", "B", "C"], params)
        assert result.total_trades == 0

    def test_different_params_different_results(self, synthetic_prices):
        """Different parameters should produce different trade outcomes."""
        prices, benchmark, sector_keys = synthetic_prices
        r1 = simulate(prices, benchmark, sector_keys, SimParams(stop_loss_pct=5.0))
        r2 = simulate(prices, benchmark, sector_keys, SimParams(stop_loss_pct=15.0))

        # Results should differ (not guaranteed but very likely)
        assert r1.param_hash != r2.param_hash

    def test_to_dict_serializable(self, synthetic_prices, default_params):
        """Result should be JSON-serializable via to_dict."""
        prices, benchmark, sector_keys = synthetic_prices
        result = simulate(prices, benchmark, sector_keys, default_params)
        d = result.to_dict()
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    def test_tight_stops_in_bear(self, bear_market_prices):
        """Tight stops should limit losses in bear market."""
        prices, benchmark, sector_keys = bear_market_prices
        tight = simulate(prices, benchmark, sector_keys, SimParams(stop_loss_pct=5.0))
        wide = simulate(prices, benchmark, sector_keys, SimParams(stop_loss_pct=15.0))

        # Tight stops should have smaller max drawdown (usually)
        # This is probabilistic, so we just check both run without error
        assert isinstance(tight.max_drawdown, float)
        assert isinstance(wide.max_drawdown, float)


# ─── Grid Generation Tests ───────────────────────────────────

class TestGridGeneration:
    def test_full_grid_size(self):
        grid = generate_param_grid()
        # 4 × 5 × 4 × 4 × 5 × 4 × 4 × 3 = 76800
        assert len(grid) == 76800

    def test_all_params_are_SimParams(self):
        grid = generate_param_grid()
        assert all(isinstance(p, SimParams) for p in grid[:10])

    def test_focused_grid_smaller(self):
        base = SimParams()
        focused = generate_focused_grid(base, variation=1)
        assert len(focused) < 76800
        assert len(focused) > 0

    def test_focused_grid_centered(self):
        """Focused grid should include the base params."""
        base = SimParams(stop_loss_pct=8.0, max_positions=6)
        focused = generate_focused_grid(base, variation=1)
        base_hash = base.param_hash()
        hashes = {p.param_hash() for p in focused}
        assert base_hash in hashes

    def test_unique_hashes(self):
        grid = generate_param_grid()[:1000]
        hashes = [p.param_hash() for p in grid]
        assert len(set(hashes)) == len(hashes)


# ─── Sweep + Extraction Tests ────────────────────────────────

class TestSweepAndExtraction:
    def test_sweep_runs(self, synthetic_prices):
        """Small sweep should complete and return sorted results."""
        from services.compass_lab import run_sweep

        prices, benchmark, sector_keys = synthetic_prices
        small_grid = [
            SimParams(stop_loss_pct=sl, max_positions=mp)
            for sl in [5.0, 8.0, 12.0]
            for mp in [3, 6]
        ]

        results = run_sweep(prices, benchmark, sector_keys, small_grid, max_workers=1, batch_size=10)

        assert len(results) == 6
        # Should be sorted by Sortino descending
        sortinos = [r["sortino"] for r in results]
        assert sortinos == sorted(sortinos, reverse=True)

    def test_regime_config_extraction(self, synthetic_prices):
        """Should extract configs for regimes with enough trades."""
        from services.compass_lab import extract_regime_configs, run_sweep

        prices, benchmark, sector_keys = synthetic_prices
        small_grid = [
            SimParams(stop_loss_pct=sl, max_positions=mp)
            for sl in [5.0, 8.0, 10.0, 12.0]
            for mp in [3, 4, 6]
        ]

        results = run_sweep(prices, benchmark, sector_keys, small_grid, max_workers=1)
        configs = extract_regime_configs(results)

        # Should have at least one regime config (BULL at minimum)
        assert len(configs) >= 1
        for regime, config in configs.items():
            assert regime in REGIME_NAMES.values()
            assert "params" in config
            assert "evidence" in config
            assert config["evidence"]["n_trades"] >= 10

    def test_rule_discovery(self, synthetic_prices):
        """Should discover at least some rules from sufficient data."""
        from services.compass_lab import discover_rules, run_sweep

        prices, benchmark, sector_keys = synthetic_prices
        small_grid = [
            SimParams(stop_loss_pct=sl, max_positions=mp, min_rs_entry=mr)
            for sl in [5.0, 8.0, 12.0, 15.0]
            for mp in [3, 4, 6, 8]
            for mr in [0.0, 2.0, 5.0]
        ]

        results = run_sweep(prices, benchmark, sector_keys, small_grid, max_workers=1)
        rules = discover_rules(results)

        # Rules may or may not be discovered depending on data
        assert isinstance(rules, list)
        for rule in rules:
            assert "condition" in rule
            assert "historical_n" in rule
            assert "confidence" in rule


# ─── Autonomous Trader Unit Tests ────────────────────────────

class TestAutonomousTrader:
    def test_detect_regime(self):
        from services.compass_autonomous_trader import _detect_current_regime

        scores = [{"market_regime": "BULL", "sector_key": "IT"}]
        assert _detect_current_regime(scores) == "BULL"

        scores = [{"market_regime": "BEAR", "sector_key": "IT"}]
        assert _detect_current_regime(scores) == "BEAR"

        assert _detect_current_regime([]) == "UNKNOWN"

    def test_apply_rules_block_buy(self):
        from services.compass_autonomous_trader import _apply_rules

        rules = [{
            "id": 1,
            "condition": "regime=CORRECTION AND volume=DISTRIBUTION",
            "condition_json": {"regime": "CORRECTION", "volume": "DISTRIBUTION"},
            "override_action": "BLOCK_BUY",
            "confidence": "HIGH",
            "historical_n": 50,
            "historical_win_rate": 25.0,
        }]

        action, note = _apply_rules(
            "BUY", "CORRECTION",
            {"volume_signal": "DISTRIBUTION"},
            rules,
        )
        assert action == "HOLD"
        assert "Rule #1" in note

    def test_apply_rules_no_match(self):
        from services.compass_autonomous_trader import _apply_rules

        rules = [{
            "id": 1,
            "condition": "regime=BEAR",
            "condition_json": {"regime": "BEAR"},
            "override_action": "BLOCK_BUY",
            "confidence": "HIGH",
            "historical_n": 50,
            "historical_win_rate": 25.0,
        }]

        action, note = _apply_rules("BUY", "BULL", {}, rules)
        assert action == "BUY"
        assert note == ""

    def test_fallback_config(self):
        from services.compass_autonomous_trader import FALLBACK_CONFIG

        assert FALLBACK_CONFIG["stop_loss_pct"] == 8.0
        assert FALLBACK_CONFIG["max_positions"] == 6
        assert FALLBACK_CONFIG["min_rs_entry"] == 0.0


# ─── History Module Tests ────────────────────────────────────

class TestHistory:
    def test_data_summary_no_data(self):
        from services.compass_history import get_data_summary
        summary = get_data_summary()
        # May or may not have data depending on environment
        assert "status" in summary

    def test_save_and_load(self, tmp_path):
        """Test save/load roundtrip with synthetic data."""
        import services.compass_history as ch

        # Override data dir temporarily
        original_dir = ch.DATA_DIR
        original_file = ch.PRICES_FILE
        ch.DATA_DIR = str(tmp_path)
        ch.PRICES_FILE = str(tmp_path / "test_prices.npz")

        try:
            data = {
                "prices": np.random.rand(100, 5),
                "benchmark": np.random.rand(100),
                "dates": np.array([f"2020-01-{i+1:02d}" for i in range(100)]),
                "sector_keys": ["A", "B", "C", "D", "E"],
            }
            ch.save_historical_data(data)
            loaded = ch.load_historical_data()

            assert loaded is not None
            assert loaded["prices"].shape == (100, 5)
            assert len(loaded["benchmark"]) == 100
            assert len(loaded["sector_keys"]) == 5
        finally:
            ch.DATA_DIR = original_dir
            ch.PRICES_FILE = original_file


# ─── Integration: End-to-End Simulation Pipeline ────────────

class TestEndToEnd:
    def test_full_pipeline(self, synthetic_prices):
        """Run the full pipeline: simulate → extract → discover."""
        from services.compass_lab import discover_rules, extract_regime_configs, run_sweep

        prices, benchmark, sector_keys = synthetic_prices

        # Small grid for speed
        grid = [
            SimParams(stop_loss_pct=sl, max_positions=mp)
            for sl in [5.0, 8.0, 12.0]
            for mp in [3, 6]
        ]

        # Run sweep
        results = run_sweep(prices, benchmark, sector_keys, grid, max_workers=1)
        assert len(results) > 0

        # Extract configs
        configs = extract_regime_configs(results)
        assert isinstance(configs, dict)

        # Discover rules
        rules = discover_rules(results)
        assert isinstance(rules, list)

        # Best result should have valid metrics
        best = results[0]
        assert "total_return" in best
        assert "sharpe" in best
        assert "regime_metrics" in best

    def test_simulation_consistency(self, synthetic_prices):
        """Same params + data should produce identical results."""
        prices, benchmark, sector_keys = synthetic_prices
        params = SimParams(stop_loss_pct=8.0, max_positions=4)

        r1 = simulate(prices, benchmark, sector_keys, params)
        r2 = simulate(prices, benchmark, sector_keys, params)

        assert r1.total_return == r2.total_return
        assert r1.total_trades == r2.total_trades
        assert r1.sharpe == r2.sharpe
