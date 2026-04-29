"""
Backtest execution endpoint.

Runs the requested strategy over the requested window and persists the
backtest, trade log, and equity curve so the frontend can read them back
through /api/backtests.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import List

import pandas as pd
from flask import Blueprint, jsonify, request

import config
from backend.backtesting.engine import EngineError, run_backtest
from backend.backtesting.metrics import compute_all
from backend.backtesting.portfolio import Portfolio
from backend.data.fetcher import fetch_benchmark, fetch_ohlcv
from backend.models import Backtest, EquityPoint, Strategy, Trade, db
from backend.strategies.registry import build_strategy

backtest_bp = Blueprint("backtest", __name__, url_prefix="/api")


def _iso(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:10]
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def _drawdown_series(equity_curve: List[float], dates: List[str]) -> list[dict]:
    """Percent drawdown from running max, aligned with `dates`."""
    if not equity_curve:
        return []
    out, peak = [], equity_curve[0]
    for d, v in zip(dates, equity_curve):
        peak = max(peak, v)
        dd = (v - peak) / peak * 100 if peak else 0.0
        out.append({"date": d, "drawdown": round(dd, 4)})
    return out


def _monthly_returns(equity_curve: List[float], dates: List[str]) -> list[dict]:
    """Calendar-month percent returns derived from the equity curve."""
    if not equity_curve or not dates:
        return []
    by_month: dict[str, list[float]] = defaultdict(list)
    for d, v in zip(dates, equity_curve):
        month = d[:7]
        by_month[month].append(v)
    out = []
    for month in sorted(by_month):
        values = by_month[month]
        first, last = values[0], values[-1]
        if first <= 0:
            continue
        out.append({"month": month, "return": round((last - first) / first * 100, 2)})
    return out


def _flatten_response(bt: Backtest, equity_curve, trade_log, dates) -> dict:
    """Shape the backtest response the way the Streamlit frontend expects."""
    metrics = bt.metrics_dict()
    profitable = sum(1 for t in trade_log if t.get("pnl", 0) > 0)
    avg_trade_return = (
        round(sum(t.get("pnl_pct", 0) for t in trade_log) / len(trade_log), 2)
        if trade_log else 0.0
    )

    trades_out = [
        {
            "entry_date": _iso(t.get("entry_date")),
            "exit_date": _iso(t.get("exit_date")),
            "entry_price": float(t.get("entry_price", 0)),
            "exit_price": float(t.get("exit_price", 0)),
            "quantity": float(t.get("quantity", 0)),
            "side": t.get("side", "long"),
            "profit": float(t.get("pnl", 0)),
            "return_pct": float(t.get("pnl_pct", 0)),
        }
        for t in trade_log
    ]

    return {
        "id": bt.id,
        "strategy_id": bt.strategy_id,
        "symbol": bt.symbol,
        "start_date": bt.start_date,
        "end_date": bt.end_date,
        "initial_capital": bt.initial_capital,
        "final_capital": bt.final_capital,
        "execution_time_ms": bt.execution_time_ms,
        "created_at": bt.created_at.isoformat() if bt.created_at else None,
        # Flattened metrics — frontend reads these at the top level.
        "total_return": metrics.get("total_return") or 0.0,
        "annualized_return": metrics.get("annualized_return") or 0.0,
        "annualized_volatility": metrics.get("annualized_volatility") or 0.0,
        "sharpe_ratio": metrics.get("sharpe_ratio") or 0.0,
        "sortino_ratio": metrics.get("sortino_ratio") or 0.0,
        "calmar_ratio": metrics.get("calmar_ratio") or 0.0,
        "max_drawdown": metrics.get("max_drawdown") or 0.0,
        "max_drawdown_start": metrics.get("max_drawdown_start"),
        "max_drawdown_end": metrics.get("max_drawdown_end"),
        "win_rate": metrics.get("win_rate") or 0.0,
        "profit_factor": metrics.get("profit_factor") or 0.0,
        "total_trades": metrics.get("total_trades") or 0,
        "avg_trade_duration": metrics.get("avg_trade_duration") or 0.0,
        "avg_trade_return": avg_trade_return,
        "avg_win": metrics.get("avg_win") or 0.0,
        "avg_loss": metrics.get("avg_loss") or 0.0,
        "max_consecutive_wins": metrics.get("max_consecutive_wins") or 0,
        "max_consecutive_losses": metrics.get("max_consecutive_losses") or 0,
        "profitable_trades": profitable,
        "alpha": metrics.get("alpha") or 0.0,
        "beta": metrics.get("beta") or 0.0,
        # Series for charts.
        "equity_curve": [{"date": d, "equity": float(e)} for d, e in zip(dates, equity_curve)],
        "drawdown_curve": _drawdown_series(equity_curve, dates),
        "monthly_returns": _monthly_returns(equity_curve, dates),
        "trades": trades_out,
        # Nested copy for callers that prefer it.
        "metrics": metrics,
    }


@backtest_bp.post("/backtest")
def run_backtest_endpoint():
    payload = request.get_json(force=True, silent=True) or {}

    symbol = (payload.get("symbol") or "").strip().upper()
    strategy_type = payload.get("strategy_type")
    parameters = payload.get("parameters") or {}
    start_date = payload.get("start_date") or config.DEFAULT_START_DATE
    end_date = payload.get("end_date") or config.DEFAULT_END_DATE
    initial_capital = float(payload.get("initial_capital") or config.INITIAL_CAPITAL)
    strategy_id = payload.get("strategy_id")

    if not symbol:
        return jsonify({"error": "symbol is required"}), 400
    if not strategy_type:
        return jsonify({"error": "strategy_type is required"}), 400

    if strategy_id is not None and Strategy.query.get(strategy_id) is None:
        return jsonify({"error": f"strategy_id {strategy_id} not found"}), 404

    try:
        strategy = build_strategy(strategy_type, parameters)
    except TypeError as e:
        return jsonify({"error": f"invalid parameters: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    data = fetch_ohlcv(symbol, start_date, end_date)
    if data.empty:
        return jsonify({"error": f"no price data for {symbol} in {start_date}..{end_date}"}), 404

    started = time.perf_counter()
    try:
        equity_curve, trade_log = run_backtest(
            strategy=strategy,
            data=data,
            config={"initial_capital": initial_capital, "commission": config.COMMISSION},
            portfolio_class=Portfolio,
        )
    except EngineError as e:
        return jsonify({"error": str(e)}), 400

    dates = [_iso(d) for d in data.index]
    benchmark = fetch_benchmark(start_date, end_date)
    metrics = compute_all(
        equity_curve=equity_curve,
        trade_log=trade_log,
        initial_capital=initial_capital,
        benchmark_prices=benchmark if not benchmark.empty else None,
        dates=dates,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    bt = Backtest(
        strategy_id=strategy_id,
        symbol=symbol,
        start_date=_iso(start_date),
        end_date=_iso(end_date),
        initial_capital=initial_capital,
        final_capital=float(equity_curve[-1]) if equity_curve else initial_capital,
        execution_time_ms=elapsed_ms,
        total_return=metrics.get("total_return") or 0.0,
        annualized_return=metrics.get("annualized_return") or 0.0,
        annualized_volatility=metrics.get("annualized_volatility") or 0.0,
        sharpe_ratio=metrics.get("sharpe_ratio") or 0.0,
        sortino_ratio=metrics.get("sortino_ratio") or 0.0,
        calmar_ratio=metrics.get("calmar_ratio") or 0.0,
        max_drawdown=metrics.get("max_drawdown") or 0.0,
        max_drawdown_start=metrics.get("max_drawdown_start"),
        max_drawdown_end=metrics.get("max_drawdown_end"),
        win_rate=metrics.get("win_rate") or 0.0,
        profit_factor=metrics.get("profit_factor"),
        total_trades=metrics.get("total_trades") or 0,
        avg_trade_duration=metrics.get("avg_trade_duration") or 0.0,
        avg_win=metrics.get("avg_win") or 0.0,
        avg_loss=metrics.get("avg_loss") or 0.0,
        max_consecutive_wins=metrics.get("max_consecutive_wins") or 0,
        max_consecutive_losses=metrics.get("max_consecutive_losses") or 0,
        alpha=metrics.get("alpha") or 0.0,
        beta=metrics.get("beta") or 0.0,
    )
    db.session.add(bt)
    db.session.flush()

    for date, equity in zip(dates, equity_curve):
        db.session.add(EquityPoint(backtest_id=bt.id, date=date, equity=float(equity)))

    for t in trade_log:
        db.session.add(
            Trade(
                backtest_id=bt.id,
                side=t.get("side", "long"),
                entry_date=_iso(t.get("entry_date")),
                exit_date=_iso(t.get("exit_date")),
                entry_price=float(t.get("entry_price", 0)),
                exit_price=float(t.get("exit_price", 0)),
                quantity=float(t.get("quantity", 0)),
                pnl=float(t.get("pnl", 0)),
                pnl_pct=float(t.get("pnl_pct", 0)),
            )
        )

    db.session.commit()

    return jsonify(_flatten_response(bt, equity_curve, trade_log, dates)), 201


@backtest_bp.get("/backtests")
def list_backtests():
    rows = Backtest.query.order_by(Backtest.created_at.desc()).limit(100).all()
    return jsonify([b.to_dict() for b in rows])


@backtest_bp.get("/backtests/<int:backtest_id>")
def get_backtest(backtest_id: int):
    bt = Backtest.query.get(backtest_id)
    if bt is None:
        return jsonify({"error": "Backtest not found"}), 404
    return jsonify(bt.to_dict(include_curve=True, include_trades=True))
