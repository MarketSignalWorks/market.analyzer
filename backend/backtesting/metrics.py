"""
Performance metrics module: pure math functions that compute backtest metrics.
Takes equity curve + trade log + benchmark prices and returns a dict of all metrics.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_daily_returns(equity_curve: np.ndarray) -> np.ndarray:
    """
    Calculate daily returns as percentage changes in equity curve.
    
    Args:
        equity_curve: Array of daily portfolio values
        
    Returns:
        Array of daily returns (as decimals, e.g. 0.05 = 5%)
    """
    equity = np.asarray(equity_curve, dtype=float)
    if len(equity) < 2:
        return np.array([])
    return np.diff(equity) / equity[:-1]


def calculate_running_maximum(equity_curve: np.ndarray) -> np.ndarray:
    """
    Calculate the running maximum of equity curve (expanding window).
    
    Args:
        equity_curve: Array of daily portfolio values
        
    Returns:
        Array of same length with running maximum at each point
    """
    equity = np.asarray(equity_curve, dtype=float)
    return np.maximum.accumulate(equity)


def calculate_drawdowns(equity_curve: np.ndarray) -> Tuple[np.ndarray, Optional[int], Optional[int]]:
    """
    Calculate drawdown at each point and find max drawdown indices.
    
    Args:
        equity_curve: Array of daily portfolio values
        
    Returns:
        Tuple of (drawdown_series, max_drawdown_idx, current_drawdown_end_idx)
        - drawdown_series: Array of drawdowns (as decimals, e.g. -0.15 = -15%)
        - max_drawdown_idx: Index of maximum drawdown point
        - current_drawdown_end_idx: Index where max drawdown ends (same as max_drawdown_idx)
    """
    equity = np.asarray(equity_curve, dtype=float)
    running_max = calculate_running_maximum(equity)
    drawdowns = (equity - running_max) / running_max
    
    max_idx = np.argmin(drawdowns)
    
    return drawdowns, max_idx, max_idx


def get_max_drawdown_dates(
    equity_curve: np.ndarray,
    dates: Optional[List[str]] = None,
    max_drawdown_idx: Optional[int] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get start and end dates of maximum drawdown.
    
    Args:
        equity_curve: Array of daily portfolio values
        dates: Optional list of date strings (ISO format)
        max_drawdown_idx: Index of maximum drawdown point
        
    Returns:
        Tuple of (start_date, end_date) as ISO strings, or (None, None) if no dates provided
    """
    if dates is None or max_drawdown_idx is None:
        return None, None
    
    equity = np.asarray(equity_curve, dtype=float)
    running_max = calculate_running_maximum(equity)
    
    # Find when the running max was set (going backwards from max_drawdown_idx)
    max_val = running_max[max_drawdown_idx]
    start_idx = np.where(equity == max_val)[0]
    start_idx = start_idx[start_idx <= max_drawdown_idx]
    if len(start_idx) == 0:
        start_idx = 0
    else:
        start_idx = start_idx[-1]  # Last occurrence before or at max_drawdown_idx
    
    start_date = dates[start_idx] if start_idx < len(dates) else None
    end_date = dates[max_drawdown_idx] if max_drawdown_idx < len(dates) else None
    
    return start_date, end_date


# ============================================================================
# RETURN METRICS
# ============================================================================

def compute_total_return(
    equity_curve: np.ndarray,
    initial_capital: float
) -> float:
    """
    Total Return: (final_value - initial_capital) / initial_capital × 100
    
    Args:
        equity_curve: Array of daily portfolio values
        initial_capital: Starting capital
        
    Returns:
        Total return as percentage
    """
    if len(equity_curve) == 0:
        return 0.0
    
    final_value = float(equity_curve[-1])
    total_return = ((final_value - initial_capital) / initial_capital) * 100.0
    return total_return


def compute_annualized_return(
    equity_curve: np.ndarray,
    initial_capital: float,
    trading_days: Optional[int] = None
) -> float:
    """
    Annualized Return: ((final_value / initial_capital) ^ (252 / trading_days) - 1) × 100
    
    Args:
        equity_curve: Array of daily portfolio values
        initial_capital: Starting capital
        trading_days: Number of trading days in the period. If None, uses len(equity_curve) - 1
        
    Returns:
        Annualized return as percentage
    """
    if len(equity_curve) < 2 or initial_capital <= 0:
        return 0.0
    
    final_value = float(equity_curve[-1])
    if trading_days is None:
        trading_days = len(equity_curve) - 1
    
    if trading_days == 0:
        return 0.0
    
    annualized = ((final_value / initial_capital) ** (252.0 / trading_days) - 1.0) * 100.0
    return annualized


def compute_annualized_volatility(
    equity_curve: np.ndarray
) -> float:
    """
    Annualized Volatility: std(daily_returns) × √252 × 100
    
    Args:
        equity_curve: Array of daily portfolio values
        
    Returns:
        Annualized volatility as percentage
    """
    daily_returns = calculate_daily_returns(equity_curve)
    
    if len(daily_returns) < 2:
        return 0.0
    
    volatility = np.std(daily_returns) * np.sqrt(252.0) * 100.0
    return volatility


# ============================================================================
# RISK-ADJUSTED METRICS
# ============================================================================

def compute_sharpe_ratio(
    equity_curve: np.ndarray,
    risk_free_rate: float = 0.05
) -> float:
    """
    Sharpe Ratio: (mean(daily_returns) / std(daily_returns)) × √252
    
    Measures return per unit of risk. Above 1.0 is decent, above 2.0 is strong.
    
    Args:
        equity_curve: Array of daily portfolio values
        risk_free_rate: Annual risk-free rate (default 0.05 = 5%)
        
    Returns:
        Sharpe ratio (annualized)
    """
    daily_returns = calculate_daily_returns(equity_curve)
    
    if len(daily_returns) < 2:
        return 0.0
    
    mean_return = np.mean(daily_returns)
    std_return = np.std(daily_returns)
    
    if std_return == 0:
        return 0.0
    
    # Annualize the daily risk-free rate
    daily_rf = (1 + risk_free_rate) ** (1.0 / 252.0) - 1.0
    
    sharpe = ((mean_return - daily_rf) / std_return) * np.sqrt(252.0)
    return sharpe


def compute_sortino_ratio(
    equity_curve: np.ndarray,
    risk_free_rate: float = 0.05
) -> float:
    """
    Sortino Ratio: (mean(daily_returns) / std(negative_daily_returns)) × √252
    
    Like Sharpe but only penalizes downside volatility.
    
    Args:
        equity_curve: Array of daily portfolio values
        risk_free_rate: Annual risk-free rate (default 0.05 = 5%)
        
    Returns:
        Sortino ratio (annualized)
    """
    daily_returns = calculate_daily_returns(equity_curve)
    
    if len(daily_returns) < 2:
        return 0.0
    
    mean_return = np.mean(daily_returns)
    
    # Capture only negative returns
    negative_returns = daily_returns[daily_returns < 0]
    
    if len(negative_returns) == 0:
        # No losses, return a very high sortino ratio
        return 100.0
    
    downside_volatility = np.std(negative_returns)
    
    if downside_volatility == 0:
        return 100.0
    
    # Annualize the daily risk-free rate
    daily_rf = (1 + risk_free_rate) ** (1.0 / 252.0) - 1.0
    
    sortino = ((mean_return - daily_rf) / downside_volatility) * np.sqrt(252.0)
    return sortino


def compute_calmar_ratio(
    equity_curve: np.ndarray,
    initial_capital: float
) -> float:
    """
    Calmar Ratio: annualized_return / abs(max_drawdown)
    
    Return relative to worst drawdown.
    
    Args:
        equity_curve: Array of daily portfolio values
        initial_capital: Starting capital
        
    Returns:
        Calmar ratio
    """
    ann_return = compute_annualized_return(equity_curve, initial_capital) / 100.0  # Convert to decimal
    max_drawdown = compute_max_drawdown(equity_curve) / 100.0  # Convert to decimal
    
    if max_drawdown == 0:
        return 0.0
    
    calmar = ann_return / abs(max_drawdown)
    return calmar


# ============================================================================
# DRAWDOWN METRICS
# ============================================================================

def compute_max_drawdown(equity_curve: np.ndarray) -> float:
    """
    Maximum Drawdown: minimum of (current_value - running_max) / running_max
    
    Args:
        equity_curve: Array of daily portfolio values
        
    Returns:
        Max drawdown as percentage (negative value)
    """
    drawdowns, _, _ = calculate_drawdowns(equity_curve)
    
    if len(drawdowns) == 0:
        return 0.0
    
    max_drawdown = np.min(drawdowns) * 100.0
    return max_drawdown


def compute_max_drawdown_with_dates(
    equity_curve: np.ndarray,
    dates: Optional[List[str]] = None
) -> Tuple[float, Optional[str], Optional[str]]:
    """
    Maximum Drawdown with start and end dates.
    
    Args:
        equity_curve: Array of daily portfolio values
        dates: Optional list of date strings (ISO format)
        
    Returns:
        Tuple of (max_drawdown_pct, start_date, end_date)
    """
    drawdowns, max_idx, _ = calculate_drawdowns(equity_curve)
    
    if len(drawdowns) == 0:
        return 0.0, None, None
    
    max_drawdown_pct = np.min(drawdowns) * 100.0
    start_date, end_date = get_max_drawdown_dates(equity_curve, dates, max_idx)
    
    return max_drawdown_pct, start_date, end_date


# ============================================================================
# TRADE STATISTICS
# ============================================================================

def compute_total_trades(trade_log: List[Dict]) -> int:
    """
    Total Trades: count of all trades
    
    Args:
        trade_log: List of trade dicts
        
    Returns:
        Number of trades
    """
    return len(trade_log)


def compute_win_rate(trade_log: List[Dict]) -> float:
    """
    Win Rate: count(trades where pnl > 0) / total_trades × 100
    
    Args:
        trade_log: List of trade dicts with 'pnl' key
        
    Returns:
        Win rate as percentage (0-100)
    """
    if len(trade_log) == 0:
        return 0.0
    
    winning_trades = sum(1 for trade in trade_log if trade.get('pnl', 0) > 0)
    win_rate = (winning_trades / len(trade_log)) * 100.0
    return win_rate


def compute_profit_factor(trade_log: List[Dict]) -> Optional[float]:
    """
    Profit Factor: sum(pnl of winning trades) / abs(sum(pnl of losing trades))
    
    Above 1.0 means profitable overall. Returns None if no losing trades (infinity case).
    
    Args:
        trade_log: List of trade dicts with 'pnl' key
        
    Returns:
        Profit factor or None if division by zero
    """
    if len(trade_log) == 0:
        return None
    
    winning_pnl = sum(trade.get('pnl', 0) for trade in trade_log if trade.get('pnl', 0) > 0)
    losing_pnl = sum(trade.get('pnl', 0) for trade in trade_log if trade.get('pnl', 0) <= 0)
    
    if losing_pnl == 0:
        # Only winning trades or no trades
        if winning_pnl > 0:
            return None  # Infinity
        return 0.0
    
    profit_factor = winning_pnl / abs(losing_pnl)
    return profit_factor


def compute_avg_trade_duration(trade_log: List[Dict]) -> float:
    """
    Avg Trade Duration: mean(exit_date - entry_date) across all trades, in days
    
    Args:
        trade_log: List of trade dicts with 'entry_date' and 'exit_date' keys
        
    Returns:
        Average duration in days
    """
    if len(trade_log) == 0:
        return 0.0
    
    durations = []
    for trade in trade_log:
        entry_date = trade.get('entry_date')
        exit_date = trade.get('exit_date')
        
        if entry_date is None or exit_date is None:
            continue
        
        # Parse dates if they're strings
        if isinstance(entry_date, str):
            entry_date = datetime.fromisoformat(entry_date.replace('Z', '+00:00')).date()
        elif isinstance(entry_date, datetime):
            entry_date = entry_date.date()
        
        if isinstance(exit_date, str):
            exit_date = datetime.fromisoformat(exit_date.replace('Z', '+00:00')).date()
        elif isinstance(exit_date, datetime):
            exit_date = exit_date.date()
        
        duration = (exit_date - entry_date).days
        durations.append(duration)
    
    if len(durations) == 0:
        return 0.0
    
    return float(np.mean(durations))


def compute_avg_win_loss(trade_log: List[Dict]) -> Tuple[float, float]:
    """
    Average Win and Average Loss: mean(pnl) for winning and losing trades separately
    
    Args:
        trade_log: List of trade dicts with 'pnl' key
        
    Returns:
        Tuple of (avg_win, avg_loss)
    """
    if len(trade_log) == 0:
        return 0.0, 0.0
    
    winning_pnls = [trade.get('pnl', 0) for trade in trade_log if trade.get('pnl', 0) > 0]
    losing_pnls = [trade.get('pnl', 0) for trade in trade_log if trade.get('pnl', 0) <= 0]
    
    avg_win = float(np.mean(winning_pnls)) if len(winning_pnls) > 0 else 0.0
    avg_loss = float(np.mean(losing_pnls)) if len(losing_pnls) > 0 else 0.0
    
    return avg_win, avg_loss


def compute_max_consecutive_wins(trade_log: List[Dict]) -> int:
    """
    Max Consecutive Wins: longest streak of trades where pnl > 0
    
    Args:
        trade_log: List of trade dicts with 'pnl' key
        
    Returns:
        Max consecutive wins count
    """
    if len(trade_log) == 0:
        return 0
    
    max_streak = 0
    current_streak = 0
    
    for trade in trade_log:
        if trade.get('pnl', 0) > 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    return max_streak


def compute_max_consecutive_losses(trade_log: List[Dict]) -> int:
    """
    Max Consecutive Losses: longest streak of trades where pnl ≤ 0
    
    Args:
        trade_log: List of trade dicts with 'pnl' key
        
    Returns:
        Max consecutive losses count
    """
    if len(trade_log) == 0:
        return 0
    
    max_streak = 0
    current_streak = 0
    
    for trade in trade_log:
        if trade.get('pnl', 0) <= 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    return max_streak


# ============================================================================
# BENCHMARK COMPARISON (vs. SPY)
# ============================================================================

def compute_beta(
    equity_curve: np.ndarray,
    spy_prices: pd.Series
) -> float:
    """
    Beta: cov(strategy_daily_returns, spy_daily_returns) / var(spy_daily_returns)
    
    How much the strategy moves relative to the market.
    
    Args:
        equity_curve: Array of daily portfolio values
        spy_prices: Pandas Series of SPY daily close prices (aligned to equity_curve)
        
    Returns:
        Beta coefficient
    """
    strategy_returns = calculate_daily_returns(equity_curve)
    spy_returns = calculate_daily_returns(spy_prices.values)
    
    # Align lengths
    min_len = min(len(strategy_returns), len(spy_returns))
    strategy_returns = strategy_returns[:min_len]
    spy_returns = spy_returns[:min_len]
    
    if len(strategy_returns) < 2 or len(spy_returns) < 2:
        return 0.0
    
    covariance = np.cov(strategy_returns, spy_returns)[0][1]
    spy_variance = np.var(spy_returns)
    
    if spy_variance == 0:
        return 0.0
    
    beta = covariance / spy_variance
    return beta


def compute_alpha(
    equity_curve: np.ndarray,
    spy_prices: pd.Series,
    initial_capital: float,
    risk_free_rate: float = 0.05
) -> float:
    """
    Alpha: annualized_strategy_return - (risk_free_rate + beta × (annualized_spy_return - risk_free_rate))
    
    Excess return above what's expected given the strategy's beta.
    
    Args:
        equity_curve: Array of daily portfolio values
        spy_prices: Pandas Series of SPY daily close prices (aligned to equity_curve)
        initial_capital: Starting capital for strategy
        risk_free_rate: Annual risk-free rate (default 0.05 = 5%)
        
    Returns:
        Alpha as percentage (annualized)
    """
    trading_days = len(equity_curve) - 1
    
    ann_strategy_return = compute_annualized_return(
        equity_curve, initial_capital, trading_days
    ) / 100.0  # Convert to decimal
    
    # Calculate SPY annualized return
    spy_return = (spy_prices.iloc[-1] - spy_prices.iloc[0]) / spy_prices.iloc[0]
    ann_spy_return = ((1 + spy_return) ** (252.0 / trading_days) - 1.0)
    
    beta = compute_beta(equity_curve, spy_prices)
    
    expected_return = risk_free_rate + beta * (ann_spy_return - risk_free_rate)
    alpha = (ann_strategy_return - expected_return) * 100.0  # Convert back to percentage
    
    return alpha


# ============================================================================
# MASTER FUNCTION
# ============================================================================

def compute_all(
    equity_curve: List[float],
    trade_log: List[Dict],
    initial_capital: float,
    benchmark_prices: Optional[pd.Series] = None,
    dates: Optional[List[str]] = None,
    risk_free_rate: float = 0.05
) -> Dict[str, Any]:
    """
    Master function: compute all metrics and return a single dictionary.
    
    Args:
        equity_curve: List or array of daily portfolio values
        trade_log: List of trade dicts with keys: entry_date, exit_date, pnl, pnl_pct
        initial_capital: Starting capital
        benchmark_prices: Optional Pandas Series of SPY daily prices
        dates: Optional list of date strings (ISO format) for max drawdown dates
        risk_free_rate: Annual risk-free rate (default 0.05)
        
    Returns:
        Dictionary with all metrics
    """
    equity_curve = np.asarray(equity_curve, dtype=float)
    
    # Validate inputs
    if len(equity_curve) < 2:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_start": None,
            "max_drawdown_end": None,
            "win_rate": 0.0,
            "profit_factor": None,
            "total_trades": 0,
            "avg_trade_duration": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "alpha": 0.0,
            "beta": 0.0,
        }
    
    # Return metrics
    total_return = compute_total_return(equity_curve, initial_capital)
    annualized_return = compute_annualized_return(equity_curve, initial_capital)
    annualized_volatility = compute_annualized_volatility(equity_curve)
    
    # Risk-adjusted metrics
    sharpe_ratio = compute_sharpe_ratio(equity_curve, risk_free_rate)
    sortino_ratio = compute_sortino_ratio(equity_curve, risk_free_rate)
    calmar_ratio = compute_calmar_ratio(equity_curve, initial_capital)
    
    # Drawdown metrics
    max_drawdown, max_drawdown_start, max_drawdown_end = compute_max_drawdown_with_dates(
        equity_curve, dates
    )
    
    # Trade statistics
    total_trades = compute_total_trades(trade_log)
    win_rate = compute_win_rate(trade_log)
    profit_factor = compute_profit_factor(trade_log)
    avg_trade_duration = compute_avg_trade_duration(trade_log)
    avg_win, avg_loss = compute_avg_win_loss(trade_log)
    max_consecutive_wins = compute_max_consecutive_wins(trade_log)
    max_consecutive_losses = compute_max_consecutive_losses(trade_log)
    
    # Benchmark comparison
    alpha = 0.0
    beta = 0.0
    if benchmark_prices is not None and len(benchmark_prices) > 0:
        # Align benchmark with equity curve
        min_len = min(len(equity_curve), len(benchmark_prices))
        aligned_equity = equity_curve[:min_len]
        aligned_benchmark = benchmark_prices.iloc[:min_len]
        
        if len(aligned_equity) >= 2:
            beta = compute_beta(aligned_equity, aligned_benchmark)
            alpha = compute_alpha(aligned_equity, aligned_benchmark, initial_capital, risk_free_rate)
    
    return {
        "total_return": round(total_return, 2),
        "annualized_return": round(annualized_return, 2),
        "annualized_volatility": round(annualized_volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_start": max_drawdown_start,
        "max_drawdown_end": max_drawdown_end,
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "total_trades": total_trades,
        "avg_trade_duration": round(avg_trade_duration, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses,
        "alpha": round(alpha, 2),
        "beta": round(beta, 2),
    }


# ============================================================================
# TEST CASES WITH HARDCODED INPUTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("METRICS MODULE TEST CASES")
    print("=" * 80)
    
    # Test 1: Simple equity curve with daily returns
    print("\n[TEST 1] Sharpe Ratio with hardcoded daily returns")
    equity_test1 = np.array([100000, 100500, 100000, 100800, 100500, 101200])
    daily_returns_test1 = calculate_daily_returns(equity_test1)
    print(f"Equity curve: {equity_test1}")
    print(f"Daily returns: {daily_returns_test1}")
    
    sharpe_test1 = compute_sharpe_ratio(equity_test1)
    print(f"Sharpe Ratio: {sharpe_test1:.4f}")
    
    # Verify manually: returns = [0.005, -0.00497, 0.00800, -0.00298, 0.00698]
    # mean = 0.001606, std = 0.00608, sharpe = (0.001606/0.00608) * sqrt(252) = 4.166
    mean_ret = np.mean(daily_returns_test1)
    std_ret = np.std(daily_returns_test1)
    manual_sharpe = (mean_ret / std_ret) * np.sqrt(252.0)
    print(f"Manual verification: {manual_sharpe:.4f}")
    
    # Test 2: Max Drawdown
    print("\n[TEST 2] Max Drawdown calculation")
    equity_test2 = np.array([100000, 105000, 110000, 108000, 95000, 98000])
    max_dd = compute_max_drawdown(equity_test2)
    print(f"Equity curve: {equity_test2}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    # Expected: peak at 110000, trough at 95000 = (95000-110000)/110000 = -13.636%
    
    # Test 3: Win Rate and Profit Factor
    print("\n[TEST 3] Trade Statistics")
    trades_test = [
        {"pnl": 1000, "entry_date": "2024-01-01", "exit_date": "2024-01-05"},
        {"pnl": -500, "entry_date": "2024-01-06", "exit_date": "2024-01-10"},
        {"pnl": 1500, "entry_date": "2024-01-11", "exit_date": "2024-01-15"},
        {"pnl": -200, "entry_date": "2024-01-16", "exit_date": "2024-01-20"},
        {"pnl": 800, "entry_date": "2024-01-21", "exit_date": "2024-01-25"},
    ]
    
    win_rate = compute_win_rate(trades_test)
    profit_factor = compute_profit_factor(trades_test)
    avg_duration = compute_avg_trade_duration(trades_test)
    avg_win, avg_loss = compute_avg_win_loss(trades_test)
    max_wins = compute_max_consecutive_wins(trades_test)
    max_losses = compute_max_consecutive_losses(trades_test)
    
    print(f"Total Trades: {len(trades_test)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Avg Trade Duration: {avg_duration:.2f} days")
    print(f"Avg Win: ${avg_win:.2f}")
    print(f"Avg Loss: ${avg_loss:.2f}")
    print(f"Max Consecutive Wins: {max_wins}")
    print(f"Max Consecutive Losses: {max_losses}")
    
    # Test 4: Full compute_all() with sample data
    print("\n[TEST 4] compute_all() - Complete backtest")
    equity_curve_full = np.array([
        100000, 100500, 101000, 100800, 101500, 102000,
        101800, 102500, 103000, 102500, 103500, 104000
    ])
    
    trade_log_full = [
        {"pnl": 1500, "entry_date": "2024-01-02", "exit_date": "2024-01-05"},
        {"pnl": -300, "entry_date": "2024-01-06", "exit_date": "2024-01-08"},
        {"pnl": 2000, "entry_date": "2024-01-09", "exit_date": "2024-01-12"},
    ]
    
    dates_full = [
        "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
        "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
        "2024-01-15", "2024-01-16"
    ]
    
    results = compute_all(
        equity_curve=equity_curve_full,
        trade_log=trade_log_full,
        initial_capital=100000,
        dates=dates_full
    )
    
    print("Complete Metrics:")
    for key, value in results.items():
        print(f"  {key}: {value}")
    
    # Test 5: Edge case - Zero trades
    print("\n[TEST 5] Edge case: Zero trades")
    results_no_trades = compute_all(
        equity_curve=[100000, 101000, 102000],
        trade_log=[],
        initial_capital=100000
    )
    print(f"Win Rate (0 trades): {results_no_trades['win_rate']}")
    print(f"Profit Factor (0 trades): {results_no_trades['profit_factor']}")
    print(f"Total Trades: {results_no_trades['total_trades']}")
    
    # Test 6: Edge case - Only winning trades
    print("\n[TEST 6] Edge case: Only winning trades")
    winning_only = [
        {"pnl": 1000, "entry_date": "2024-01-01", "exit_date": "2024-01-05"},
        {"pnl": 500, "entry_date": "2024-01-06", "exit_date": "2024-01-10"},
    ]
    results_wins = compute_all(
        equity_curve=[100000, 101000, 101500],
        trade_log=winning_only,
        initial_capital=100000
    )
    print(f"Win Rate (only wins): {results_wins['win_rate']}%")
    print(f"Profit Factor (only wins): {results_wins['profit_factor']}")
    
    # Test 7: Annualized metrics
    print("\n[TEST 7] Annualized Returns")
    # Create 1 year of data: 252 trading days
    np.random.seed(42)
    daily_rets = np.random.normal(0.0005, 0.01, 252)  # Small positive drift
    equity_1yr = 100000 * np.cumprod(1 + daily_rets)
    
    total_ret = compute_total_return(equity_1yr, 100000)
    ann_ret = compute_annualized_return(equity_1yr, 100000)
    ann_vol = compute_annualized_volatility(equity_1yr)
    
    print(f"1-Year Backtest:")
    print(f"  Total Return: {total_ret:.2f}%")
    print(f"  Annualized Return: {ann_ret:.2f}%")
    print(f"  Annualized Volatility: {ann_vol:.2f}%")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)
