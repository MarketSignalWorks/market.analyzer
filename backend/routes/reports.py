"""
SQL-powered reporting endpoints.

These endpoints run the queries shipped in sql/example_queries.sql against
the live SQLAlchemy session so the Streamlit "SQL Reports" page can render
the same JOIN/aggregation results.
"""

from __future__ import annotations

from flask import Blueprint, jsonify
from sqlalchemy import text

from backend.models import db

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def _rows(result):
    return [dict(row._mapping) for row in result]


# -----------------------------------------------------------------------------
# Dashboard summary card (used by the Dashboard page).
# -----------------------------------------------------------------------------
@reports_bp.get("/dashboard-summary")
def dashboard_summary():
    sql = text(
        """
        SELECT
            (SELECT COUNT(*) FROM strategies)                    AS active_strategies,
            (SELECT COUNT(*) FROM backtests)                     AS total_backtests,
            (SELECT COUNT(DISTINCT symbol) FROM backtests)       AS symbols_tested,
            (SELECT COALESCE(SUM(total_trades), 0) FROM backtests) AS total_trades,
            (SELECT COALESCE(AVG(total_return), 0) FROM backtests) AS avg_return,
            (SELECT COALESCE(MAX(total_return), 0) FROM backtests) AS best_return,
            (SELECT COALESCE(AVG(sharpe_ratio), 0) FROM backtests) AS avg_sharpe,
            (SELECT COALESCE(AVG(win_rate), 0) FROM backtests)     AS avg_win_rate
        """
    )
    row = db.session.execute(sql).first()
    return jsonify(dict(row._mapping) if row else {})


# -----------------------------------------------------------------------------
# SQL Reports page — endpoint names match the frontend's report_options dict.
# -----------------------------------------------------------------------------
@reports_bp.get("/strategy-comparison")
def strategy_comparison():
    sql = text(
        """
        SELECT
            s.name                            AS strategy_name,
            s.strategy_type                   AS strategy_type,
            COUNT(b.id)                       AS total_backtests,
            COALESCE(AVG(b.total_return), 0)  AS avg_return,
            COALESCE(AVG(b.sharpe_ratio), 0)  AS avg_sharpe,
            COALESCE(AVG(b.max_drawdown), 0)  AS avg_max_drawdown,
            COALESCE(MAX(b.total_return), 0)  AS best_return,
            COALESCE(MIN(b.total_return), 0)  AS worst_return
        FROM strategies s
        LEFT JOIN backtests b ON s.id = b.strategy_id
        GROUP BY s.id, s.name, s.strategy_type
        HAVING COUNT(b.id) > 0
        ORDER BY avg_return DESC
        """
    )
    return jsonify(_rows(db.session.execute(sql)))


@reports_bp.get("/performance-by-symbol")
def performance_by_symbol():
    sql = text(
        """
        SELECT
            b.symbol,
            s.strategy_type,
            COUNT(b.id)                       AS backtest_count,
            COALESCE(AVG(b.total_return), 0)  AS avg_return,
            COALESCE(AVG(b.sharpe_ratio), 0)  AS avg_sharpe,
            SUM(CASE WHEN b.total_return > 0 THEN 1 ELSE 0 END) AS profitable_runs
        FROM backtests b
        LEFT JOIN strategies s ON b.strategy_id = s.id
        GROUP BY b.symbol, s.strategy_type
        ORDER BY b.symbol, avg_return DESC
        """
    )
    return jsonify(_rows(db.session.execute(sql)))


@reports_bp.get("/time-analysis")
def time_analysis():
    sql = text(
        """
        SELECT
            strftime('%Y-%m', b.created_at)   AS month,
            COUNT(b.id)                       AS backtests_run,
            COALESCE(AVG(b.total_return), 0)  AS avg_return,
            COALESCE(AVG(b.sharpe_ratio), 0)  AS avg_sharpe,
            COALESCE(SUM(b.total_trades), 0)  AS total_trades
        FROM backtests b
        GROUP BY strftime('%Y-%m', b.created_at)
        ORDER BY month DESC
        LIMIT 12
        """
    )
    return jsonify(_rows(db.session.execute(sql)))


@reports_bp.get("/top-performers")
def top_performers():
    sql = text(
        """
        SELECT
            b.id,
            s.name,
            b.symbol,
            b.total_return,
            b.sharpe_ratio,
            b.max_drawdown,
            b.win_rate,
            b.total_trades
        FROM backtests b
        LEFT JOIN strategies s ON b.strategy_id = s.id
        ORDER BY b.total_return DESC
        LIMIT 10
        """
    )
    return jsonify(_rows(db.session.execute(sql)))


@reports_bp.get("/risk-metrics")
def risk_metrics():
    sql = text(
        """
        SELECT
            s.strategy_type,
            COUNT(b.id)                                                       AS sample_size,
            COALESCE(AVG(b.max_drawdown), 0)                                  AS avg_drawdown,
            COALESCE(MIN(b.max_drawdown), 0)                                  AS worst_drawdown,
            COALESCE(AVG(b.sharpe_ratio), 0)                                  AS avg_sharpe,
            COALESCE(AVG(b.total_return / NULLIF(ABS(b.max_drawdown), 0)), 0) AS return_to_drawdown
        FROM backtests b
        LEFT JOIN strategies s ON b.strategy_id = s.id
        GROUP BY s.strategy_type
        ORDER BY avg_sharpe DESC
        """
    )
    return jsonify(_rows(db.session.execute(sql)))


# Convenience extras kept from the earlier pass.
@reports_bp.get("/recent-backtests")
def recent_backtests():
    sql = text(
        """
        SELECT
            b.id, b.symbol, b.start_date, b.end_date,
            b.total_return, b.sharpe_ratio, b.max_drawdown,
            b.total_trades, b.created_at,
            s.name AS strategy_name
        FROM backtests b
        LEFT JOIN strategies s ON b.strategy_id = s.id
        ORDER BY b.created_at DESC
        LIMIT 25
        """
    )
    return jsonify(_rows(db.session.execute(sql)))


@reports_bp.get("/top-trades")
def top_trades():
    sql = text(
        """
        SELECT
            t.entry_date, t.exit_date, t.side,
            t.entry_price, t.exit_price, t.quantity,
            t.pnl, t.pnl_pct,
            b.symbol            AS symbol,
            s.name              AS strategy_name
        FROM trades t
        JOIN backtests  b ON t.backtest_id = b.id
        LEFT JOIN strategies s ON b.strategy_id = s.id
        ORDER BY t.pnl DESC
        LIMIT 10
        """
    )
    return jsonify(_rows(db.session.execute(sql)))
