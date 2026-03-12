# Bollinger Bands — Start Here

## Team Roles at a Glance

Pick a role that interests you. Each person owns specific files — no overlap, no stepping on each other's toes.

| Person | Role | What You Own | File(s) | Estimated Time |
|--------|------|-------------|---------|----------------|
| **1** | **Data + Math** | Download stock data from Yahoo Finance AND compute the three Bollinger Band lines | `backend/data/fetcher.py` + `backend/strategies/bollinger_bands.py` | ~30 min |
| **2** | **Signal Logic** | Build the strategy class that detects band crossovers and outputs buy/sell/hold signals | `backend/strategies/bollinger_bands.py` (below Person 1's code) | ~30 min |
| **3** | **Chart Builder** | Create an interactive Plotly candlestick chart with band lines and buy/sell markers | `frontend/ui/charts.py` | ~30 min |
| **4** | **Streamlit Integration** | Build the full UI (inputs, layout, button) and wire it to the backend modules | `frontend/streamlit_app.py` | ~40 min |

---

## Work Order — Who Goes When

This is important. Some tasks depend on the previous person's code, so you **cannot** all start at the same time.

```
TIMELINE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Person 1 ██████████ (starts immediately)
Person 4 ██████ · · · · · · · ████ (starts UI immediately, wiring at the end)
Person 2      wait ██████████ (starts after Person 1 merges)
Person 3                wait ██████████ (starts after Person 2 merges)
Person 4 (wiring)                  wait ████ (finishes after everyone merges)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**In plain English:**
1. **Person 1** and **Person 4** start right now — they have no dependencies
2. Person 4 builds the UI layout (sliders, inputs, button) while waiting for the backend
3. When **Person 1** finishes and merges → **Person 2** pulls main and starts coding
4. When **Person 2** finishes and merges → **Person 3** pulls main and starts coding
5. When **Person 3** finishes and merges → **Person 4** pulls main and wires everything together

**Why this order?** Each person's code imports the previous person's code. Person 2's class uses Person 1's function. Person 3's chart uses Person 2's output. Person 4 connects all of it.

**Tip:** Person 1 finishes early. Once done, help Person 4 with the Streamlit wiring — they have the most work.

---

## Git Workflow — How to Use Your Branch

Each person has their own branch. This keeps main clean and prevents merge conflicts.

| Person | Branch Name |
|--------|------------|
| 1 | `data-math` |
| 2 | `signal-logic` |
| 3 | `charts` |
| 4 | `streamlit-ui` |

### Step-by-step (everyone follow this):

**1. Switch to your branch:**
```bash
git checkout data-math        # Person 1
git checkout signal-logic     # Person 2
git checkout charts           # Person 3
git checkout streamlit-ui     # Person 4
```

**2. Before you start coding, pull the latest main into your branch:**
```bash
git pull origin main
```
This is especially important for Persons 2, 3, and 4 — you need the previous person's code.

**3. Do your work.** Code your task following the instructions below.

**4. When you're done, push your branch:**
```bash
git add .
git commit -m "describe what you did"
git push origin your-branch-name
```

**5. Open a Pull Request (PR) on GitHub:**
- Go to the repo on GitHub
- You'll see a banner saying your branch has recent pushes — click "Compare & pull request"
- Add a short description of what you built
- Tag the team lead to review

**6. After your PR is approved and merged, tell the next person.** They need to pull main before starting.

### Merge order (must follow this):
```
Person 1 merges first → Person 2 merges → Person 3 merges → Person 4 merges last
```

---

## The Algorithm (Everyone Read This)

Bollinger Bands are three lines on a stock price chart:

```
Middle Band = 20-day rolling average of closing price
Upper Band  = Middle Band + (2 x 20-day rolling standard deviation)
Lower Band  = Middle Band - (2 x 20-day rolling standard deviation)
```

**What does this mean in simple terms?**
- The middle band is just the average closing price over the last 20 days. It smooths out the noise.
- Standard deviation measures how much the price typically bounces around that average. Big swings = wide bands. Small swings = narrow bands.
- About 95% of the time, the price stays inside the bands.

**Signal rules (mean reversion):**
- Price crosses below the lower band → **BUY (1)** — stock is oversold, it stretched too far down, expect it to bounce back up
- Price crosses above the upper band → **SELL (-1)** — stock is overbought, it stretched too far up, expect it to pull back
- Price stays between the bands → **HOLD (0)** — nothing unusual, do nothing

**The one-sentence version:** We're betting that extreme price moves are temporary and the price will return to its average.

**Before writing any code, read `backend/strategies/base.py`.** Your strategy class must follow that contract.

---

## Person 1 — Data Fetcher + BB Math

You have two parts. Do the data fetcher first, then the BB math.

### Part A: Data Fetcher

**File:** `backend/data/fetcher.py`

**What to build:** A function called `fetch_ohlcv` that takes a stock ticker symbol (e.g. "SPY"), a start date, and an end date, then returns a pandas DataFrame with columns: Open, High, Low, Close, Volume. The index should be dates.

**Function signature:**
```python
def fetch_ohlcv(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
```

**Requirements:**
- Use the `yfinance` library (already in `requirements.txt`)
- Handle the case where yfinance returns multi-level column headers — flatten them
- Drop any rows with missing data
- Return an empty DataFrame if the symbol is invalid (don't crash)

**Verify your work:** Call your function with `"SPY"`, `"2022-01-01"`, `"2024-01-01"` — you should get roughly 500 rows with 5 columns.

**Resources:**
- [yfinance docs](https://pypi.org/project/yfinance/)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- [pandas DataFrame overview](https://pandas.pydata.org/docs/user_guide/dsintro.html#dataframe)

### Part B: Bollinger Bands Math

**File:** `backend/strategies/bollinger_bands.py` (create this file)

**What to build:** A function called `compute_bollinger_bands` that takes a pandas Series of closing prices, a window size (default 20), and a standard deviation multiplier (default 2.0). It should return three pandas Series: the middle band, upper band, and lower band.

**Function signature:**
```python
def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    # Returns: (middle, upper, lower) — three pd.Series
```

**Requirements:**
- Middle band = rolling mean over the window period
- Upper band = middle + (multiplier x rolling standard deviation)
- Lower band = middle - (multiplier x rolling standard deviation)
- The first `window - 1` values will be NaN — that's expected, don't remove them

**Verify your work:** Pass in a Series of 100 random prices. Confirm that for every non-NaN row: upper > middle > lower.

**Resources:**
- [pandas rolling() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html)
- [pandas rolling().std() docs](https://pandas.pydata.org/docs/reference/api/pandas.core.window.rolling.Rolling.std.html)

**Push both parts before Person 2 starts.**

---

## Person 2 — Signal Logic

**File:** `backend/strategies/bollinger_bands.py` (same file as Person 1 — add your code below their `compute_bollinger_bands` function)

**Before you start:** Run `git pull origin main` to get Person 1's code.

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

**Verify your work:** Run it on SPY data from 2020-2024. You should see some rows with signal = 1 and some with signal = -1. If you get zero of both, your crossover logic has a bug.

**Resources:**
- [pandas shift() docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.shift.html)
- [Boolean indexing in pandas](https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-indexing)
- [Python abstract base classes (ABC)](https://docs.python.org/3/library/abc.html)

---

## Person 3 — Bollinger Bands Chart

**File:** `frontend/ui/charts.py`

**Before you start:** Run `git pull origin main` to get Persons 1-2's code.

**What to build:** A function called `plot_bollinger_bands` that takes the DataFrame output from Person 2 and returns a Plotly `Figure` object.

**Function signature:**
```python
def plot_bollinger_bands(data: pd.DataFrame) -> go.Figure:
```

**Your chart must include:**
1. **Candlestick chart** of the price data (Open, High, Low, Close)
2. **Three band lines** overlaid on the chart:
   - Upper band — reddish color
   - Middle band — white dashed line
   - Lower band — greenish color
   - Shade the area between the upper and lower bands lightly
3. **Buy signal markers** — green upward triangles at buy signal locations (place below the lower band so they don't overlap candles)
4. **Sell signal markers** — red downward triangles at sell signal locations (place above the upper band)

**Requirements:**
- Use `plotly.graph_objects`
- Dark theme layout to match STRATEX styling: `paper_bgcolor='#0a0e14'`, `plot_bgcolor='#0a0e14'`, `template='plotly_dark'`
- Disable the range slider on the x-axis
- Return the Figure — don't render it

**Verify your work:** Call `fig.show()` on the returned figure — it should open in your browser with a dark-themed candlestick chart, 3 band lines, and colored triangle markers.

**Resources:**
- [Plotly candlestick charts](https://plotly.com/python/candlestick-charts/)
- [Plotly Scatter traces](https://plotly.com/python/line-and-scatter/)
- [Plotly fill between traces](https://plotly.com/python/filled-area-plots/)
- [Plotly dark theme / layout options](https://plotly.com/python/templates/)

---

## Person 4 — Streamlit Integration

**File:** `frontend/streamlit_app.py`

You have two phases. Start Phase 1 immediately. Phase 2 comes after everyone else merges.

### Phase 1: UI Layout (start now)

**Where to add it:** Inside the `elif page == "⚡ Strategy Builder":` block, at the bottom before the next `elif`. Do **not** remove or break any existing code.

**What to build:**
- Section header and description for "Bollinger Bands Strategy"
- Two columns layout:
  - Left column: symbol text input (default "SPY"), start date picker, end date picker
  - Right column: window slider (5-50, default 20), std dev slider (1.0-3.0, default 2.0), initial capital input
- A "Run Bollinger Bands" button (primary style)
- Use unique `key` parameters on every widget (e.g. `key="bb_symbol"`) to avoid Streamlit duplicate key errors
- Add placeholder text below the button: `st.info("Backend wiring in progress — coming soon.")`

**Verify Phase 1:** Run `streamlit run frontend/streamlit_app.py`, go to Strategy Builder, and confirm the input controls and button render correctly.

### Phase 2: Wiring (after Persons 1-3 merge)

**Before you start:** Run `git pull origin main` to get everyone's code.

**What to build:**
- Add `sys.path` setup so Python can find the backend modules from the frontend directory
- Remove the placeholder `st.info()` message
- Inside the button click handler:
  1. Import and call Person 1's `fetch_ohlcv()` to get price data
  2. Import and call Person 2's `BollingerBandsStrategy.generate_signals()` to compute signals
  3. Import and call Person 3's `plot_bollinger_bands()` to render the chart via `st.plotly_chart()`
  4. Show metric cards using `st.metric()`: symbol name, data point count, number of buy signals, number of sell signals
  5. Save the signal DataFrame to `st.session_state['bb_signals']` for the backtesting team
- Handle errors gracefully — show `st.error()` if data fetch fails or a module isn't implemented yet

**Verify Phase 2:** Run `streamlit run frontend/streamlit_app.py`, go to Strategy Builder, enter SPY, click Run. The chart and metrics should appear.

**Resources:**
- [Streamlit widgets](https://docs.streamlit.io/develop/api-reference/widgets)
- [Streamlit columns layout](https://docs.streamlit.io/develop/api-reference/layout/st.columns)
- [Streamlit st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [Streamlit session_state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [Python sys.path for imports](https://docs.python.org/3/library/sys.html#sys.path)

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

If you're blocked, check `docs/signal/bollinger_bands_reference.md` for full code examples. Try to solve it yourself first using the resources linked above.
