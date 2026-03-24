"""
Core backtesting engine.
"""

# TODO: Implement backtesting 
from __future__ import annotations
from typing import Any, Dict, List, Tuple
import pandas as pd


class EngineError(Exception):
    pass


def _validate_data(data: pd.DataFrame) -> None:
    if data is None or data.empty:
        raise EngineError("Input price data is empty.")

    required_columns = {"Open", "High", "Low", "Close", "Volume"}
    missing = required_columns - set(data.columns)
    if missing:
        raise EngineError(f"Missing required columns: {sorted(missing)}")

    if not isinstance(data.index, pd.DatetimeIndex):
        raise EngineError("Price data index must be a pandas DatetimeIndex.")

    if data["Close"].isna().any():
        raise EngineError("Price data contains NaN values in the Close column.")


def _normalize_signal(raw_signal: Any) -> int:
    if pd.isna(raw_signal):
        return 0

    try:
        value = float(raw_signal)
    except (TypeError, ValueError):
        return 0

    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def run_backtest(
    strategy: Any,
    data: pd.DataFrame,
    config: Dict[str, Any],
    portfolio_class: Any,
) -> Tuple[List[float], List[Dict[str, Any]]]:
    _validate_data(data)

    if not hasattr(strategy, "generate_signals"):
        raise EngineError("Strategy object must implement generate_signals(data).")

    initial_capital = float(config.get("initial_capital", 100000))
    commission_rate = float(config.get("commission", 0.001))

    portfolio = portfolio_class(
        initial_capital=initial_capital,
        commission_rate=commission_rate,
    )

    equity_curve: List[float] = []

    for i in range(len(data)):
        window = data.iloc[: i + 1].copy()

        current_timestamp = data.index[i]
        current_close = float(data["Close"].iloc[i])

        signal_df = strategy.generate_signals(window)

        if not isinstance(signal_df, pd.DataFrame):
            raise EngineError(
                f"Strategy.generate_signals() must return a DataFrame, got {type(signal_df)}."
            )

        if "signal" not in signal_df.columns:
            raise EngineError("Strategy output must include a 'signal' column.")

        if signal_df.empty:
            raise EngineError("Strategy returned an empty DataFrame.")

        raw_signal = signal_df["signal"].iloc[-1]
        signal = _normalize_signal(raw_signal)

        if signal == 1:
            portfolio.execute_trade("buy", current_close, current_timestamp)
        elif signal == -1:
            portfolio.execute_trade("sell", current_close, current_timestamp)

        portfolio_value = portfolio.get_portfolio_value(current_close)
        equity_curve.append(float(portfolio_value))

    if hasattr(portfolio, "close_open_position"):
        last_timestamp = data.index[-1]
        last_close = float(data["Close"].iloc[-1])
        portfolio.close_open_position(last_close, last_timestamp)
        equity_curve[-1] = float(portfolio.get_portfolio_value(last_close))

    trade_log = portfolio.get_trade_log()

    return equity_curve, trade_log
