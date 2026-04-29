"""
SQLAlchemy models for strategies, backtest results, trades, and equity curve points.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Strategy(db.Model):
    __tablename__ = "strategies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    strategy_type = db.Column(db.String(50), nullable=False)
    parameters = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    backtests = db.relationship(
        "Backtest", backref="strategy", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "parameters": self.parameters or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Backtest(db.Model):
    __tablename__ = "backtests"

    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(
        db.Integer, db.ForeignKey("strategies.id", ondelete="CASCADE"), nullable=True
    )
    symbol = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.String(10), nullable=False)
    end_date = db.Column(db.String(10), nullable=False)
    initial_capital = db.Column(db.Float, nullable=False)
    final_capital = db.Column(db.Float, nullable=False)

    total_return = db.Column(db.Float, default=0.0)
    annualized_return = db.Column(db.Float, default=0.0)
    annualized_volatility = db.Column(db.Float, default=0.0)
    sharpe_ratio = db.Column(db.Float, default=0.0)
    sortino_ratio = db.Column(db.Float, default=0.0)
    calmar_ratio = db.Column(db.Float, default=0.0)
    max_drawdown = db.Column(db.Float, default=0.0)
    max_drawdown_start = db.Column(db.String(10), nullable=True)
    max_drawdown_end = db.Column(db.String(10), nullable=True)

    win_rate = db.Column(db.Float, default=0.0)
    profit_factor = db.Column(db.Float, nullable=True)
    total_trades = db.Column(db.Integer, default=0)
    avg_trade_duration = db.Column(db.Float, default=0.0)
    avg_win = db.Column(db.Float, default=0.0)
    avg_loss = db.Column(db.Float, default=0.0)
    max_consecutive_wins = db.Column(db.Integer, default=0)
    max_consecutive_losses = db.Column(db.Integer, default=0)

    alpha = db.Column(db.Float, default=0.0)
    beta = db.Column(db.Float, default=0.0)

    execution_time_ms = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    trades = db.relationship(
        "Trade", backref="backtest", lazy=True, cascade="all, delete-orphan"
    )
    equity_points = db.relationship(
        "EquityPoint", backref="backtest", lazy=True, cascade="all, delete-orphan"
    )

    def metrics_dict(self):
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "annualized_volatility": self.annualized_volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_start": self.max_drawdown_start,
            "max_drawdown_end": self.max_drawdown_end,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "avg_trade_duration": self.avg_trade_duration,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "alpha": self.alpha,
            "beta": self.beta,
        }

    def to_dict(self, include_curve=False, include_trades=False):
        out = {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metrics": self.metrics_dict(),
        }
        if include_curve:
            out["equity_curve"] = [p.to_dict() for p in self.equity_points]
        if include_trades:
            out["trades"] = [t.to_dict() for t in self.trades]
        return out


class Trade(db.Model):
    __tablename__ = "trades"

    id = db.Column(db.Integer, primary_key=True)
    backtest_id = db.Column(
        db.Integer, db.ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False
    )
    side = db.Column(db.String(10), nullable=False, default="long")
    entry_date = db.Column(db.String(10), nullable=False)
    exit_date = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    pnl = db.Column(db.Float, nullable=False)
    pnl_pct = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "side": self.side,
            "entry_date": self.entry_date,
            "exit_date": self.exit_date,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
        }


class EquityPoint(db.Model):
    __tablename__ = "equity_points"

    id = db.Column(db.Integer, primary_key=True)
    backtest_id = db.Column(
        db.Integer, db.ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False
    )
    date = db.Column(db.String(10), nullable=False)
    equity = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {"date": self.date, "equity": self.equity}
