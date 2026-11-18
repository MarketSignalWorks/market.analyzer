"""
Core backtesting engine.

Walks the price data bar by bar. On each bar the strategy only sees data up
to and including that bar (no look-ahead), and any trade fills at that bar's
close. A position still open after the last bar is closed at the final close
so the trade log and trade metrics include it.
"""

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

    if not data.index.is_monotonic_increasing:
        raise EngineError("Price data index must be sorted in ascending date order.")

    if data.index.has_duplicates:
        raise EngineError("Price data index contains duplicate timestamps.")

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


def _close_open_position(portfolio: Any, price: float, timestamp: Any) -> None:
    """Close any open position, using whichever method the portfolio provides."""
    for name in ("close_open_position", "force_close"):
        closer = getattr(portfolio, name, None)
        if callable(closer):
            closer(price, timestamp)
            return
    raise EngineError(
        "Portfolio must implement force_close(price, timestamp) or "
        "close_open_position(price, timestamp)."
    )


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

        try:
            signal_df = strategy.generate_signals(window)
        except Exception as e:
            raise EngineError(
                f"Strategy failed on bar {i} ({current_timestamp.date()}): {e}"
            ) from e

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

        # On the final bar, close anything still open before marking equity,
        # so the last point includes the exit commission and the trade is logged.
        if i == len(data) - 1:
            _close_open_position(portfolio, current_close, current_timestamp)

        portfolio_value = portfolio.get_portfolio_value(current_close)
        equity_curve.append(float(portfolio_value))

    trade_log = portfolio.get_trade_log()

    return equity_curve, trade_log
