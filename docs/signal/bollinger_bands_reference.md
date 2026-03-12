# Bollinger Bands — Reference Guide

This is the **answer key**. Try to solve your task using the Start Here doc first. Come here only if you're stuck.

---

## Git Workflow Quick Reference

| Person | Branch | Merge Order |
|--------|--------|-------------|
| 1 | `data-math` | Merges 1st |
| 2 | `signal-logic` | Merges 2nd (after Person 1) |
| 3 | `charts` | Merges 3rd (after Person 2) |
| 4 | `streamlit-ui` | Merges last (after Person 3) |

```bash
# Switch to your branch
git checkout your-branch-name

# Pull latest main before starting (especially Persons 2-4)
git pull origin main

# When done — push and open a PR
git add .
git commit -m "describe what you did"
git push origin your-branch-name
```

---

## Codebase Structure

```
market.analyzer/
├── backend/
│   ├── data/
│   │   └── fetcher.py             ← Person 1 (Part A)
│   ├── strategies/
│   │   ├── base.py                ← READ THIS — base class you must extend
│   │   └── bollinger_bands.py     ← Person 1 (Part B) + Person 2
├── frontend/
│   ├── streamlit_app.py           ← Person 4
│   └── ui/
│       └── charts.py              ← Person 3
└── docs/
    └── signal/
        ├── bollinger_bands_start_here.md   ← Task specs (no code)
        └── bollinger_bands_reference.md    ← You are here (full code)
```

---

## Understanding the Algorithm

Bollinger Bands are a volatility indicator invented by John Bollinger. They consist of three lines drawn on top of a price chart:

```
Middle Band = Rolling 20-period average (SMA) of closing price
Upper Band  = Middle Band + (2 x rolling 20-period standard deviation)
Lower Band  = Middle Band - (2 x rolling 20-period standard deviation)
```

As price volatility increases, the bands widen. As it decreases, they contract.

### Trading Logic (Mean Reversion)

| Condition | Signal | Interpretation |
|---|---|---|
| Price crosses **below** the lower band | **BUY (1)** | Stock is oversold — price stretched too far down, expect a bounce back up |
| Price crosses **above** the upper band | **SELL (-1)** | Stock is overbought — price stretched too far up, expect a pullback |
| Price is between the bands | **HOLD (0)** | No action |

### Visual Reference

```
  Price Chart:
  ─────────────────────────────────
  Upper Band ·····················  ← Overbought zone (sell signal here)

                 /\    /\
  Middle Band __/  \__/  \________  ← 20-day moving average
              \        /
  Lower Band   \______/             ← Oversold zone (buy signal here)
  ─────────────────────────────────
```

**Further reading:**
- [Bollinger Bands explained (Investopedia)](https://www.investopedia.com/terms/b/bollingerbands.asp)
- [Original reference by John Bollinger](https://www.bollingerbands.com/bollinger-bands)

---

## Person 1 Reference — Data Fetcher + BB Math

### Part A: Data Fetcher

**File:** `backend/data/fetcher.py`

```python
"""
Market data fetcher using yfinance.
"""

import yfinance as yf
import pandas as pd


def fetch_ohlcv(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Download historical OHLCV data for a stock symbol.

    Args:
        symbol:     Ticker symbol, e.g. "SPY", "AAPL", "TSLA"
        start_date: Start date string "YYYY-MM-DD"
        end_date:   End date string "YYYY-MM-DD"

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        Indexed by date (DatetimeIndex), sorted oldest to newest.
    """
    df = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True, progress=False)

    # yfinance can return multi-level columns — flatten them if so
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    df.dropna(inplace=True)
    return df
```

**Test it:**
```python
from backend.data.fetcher import fetch_ohlcv

data = fetch_ohlcv("SPY", "2022-01-01", "2024-01-01")
print(data.head())
print(f"Shape: {data.shape}")       # Should be roughly (500, 5)
print(data.columns.tolist())        # Should be ['Open', 'High', 'Low', 'Close', 'Volume']
```

### Part B: BB Math

**File:** `backend/strategies/bollinger_bands.py` (create this file)

```python
"""
Bollinger Bands indicator and strategy.
"""

import pandas as pd


def compute_bollinger_bands(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0
):
    """
    Compute the three Bollinger Band lines.

    Args:
        close:   A pandas Series of closing prices (DatetimeIndex)
        window:  Lookback period for rolling average. Default: 20
        num_std: Number of standard deviations for band width. Default: 2.0

    Returns:
        Tuple of three pandas Series: (middle, upper, lower)
        The first `window - 1` rows will be NaN — not enough history yet.
    """
    middle = close.rolling(window=window).mean()
    std    = close.rolling(window=window).std()
    upper  = middle + (num_std * std)
    lower  = middle - (num_std * std)
    return middle, upper, lower
```

**Test it:**
```python
import pandas as pd
import numpy as np
from backend.strategies.bollinger_bands import compute_bollinger_bands

prices = pd.Series(np.random.uniform(100, 200, 100))
middle, upper, lower = compute_bollinger_bands(prices)

non_nan = ~middle.isna()
assert (upper[non_nan] > middle[non_nan]).all(), "Upper must be above middle"
assert (middle[non_nan] > lower[non_nan]).all(), "Middle must be above lower"
print("All checks passed!")
```

---

## Person 2 Reference — Signal Logic

**File:** `backend/strategies/bollinger_bands.py` (add below Person 1's code)

```python
from backend.strategies.base import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands mean-reversion strategy.

    Generates buy signals when price crosses below the lower band (oversold),
    and sell signals when price crosses above the upper band (overbought).
    """

    def __init__(self, window: int = 20, num_std: float = 2.0):
        super().__init__(
            name="Bollinger Bands",
            params={"window": window, "num_std": num_std}
        )
        self.window = window
        self.num_std = num_std

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Input:
            data — DataFrame from fetch_ohlcv() — must have a 'Close' column

        Output:
            Same DataFrame with four new columns:
              - 'middle'  — 20-day SMA (middle Bollinger Band)
              - 'upper'   — upper band
              - 'lower'   — lower band
              - 'signal'  — 1 (buy), -1 (sell), or 0 (hold)
        """
        close = data['Close']
        middle, upper, lower = compute_bollinger_bands(close, self.window, self.num_std)

        data = data.copy()
        data['middle'] = middle
        data['upper']  = upper
        data['lower']  = lower

        signal = pd.Series(0, index=data.index)

        # BUY: yesterday close was >= lower band, today close fell below it
        buy_condition  = (close.shift(1) >= lower.shift(1)) & (close < lower)

        # SELL: yesterday close was <= upper band, today close went above it
        sell_condition = (close.shift(1) <= upper.shift(1)) & (close > upper)

        signal[buy_condition]  =  1
        signal[sell_condition] = -1

        data['signal'] = signal
        return data
```

**Test it:**
```python
from backend.data.fetcher import fetch_ohlcv
from backend.strategies.bollinger_bands import BollingerBandsStrategy

data    = fetch_ohlcv("SPY", "2020-01-01", "2024-01-01")
strat   = BollingerBandsStrategy(window=20, num_std=2.0)
signals = strat.generate_signals(data)

buys  = signals[signals['signal'] ==  1]
sells = signals[signals['signal'] == -1]

print(f"Total rows:    {len(signals)}")
print(f"Buy signals:   {len(buys)}")
print(f"Sell signals:  {len(sells)}")
print("\nSample buy rows:")
print(buys[['Close', 'lower', 'signal']].head())
```

---

## Person 3 Reference — BB Chart

**File:** `frontend/ui/charts.py`

```python
"""
Chart building utilities for the STRATEX frontend.
"""

import plotly.graph_objects as go
import pandas as pd


def plot_bollinger_bands(data: pd.DataFrame) -> go.Figure:
    """
    Create an interactive Bollinger Bands chart.

    Args:
        data — DataFrame output from BollingerBandsStrategy.generate_signals()
               Required columns: Open, High, Low, Close, middle, upper, lower, signal

    Returns:
        Plotly Figure object — pass this to st.plotly_chart() in Streamlit.
    """
    fig = go.Figure()

    # Candlestick price bars
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price',
        increasing_line_color='#3fb950',
        decreasing_line_color='#ff6b6b'
    ))

    # Upper band (red tint)
    fig.add_trace(go.Scatter(
        x=data.index, y=data['upper'],
        line=dict(color='rgba(255,107,107,0.7)', width=1),
        name='Upper Band'
    ))

    # Lower band (green tint) with shaded fill between upper and lower
    fig.add_trace(go.Scatter(
        x=data.index, y=data['lower'],
        line=dict(color='rgba(0,212,170,0.7)', width=1),
        fill='tonexty',
        fillcolor='rgba(120,120,120,0.08)',
        name='Lower Band'
    ))

    # Middle band (dashed white)
    fig.add_trace(go.Scatter(
        x=data.index, y=data['middle'],
        line=dict(color='rgba(255,255,255,0.5)', width=1, dash='dot'),
        name='Middle Band (SMA)'
    ))

    # Buy signals — green triangles pointing up, placed just below lower band
    buys = data[data['signal'] == 1]
    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['lower'] * 0.994,
        mode='markers',
        marker=dict(symbol='triangle-up', size=10, color='#00d4aa'),
        name='Buy Signal'
    ))

    # Sell signals — red triangles pointing down, placed just above upper band
    sells = data[data['signal'] == -1]
    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['upper'] * 1.006,
        mode='markers',
        marker=dict(symbol='triangle-down', size=10, color='#ff6b6b'),
        name='Sell Signal'
    ))

    # Dark theme layout (matches the rest of STRATEX)
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0a0e14',
        plot_bgcolor='#0a0e14',
        title='Bollinger Bands Strategy',
        xaxis_title='Date',
        yaxis_title='Price ($)',
        xaxis_rangeslider_visible=False,
        height=520,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )

    return fig
```

**Test it:**
```python
from backend.data.fetcher import fetch_ohlcv
from backend.strategies.bollinger_bands import BollingerBandsStrategy
from frontend.ui.charts import plot_bollinger_bands

data    = fetch_ohlcv("AAPL", "2023-01-01", "2024-01-01")
strat   = BollingerBandsStrategy()
signals = strat.generate_signals(data)

fig = plot_bollinger_bands(signals)
fig.show()   # Opens an interactive chart in your browser
```

---

## Person 4 Reference — Streamlit Integration

**File:** `frontend/streamlit_app.py`

Add this inside the `elif page == "⚡ Strategy Builder":` block, at the bottom before the next `elif`:

```python
    # -------------------------------------------------------------------------
    # BOLLINGER BANDS — Standalone Runner (no Flask backend needed)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("Bollinger Bands Strategy")
    st.markdown("Fetch live price data and compute BB signals directly in the browser.")

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    col_left, col_right = st.columns(2)

    with col_left:
        bb_symbol  = st.text_input("Symbol (e.g. SPY, AAPL, TSLA)", value="SPY", key="bb_symbol")
        bb_start   = st.date_input("Start Date", value=datetime.now() - timedelta(days=730), key="bb_start")
        bb_end     = st.date_input("End Date",   value=datetime.now(), key="bb_end")

    with col_right:
        bb_window  = st.slider("Window (periods)", min_value=5,   max_value=50,  value=20,  key="bb_window")
        bb_num_std = st.slider("Num Std Deviations", min_value=1.0, max_value=3.0, value=2.0, step=0.1, key="bb_std")
        bb_capital = st.number_input("Initial Capital ($)", value=10000, min_value=1000, step=1000, key="bb_capital")

    if st.button("▶ Run Bollinger Bands", type="primary", key="bb_run"):
        with st.spinner(f"Fetching {bb_symbol} data and computing signals..."):
            try:
                from backend.data.fetcher import fetch_ohlcv
                from backend.strategies.bollinger_bands import BollingerBandsStrategy
                from frontend.ui.charts import plot_bollinger_bands

                # Step 1: Fetch OHLCV data
                data = fetch_ohlcv(bb_symbol, bb_start.isoformat(), bb_end.isoformat())

                if data.empty:
                    st.error(f"No data found for '{bb_symbol}'. Check the ticker symbol and date range.")
                else:
                    # Step 2: Run the BB strategy to get signals
                    strategy = BollingerBandsStrategy(window=bb_window, num_std=bb_num_std)
                    signals  = strategy.generate_signals(data)

                    # Step 3: Render the chart
                    st.plotly_chart(plot_bollinger_bands(signals), use_container_width=True)

                    # Step 4: Show a signal summary
                    n_buys  = int((signals['signal'] ==  1).sum())
                    n_sells = int((signals['signal'] == -1).sum())

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Symbol",       bb_symbol.upper())
                    c2.metric("Data Points",  len(signals))
                    c3.metric("Buy Signals",  n_buys)
                    c4.metric("Sell Signals", n_sells)

                    # Step 5: Save signal DataFrame for the backtesting team
                    st.session_state['bb_signals'] = signals
                    st.success("Signal data saved to session state under key `bb_signals`.")

            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Make sure Persons 1-3 have all pushed their code before running this.")
```

**Test it:**
```bash
streamlit run frontend/streamlit_app.py
```

---

## Integration Order

```
Person 1 (Data + Math) ──► Person 2 (Signals) ──► Person 3 (Chart) ──┐
                                                                      ├──► Person 4 (Wiring)
                                                   Person 4 (UI) ────┘
```

**Persons 1 and 4 can start in parallel right now.** Person 4 builds the UI layout first, then wires the backend once Persons 1-3 are done.

---

## Handoff to Backtesting Team

Once done, `st.session_state['bb_signals']` holds a DataFrame with:

| Column | Type | Description |
|---|---|---|
| `Open, High, Low, Close, Volume` | float | Raw OHLCV price data |
| `middle` | float | Middle Bollinger Band value |
| `upper` | float | Upper band value |
| `lower` | float | Lower band value |
| `signal` | int | **1** = buy, **-1** = sell, **0** = hold |

The backtesting team reads the `signal` column to simulate trades. This contract is defined in `backend/strategies/base.py`.

---

## Troubleshooting

| Error | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: backend.data.fetcher` | Python can't find the module | Make sure `__init__.py` exists in `backend/` and `backend/data/` |
| `No data found for 'XYZ'` | Bad ticker symbol or date range | Try `SPY` with dates after 2010 |
| `KeyError: 'Close'` | yfinance multi-level column issue | Person 1 should add the `droplevel(1)` fix |
| Chart is blank / no signals showing | Signal logic bug | Check Person 2's crossover conditions with a print statement |
