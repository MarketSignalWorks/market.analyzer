"""
Core backtesting engine.
"""

# TODO: Implement backtesting loop
def run_backtest(strategy, data, config, portfolio_class):
    portfolio = portfolio_class(
        initial_capital=config["initial_capital"],
        commission_rate=config["commission"],
    )

    equity_curve = []

    for i in range(len(data)):
        window = data.iloc[: i + 1]

        signal_df = strategy.generate_signals(window)
        signal = signal_df["signal"].iloc[-1]

        price = data["Close"].iloc[i]
        timestamp = data.index[i]

        if signal == 1:
            portfolio.execute_trade("buy", price, timestamp)
        elif signal == -1:
            portfolio.execute_trade("sell", price, timestamp)

        value = portfolio.get_portfolio_value(price)
        equity_curve.append(value)

    portfolio.close_open_position(data["Close"].iloc[-1], data.index[-1])

    return equity_curve, portfolio.get_trade_log()
