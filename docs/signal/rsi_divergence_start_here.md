# RSI Divergence — Start Here

## Team Roles at a Glance

Pick a role that interests you. Each person owns specific files — no overlap, no stepping on each other's toes.

| Person | Role | What You Own | File(s) | Estimated Time |
|--------|------|-------------|---------|----------------|
| **1** | **RSI Math** | Compute the RSI indicator line from closing prices | `backend/strategies/rsi_divergence.py` (create this file) | ~25 min |
| **2** | **Signal Logic** | Build the strategy class that detects price/RSI divergence and outputs buy/sell/hold signals | `backend/strategies/rsi_divergence.py` (below Person 1's code) | ~35 min |
| **3** | **Chart Builder** | Create an interactive Plotly chart with a candlestick panel on top and an RSI panel below, with divergence markers | `frontend/ui/charts.py` | ~35 min |
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

**Note:** The data fetcher (`fetch_ohlcv`) is already built from the Bollinger Bands task — Person 1 does not need to rebuild it. Just import it when testing.

---

## Git Workflow — How to Use Your Branch

Each person has their own branch. This keeps main clean and prevents merge conflicts.

| Person | Branch Name |
|--------|------------|
| 1 | `rsi-math` |
| 2 | `rsi-signal-logic` |
| 3 | `rsi-charts` |
| 4 | `rsi-streamlit-ui` |

### Step-by-step (everyone follow this):

**1. Switch to your branch:**
```bash
git checkout rsi-math           # Person 1
git checkout rsi-signal-logic   # Person 2
git checkout rsi-charts         # Person 3
git checkout rsi-streamlit-ui   # Person 4
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

RSI Divergence detects when a stock's **price** and its **momentum** stop agreeing with each other. This disagreement — called a divergence — often signals an upcoming reversal.

### Step 1: Compute RSI

RSI (Relative Strength Index) measures momentum on a 0–100 scale. High RSI = strong upward momentum. Low RSI = strong downward momentum.

```
RSI = 100 - (100 / (1 + RS))

Where:
  RS         = Average Gain over period / Average Loss over period
  period     = rsi_period (default: 14 days)
```

**Threshold levels:**
- RSI above 70 → overbought (price ran up too fast, may reverse down)
- RSI below 30 → oversold (price fell too fast, may reverse up)

### Step 2: Detect Divergence

Look back `divergence_window` bars (default: 5) and compare what price did vs. what RSI did:

```
BULLISH DIVERGENCE (+1 — BUY):
  Price made a LOWER low than 5 bars ago   (still falling)
  BUT RSI made a HIGHER low than 5 bars ago (momentum improving)
  AND current RSI is in the oversold zone (<30)
  ────────────────────────────────────────────
  Interpretation: Price is dropping but the selling force is weakening.
  A reversal upward is likely.

BEARISH DIVERGENCE (-1 — SELL):
  Price made a HIGHER high than 5 bars ago  (still rising)
  BUT RSI made a LOWER high than 5 bars ago (momentum weakening)
  AND current RSI is in the overbought zone (>70)
  ────────────────────────────────────────────
  Interpretation: Price is rising but the buying force is fading.
  A reversal downward is likely.

HOLD (0):
  Neither condition met — no divergence detected.
```

### Visual Reference

```
  BEARISH DIVERGENCE:
  ─────────────────────────────────
  Price:    ___/\/\___/\/\/\____     ← price hits a higher high
  RSI:      ___/\/\____/\/\____      ← RSI hits a lower high (diverges)
  Signal:                   ↓        ← bearish divergence = SELL

  BULLISH DIVERGENCE:
  ─────────────────────────────────
  Price:    ‾‾‾\/‾‾‾\/\/‾‾‾‾‾      ← price hits a lower low
  RSI:      ‾‾‾\/‾‾‾‾\/‾‾‾‾‾‾      ← RSI hits a higher low (diverges)
  Signal:              ↑             ← bullish divergence = BUY
```

**Before writing any code, read `backend/strategies/base.py`.** Your strategy class must follow that contract.

---

## Person 1 — RSI Math

**File:** `backend/strategies/rsi_divergence.py` (create this file)

**What to build:** A function called `compute_rsi` that takes a pandas Series of closing prices and an integer period (default 14), and returns a pandas Series of RSI values on the same index.

**Function signature:**
```python
def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
```

**Requirements:**
- Calculate day-over-day price changes using `diff()`
- Separate the changes into gains (positive changes) and losses (absolute value of negative changes)
- Use **exponential weighted moving average (EWMA)** with `com=period-1` and `min_periods=period` to smooth gains and losses — this is Wilder's smoothing method and gives the standard RSI output
- Compute RS = average gain / average loss
- Compute RSI = 100 − (100 / (1 + RS))
- The first `period` rows will be NaN — that's expected

**Verify your work:** Feed in 100 days of SPY closing prices. Confirm every non-NaN value is between 0 and 100.

**Resources:**
- [RSI explained (Investopedia)](https://www.investopedia.com/terms/r/rsi.asp)
- [pandas diff() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.diff.html)
- [pandas ewm() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.ewm.html)
- [pandas clip() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.clip.html)

**Push before Person 2 starts.**

---

## Person 2 — Signal Logic

**File:** `backend/strategies/rsi_divergence.py` (same file — add your code below Person 1's `compute_rsi` function)

**Before you start:** Run `git pull origin main` to get Person 1's code.

**What to build:** A class called `RSIDivergenceStrategy` that extends `BaseStrategy` from `backend/strategies/base.py`. It must implement the `generate_signals()` method.

**Requirements:**
- Constructor takes: `rsi_period` (int, default 14), `divergence_window` (int, default 5), `overbought` (int, default 70), `oversold` (int, default 30)
- `generate_signals()` accepts a DataFrame with at minimum a `Close` column
- Use Person 1's `compute_rsi()` to generate the RSI column
- Add two new columns to the DataFrame: `rsi`, `signal`
- Signal logic:
  - **Bullish divergence (1):** `close < close.shift(divergence_window)` AND `rsi > rsi.shift(divergence_window)` AND `rsi < oversold`
  - **Bearish divergence (-1):** `close > close.shift(divergence_window)` AND `rsi < rsi.shift(divergence_window)` AND `rsi > overbought`
  - **Hold (0):** everything else
- Return the DataFrame with all original columns plus `rsi` and `signal`

**Hint:** Use `pandas.Series.shift(n)` to look back `n` bars for both close and RSI values.

**Verify your work:** Run it on SPY data from 2018-2024. You should see a mix of 1s, -1s, and 0s. If every row is 0, check that you're using the right comparison direction (lower low vs higher RSI, and vice versa).

**Resources:**
- [pandas shift() docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.shift.html)
- [Boolean indexing in pandas](https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-indexing)
- [Python abstract base classes (ABC)](https://docs.python.org/3/library/abc.html)

---

## Person 3 — RSI Divergence Chart

**File:** `frontend/ui/charts.py`

**Before you start:** Run `git pull origin main` to get Persons 1–2's code.

**What to build:** A function called `plot_rsi_divergence` that takes the DataFrame output from Person 2 and returns a Plotly `Figure` object with **two stacked subplots**.

**Function signature:**
```python
def plot_rsi_divergence(data: pd.DataFrame) -> go.Figure:
```

**Your chart must include:**
1. **Top panel — Candlestick chart** of OHLCV price data
   - Buy signal markers: green upward triangles placed below the candle low at buy dates
   - Sell signal markers: red downward triangles placed above the candle high at sell dates
2. **Bottom panel — RSI line chart**
   - A single RSI line in light blue
   - Horizontal dashed lines at 70 (overbought) and 30 (oversold) in red and green respectively
   - Shaded zones: light red fill above 70, light green fill below 30
   - Buy/sell divergence markers mirrored on the RSI panel too (same x-positions)

**Requirements:**
- Use `plotly.graph_objects` and `make_subplots` from `plotly.subplots`
- Two rows: `rows=2`, `cols=1`, with `row_heights=[0.65, 0.35]` and `shared_xaxes=True`
- Dark theme layout: `paper_bgcolor='#0a0e14'`, `plot_bgcolor='#0a0e14'`, `template='plotly_dark'`
- Disable the range slider on the x-axis
- Return the Figure — don't render it

**Verify your work:** Call `fig.show()` — a browser window should open with the two-panel chart showing price candles on top and RSI oscillator on the bottom, with colored markers where divergences were detected.

**Resources:**
- [Plotly subplots](https://plotly.com/python/subplots/)
- [Plotly candlestick charts](https://plotly.com/python/candlestick-charts/)
- [Plotly Scatter traces](https://plotly.com/python/line-and-scatter/)
- [Plotly filled area between traces](https://plotly.com/python/filled-area-plots/)

---

## Person 4 — Streamlit Integration

**File:** `frontend/streamlit_app.py`

You have two phases. Start Phase 1 immediately. Phase 2 comes after everyone else merges.

### Phase 1: UI Layout (start now)

**Where to add it:** Inside the `elif page == "⚡ Strategy Builder":` block, below the Bollinger Bands section. Do **not** remove or break any existing code.

**What to build:**
- Section header and description for "RSI Divergence Strategy"
- Two columns layout:
  - Left column: symbol text input (default "SPY"), start date picker, end date picker
  - Right column: RSI period slider (5–30, default 14), divergence window slider (3–20, default 5), overbought threshold (60–90, default 70), oversold threshold (10–40, default 30)
- A "Run RSI Divergence" button (primary style)
- Use unique `key` parameters on every widget (e.g. `key="rsi_symbol"`) to avoid Streamlit duplicate key errors
- Add placeholder text below the button: `st.info("Backend wiring in progress — coming soon.")`

**Verify Phase 1:** Run `streamlit run frontend/streamlit_app.py`, go to Strategy Builder, and confirm the new RSI Divergence controls render below the Bollinger Bands section.

### Phase 2: Wiring (after Persons 1–3 merge)

**Before you start:** Run `git pull origin main` to get everyone's code.

**What to build:**
- Remove the placeholder `st.info()` message
- Inside the button click handler:
  1. Import and call `fetch_ohlcv()` to get price data
  2. Import and call `RSIDivergenceStrategy.generate_signals()` to compute signals
  3. Import and call `plot_rsi_divergence()` to render the chart via `st.plotly_chart()`
  4. Show metric cards using `st.metric()`: symbol name, data point count, number of bullish divergences, number of bearish divergences
  5. Save the signal DataFrame to `st.session_state['rsi_signals']` for the backtesting team
- Handle errors gracefully — show `st.error()` if data fetch fails or a module isn't implemented yet

**Verify Phase 2:** Run the app, enter SPY, click Run RSI Divergence. The two-panel chart and metrics should appear.

**Resources:**
- [Streamlit widgets](https://docs.streamlit.io/develop/api-reference/widgets)
- [Streamlit columns layout](https://docs.streamlit.io/develop/api-reference/layout/st.columns)
- [Streamlit st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [Streamlit session_state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)

---

## Handoff to Backtesting Team

Once done, `st.session_state['rsi_signals']` holds a DataFrame with:

| Column | Type | What It Is |
|--------|------|-----------|
| Open, High, Low, Close, Volume | float | Raw price data |
| rsi | float | RSI value (0–100) at each bar |
| signal | int | 1 = bullish divergence (buy), -1 = bearish divergence (sell), 0 = hold |

The backtesting team reads the `signal` column. This contract is defined in `backend/strategies/base.py`.

---

## Stuck?

If you're blocked, check `docs/signal/rsi_divergence_reference.md` for full code examples. Try to solve it yourself first using the resources linked above.
