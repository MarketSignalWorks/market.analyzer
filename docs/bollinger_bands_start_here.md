# Bollinger Bands — Start Here

## Pick Your Task

Read the descriptions below and claim one. Tasks 1 and 2 can start immediately. Tasks 3, 4, and 5 have dependencies — check the dependency chart at the bottom.

| Task | What You'll Do | File | Difficulty | Can Start Now? |
|------|---------------|------|------------|----------------|
| **1 — Data Fetcher** | Write a function that downloads stock price data from Yahoo Finance | `backend/data/fetcher.py` | Easiest | Yes |
| **2 — BB Math** | Write the Bollinger Bands formula (rolling average + standard deviation) | `backend/strategies/bollinger_bands.py` | Easy | Yes |
| **3 — Signal Logic** | Build the strategy class that decides when to buy, sell, or hold | `backend/strategies/bollinger_bands.py` | Medium | After Task 2 |
| **4 — BB Chart** | Create a Plotly candlestick chart with band lines and signal markers | `frontend/ui/charts.py` | Medium | After Task 3 |
| **5 — Streamlit Integration** | Wire everything into the Strategy Builder page so it runs in the browser | `frontend/streamlit_app.py` | Medium-Hard | After Tasks 1–4 |

---

## The Algorithm (Read This First)

Bollinger Bands are three lines drawn on a stock price chart:

```
Middle Band = 20-day rolling average of closing price
Upper Band  = Middle Band + (2 × 20-day rolling standard deviation)
Lower Band  = Middle Band − (2 × 20-day rolling standard deviation)
```

**Signal rules (mean reversion):**
- Price crosses below the lower band → **BUY (1)** — stock is oversold, expect bounce up
- Price crosses above the upper band → **SELL (-1)** — stock is overbought, expect pullback
- Price stays between the bands → **HOLD (0)** — no action

**Before writing any code, read `backend/strategies/base.py`.** Your strategy class must follow that contract.

---

## Task 1 — Data Fetcher

**File:** `backend/data/fetcher.py`

**What to build:** A function called `fetch_ohlcv` that takes a stock ticker symbol (e.g. "SPY"), a start date, and an end date, then returns a pandas DataFrame with columns: Open, High, Low, Close, Volume. The index should be dates.

**Requirements:**
- Use the `yfinance` library (already in `requirements.txt`)
- Handle the case where yfinance returns multi-level column headers — flatten them
- Drop any rows with missing data
- Return an empty DataFrame if the symbol is invalid (don't crash)

**Function signature:**
```python
def fetch_ohlcv(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
```

**Verify your work:** Call your function with `"SPY"`, `"2022-01-01"`, `"2024-01-01"` — you should get roughly 500 rows with 5 columns.

**Resources:**
- [yfinance docs](https://pypi.org/project/yfinance/)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)

---

## Task 2 — Bollinger Bands Math

**File:** `backend/strategies/bollinger_bands.py` (create this file)

**What to build:** A function called `compute_bollinger_bands` that takes a pandas Series of closing prices, a window size (default 20), and a standard deviation multiplier (default 2.0). It should return three pandas Series: the middle band, upper band, and lower band.

**Requirements:**
- Middle band = rolling mean over the window period
- Upper band = middle + (multiplier × rolling standard deviation)
- Lower band = middle − (multiplier × rolling standard deviation)
- The first `window - 1` values will be NaN — that's expected, don't remove them

**Function signature:**
```python
def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    # Returns: (middle, upper, lower) — three pd.Series
```

**Verify your work:** Pass in a Series of 100 random prices. Confirm that for every non-NaN row: upper > middle > lower.

**Resources:**
- [pandas rolling() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html)

---

## Task 3 — Signal Generation

**File:** `backend/strategies/bollinger_bands.py` (same file as Task 2)

**What to build:** A class called `BollingerBandsStrategy` that extends `BaseStrategy` from `backend/strategies/base.py`. It must implement the `generate_signals()` method.

**Requirements:**
- Constructor takes `window` (int, default 20) and `num_std` (float, default 2.0)
- `generate_signals()` accepts a DataFrame with at minimum a `Close` column
- Use Task 2's `compute_bollinger_bands()` function to get the bands
- Add four new columns to the DataFrame: `middle`, `upper`, `lower`, `signal`
- Signal logic uses **crossover detection**: compare today's close to today's band AND yesterday's close to yesterday's band to detect the moment price crosses a band
  - BUY (1): price was above or at the lower band yesterday, but dropped below it today
  - SELL (-1): price was below or at the upper band yesterday, but went above it today
  - HOLD (0): everything else
- Return the DataFrame with all original columns plus the four new ones

**Hint:** Look into `pandas.Series.shift()` for comparing today vs yesterday.

**Verify your work:** Run it on SPY data from 2020–2024. You should see some rows with signal = 1 and some with signal = -1. If you get zero of both, your crossover logic has a bug.

**Resources:**
- [pandas shift() docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.shift.html)
- [Boolean indexing in pandas](https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-indexing)

---

## Task 4 — Bollinger Bands Chart

**File:** `frontend/ui/charts.py`

**What to build:** A function called `plot_bollinger_bands` that takes the DataFrame output from Task 3 and returns a Plotly `Figure` object showing:

1. **Candlestick chart** of the price data (Open, High, Low, Close)
2. **Three band lines** overlaid on the chart:
   - Upper band — use a reddish color
   - Middle band — use a white dashed line
   - Lower band — use a greenish color
   - Shade the area between the upper and lower bands lightly
3. **Buy signal markers** — green upward triangles at buy signal locations
4. **Sell signal markers** — red downward triangles at sell signal locations

**Requirements:**
- Use `plotly.graph_objects` (already in `requirements.txt`)
- Dark theme layout to match STRATEX styling: `paper_bgcolor='#0a0e14'`, `plot_bgcolor='#0a0e14'`, `template='plotly_dark'`
- Disable the range slider on the x-axis
- Place buy markers slightly below the lower band, sell markers slightly above the upper band (so they don't overlap the candles)
- Return the Figure — don't render it

**Function signature:**
```python
def plot_bollinger_bands(data: pd.DataFrame) -> go.Figure:
```

**Verify your work:** Call `fig.show()` on the returned figure — it should open in your browser with a dark-themed candlestick chart, 3 band lines, and colored triangle markers.

**Resources:**
- [Plotly candlestick charts](https://plotly.com/python/candlestick-charts/)
- [Plotly Scatter traces](https://plotly.com/python/line-and-scatter/)
- [Plotly fill between traces](https://plotly.com/python/filled-area-plots/)

---

## Task 5 — Streamlit Integration

**File:** `frontend/streamlit_app.py`

**What to build:** Add a Bollinger Bands section to the existing Strategy Builder page. Do **not** remove or break any existing code — add yours below it.

**Requirements:**
- Add the section inside the `elif page == "⚡ Strategy Builder":` block, at the bottom before the next `elif`
- Add `sys.path` setup so Python can find the backend modules from the frontend directory
- Create input controls in two columns:
  - Left: symbol text input (default "SPY"), start date picker, end date picker
  - Right: window slider (5–50, default 20), std dev slider (1.0–3.0, default 2.0), initial capital input
- A "Run Bollinger Bands" button that when clicked:
  1. Calls Task 1's `fetch_ohlcv()` to get price data
  2. Calls Task 3's `BollingerBandsStrategy.generate_signals()` to compute signals
  3. Calls Task 4's `plot_bollinger_bands()` to render the chart via `st.plotly_chart()`
  4. Shows metric cards: symbol name, data point count, number of buy signals, number of sell signals
  5. Saves the signal DataFrame to `st.session_state['bb_signals']` for the backtesting team
- Handle errors gracefully — show `st.error()` if data fetch fails or a module isn't implemented yet

**Verify your work:** Run `streamlit run frontend/streamlit_app.py`, go to Strategy Builder, enter SPY, click Run. The chart and metrics should appear.

**Resources:**
- [Streamlit st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [Streamlit session_state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [Streamlit widgets](https://docs.streamlit.io/develop/api-reference/widgets)

---

## Dependency Chart

```
Task 1 (Data Fetcher) ────────────────────────────────────────► Task 5 (Streamlit)
Task 2 (BB Math) ──────► Task 3 (Signals) ──► Task 4 (Chart) ──► Task 5 (Streamlit)
```

Tasks 1 and 2 start now in parallel. Everything flows into Task 5 at the end.

---

## Handoff to Backtesting Team

Once done, `st.session_state['bb_signals']` holds a DataFrame with:

| Column | Type | What It Is |
|--------|------|-----------|
| Open, High, Low, Close, Volume | float | Raw price data |
| middle | float | Middle Bollinger Band |
| upper | float | Upper band |
| lower | float | Lower band |
| signal | int | 1 = buy, -1 = sell, 0 = hold |

The backtesting team reads the `signal` column. This contract is defined in `backend/strategies/base.py`.

---

## Stuck?

If you're blocked, check `docs/bollinger_bands_reference.md` for detailed examples. Try to solve it yourself first using the resources linked above.
