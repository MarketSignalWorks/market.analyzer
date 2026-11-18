"""
Tests for engine.py and the metrics fixes it relies on.
Run with: python -m pytest backend/backtesting/test_engine.py -v
"""

import numpy as np
import pandas as pd
import pytest

from backend.backtesting.engine import EngineError, run_backtest
from backend.backtesting.metrics import compute_all, compute_beta
from backend.backtesting.portfolio import Portfolio


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_data(closes, start="2023-01-02"):
    idx = pd.bdate_range(start, periods=len(closes))
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "Open": closes,
            "High": closes * 1.01,
            "Low": closes * 0.99,
            "Close": closes,
            "Volume": np.full(len(closes), 1_000_000.0),
        },
        index=idx,
    )


class ScriptedStrategy:
    """Emits a fixed signal for each bar index (by window length)."""

    def __init__(self, signals):
        self.signals = signals
        self.max_window_seen = 0

    def generate_signals(self, data):
        self.max_window_seen = max(self.max_window_seen, len(data))
        out = data.copy()
        out["signal"] = 0
        out.iloc[-1, out.columns.get_loc("signal")] = self.signals.get(len(data) - 1, 0)
        return out


CONFIG = {"initial_capital": 10_000, "commission": 0.001}


# ── Engine ────────────────────────────────────────────────────────────────────

class TestEngine:
    def test_round_trip_logged(self):
        data = make_data([100, 101, 105, 110, 108])
        strat = ScriptedStrategy({1: 1, 3: -1})
        equity, trades = run_backtest(strat, data, CONFIG, Portfolio)
        assert len(equity) == len(data)
        assert len(trades) == 1
        assert trades[0]["entry_price"] == 101
        assert trades[0]["exit_price"] == 110

    def test_open_position_closed_at_end(self):
        data = make_data([100, 101, 105, 110, 120])
        strat = ScriptedStrategy({1: 1})  # buy, never sell
        equity, trades = run_backtest(strat, data, CONFIG, Portfolio)
        assert len(trades) == 1
        assert trades[0]["exit_price"] == 120
        assert trades[0]["exit_date"] == data.index[-1]

    def test_final_equity_includes_exit_commission(self):
        data = make_data([100, 100, 120])
        strat = ScriptedStrategy({0: 1})
        equity, trades = run_backtest(strat, data, CONFIG, Portfolio)
        qty = trades[0]["quantity"]
        # Final value is pure cash after the forced exit.
        expected = 10_000 - qty * 100 * 1.001 + qty * 120 * 0.999
        assert equity[-1] == pytest.approx(expected)

    def test_no_duplicate_point_in_portfolio_curve(self):
        data = make_data([100, 101, 102])
        captured = {}

        class SpyPortfolio(Portfolio):
            def __init__(self, **kw):
                super().__init__(**kw)
                captured["p"] = self

        run_backtest(ScriptedStrategy({0: 1}), data, CONFIG, SpyPortfolio)
        assert len(captured["p"].get_equity_curve()) == len(data)

    def test_no_look_ahead(self):
        data = make_data([100, 101, 102, 103])
        strat = ScriptedStrategy({})
        run_backtest(strat, data, CONFIG, Portfolio)
        assert strat.max_window_seen == len(data)

    def test_unsorted_index_rejected(self):
        data = make_data([100, 101, 102]).iloc[::-1]
        with pytest.raises(EngineError, match="sorted"):
            run_backtest(ScriptedStrategy({}), data, CONFIG, Portfolio)

    def test_duplicate_index_rejected(self):
        data = make_data([100, 101, 102])
        data = pd.concat([data, data.iloc[[-1]]])
        with pytest.raises(EngineError, match="duplicate"):
            run_backtest(ScriptedStrategy({}), data, CONFIG, Portfolio)

    def test_strategy_exception_becomes_engine_error(self):
        class Broken:
            def generate_signals(self, data):
                raise ValueError("boom")

        with pytest.raises(EngineError, match="boom"):
            run_backtest(Broken(), make_data([100, 101]), CONFIG, Portfolio)


# ── Real strategies through the engine ────────────────────────────────────────

@pytest.mark.parametrize("strategy_type", ["vwap_reversion", "macd_crossover"])
def test_regime_strategies_survive_short_history(strategy_type):
    pytest.importorskip("sklearn")
    from backend.strategies.registry import build_strategy

    rng = np.random.default_rng(0)
    closes = 100 * np.cumprod(1 + rng.normal(0, 0.01, 60))
    equity, _ = run_backtest(build_strategy(strategy_type, {}), make_data(closes), CONFIG, Portfolio)
    assert len(equity) == 60


# ── Metrics ───────────────────────────────────────────────────────────────────

class TestMetrics:
    def test_beta_of_benchmark_against_itself_is_one(self):
        rng = np.random.default_rng(1)
        prices = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 100)))
        assert compute_beta(prices.values, prices) == pytest.approx(1.0)

    def test_benchmark_aligned_by_date(self):
        rng = np.random.default_rng(2)
        idx = pd.bdate_range("2023-01-02", periods=50)
        bench = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 50)), index=idx)
        # Strategy equity tracks the benchmark exactly, but the benchmark
        # series has extra leading days the strategy doesn't.
        dates = [d.date().isoformat() for d in idx[10:]]
        equity = (bench.iloc[10:] * 100).tolist()
        result = compute_all(equity, [], equity[0], benchmark_prices=bench, dates=dates)
        assert result["beta"] == pytest.approx(1.0, abs=0.01)

    def test_no_drawdown_has_no_dates(self):
        result = compute_all(
            [100, 101, 102], [], 100, dates=["2023-01-02", "2023-01-03", "2023-01-04"]
        )
        assert result["max_drawdown"] == 0.0
        assert result["max_drawdown_start"] is None
        assert result["max_drawdown_end"] is None
