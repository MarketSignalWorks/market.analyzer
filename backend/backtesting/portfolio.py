from dataclasses import dataclass, asdict
from datetime import datetime
import math


@dataclass
class Trade:
    entry_date: datetime
    exit_date: datetime
    side: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    commission_paid: float


class Portfolio:
    def __init__(self, initial_capital: float, commission_rate: float):
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.position = None
        self.trade_log: list[Trade] = []
        self.equity_curve: list[float] = []

    def execute_trade(self, signal: str, price: float, timestamp: datetime):
        if price <= 0:
            return

        if signal == "buy" and self.position is None:
            quantity = math.floor(self.cash / (price * (1 + self.commission_rate)))
            if quantity < 1:
                return
            commission = price * quantity * self.commission_rate
            self.cash -= (price * quantity + commission)
            self.position = {
                "entry_date": timestamp,
                "entry_price": price,
                "quantity": quantity,
                "entry_commission": commission,
            }

        elif signal == "sell" and self.position is not None:
            quantity = self.position["quantity"]
            exit_commission = price * quantity * self.commission_rate
            proceeds = price * quantity - exit_commission
            self.cash += proceeds

            # pnl = (exit - entry) * quantity, per spec — commissions tracked separately
            pnl = (price - self.position["entry_price"]) * quantity
            pnl_pct = pnl / (self.position["entry_price"] * quantity) * 100
            total_commission = self.position["entry_commission"] + exit_commission

            self.trade_log.append(Trade(
                entry_date=self.position["entry_date"],
                exit_date=timestamp,
                side="long",
                entry_price=self.position["entry_price"],
                exit_price=price,
                quantity=quantity,
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission_paid=total_commission,
            ))
            self.position = None

    def get_portfolio_value(self, current_price: float) -> float:
        if self.position is None:
            value = self.cash
        else:
            value = self.cash + self.position["quantity"] * current_price
        self.equity_curve.append(value)
        return value

    def get_equity_curve(self) -> list[float]:
        return self.equity_curve

    def get_trade_log(self) -> list[dict]:
        return [asdict(t) for t in self.trade_log]

    def force_close(self, price: float, timestamp: datetime):
        """Call at end of backtest if a position is still open."""
        if self.position is not None:
            self.execute_trade("sell", price, timestamp)


# ── Quick sanity test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = Portfolio(initial_capital=10000, commission_rate=0.001)

    p.execute_trade("buy", 100, datetime(2023, 1, 1))
    print(f"Cash after buy : {p.cash:.2f}")
    print(f"Portfolio value: {p.get_portfolio_value(100):.2f}")

    p.execute_trade("sell", 110, datetime(2023, 1, 10))
    print(f"Cash after sell: {p.cash:.2f}")

    trade = p.get_trade_log()[0]
    print(f"PnL            : {trade['pnl']:.2f}")       # expect ~990 (99 shares × $10)
    print(f"PnL %          : {trade['pnl_pct']:.2f}%")  # expect ~10%
    print(f"Commission paid: {trade['commission_paid']:.2f}")
    print(f"Equity curve   : {p.get_equity_curve()}")