# RSI Divergence — Reference Guide

This is the **answer key**. Try to solve your task using the Start Here doc first. Come here only if you're stuck.

---

## Git Workflow Quick Reference

| Person | Branch | Merge Order |
|--------|--------|-------------|
| 1 | `rsi-math` | Merges 1st |
| 2 | `rsi-signal-logic` | Merges 2nd (after Person 1) |
| 3 | `rsi-charts` | Merges 3rd (after Person 2) |
| 4 | `rsi-streamlit-ui` | Merges last (after Person 3) |

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
│   │   └── fetcher.py             ← Already built (from Bollinger Bands task)
│   ├── strategies/
│   │   ├── base.py                ← READ THIS — base class you must extend
│   │   └── rsi_divergence.py      ← Person 1 + Person 2 (create this file)
├── frontend/
│   ├── streamlit_app.py           ← Person 4
│   └── ui/
│       └── charts.py              ← Person 3 (add new function here)
└── docs/
    └── signal/
        ├── rsi_divergence_start_here.md   ← Task specs (no code)
        └── rsi_divergence_reference.md    ← You are here (full code)
```

---

## Understanding the Algorithm

RSI Divergence is a momentum strategy that identifies when price action and momentum stop agreeing — a reliable early warning of reversals.

### RSI Formula

```
RSI = 100 - (100 / (1 + RS))

RS = Wilder's Smoothed Average Gain / Wilder's Smoothed Average Loss
   = ewm(com=period-1, min_periods=period).mean() of gains
     ────────────────────────────────────────────────────────
     ewm(com=period-1, min_periods=period).mean() of losses
```

RSI oscillates between 0 and 100:
- **Above 70** — overbought (price ran up fast, often followed by pullback)
- **Below 30** — oversold (price dropped fast, often followed by bounce)

### Divergence Logic

| Condition | Signal | Interpretation |
|---|---|---|
| Price lower low + RSI higher low + RSI < oversold | **BUY (+1)** | Bullish divergence — selling pressure is fading |
| Price higher high + RSI lower high + RSI > overbought | **SELL (-1)** | Bearish divergence — buying pressure is fading |
| Neither condition met | **HOLD (0)** | No actionable divergence |

### Visual Reference

```
  BEARISH DIVERGENCE (SELL):
  ─────────────────────────────────────────
  Price:  · · · · /\ · · · · /\ · ·   ← higher high in price
  RSI:    · · · · /\ · · · · /·  · ·   ← lower high in RSI (diverges down)
  Signal: · · · · · · · · · · ↓  · ·   ← sell here

  BULLISH DIVERGENCE (BUY):
  ─────────────────────────────────────────
  Price:  · · · · \/ · · · · \/ · ·   ← lower low in price
  RSI:    · · · · \/ · · · · /· · ·   ← higher low in RSI (diverges up)
  Signal: · · · · · · · · · · ↑  · ·   ← buy here
```

**Further reading:**
- [RSI Divergence explained (Investopedia)](https://www.investopedia.com/terms/r/rsi.asp)
- [Divergence trading strategies (Investopedia)](https://www.investopedia.com/articles/trading/09/trade-forex-divergence.asp)

---

## Person 1 Reference — RSI Math

**File:** `backend/strategies/rsi_divergence.py` (create this file)

```python
"""
RSI Divergence indicator and strategy.
"""

import pandas as pd


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute the Relative Strength Index (RSI) using Wilder's smoothing.

    Args:
        close:  A pandas Series of closing prices (DatetimeIndex)
        period: Lookback period. Default: 14

    Returns:
        A pandas Series of RSI values in the range [0, 100].
        The first `period` rows will be NaN — not enough history yet.
    """
    delta = close.diff()

    gain = delta.clip(lower=0)           # positive changes only
    loss = -delta.clip(upper=0)          # absolute value of negative changes

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi
```

**Test it:**
```python
from backend.data.fetcher import fetch_ohlcv
from backend.strategies.rsi_divergence import compute_rsi

data = fetch_ohlcv("SPY", "2022-01-01", "2024-01-01")
rsi  = compute_rsi(data['Close'])

non_nan = rsi.dropna()
assert (non_nan >= 0).all() and (non_nan <= 100).all(), "RSI must be in [0, 100]"
print(f"RSI range: {non_nan.min():.1f} – {non_nan.max():.1f}")
print(rsi.tail(10))
```

---

## Person 2 Reference — Signal Logic

**File:** `backend/strategies/rsi_divergence.py` (add below Person 1's code)

```python
from backend.strategies.base import BaseStrategy


class RSIDivergenceStrategy(BaseStrategy):
    """
    RSI Divergence strategy.

    Generates buy signals when price makes a lower low but RSI makes a higher
    low (bullish divergence), and sell signals when price makes a higher high
    but RSI makes a lower high (bearish divergence).
    """

    def __init__(
        self,
        rsi_period: int = 14,
        divergence_window: int = 5,
        overbought: int = 70,
        oversold: int = 30,
    ):
        super().__init__(
            name="RSI Divergence",
            params={
                "rsi_period": rsi_period,
                "divergence_window": divergence_window,
                "overbought": overbought,
                "oversold": oversold,
            }
        )
        self.rsi_period        = rsi_period
        self.divergence_window = divergence_window
        self.overbought        = overbought
        self.oversold          = oversold

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Input:
            data — DataFrame from fetch_ohlcv() — must have a 'Close' column

        Output:
            Same DataFrame with two new columns:
              - 'rsi'    — RSI value at each bar (0–100)
              - 'signal' — 1 (bullish divergence), -1 (bearish divergence), 0 (hold)
        """
        data  = data.copy()
        close = data['Close']
        rsi   = compute_rsi(close, self.rsi_period)

        data['rsi'] = rsi

        w = self.divergence_window

        # Bullish divergence: price lower low, RSI higher low, RSI oversold
        bullish = (
            (close < close.shift(w)) &
            (rsi   > rsi.shift(w))   &
            (rsi   < self.oversold)
        )

        # Bearish divergence: price higher high, RSI lower high, RSI overbought
        bearish = (
            (close > close.shift(w)) &
            (rsi   < rsi.shift(w))   &
            (rsi   > self.overbought)
        )

        signal = pd.Series(0, index=data.index)
        signal[bullish] =  1
        signal[bearish] = -1

        data['signal'] = signal
        return data
```

**Test it:**
```python
from backend.data.fetcher import fetch_ohlcv
from backend.strategies.rsi_divergence import RSIDivergenceStrategy

data     = fetch_ohlcv("SPY", "2018-01-01", "2024-01-01")
strat    = RSIDivergenceStrategy(rsi_period=14, divergence_window=5, overbought=70, oversold=30)
signals  = strat.generate_signals(data)

bullish = signals[signals['signal'] ==  1]
bearish = signals[signals['signal'] == -1]

print(f"Total rows:          {len(signals)}")
print(f"Bullish divergences: {len(bullish)}")
print(f"Bearish divergences: {len(bearish)}")
print("\nSample bullish rows:")
print(bullish[['Close', 'rsi', 'signal']].head())
```

---

## Person 3 Reference — RSI Divergence Chart

**File:** `frontend/ui/charts.py` (add this function below the existing `plot_bollinger_bands` function)

```python
from plotly.subplots import make_subplots


def plot_rsi_divergence(data: pd.DataFrame) -> go.Figure:
    """
    Create an interactive RSI Divergence chart with two stacked panels.

    Args:
        data — DataFrame output from RSIDivergenceStrategy.generate_signals()
               Required columns: Open, High, Low, Close, rsi, signal

    Returns:
        Plotly Figure with a candlestick chart on top and an RSI panel below.
        Pass this to st.plotly_chart() in Streamlit.
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.04
    )

    # ── Top panel: Candlestick ──────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price',
        increasing_line_color='#3fb950',
        decreasing_line_color='#ff6b6b'
    ), row=1, col=1)

    # Buy markers on price panel — green triangles below the candle low
    buys = data[data['signal'] == 1]
    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['Low'] * 0.993,
        mode='markers',
        marker=dict(symbol='triangle-up', size=10, color='#00d4aa'),
        name='Bullish Divergence'
    ), row=1, col=1)

    # Sell markers on price panel — red triangles above the candle high
    sells = data[data['signal'] == -1]
    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['High'] * 1.007,
        mode='markers',
        marker=dict(symbol='triangle-down', size=10, color='#ff6b6b'),
        name='Bearish Divergence'
    ), row=1, col=1)

    # ── Bottom panel: RSI ───────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=data.index, y=data['rsi'],
        line=dict(color='#58a6ff', width=1.5),
        name='RSI'
    ), row=2, col=1)

    # Overbought line at 70
    fig.add_hline(y=70, line=dict(color='rgba(255,107,107,0.6)', width=1, dash='dash'), row=2, col=1)

    # Oversold line at 30
    fig.add_hline(y=30, line=dict(color='rgba(0,212,170,0.6)', width=1, dash='dash'), row=2, col=1)

    # Shaded overbought zone (70–100)
    fig.add_hrect(y0=70, y1=100, fillcolor='rgba(255,107,107,0.06)', line_width=0, row=2, col=1)

    # Shaded oversold zone (0–30)
    fig.add_hrect(y0=0, y1=30, fillcolor='rgba(0,212,170,0.06)', line_width=0, row=2, col=1)

    # Divergence markers mirrored on the RSI panel
    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['rsi'],
        mode='markers',
        marker=dict(symbol='triangle-up', size=8, color='#00d4aa'),
        showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['rsi'],
        mode='markers',
        marker=dict(symbol='triangle-down', size=8, color='#ff6b6b'),
        showlegend=False
    ), row=2, col=1)

    # ── Layout ──────────────────────────────────────────────────────────────
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0a0e14',
        plot_bgcolor='#0a0e14',
        title='RSI Divergence Strategy',
        xaxis_title='',
        xaxis2_title='Date',
        yaxis_title='Price ($)',
        yaxis2_title='RSI',
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )

    # Keep RSI y-axis fixed between 0 and 100
    fig.update_yaxes(range=[0, 100], row=2, col=1)

    return fig
```

**Test it:**
```python
from backend.data.fetcher import fetch_ohlcv
from backend.strategies.rsi_divergence import RSIDivergenceStrategy
from frontend.ui.charts import plot_rsi_divergence

data    = fetch_ohlcv("AAPL", "2022-01-01", "2024-01-01")
strat   = RSIDivergenceStrategy()
signals = strat.generate_signals(data)

fig = plot_rsi_divergence(signals)
fig.show()   # Opens an interactive two-panel chart in your browser
```

---

## Person 4 Reference — Streamlit Integration

**File:** `frontend/streamlit_app.py`

Add this inside the `elif page == "⚡ Strategy Builder":` block, below the Bollinger Bands section:

```python
    # -------------------------------------------------------------------------
    # RSI DIVERGENCE — Standalone Runner
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("RSI Divergence Strategy")
    st.markdown("Detect divergences between price and RSI momentum to catch early reversals.")

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    col_left, col_right = st.columns(2)

    with col_left:
        rsi_symbol = st.text_input("Symbol (e.g. SPY, AAPL, TSLA)", value="SPY", key="rsi_symbol")
        rsi_start  = st.date_input("Start Date", value=datetime.now() - timedelta(days=1095), key="rsi_start")
        rsi_end    = st.date_input("End Date",   value=datetime.now(), key="rsi_end")

    with col_right:
        rsi_period   = st.slider("RSI Period",           min_value=5,  max_value=30,  value=14, key="rsi_period")
        rsi_div_win  = st.slider("Divergence Window",    min_value=3,  max_value=20,  value=5,  key="rsi_div_win")
        rsi_ob       = st.slider("Overbought Threshold", min_value=60, max_value=90,  value=70, key="rsi_ob")
        rsi_os       = st.slider("Oversold Threshold",   min_value=10, max_value=40,  value=30, key="rsi_os")

    if st.button("▶ Run RSI Divergence", type="primary", key="rsi_run"):
        with st.spinner(f"Fetching {rsi_symbol} data and computing RSI divergences..."):
            try:
                from backend.data.fetcher import fetch_ohlcv
                from backend.strategies.rsi_divergence import RSIDivergenceStrategy
                from frontend.ui.charts import plot_rsi_divergence

                # Step 1: Fetch OHLCV data
                data = fetch_ohlcv(rsi_symbol, rsi_start.isoformat(), rsi_end.isoformat())

                if data.empty:
                    st.error(f"No data found for '{rsi_symbol}'. Check the ticker symbol and date range.")
                else:
                    # Step 2: Run the RSI Divergence strategy
                    strategy = RSIDivergenceStrategy(
                        rsi_period=rsi_period,
                        divergence_window=rsi_div_win,
                        overbought=rsi_ob,
                        oversold=rsi_os,
                    )
                    signals = strategy.generate_signals(data)

                    # Step 3: Render the two-panel chart
                    st.plotly_chart(plot_rsi_divergence(signals), use_container_width=True)

                    # Step 4: Show a signal summary
                    n_bullish = int((signals['signal'] ==  1).sum())
                    n_bearish = int((signals['signal'] == -1).sum())

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Symbol",               rsi_symbol.upper())
                    c2.metric("Data Points",          len(signals))
                    c3.metric("Bullish Divergences",  n_bullish)
                    c4.metric("Bearish Divergences",  n_bearish)

                    # Step 5: Save signal DataFrame for the backtesting team
                    st.session_state['rsi_signals'] = signals
                    st.success("Signal data saved to session state under key `rsi_signals`.")

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
Person 1 (RSI Math) ──► Person 2 (Signals) ──► Person 3 (Chart) ──┐
                                                                   ├──► Person 4 (Wiring)
                                               Person 4 (UI) ─────┘
```

**Persons 1 and 4 can start in parallel right now.** Person 4 builds the UI layout first, then wires the backend once Persons 1–3 are done.

---

## Handoff to Backtesting Team

Once done, `st.session_state['rsi_signals']` holds a DataFrame with:

| Column | Type | Description |
|---|---|---|
| `Open, High, Low, Close, Volume` | float | Raw OHLCV price data |
| `rsi` | float | RSI value at each bar (0–100) |
| `signal` | int | **1** = bullish divergence (buy), **-1** = bearish divergence (sell), **0** = hold |

The backtesting team reads the `signal` column to simulate trades. This contract is defined in `backend/strategies/base.py`.

---

## Troubleshooting

| Error | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: backend.strategies.rsi_divergence` | File not yet created or merged | Make sure Person 1 has pushed and merged their code |
| `KeyError: 'rsi'` | `generate_signals()` not called before charting | Person 3 should always call `generate_signals()` before passing data to `plot_rsi_divergence()` |
| `Zero bullish or bearish signals` | Thresholds too strict or window too large | Try a longer date range (3–5 years). Divergences are rare events by design |
| `RSI is all NaN` | Not enough data for the lookback period | Make sure date range is at least 30 days longer than `rsi_period` |
| Chart is blank | Missing `rsi` or `signal` column | Confirm `generate_signals()` returned both columns correctly |
