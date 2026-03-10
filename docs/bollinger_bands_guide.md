# Bollinger Bands — Signal Team Implementation Guide

## What Are We Building?

This document is your complete reference for implementing the **Bollinger Bands trading signal** in the STRATEX codebase. It covers the algorithm, your specific task, code examples, and resources to unblock yourself.

**You do not need to implement the backtesting engine, equity curve, or trade history — that is handled by a separate team.** Your deliverable is the signal generation logic and the Bollinger Bands price chart.

---

## Understanding the Bollinger Bands Algorithm

Bollinger Bands are a volatility indicator invented by John Bollinger. They consist of three lines drawn on top of a price chart:

```
Middle Band = Rolling 20-period average (SMA) of closing price
Upper Band  = Middle Band + (2 × rolling 20-period standard deviation)
Lower Band  = Middle Band − (2 × rolling 20-period standard deviation)
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

**Resources to read before you start:**
- [Bollinger Bands explained (Investopedia)](https://www.investopedia.com/terms/b/bollingerbands.asp)
- [Original reference by John Bollinger](https://www.bollingerbands.com/bollinger-bands)

---

## Codebase Structure — What You Need to Know

```
market.analyzer/
├── backend/
│   ├── data/
│   │   └── fetcher.py             ← Person 1 works here
│   ├── strategies/
│   │   ├── base.py                ← READ THIS — base class you must extend
│   │   └── bollinger_bands.py     ← Person 2 & 3 work here (new file to create)
├── frontend/
│   ├── streamlit_app.py           ← Person 5 works here
│   └── ui/
│       └── charts.py              ← Person 4 works here
└── docs/
    └── bollinger_bands_guide.md   ← You are here
```

**Before writing any code, read `backend/strategies/base.py`.** Every strategy must subclass `BaseStrategy` and implement `generate_signals()`. Your code must follow that contract.

---

## Task 1 — Data Fetcher
**File:** `backend/data/fetcher.py`

### What You're Building
A function that downloads historical stock price data using the `yfinance` library (already listed in `requirements.txt` — no install needed beyond `pip install -r requirements.txt`).

### Your Implementation

Replace the placeholder comment in `fetcher.py` with:

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

### How to Test Your Work

Create a temporary test script (e.g. `test_fetcher.py`) in the project root:

```python
from backend.data.fetcher import fetch_ohlcv

data = fetch_ohlcv("SPY", "2022-01-01", "2024-01-01")
print(data.head())
print(f"Shape: {data.shape}")       # Should be roughly (500, 5)
print(data.columns.tolist())        # Should be ['Open', 'High', 'Low', 'Close', 'Volume']
```

Run it with: `python test_fetcher.py`

### Resources
- [yfinance documentation](https://pypi.org/project/yfinance/)
- [yfinance GitHub with usage examples](https://github.com/ranaroussi/yfinance)
- [pandas DataFrame overview](https://pandas.pydata.org/docs/user_guide/dsintro.html#dataframe)

---

## Task 2 — Bollinger Bands Math
**File:** `backend/strategies/bollinger_bands.py` (you will create this file)

### What You're Building
A standalone Python function that computes the three Bollinger Band lines from a pandas price Series. Keep it as a pure function — no class, no side effects, just math in and bands out.

### Your Implementation

Create the file `backend/strategies/bollinger_bands.py` and add:

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

### How to Test Your Work

```python
import pandas as pd
import numpy as np
from backend.strategies.bollinger_bands import compute_bollinger_bands

# Simulated price data
prices = pd.Series(np.random.uniform(100, 200, 100))
middle, upper, lower = compute_bollinger_bands(prices)

# Verify the math — upper must always be above middle, middle above lower
non_nan = ~middle.isna()
assert (upper[non_nan] > middle[non_nan]).all(), "Upper must be above middle"
assert (middle[non_nan] > lower[non_nan]).all(), "Middle must be above lower"
print("All checks passed!")
print(middle.dropna().head())
```

### Resources
- [pandas rolling().mean() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html)
- [pandas rolling().std() docs](https://pandas.pydata.org/docs/reference/api/pandas.core.window.rolling.Rolling.std.html)
- [What is standard deviation? (visual explanation)](https://www.khanacademy.org/math/statistics-probability/summarizing-quantitative-data/variance-standard-deviation-population/a/calculating-standard-deviation-step-by-step)

---

## Task 3 — Signal Generation (Strategy Class)
**File:** `backend/strategies/bollinger_bands.py` (continue in the same file as Task 2)

### What You're Building
The `BollingerBandsStrategy` class. It must extend `BaseStrategy` (read that file first!) and use the `compute_bollinger_bands()` function from Task 2 to produce a DataFrame with a `signal` column.

### Your Implementation

Add this **below** the `compute_bollinger_bands` function in the same file:

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

### How to Test Your Work

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

You should see some buy and sell signals. If you see 0 of both, something is wrong with the crossover logic — re-read the `shift(1)` logic carefully.

### Resources
- [pandas shift() — compare a row to the previous one](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.shift.html)
- [Boolean indexing in pandas](https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-indexing)
- [Python abstract base classes (ABC)](https://docs.python.org/3/library/abc.html)

---

## Task 4 — Bollinger Bands Chart
**File:** `frontend/ui/charts.py`

### What You're Building
A Plotly function that renders a candlestick price chart with the three Bollinger Band lines overlaid, plus green triangle markers for buy signals and red triangle markers for sell signals. This is what users will see in the browser.

### Your Implementation

Replace the placeholder comment in `charts.py` with:

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

### How to Test Your Work (standalone, no Streamlit)

```python
from backend.data.fetcher import fetch_ohlcv
from backend.strategies.bollinger_bands import BollingerBandsStrategy
from frontend.ui.charts import plot_bollinger_bands

data    = fetch_ohlcv("AAPL", "2023-01-01", "2024-01-01")
strat   = BollingerBandsStrategy()
signals = strat.generate_signals(data)

fig = plot_bollinger_bands(signals)
fig.show()   # This opens an interactive chart in your default browser
```

What to verify:
- Three band lines are visible on the chart
- Green triangle markers appear near buy signal dates
- Red triangle markers appear near sell signal dates
- Dark background styling matches the app

### Resources
- [Plotly candlestick chart docs](https://plotly.com/python/candlestick-charts/)
- [Plotly Scatter trace (lines and markers)](https://plotly.com/python/line-and-scatter/)
- [Plotly fill options (tonexty)](https://plotly.com/python/filled-area-plots/)
- [Plotly dark theme / layout options](https://plotly.com/python/templates/)

---

## Task 5 — Streamlit Integration
**File:** `frontend/streamlit_app.py`

### What You're Building
Add a working Bollinger Bands runner to the existing Strategy Builder page. Users pick a symbol, adjust BB parameters with sliders, click a button, and the chart + signal summary appears inline. **Do not remove or break any existing code** — find the correct location and add your section there.

### Where to Add It

Open `streamlit_app.py` and find this block:

```python
elif page == "⚡ Strategy Builder":
```

Scroll to the **bottom** of that section (look for the blank line just before the next `elif page ==`). Insert your code there, keeping the same indentation level as the rest of the Strategy Builder block.

### Your Implementation

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
                st.info("Make sure Tasks 1–4 are all implemented before running this.")
```

### How to Run the Full App

```bash
# From the project root directory:
streamlit run frontend/streamlit_app.py
```

Open the browser, go to **Strategy Builder** in the sidebar, scroll to the **Bollinger Bands Strategy** section.

### Troubleshooting

| Error | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: backend.data.fetcher` | Python can't find the module | Make sure `__init__.py` exists in `backend/` and `backend/data/` |
| `No data found for 'XYZ'` | Bad ticker symbol or date range | Try `SPY` with dates after 2010 |
| `KeyError: 'Close'` | yfinance multi-level column issue | Person 1 should add the `droplevel(1)` fix shown in Task 1 |
| Chart is blank / no signals showing | Signal logic bug | Check Person 3's crossover conditions with a print statement |

### Resources
- [Streamlit st.plotly_chart docs](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [Streamlit session_state guide](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [Streamlit input widgets reference](https://docs.streamlit.io/develop/api-reference/widgets)
- [How to import modules from a parent directory in Python](https://docs.python.org/3/reference/import.html)

---

## Integration Order — Who Depends on Who

```
Task 1 (Data Fetcher) ────────────────────────────────────────────► Task 5 (Streamlit)
Task 2 (BB Math) ──────► Task 3 (Signals) ──► Task 4 (Chart) ──► Task 5 (Streamlit)
```

**Tasks 1 and 2 can start in parallel right now.** Task 3 needs Task 2 done first. Task 4 needs Task 3 done. Task 5 integrates everything — start it last.

---

## Handoff to Backtesting Team

Once Task 5 is working, `st.session_state['bb_signals']` holds a DataFrame with these columns:

| Column | Type | Description |
|---|---|---|
| `Open, High, Low, Close, Volume` | float | Raw OHLCV price data |
| `middle` | float | Middle Bollinger Band value |
| `upper` | float | Upper band value |
| `lower` | float | Lower band value |
| `signal` | int | **1** = buy, **-1** = sell, **0** = hold |

The backtesting team reads the `signal` column to simulate trades. This contract is defined in `backend/strategies/base.py` — the `generate_signals()` return format. Do not change the column name or encoding.
