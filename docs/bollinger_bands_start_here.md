# Bollinger Bands — Start Here

## Pick Your Task

Read the descriptions below and claim one. Persons 1 and 4 can start immediately. Check the dependency chart at the bottom before you begin.

| Person | What You'll Do | File(s) | Difficulty | Can Start Now? |
|--------|---------------|---------|------------|----------------|
| **1 — Data + BB Math** | Download stock data from Yahoo Finance AND write the Bollinger Bands formula | `backend/data/fetcher.py` + `backend/strategies/bollinger_bands.py` | Medium | Yes |
| **2 — Signal Logic** | Build the strategy class that detects band crossovers and outputs buy/sell/hold | `backend/strategies/bollinger_bands.py` (below Person 1's code) | Medium | After Person 1 |
| **3 — BB Chart** | Create a Plotly candlestick chart with band lines and signal markers | `frontend/ui/charts.py` | Medium | After Person 2 |
| **4 — Streamlit UI** | Build the input controls, layout, and columns on the Strategy Builder page | `frontend/streamlit_app.py` | Medium | Yes |
| **5 — Streamlit Wiring** | Connect all the modules together — imports, button logic, error handling, session state | `frontend/streamlit_app.py` (builds on Person 4's UI) | Medium | After Persons 1–4 |

**Note:** Persons 4 and 5 both work in `streamlit_app.py`. Person 4 pushes their UI code first, then Person 5 pulls and wires the backend into it. Coordinate so you don't get merge conflicts.

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

## Person 1 — Data Fetcher + BB Math

You have two parts. Do the data fetcher first, then the BB math.

### Part A: Data Fetcher

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

### Part B: Bollinger Bands Math

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

**Push both parts before Person 2 starts.**

---

## Person 2 — Signal Logic

**File:** `backend/strategies/bollinger_bands.py` (same file as Person 1 — add your code below their `compute_bollinger_bands` function)

**What to build:** A class called `BollingerBandsStrategy` that extends `BaseStrategy` from `backend/strategies/base.py`. It must implement the `generate_signals()` method.

**Requirements:**
- Constructor takes `window` (int, default 20) and `num_std` (float, default 2.0)
- `generate_signals()` accepts a DataFrame with at minimum a `Close` column
- Use Person 1's `compute_bollinger_bands()` function to get the bands
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

## Person 3 — Bollinger Bands Chart

**File:** `frontend/ui/charts.py`

**What to build:** A function called `plot_bollinger_bands` that takes the DataFrame output from Person 2 and returns a Plotly `Figure` object showing:

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

## Person 4 — Streamlit UI Layout

**File:** `frontend/streamlit_app.py`

**What to build:** Add the Bollinger Bands UI controls to the Strategy Builder page. You are building the **layout only** — Person 5 will wire it to the backend.

**Where to add it:** Inside the `elif page == "⚡ Strategy Builder":` block, at the bottom before the next `elif`. Do **not** remove or break any existing code.

**Requirements:**
- Add a section header and description for "Bollinger Bands Strategy"
- Create two columns:
  - Left column: symbol text input (default "SPY"), start date picker, end date picker
  - Right column: window slider (5–50, default 20), std dev slider (1.0–3.0, default 2.0), initial capital input
- Add a "Run Bollinger Bands" button (primary style)
- Use unique `key` parameters on every widget (e.g. `key="bb_symbol"`) to avoid Streamlit duplicate key errors
- Add placeholder text below the button: `st.info("Wiring in progress — Person 5 will connect this.")`

**Verify your work:** Run `streamlit run frontend/streamlit_app.py`, go to Strategy Builder, and confirm the input controls and button render correctly.

**Push your code before Person 5 starts.**

**Resources:**
- [Streamlit widgets](https://docs.streamlit.io/develop/api-reference/widgets)
- [Streamlit columns layout](https://docs.streamlit.io/develop/api-reference/layout/st.columns)

---

## Person 5 — Streamlit Wiring

**File:** `frontend/streamlit_app.py` (builds on Person 4's UI — pull their code first)

**What to build:** Connect Person 4's UI to the backend modules so clicking the button actually runs the strategy.

**Requirements:**
- Add `sys.path` setup so Python can find the backend modules from the frontend directory
- Inside the button click handler:
  1. Import and call Person 1's `fetch_ohlcv()` to get price data
  2. Import and call Person 2's `BollingerBandsStrategy.generate_signals()` to compute signals
  3. Import and call Person 3's `plot_bollinger_bands()` to render the chart via `st.plotly_chart()`
  4. Show metric cards using `st.metric()`: symbol name, data point count, number of buy signals, number of sell signals
  5. Save the signal DataFrame to `st.session_state['bb_signals']` for the backtesting team
- Handle errors gracefully — show `st.error()` if data fetch fails or a module isn't implemented yet
- Remove Person 4's placeholder `st.info()` message

**Verify your work:** Run `streamlit run frontend/streamlit_app.py`, go to Strategy Builder, enter SPY, click Run. The chart and metrics should appear.

**Resources:**
- [Streamlit st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [Streamlit session_state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [Python sys.path for imports](https://docs.python.org/3/library/sys.html#sys.path)

---

## Dependency Chart

```
Person 1 (Data + Math) ──► Person 2 (Signals) ──► Person 3 (Chart) ──► Person 5 (Wiring)
Person 4 (UI Layout) ──────────────────────────────────────────────► Person 5 (Wiring)
```

Persons 1 and 4 can start right now in parallel. Person 5 goes last — they connect everything.

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
