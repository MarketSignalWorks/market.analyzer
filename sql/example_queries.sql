-- =============================================================================
-- STRATEX example queries
--
-- These queries match the endpoints in backend/routes/reports.py and the
-- "SQL Reports" page in the Streamlit frontend. Schema is defined by the
-- SQLAlchemy models in backend/models/models.py.
--
-- Tables:
--   strategies(id, name, description, strategy_type, parameters, created_at)
--   backtests(id, strategy_id, symbol, start_date, end_date,
--             initial_capital, final_capital,
--             total_return, annualized_return, annualized_volatility,
--             sharpe_ratio, sortino_ratio, calmar_ratio,
--             max_drawdown, max_drawdown_start, max_drawdown_end,
--             win_rate, profit_factor, total_trades, avg_trade_duration,
--             avg_win, avg_loss, max_consecutive_wins, max_consecutive_losses,
--             alpha, beta, execution_time_ms, created_at)
--   trades(id, backtest_id, side, entry_date, exit_date, entry_price,
--          exit_price, quantity, pnl, pnl_pct)
--   equity_points(id, backtest_id, date, equity)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Dashboard summary — top-level numbers shown on the Dashboard page.
--    Uses correlated subqueries so a single row is returned even when no
--    backtests have been recorded yet.
-- -----------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM strategies)                      AS active_strategies,
    (SELECT COUNT(*) FROM backtests)                       AS total_backtests,
    (SELECT COUNT(DISTINCT symbol) FROM backtests)         AS symbols_tested,
    (SELECT COALESCE(SUM(total_trades), 0) FROM backtests) AS total_trades,
    (SELECT COALESCE(AVG(total_return), 0) FROM backtests) AS avg_return,
    (SELECT COALESCE(MAX(total_return), 0) FROM backtests) AS best_return,
    (SELECT COALESCE(AVG(sharpe_ratio), 0) FROM backtests) AS avg_sharpe,
    (SELECT COALESCE(AVG(win_rate), 0) FROM backtests)     AS avg_win_rate;


-- -----------------------------------------------------------------------------
-- 2. Strategy performance — LEFT JOIN so strategies with zero backtests still
--    appear (with NULL/0 metrics). Sorted by best average return first.
-- -----------------------------------------------------------------------------
SELECT
    s.id                              AS strategy_id,
    s.name                            AS strategy_name,
    s.strategy_type                   AS strategy_type,
    COUNT(b.id)                       AS num_backtests,
    COALESCE(AVG(b.total_return), 0)  AS avg_return,
    COALESCE(AVG(b.sharpe_ratio), 0)  AS avg_sharpe,
    COALESCE(AVG(b.win_rate), 0)      AS avg_win_rate,
    COALESCE(MAX(b.total_return), 0)  AS best_return,
    COALESCE(MIN(b.max_drawdown), 0)  AS worst_drawdown
FROM strategies s
LEFT JOIN backtests b ON b.strategy_id = s.id
GROUP BY s.id, s.name, s.strategy_type
ORDER BY avg_return DESC;


-- -----------------------------------------------------------------------------
-- 3. Symbol performance — which tickers our strategies trade best on.
-- -----------------------------------------------------------------------------
SELECT
    symbol,
    COUNT(*)                          AS num_backtests,
    COALESCE(AVG(total_return), 0)    AS avg_return,
    COALESCE(AVG(sharpe_ratio), 0)    AS avg_sharpe,
    COALESCE(AVG(max_drawdown), 0)    AS avg_max_drawdown,
    COALESCE(SUM(total_trades), 0)    AS total_trades
FROM backtests
GROUP BY symbol
HAVING COUNT(*) > 0
ORDER BY avg_sharpe DESC;


-- -----------------------------------------------------------------------------
-- 4. Top 10 most profitable individual trades, joined to their strategy.
-- -----------------------------------------------------------------------------
SELECT
    t.entry_date,
    t.exit_date,
    t.side,
    t.entry_price,
    t.exit_price,
    t.quantity,
    t.pnl,
    t.pnl_pct,
    b.symbol            AS symbol,
    s.name              AS strategy_name
FROM trades t
JOIN backtests b      ON t.backtest_id = b.id
LEFT JOIN strategies s ON b.strategy_id = s.id
ORDER BY t.pnl DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- 5. Recent backtests — last 25 with their owning strategy name.
-- -----------------------------------------------------------------------------
SELECT
    b.id,
    b.symbol,
    b.start_date,
    b.end_date,
    b.total_return,
    b.sharpe_ratio,
    b.max_drawdown,
    b.total_trades,
    b.created_at,
    s.name AS strategy_name
FROM backtests b
LEFT JOIN strategies s ON b.strategy_id = s.id
ORDER BY b.created_at DESC
LIMIT 25;


-- -----------------------------------------------------------------------------
-- 6. Win/loss distribution per strategy — uses conditional aggregation to
--    compute winners, losers, gross profit, and gross loss in a single pass.
-- -----------------------------------------------------------------------------
SELECT
    s.name                                                          AS strategy_name,
    COUNT(t.id)                                                     AS total_trades,
    SUM(CASE WHEN t.pnl > 0 THEN 1 ELSE 0 END)                      AS winning_trades,
    SUM(CASE WHEN t.pnl < 0 THEN 1 ELSE 0 END)                      AS losing_trades,
    ROUND(AVG(CASE WHEN t.pnl > 0 THEN t.pnl END), 2)               AS avg_win,
    ROUND(AVG(CASE WHEN t.pnl < 0 THEN t.pnl END), 2)               AS avg_loss,
    ROUND(SUM(CASE WHEN t.pnl > 0 THEN t.pnl ELSE 0 END), 2)        AS gross_profit,
    ROUND(SUM(CASE WHEN t.pnl < 0 THEN t.pnl ELSE 0 END), 2)        AS gross_loss
FROM strategies s
JOIN backtests  b ON b.strategy_id = s.id
JOIN trades     t ON t.backtest_id = b.id
GROUP BY s.id, s.name
ORDER BY gross_profit DESC;


-- -----------------------------------------------------------------------------
-- 7. Best backtest per symbol — uses a correlated subquery to find each
--    symbol's highest-Sharpe run. Useful for the "leaderboard" view.
-- -----------------------------------------------------------------------------
SELECT
    b.symbol,
    s.name           AS strategy_name,
    b.sharpe_ratio,
    b.total_return,
    b.max_drawdown,
    b.start_date,
    b.end_date
FROM backtests b
LEFT JOIN strategies s ON b.strategy_id = s.id
WHERE b.sharpe_ratio = (
    SELECT MAX(sharpe_ratio) FROM backtests b2 WHERE b2.symbol = b.symbol
)
ORDER BY b.sharpe_ratio DESC;


-- -----------------------------------------------------------------------------
-- 8. Equity curve for a single backtest — used by the Backtest Results page.
--    Replace :backtest_id with the id you want to inspect.
-- -----------------------------------------------------------------------------
SELECT date, equity
FROM equity_points
WHERE backtest_id = :backtest_id
ORDER BY date ASC;


-- -----------------------------------------------------------------------------
-- 9. Monthly trade volume across all backtests — handy for spotting
--    seasonality. Works on SQLite (substr on ISO date string).
-- -----------------------------------------------------------------------------
SELECT
    substr(t.entry_date, 1, 7) AS month,
    COUNT(*)                   AS num_trades,
    ROUND(SUM(t.pnl), 2)       AS total_pnl,
    ROUND(AVG(t.pnl), 2)       AS avg_pnl
FROM trades t
GROUP BY substr(t.entry_date, 1, 7)
ORDER BY month DESC;


-- -----------------------------------------------------------------------------
-- 10. Strategies that beat SPY's typical Sharpe (~0.5 on a long-only basis).
--     Filters on a HAVING clause so it operates on aggregated metrics.
-- -----------------------------------------------------------------------------
SELECT
    s.name                            AS strategy_name,
    s.strategy_type                   AS strategy_type,
    COUNT(b.id)                       AS num_backtests,
    ROUND(AVG(b.sharpe_ratio), 2)     AS avg_sharpe,
    ROUND(AVG(b.total_return), 2)     AS avg_return
FROM strategies s
JOIN backtests   b ON b.strategy_id = s.id
GROUP BY s.id, s.name, s.strategy_type
HAVING AVG(b.sharpe_ratio) > 0.5
ORDER BY avg_sharpe DESC;
