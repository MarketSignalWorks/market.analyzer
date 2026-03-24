# Metrics Module - Quick Integration Guide

## For Frontend/Streamlit Developer

### One-Liner Integration

```python
from backend.backtesting.metrics import compute_all

results = compute_all(
    equity_curve=equity_curve,
    trade_log=trade_log,
    initial_capital=initial_capital,
    benchmark_prices=spy_prices,
    dates=dates
)
```

### What You Get Back

```python
{
    'total_return': 24.5,  # %
    'annualized_return': 11.2,  # %
    'annualized_volatility': 18.3,  # %
    'sharpe_ratio': 1.42,
    'sortino_ratio': 1.85,
    'calmar_ratio': 2.1,
    'max_drawdown': -15.3,  # %
    'max_drawdown_start': '2024-06-13',  # ISO date or None
    'max_drawdown_end': '2024-10-15',  # ISO date or None
    'win_rate': 58.3,  # %
    'profit_factor': 1.65,  # or None if only winners
    'total_trades': 42,
    'avg_trade_duration': 8.5,  # days
    'avg_win': 1250.0,  # dollars
    'avg_loss': -780.0,  # dollars
    'max_consecutive_wins': 7,
    'max_consecutive_losses': 4,
    'alpha': 3.2,  # % annualized
    'beta': 0.85,
}
```

### Display Examples

#### Performance Card
```python
results = compute_all(...)
st.metric("Total Return", f"{results['total_return']}%")
st.metric("Sharpe Ratio", results['sharpe_ratio'])
st.metric("Max Drawdown", f"{results['max_drawdown']}%")
```

#### Metrics Grid
```python
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Return", f"{results['annualized_return']}%")
with col2:
    st.metric("Volatility", f"{results['annualized_volatility']}%")
with col3:
    st.metric("Sharpe", results['sharpe_ratio'])
```

#### Trade Statistics Table
```python
trade_stats = {
    'Metric': ['Win Rate', 'Total Trades', 'Avg Win', 'Avg Loss', 'Profit Factor'],
    'Value': [
        f"{results['win_rate']}%",
        results['total_trades'],
        f"${results['avg_win']:,.2f}",
        f"${results['avg_loss']:,.2f}",
        results['profit_factor'] if results['profit_factor'] else '∞'
    ]
}
st.dataframe(pd.DataFrame(trade_stats))
```

#### Risk Assessment
```python
def risk_color(max_dd):
    if max_dd > -5: return '🟢'  # Green
    if max_dd > -15: return '🟡'  # Yellow
    return '🔴'  # Red

st.write(f"{risk_color(results['max_drawdown'])} Max Drawdown: {results['max_drawdown']}%")
```

---

## What Each Metric Means (For UI Tooltips)

| Metric | Meaning | Good Range | Tooltip |
|--------|---------|-----------|---------|
| **Total Return** | Overall profit as % | > 10% | End value compared to start |
| **Annualized Return** | Yearly extrapolated % | 5-20% | Scales any period to annual |
| **Annualized Volatility** | Yearly price swings | 10-20% | Measure of risk/choppiness |
| **Sharpe Ratio** | Return per unit risk | > 1.0 | Higher = better risk-adjusted |
| **Sortino Ratio** | Return per downside risk | > 1.0 | Only penalizes bad days |
| **Calmar Ratio** | Return per drawdown size | > 1.0 | How much you earn per 1% drawdown |
| **Max Drawdown** | Worst peak-to-trough drop | -15% to 0% | Worst case decline |
| **Win Rate** | % of profitable trades | 40-60% | Not as important as avg win/loss |
| **Profit Factor** | Gross win / Gross loss | > 1.5 | Should exceed 1.0 to be profitable |
| **Avg Trade Duration** | Average hold time (days) | Varies | Scalper=0.5, Swing=5-10, Position=30+ |
| **Avg Win / Loss** | Mean dollars made/lost | Win >> \|Loss\| | Bigger winners = bigger edge |
| **Max Consecutive** | Longest win/loss streak | - | Psychological resilience indicator |
| **Alpha** | Excess return vs market | > 0% | Beat the market? True skill signal |
| **Beta** | How much you follow market | 0.8-1.2 | 1.0 = move with SPY |

---

## Input Data Format (From Backtesting Engine)

### Equity Curve
```python
# Daily portfolio closing value
equity_curve = [
    100000,  # Day 1
    100500,  # Day 2
    100200,  # Day 3
    101000,  # Day 4
    ...
]
```

### Trade Log
```python
# Each element is a closed trade
trade_log = [
    {
        "entry_date": "2024-01-01",  # Can be string or datetime
        "exit_date": "2024-01-05",
        "entry_price": 100,
        "exit_price": 105,
        "quantity": 100,
        "side": "long",  # or "short"
        "pnl": 500,  # dollars
        "pnl_pct": 5.0  # percent
    },
    {
        "entry_date": "2024-01-05",
        "exit_date": "2024-01-10",
        "entry_price": 105,
        "exit_price": 103,
        "quantity": 100,
        "side": "long",
        "pnl": -200,
        "pnl_pct": -1.9
    },
    ...
]
```

### Benchmark Prices (SPY)
```python
# Pandas Series of daily close prices, same length as equity_curve
import pandas as pd
spy_series = pd.Series([
    380.0,  # Day 1
    381.5,  # Day 2
    380.8,  # Day 3
    382.2,  # Day 4
    ...
])
```

### Dates (Optional)
```python
# ISO format strings, one per day in equity_curve
dates = [
    "2024-01-01",
    "2024-01-02",
    "2024-01-03",
    "2024-01-04",
    ...
]
# Only needed if you want max_drawdown_start and max_drawdown_end
```

---

## Error Handling

The module is defensive—it won't crash on bad inputs:

```python
# These all work fine (return 0.0 or None for problem metrics):
compute_all([100], [], 100)  # Single day, no trades → OK
compute_all([100]*10, [], 100)  # Flat equity → OK
compute_all([100, 110], [], 100)  # No dates → max_drawdown dates are None
compute_all([100, 110], trades, 100, benchmark_prices=None)  # No SPY → alpha/beta = 0.0
```

**No exceptions thrown** for realistic backtest data.

---

## Performance Notes

- **Speed:** < 1ms for typical 1-year backtest (252 trading days, 100 trades)
- **Memory:** < 1MB for any reasonable data size
- **Dependencies:** numpy, pandas (already in requirements.txt)

---

## Debugging Checklist

If metrics look wrong:

1. **Equity curve:** Is it in chronological order (earliest first)?
2. **Trade PnLs:** Do they match manual calculations?
3. **Dates:** If max_drawdown_start/end are None, did you pass `dates` param?
4. **Benchmark:** Is SPY Series same length or longer than equity_curve?
5. **Initial capital:** Should match first element of equity_curve

---

## Example Streamlit Integration

```python
import streamlit as st
import pandas as pd
from backend.backtesting.metrics import compute_all

# Assume you got these from backtesting engine
equity_curve = [100000, 100500, 101200, ...]
trade_log = [{...}, {...}, ...]
initial_capital = 100000
spy_prices = pd.Series([...])
dates = ["2024-01-01", "2024-01-02", ...]

# Compute
results = compute_all(equity_curve, trade_log, initial_capital, spy_prices, dates)

# Display
st.title("Backtest Results")

# KPI cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Return", f"{results['total_return']}%")
col2.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
col3.metric("Max Drawdown", f"{results['max_drawdown']:.2f}%")
col4.metric("Win Rate", f"{results['win_rate']:.1f}%")

# Drawdown details
if results['max_drawdown_start']:
    st.write(f"Maximum drawdown from **{results['max_drawdown_start']}** to **{results['max_drawdown_end']}**")

# Trade stats table
st.subheader("Trade Statistics")
st.dataframe({
    "Metric": ["Trades", "Avg Duration (days)", "Avg Win", "Avg Loss", "Profit Factor"],
    "Value": [
        results['total_trades'],
        f"{results['avg_trade_duration']:.1f}",
        f"${results['avg_win']:,.0f}",
        f"${results['avg_loss']:,.0f}",
        f"{results['profit_factor']:.2f}" if results['profit_factor'] else "∞"
    ]
})

# Risk metrics
st.subheader("Risk Metrics")
st.dataframe({
    "Metric": ["Volatility", "Sharpe", "Sortino", "Calmar"],
    "Value": [
        f"{results['annualized_volatility']:.1f}%",
        f"{results['sharpe_ratio']:.2f}",
        f"{results['sortino_ratio']:.2f}",
        f"{results['calmar_ratio']:.2f}"
    ]
})

# Benchmark comparison
if results['beta'] != 0:
    st.subheader("Benchmark Comparison (vs SPY)")
    st.dataframe({
        "Metric": ["Beta", "Alpha"],
        "Value": [f"{results['beta']:.2f}", f"{results['alpha']:.2f}%"]
    })
```

---

## Common Questions

**Q: Why is profit_factor None sometimes?**  
A: When you have only winning trades (no losses to divide by). Mathematically infinity, so we return None. Display as "∞" in UI.

**Q: Why is alpha 0 when I don't provide benchmark?**  
A: We can't compare to market if you don't give us market data. Defaults to 0.0.

**Q: What if equity_curve goes to 0?**  
A: Returns will be negative, but no division-by-zero errors. Metrics will show the losses accurately.

**Q: Do I need the dates param?**  
A: Optional. Without it, max_drawdown_start/end are None. Useful for displaying "Drawdown lasted from June 13 to Oct 15."

**Q: Can I use currencies other than dollars?**  
A: Yes! trade_log PnLs and equity_curve can be in any units. Output units match your input.

---

## Next Steps

1. Integrate `compute_all()` into your Streamlit app
2. Display results in dashboard cards/tables (examples above)
3. Build comparison view for multiple backtest runs
4. Add alerts for poor metrics ("Max drawdown > 30%? ⚠️")
5. Store results in database for historical tracking
