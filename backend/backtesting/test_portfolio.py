"""
Tests for portfolio.py — covers all spec requirements and edge cases.
Run with: python -m pytest backend/backtesting/test_portfolio.py -v
"""

import math
import pytest
from datetime import datetime
from backend.backtesting.portfolio import Portfolio, Trade


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_portfolio(capital=10_000, commission=0.001):
    return Portfolio(initial_capital=capital, commission_rate=commission)

T1 = datetime(2023, 1, 1)
T2 = datetime(2023, 1, 10)
T3 = datetime(2023, 1, 20)


# ── 1. Basic buy → sell round trip ────────────────────────────────────────────

class TestBasicRoundTrip:
    def test_quantity_bought(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        # floor(10000 / (100 * 1.001)) = floor(99.9) = 99
        assert p.position["quantity"] == 99

    def test_cash_after_buy(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        cost = 99 * 100 + 99 * 100 * 0.001   # shares + commission
        assert abs(p.cash - (10_000 - cost)) < 0.01

    def test_pnl_correct(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        p.execute_trade("sell", 110, T2)
        trade = p.get_trade_log()[0]
        # pnl = (110 - 100) * 99 = 990
        assert abs(trade["pnl"] - 990.0) < 0.01

    def test_pnl_pct_correct(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        p.execute_trade("sell", 110, T2)
        trade = p.get_trade_log()[0]
        # pnl_pct = 990 / (100*99) * 100 = 10%
        assert abs(trade["pnl_pct"] - 10.0) < 0.01

    def test_commission_both_legs(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        q = p.position["quantity"]
        p.execute_trade("sell", 110, T2)
        trade = p.get_trade_log()[0]
        expected = q * 100 * 0.001 + q * 110 * 0.001
        assert abs(trade["commission_paid"] - expected) < 0.01

    def test_cash_after_sell(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        q = p.position["quantity"]
        p.execute_trade("sell", 110, T2)
        # proceeds = q*110 - q*110*0.001
        proceeds = q * 110 * (1 - 0.001)
        # cash before sell was near 0 (all-in)
        cost = q * 100 * (1 + 0.001)
        expected_cash = 10_000 - cost + proceeds
        assert abs(p.cash - expected_cash) < 0.01

    def test_position_cleared_after_sell(self):
        p = make_portfolio()
        p.execute_trade("buy", 100, T1)
        p.execute_trade("sell", 110, T2)
        assert p.position is None

    def test_trade_log_has_one_entry(self):
        p = make_portfolio()
        p.execute_trade("buy", 100, T1)
        p.execute_trade("sell", 110, T2)
        assert len(p.get_trade_log()) == 1

    def test_trade_log_returns_dicts(self):
        """Ensures metrics.py compatibility — trade log must be list of dicts."""
        p = make_portfolio()
        p.execute_trade("buy", 100, T1)
        p.execute_trade("sell", 110, T2)
        trade = p.get_trade_log()[0]
        assert isinstance(trade, dict)
        # All keys expected by metrics.py must be present
        for key in ("pnl", "pnl_pct", "entry_date", "exit_date",
                    "entry_price", "exit_price", "quantity", "commission_paid", "side"):
            assert key in trade, f"missing key: {key}"

    def test_losing_trade_pnl(self):
        p = make_portfolio()
        p.execute_trade("buy", 100, T1)
        p.execute_trade("sell", 90, T2)
        trade = p.get_trade_log()[0]
        assert trade["pnl"] < 0


# ── 2. Edge cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_buy_when_already_holding_ignored(self):
        p = make_portfolio()
        p.execute_trade("buy", 100, T1)
        pos_before = dict(p.position)
        p.execute_trade("buy", 105, T2)   # should be ignored
        assert p.position["entry_price"] == pos_before["entry_price"]
        assert p.position["quantity"] == pos_before["quantity"]

    def test_sell_with_no_position_ignored(self):
        p = make_portfolio()
        p.execute_trade("sell", 100, T1)  # no position — should do nothing
        assert p.position is None
        assert len(p.get_trade_log()) == 0
        assert abs(p.cash - 10_000) < 0.01

    def test_zero_price_skipped(self):
        p = make_portfolio()
        p.execute_trade("buy", 0, T1)
        assert p.position is None

    def test_negative_price_skipped(self):
        p = make_portfolio()
        p.execute_trade("buy", -50, T1)
        assert p.position is None

    def test_not_enough_cash_skipped(self):
        p = make_portfolio(capital=5)   # $5 capital
        p.execute_trade("buy", 100, T1)  # can't buy even 1 share
        assert p.position is None
        assert abs(p.cash - 5) < 0.01


# ── 3. force_close ────────────────────────────────────────────────────────────

class TestForceClose:
    def test_force_close_logs_trade(self):
        p = make_portfolio()
        p.execute_trade("buy", 100, T1)
        p.force_close(115, T3)
        assert len(p.get_trade_log()) == 1

    def test_force_close_clears_position(self):
        p = make_portfolio()
        p.execute_trade("buy", 100, T1)
        p.force_close(115, T3)
        assert p.position is None

    def test_force_close_with_no_position_does_nothing(self):
        p = make_portfolio()
        p.force_close(100, T1)   # should not crash or create a trade
        assert len(p.get_trade_log()) == 0

    def test_force_close_pnl(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        q = p.position["quantity"]
        p.force_close(120, T3)
        trade = p.get_trade_log()[0]
        assert abs(trade["pnl"] - (120 - 100) * q) < 0.01


# ── 4. get_portfolio_value / equity curve ─────────────────────────────────────

class TestPortfolioValue:
    def test_value_with_no_position(self):
        p = make_portfolio(10_000)
        val = p.get_portfolio_value(100)
        assert abs(val - 10_000) < 0.01

    def test_value_with_open_position(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy", 100, T1)
        q = p.position["quantity"]
        val = p.get_portfolio_value(110)
        expected = p.cash + q * 110
        assert abs(val - expected) < 0.01

    def test_equity_curve_appends_each_call(self):
        p = make_portfolio()
        p.get_portfolio_value(100)
        p.get_portfolio_value(105)
        p.get_portfolio_value(110)
        assert len(p.get_equity_curve()) == 3

    def test_equity_curve_values_correct(self):
        p = make_portfolio(10_000)
        p.get_portfolio_value(100)
        p.get_portfolio_value(200)
        curve = p.get_equity_curve()
        assert abs(curve[0] - 10_000) < 0.01
        assert abs(curve[1] - 10_000) < 0.01  # no position, cash unchanged


# ── 5. Multiple trades ────────────────────────────────────────────────────────

class TestMultipleTrades:
    def test_two_round_trips(self):
        p = make_portfolio(10_000, 0.001)
        p.execute_trade("buy",  100, datetime(2023, 1, 1))
        p.execute_trade("sell", 110, datetime(2023, 1, 10))
        p.execute_trade("buy",  110, datetime(2023, 1, 11))
        p.execute_trade("sell", 105, datetime(2023, 1, 20))
        log = p.get_trade_log()
        assert len(log) == 2
        assert log[0]["pnl"] > 0   # first trade profitable
        assert log[1]["pnl"] < 0   # second trade a loss

    def test_trade_dates_stored_correctly(self):
        p = make_portfolio()
        p.execute_trade("buy",  100, T1)
        p.execute_trade("sell", 110, T2)
        trade = p.get_trade_log()[0]
        assert trade["entry_date"] == T1
        assert trade["exit_date"] == T2
