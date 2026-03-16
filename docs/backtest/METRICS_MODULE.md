# Metrics Module Documentation

## Overview

The `backend/backtesting/metrics.py` module is a pure mathematics implementation that computes comprehensive performance metrics from backtest results. It takes daily equity curve values and trade logs and returns a dictionary with 18+ performance metrics.

## Architecture

The module is organized into logical sections:

1. **Helper Functions** - Internal utilities for computing daily returns, running maximums, and drawdowns
2. **Return Metrics** - Total return, annualized return, annualized volatility
3. **Risk-Adjusted Metrics** - Sharpe ratio, Sortino ratio, Calmar ratio
4. **Drawdown Metrics** - Maximum drawdown with start/end dates
5. **Trade Statistics** - Win rate, profit factor, trade duration, consecutive streaks
6. **Benchmark Comparison** - Beta and Alpha relative to SPY
7. **Master Function** - `compute_all()` that orchestrates everything

## Key Functions

### Master Function: `compute_all()`

**Most common usage** - call this single function with your backtest data:

```python
from backend.backtesting.metrics import compute_all
import pandas as pd

# Your backtest results
equity_curve = [100000, 100500, 101200, ...]  # Daily portfolio values
trade_log = [
    {
        "entry_date": "2024-01-01",
        "exit_date": "2024-01-05",
        "pnl": 1500,
        "pnl_pct": 1.5,
        ...
    },
    ...
]

# Optional: SPY prices for alpha/beta
spy_prices = pd.Series([...]  # Aligned with equity_curve dates)

# Compute all metrics
results = compute_all(
    equity_curve=equity_curve,
    trade_log=trade_log,
    initial_capital=100000,
    benchmark_prices=spy_prices,  # Optional
    dates=["2024-01-01", "2024-01-02", ...],  # Optional, for drawdown dates
    risk_free_rate=0.05  # Default is 5%
)

# Access results
print(f"Sharpe Ratio: {results['sharpe_ratio']}")
print(f"Max Drawdown: {results['max_drawdown']}%")
print(f"Win Rate: {results['win_rate']}%")
```

**Returns:** Dictionary with all computed metrics (see Output Format below)

---

## Detailed Metrics

### Return Metrics

#### Total Return
$$\text{Total Return} = \frac{\text{final\_value} - \text{initial\_capital}}{\text{initial\_capital}} \times 100$$

- **What it is:** Overall profit/loss as a percentage
- **Example:** Starting with $100,000, ending at $120,000 → 20% total return
- **Function:** `compute_total_return(equity_curve, initial_capital)`

#### Annualized Return
$$\text{Annualized Return} = \left(\frac{\text{final\_value}}{\text{initial\_capital}}\right)^{\frac{252}{\text{trading\_days}}} - 1 \times 100$$

- **What it is:** Extrapolated yearly return (scales short backtests to annual basis)
- **Why:** Allows comparing strategies with different time horizons
- **Example:** 3-month backtest with 10% return → ~40% annualized return
- **Function:** `compute_annualized_return(equity_curve, initial_capital, trading_days=None)`

#### Annualized Volatility
$$\text{Annualized Volatility} = \sqrt{252} \times \text{std}(\text{daily\_returns}) \times 100$$

- **What it is:** Annualized standard deviation of daily returns
- **Interpretation:** Measures price swings; higher = riskier
- **Typical ranges:** Conservative strategies 5-10%, aggressive 15-30%
- **Function:** `compute_annualized_volatility(equity_curve)`

---

### Risk-Adjusted Metrics

#### Sharpe Ratio
$$\text{Sharpe Ratio} = \frac{\text{mean(daily\_returns)} - r_f}{\text{std(daily\_returns)}} \times \sqrt{252}$$

- **What it is:** Return per unit of total risk
- **Benchmark:** > 1.0 is decent, > 2.0 is strong, > 3.0 is excellent
- **Interpretation:** Higher is better. A Sharpe of 1.5 means you earn 1.5% extra per 1% of volatility
- **Function:** `compute_sharpe_ratio(equity_curve, risk_free_rate=0.05)`

#### Sortino Ratio
$$\text{Sortino Ratio} = \frac{\text{mean(daily\_returns)} - r_f}{\text{std(negative\_returns)}} \times \sqrt{252}$$

- **What it is:** Like Sharpe, but only penalizes downside volatility (bad days)
- **Why:** Many prefer this—ignores upside volatility you don't mind
- **Example:** Strategy with +5%, +4%, -1%, -1% days
  - Sharpe sees all volatility
  - Sortino ignores the +5% and +4% "good" volatility
- **Typically higher than Sharpe** for strategies with upside skew
- **Function:** `compute_sortino_ratio(equity_curve, risk_free_rate=0.05)`

#### Calmar Ratio
$$\text{Calmar Ratio} = \frac{\text{annualized\_return}}{|\text{max\_drawdown}|}$$

- **What it is:** Return relative to worst drawdown
- **Interpretation:** How much yearly return you earn per 1% of drawdown risk
- **Example:** 12% annualized return / 10% max drawdown = 1.2 Calmar
- **Benchmark:** > 1.0 is good, > 3.0 is excellent
- **Function:** `compute_calmar_ratio(equity_curve, initial_capital)`

---

### Drawdown Metrics

#### Maximum Drawdown
$$\text{Max Drawdown} = \min\left(\frac{\text{current} - \text{running\_max}}{\text{running\_max}}\right)$$

- **What it is:** Largest peak-to-trough decline from a high-water mark
- **Interpretation:** Worst case scenario for your strategy
- **Example:** Portfolio goes $100k → $110k → $88k → Drawdown is (88-110)/110 = -20%
- **Critical for risk management:** Affects position sizing and client confidence
- **Function:** `compute_max_drawdown(equity_curve)`
- **With dates:** `compute_max_drawdown_with_dates(equity_curve, dates)` returns `(value, start_date, end_date)`

---

### Trade Statistics

#### Win Rate
$$\text{Win Rate} = \frac{\text{count(pnl} > 0)}{\text{total\_trades}} \times 100$$

- **Typical:** 40-50% is realistic even for good strategies (larger winners offset fewer trades)
- **Beware:** 70% win rate with tiny wins vs 30% win rate with huge winners → 30% can be better
- **Function:** `compute_win_rate(trade_log)`

#### Profit Factor
$$\text{Profit Factor} = \frac{\sum(\text{winning PnLs})}{\left|\sum(\text{losing PnLs})\right|}$$

- **What it is:** Gross profit / Gross loss ratio
- **Benchmark:** > 1.0 is profitable, > 1.5 is solid, > 2.0 is excellent
- **Example:** Won $10,000 on winners, lost $5,000 on losers → 2.0 profit factor
- **Special case:** Only winning trades → returns `None` (infinity)
- **Function:** `compute_profit_factor(trade_log)`

#### Average Trade Duration
$$\text{Avg Duration} = \frac{\sum(\text{exit\_date} - \text{entry\_date})}{\text{total\_trades}}$$

- **Unit:** Days
- **Interpretation:** How long you typically hold positions
- **Example:** Scalper might be 0.5 days, swing trader 5-10 days, position trader 30+ days
- **Function:** `compute_avg_trade_duration(trade_log)`

#### Average Win / Average Loss
- **Avg Win:** Mean PnL of profitable trades
- **Avg Loss:** Mean PnL of losing trades
- **Interpretation:** Right-hand side of the classic "let winners run, cut losers" insight
- **Good sign:** Avg Win >> |Avg Loss|
- **Function:** `compute_avg_win_loss(trade_log)` returns `(avg_win, avg_loss)`

#### Max Consecutive Wins / Losses
- **Max Consecutive Wins:** Longest streak of profitable trades
- **Max Consecutive Losses:** Longest streak of unprofitable trades
- **Interpretation:** 
  - Long win streaks = confidence builder
  - Long loss streaks = mental/account drawdown challenges
- **Functions:**
  - `compute_max_consecutive_wins(trade_log)`
  - `compute_max_consecutive_losses(trade_log)`

---

### Benchmark Comparison (vs. SPY)

#### Beta
$$\beta = \frac{\text{cov(strategy\_returns, SPY\_returns)}}{\text{var(SPY\_returns)}}$$

- **What it is:** How much your strategy moves relative to the market
- **Interpretation:**
  - β = 1.0 → moves exactly like SPY
  - β = 0.5 → half as volatile as SPY (defensive)
  - β = 1.5 → 50% more volatile than SPY (aggressive)
  - β = -0.5 → inverse correlation (hedging quality)
- **Function:** `compute_beta(equity_curve, spy_prices)`

#### Alpha
$$\alpha = r_s - (r_f + \beta \times (r_m - r_f))$$

Where:
- $r_s$ = annualized strategy return
- $r_f$ = risk-free rate (typically 5%)
- $r_m$ = annualized market (SPY) return
- $\beta$ = your strategy's beta

- **What it is:** Excess return beyond what your beta would predict
- **Interpretation:**
  - α > 0 → You beat the market relative to your risk level (skill!)
  - α = 0 → Returns are what you'd expect from beta alone
  - α < 0 → Underperforming relative to risk
- **Example:** SPY returned 10%, risk-free is 5%, your strategy returned 15%, β = 1.0
  - Expected return: 5% + 1.0 × (10% - 5%) = 10%
  - Actual return: 15%
  - Alpha: 15% - 10% = 5% (excellent!)
- **Function:** `compute_alpha(equity_curve, spy_prices, initial_capital, risk_free_rate=0.05)`

---

## Output Format

`compute_all()` returns a dictionary with this exact structure:

```python
{
    # Return metrics (%)
    "total_return": 24.5,
    "annualized_return": 11.2,
    "annualized_volatility": 18.3,
    
    # Risk-adjusted metrics
    "sharpe_ratio": 1.42,
    "sortino_ratio": 1.85,
    "calmar_ratio": 2.1,
    
    # Drawdown (%, dates as ISO strings or None)
    "max_drawdown": -15.3,
    "max_drawdown_start": "2024-06-13",
    "max_drawdown_end": "2024-10-15",
    
    # Trade statistics
    "win_rate": 58.3,
    "profit_factor": 1.65,  # or None if only winners
    "total_trades": 42,
    "avg_trade_duration": 8.5,  # in days
    "avg_win": 1250.0,
    "avg_loss": -780.0,
    "max_consecutive_wins": 7,
    "max_consecutive_losses": 4,
    
    # Benchmark comparison
    "alpha": 3.2,
    "beta": 0.85,
}
```

All numeric values are **rounded to 2 decimal places**. ISO date strings or None for dates.

---

## Edge Cases Handled

### 1. Zero Trades
```python
trade_log = []
# Returns: win_rate=0.0, profit_factor=None, total_trades=0, etc.
```

### 2. Only Winning Trades
```python
trade_log = [{"pnl": 100}, {"pnl": 200}]
# Returns: profit_factor=None (infinity), win_rate=100.0
```

### 3. Only Losing Trades
```python
trade_log = [{"pnl": -100}, {"pnl": -200}]
# Returns: profit_factor=0.0 (or very small), win_rate=0.0
```

### 4. Single Trade
```python
trade_log = [{"pnl": 500, "entry_date": "2024-01-01", "exit_date": "2024-01-05"}]
# Returns: avg_trade_duration=4.0, max_consecutive_wins=1
```

### 5. No Dates Provided
```python
compute_all(equity_curve=..., trade_log=..., initial_capital=..., dates=None)
# Returns: max_drawdown_start=None, max_drawdown_end=None
```

### 6. Misaligned Benchmark Data
```python
# equity_curve has 252 days, spy_prices has 100 days
# Aligns automatically to min length (100 days) for beta/alpha calculation
```

---

## Input Requirements

### `equity_curve`
- **Type:** List or numpy array of floats
- **Content:** Daily portfolio values (closing NAV each day)
- **Order:** Chronological (earliest to latest)
- **Min length:** 2 values
- **Example:** `[100000, 100500, 100200, 101000, ...]`

### `trade_log`
- **Type:** List of dictionaries
- **Required keys per trade:** `pnl`
- **Optional keys:** `entry_date`, `exit_date`, `entry_price`, `exit_price`, `quantity`, `side`, `pnl_pct`
- **Date format:** ISO 8601 string (e.g., "2024-01-01") or datetime object
- **Example:**
```python
[
    {
        "entry_date": "2024-01-01",
        "exit_date": "2024-01-05",
        "side": "long",
        "entry_price": 100,
        "exit_price": 105,
        "quantity": 100,
        "pnl": 500,
        "pnl_pct": 5.0
    },
    ...
]
```

### `initial_capital`
- **Type:** Float
- **Content:** Starting account value
- **Example:** `100000`

### `benchmark_prices` (Optional)
- **Type:** Pandas Series or None
- **Content:** Daily close prices of SPY (or other benchmark)
- **Length:** Should match or exceed `equity_curve` length
- **Index:** Can be dates or numeric; alignment is by position
- **Example:** `pd.Series([380.0, 381.5, 380.8, ...])`
- **If None:** Alpha and Beta return 0.0

### `dates` (Optional)
- **Type:** List of strings or None
- **Format:** ISO 8601 date strings ("YYYY-MM-DD")
- **Length:** Must equal length of `equity_curve`
- **If None:** `max_drawdown_start` and `max_drawdown_end` return None
- **Example:** `["2024-01-01", "2024-01-02", "2024-01-03", ...]`

### `risk_free_rate` (Optional)
- **Type:** Float
- **Default:** 0.05 (5% annual)
- **Usage:** Affects Sharpe, Sortino, and Alpha calculations
- **Example:** Pass 0.04 for 4% risk-free rate

---

## Common Use Cases

### Use Case 1: Display Summary to User (Dashboard)
```python
results = compute_all(equity_curve, trade_log, initial_capital, spyprices, dates)

print("=== Performance Summary ===")
print(f"Total Return: {results['total_return']}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']}")
print(f"Max Drawdown: {results['max_drawdown']}% ({results['max_drawdown_start']} to {results['max_drawdown_end']})")
print(f"Win Rate: {results['win_rate']}%")
print(f"Total Trades: {results['total_trades']}")
```

### Use Case 2: Risk Assessment
```python
if results['max_drawdown'] < -30:
    print("❌ Drawdown too high for typical investor")
elif results['max_drawdown'] < -15:
    print("⚠️ Moderate drawdown risk")
else:
    print("✓ Acceptable drawdown")

if results['sharpe_ratio'] > 2.0:
    print("✓ Excellent risk-adjusted returns")
```

### Use Case 3: Compare Strategies
```python
results_strategy_a = compute_all(eq_a, trades_a, capital, spy, dates)
results_strategy_b = compute_all(eq_b, trades_b, capital, spy, dates)

# Which is better risk-adjusted?
if results_strategy_a['sharpe_ratio'] > results_strategy_b['sharpe_ratio']:
    print("Strategy A has better risk-adjusted returns")
else:
    print("Strategy B is superior")
```

### Use Case 4: Track Over Time
```python
# Store results in database after each backtest
results = compute_all(...)
db.insert_backtest_results({
    "strategy_id": "momentum_v2",
    "timestamp": datetime.now(),
    "metrics": results
})
```

---

## Testing

Run the included test suite:

```bash
python backend/backtesting/metrics.py
```

This runs 7 comprehensive tests:
1. Sharpe ratio calculation with manual verification
2. Max drawdown with known answer
3. Trade statistics (win rate, profit factor, duration, streaks)
4. Complete `compute_all()` end-to-end
5. Edge case: zero trades
6. Edge case: only winning trades
7. Annualized metrics with realistic 1-year data

All tests output expected values and verification formulas.

---

## Integration Notes

### Coordinate with Other Modules

- **Person 2 (Backtesting Engine):** Provides `equity_curve` (list of daily NAVs) and `trade_log` (list of Trade dicts)
- **Person 5 (Data Fetching):** Provides `benchmark_prices` (Pandas Series of SPY close prices)
- **Frontend (Streamlit):** Consumes the output dict directly for dashboards

### Trade Log Format Expectation

This module expects `trade_log` items to have at minimum:
- `pnl` (float): Profit/loss in dollars
- `entry_date`, `exit_date` (string or datetime): For duration calculations

Example from backtesting engine→metrics workflow:
```python
# Backtesting engine produces:
trade_log = [
    {
        "entry_date": "2024-01-01",
        "exit_date": "2024-01-05",
        "entry_price": 100,
        "exit_price": 105,
        "quantity": 100,
        "side": "long",
        "pnl": 500,
        "pnl_pct": 5.0
    },
    ...
]

# metrics.py consumes it:
results = compute_all(equity_curve, trade_log, initial_capital)
```

### Optional Enhancements (Future)

1. **Underwater Plot Data:** Return list of (date, drawdown_pct) for visualization
2. **Monthly Returns Matrix:** For calendar heatmaps
3. **Consecutive Trade Streaks:** Detailed breakdown of win/loss sequences
4. **Regime Analysis:** Metrics split by market condition (bull/bear)
5. **Rolling Metrics:** Sharpe/volatility computed over rolling 63-day windows

---

## Formula References

All formulas use:
- $r_i$ = daily return for day $i$
- $\mu$ = mean return
- $\sigma$ = standard deviation of returns
- $\sqrt{252}$ = trading days in a year (annualization factor)
- $r_f$ = risk-free rate (daily: $(1 + r_f)^{1/252} - 1$)

**Sharpe Ratio:**
$$S = \frac{\mu - r_f}{\sigma} \sqrt{252}$$

**Sortino Ratio (downside volatility):**
$$\text{Sortino} = \frac{\mu - r_f}{\sigma_{\text{down}}} \sqrt{252}$$
where $\sigma_{\text{down}} = \sqrt{\frac{\sum \max(0, -r_i)^2}{n}}$

**Running Maximum & Drawdown:**
$$\text{HD}_t = \max(S_0, S_1, \ldots, S_t)$$
$$\text{DD}_t = \frac{S_t - \text{HD}_t}{\text{HD}_t}$$
$$\text{MDD} = \min(\text{DD}_t)$$

---

## Authors & Version

- **Module:** `backend/backtesting/metrics.py`
- **Version:** 1.0
- **Pure Python:** No external dependencies except numpy and pandas (already in requirements.txt)
- **Tested:** Yes, with 7 comprehensive test cases
