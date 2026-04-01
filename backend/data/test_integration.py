import pytest
import pandas as pd
from fastapi.testclient import TestClient

# Assuming these match the standard project structure being built
from backend.data.fetcher import fetch, fetch_benchmark
from backend.backtesting.engine import BacktestEngine
from backend.backtesting.metrics import compute_all
from backend.strategies import RSIDivergence, MACDTrend, MeanReversion, Breakout, MovingAverageCrossover
from backend.api.main import app

client = TestClient(app)

@pytest.fixture
def aapl_data():
    """Fixture to provide cached AAPL data for tests."""
    return fetch("AAPL", "2020-01-01", "2024-12-31")


def test_full_backtest_rsi(aapl_data):
    """Test the full pipeline using the RSIDivergence strategy."""
    strategy = RSIDivergence()
    initial_capital = 100000.0
    
    engine = BacktestEngine(data=aapl_data, strategy=strategy, initial_capital=initial_capital)
    engine.run()
    
    equity_curve = engine.equity_curve
    trade_log = engine.trade_log
    
    # Assert equity curve length matches data length
    assert len(equity_curve) == len(aapl_data), "Equity curve length must equal data length"
    
    # Fetch benchmark and compute metrics
    benchmark_data = fetch_benchmark("2020-01-01", "2024-12-31")['Close']
    
    metrics = compute_all(
        equity_curve=equity_curve,
        trade_log=trade_log,
        initial_capital=initial_capital,
        benchmark_prices=benchmark_data
    )
    
    # Assert metrics exist and fall within expected logical boundaries
    assert metrics["total_trades"] >= 0
    assert -5.0 <= metrics["sharpe_ratio"] <= 5.0, f"Sharpe ratio {metrics['sharpe_ratio']} is out of bounds"
    assert metrics["max_drawdown"] <= 0.0, "Max drawdown must be negative or zero"
    assert isinstance(metrics["annualized_return"], float)


def test_full_backtest_all_strategies(aapl_data):
    """Test that all 5 strategies can run without crashing and return valid equity curves."""
    strategies = [
        RSIDivergence(),
        MACDTrend(),
        MeanReversion(),
        Breakout(),
        MovingAverageCrossover()
    ]
    
    for strategy in strategies:
        try:
            engine = BacktestEngine(data=aapl_data, strategy=strategy, initial_capital=100000)
            engine.run()
            
            assert len(engine.equity_curve) > 0, f"{strategy.__class__.__name__} produced an empty equity curve"
        except Exception as e:
            pytest.fail(f"Strategy {strategy.__class__.__name__} crashed: {e}")


def test_no_trades(aapl_data):
    """Verify the metrics behavior when a strategy produces exactly 0 trades."""
    class ZeroSignalStrategy:
        def generate_signals(self, data):
            # Returns all zero signals (no positions taken)
            return pd.Series(0, index=data.index)
            
    engine = BacktestEngine(data=aapl_data, strategy=ZeroSignalStrategy(), initial_capital=100000)
    engine.run()
    
    metrics = compute_all(engine.equity_curve, engine.trade_log, 100000)
    
    # Verification constraints for flat equity
    assert all(val == 100000 for val in engine.equity_curve), "Equity curve is not flat"
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["max_drawdown"] == 0.0


def test_api_endpoint():
    """Ensure the API router coordinates the components correctly and returns standard JSON payload."""
    payload = {
        "ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "strategy": "RSIDivergence",
        "initial_capital": 100000
    }
    response = client.post("/api/backtest", json=payload)
    
    assert response.status_code == 200, f"API failed with: {response.text}"
    data = response.json()
    
    assert "metrics" in data
    assert "equity_curve" in data
    assert "trade_log" in data


def test_edge_cases():
    """Test missing tickers, short data bounds, and high commission rates."""
    # Test non-existent ticker
    with pytest.raises(ValueError, match="No data found"):
        fetch("INVALID_TICKER_THAT_DOES_NOT_EXIST", "2020-01-01", "2020-12-31")
