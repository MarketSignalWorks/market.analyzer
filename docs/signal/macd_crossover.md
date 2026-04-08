# MACD Crossover — Full Guide

## Team Roles at a Glance

| Person | Role                                           | What You Own                                                                          | File(s)                                                        | Est. Time |
| ------ | ---------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------- | --------- |
| **1**  | **MACD Math + Feature Engineering**            | Compute MACD indicators, 200 EMA trend line, and ML input features | `backend/strategies/macd_crossover.py` (create this file)      | ~45 min   |
| **2**  | **Signal Logic + Regime Detection + ML Model** | Strategy class, zero-line filter, cooldown, 200 EMA gate, K-means regime filter, ML confidence model | `backend/strategies/macd_crossover.py` (below Person 1's code) | ~60 min   |
| **3**  | **Chart Builder + Regime Overlay**             | Two-panel chart with 200 EMA line, regime background bands, confidence annotations | `frontend/ui/charts.py`                                        | ~50 min   |
| **4**  | **Streamlit + Walk-Forward Validation**        | UI controls, out-of-sample backtesting, Sharpe ratio, max drawdown display | `frontend/streamlit_app.py`                                    | ~65 min   |

---

## Work Order — Who Goes When

```
TIMELINE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Person 1 ██████████ (starts immediately)
Person 4 ██████ · · · · · · · ████ (Phase 1 now, Phase 2 wiring at end)
Person 2      wait ██████████ (starts after Person 1 merges)
Person 3                wait ██████████ (starts after Person 2 merges)
Person 4 (wiring)                  wait ████ (finishes after everyone merges)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

1. **Person 1** and **Person 4** start right now
2. Person 4 builds the full UI layout (all sliders, inputs, button) while waiting for backend
3. Person 1 merges → Person 2 pulls and starts
4. Person 2 merges → Person 3 pulls and starts
5. Person 3 merges → Person 4 pulls and wires everything

**Note:** `fetch_ohlcv` is already built from Bollinger Bands. Do not rebuild it — just import it.

---

## Git Workflow

| Person | Branch Name         |
| ------ | ------------------- |
| 1      | `macd-math`         |
| 2      | `macd-signal-logic` |
| 3      | `macd-charts`       |
| 4      | `macd-streamlit-ui` |

```bash
# Switch to your branch
git checkout macd-math           # Person 1
git checkout macd-signal-logic   # Person 2
git checkout macd-charts         # Person 3
git checkout macd-streamlit-ui   # Person 4

# Always pull main before you start
git pull origin main

# When done
git add .
git commit -m "describe what you did"
git push origin your-branch-name
```

Open a Pull Request on GitHub. Tag the team lead. Wait for approval before the next person starts.

**Merge order:** Person 1 → Person 2 → Person 3 → Person 4

---

## The Algorithm (Everyone Read This)

MACD (Moving Average Convergence/Divergence) measures the relationship between two exponential moving averages of price. When faster momentum crosses slower momentum, it signals a potential trend shift.

### Step 1: Compute the MACD Line

```
MACD Line = EMA(fast_period) − EMA(slow_period)

Defaults:
  fast_period  = 12   (short-term momentum)
  slow_period  = 26   (long-term momentum)
```

Positive MACD → short-term average above long-term → bullish momentum.
Negative MACD → short-term below long-term → bearish momentum.

### Step 2: Compute the Signal Line

```
Signal Line = EMA(signal_period) of MACD Line   [default: 9]
```

The signal line is a smoothed version of MACD. Crossovers between the two = buy/sell triggers.

### Step 3: Compute the Histogram

```
Histogram = MACD Line − Signal Line
```

Growing bars → momentum building. Shrinking bars → momentum fading. Bars flipping sign = crossover.

### Step 4: Detect Crossovers

```
BULLISH CROSSOVER (+1 — BUY):
  Previous bar: MACD < Signal
  Current bar:  MACD > Signal
  AND Histogram > histogram_threshold (default 0.0)

BEARISH CROSSOVER (-1 — SELL):
  Previous bar: MACD > Signal
  Current bar:  MACD < Signal
  AND Histogram < -histogram_threshold

HOLD (0): no crossover this bar
```

### Step 5: All Filters Applied (what separates this from a basic implementation)

**Zero-line filter** — Only take bullish crossovers when MACD > 0 (uptrend confirmed). Only take bearish crossovers when MACD < 0. Cuts false signals in choppy markets.

**Cooldown debounce** — After a signal fires, ignore the next N bars. Prevents thrashing during choppy crossover clusters.

**200 EMA trend filter** — The 200 EMA (Exponential Moving Average) is computed over the last 200 closing prices, giving more weight to recent prices than older ones. It acts as a long-term trend line. If price is above the 200 EMA, the stock is in an uptrend. Below it, a downtrend. We only take bullish MACD crossovers when price is above the 200 EMA, and only take bearish crossovers when price is below it. This prevents trading against the dominant trend — one of the most common mistakes in momentum strategies.

Why EMA and not SMA (simple average)? Because MACD is itself built on EMAs. Both the 12-period and 26-period lines that make up MACD use exponential weighting. Using a 200 EMA as the trend filter keeps the entire system internally consistent — everything reacts to recent price action with the same exponential logic. A 200 SMA would lag behind trend changes more, creating mismatches where MACD signals a new trend but the trend filter still references old price data.

**Regime detection** — Use K-means clustering on volatility + momentum features to classify each period as "trending" or "choppy." Only fire signals in trending regimes.

**ML confidence filter** — Train a logistic regression on indicator features (MACD slope, histogram momentum, price momentum, volatility) to estimate the probability the trade goes in the expected direction. Only take signals above a confidence threshold. Trained on historical data only — tested on unseen data (no look-ahead bias).

**Walk-forward validation** — Split data 70/30 into train and test sets. Fit the ML model on train, run the strategy on test only. Compute Sharpe ratio and max drawdown on the out-of-sample test set. This is how quant researchers prove a strategy isn't overfit to historical data.

### Visual Reference

```
  BULLISH CROSSOVER:
  ─────────────────────────────────
  MACD:    ___╲___╱──────────      ← MACD crosses above signal
  Signal:  ────────────────────
  Hist:    ███▓░░  ░░▓███████      ← bars flip negative→positive
  Signal:         ↑ BUY

  BEARISH CROSSOVER:
  ─────────────────────────────────
  MACD:    ────────────╲_______    ← MACD crosses below signal
  Signal:  ────────────────────
  Hist:    ███████░░  ░░▓███▓░     ← bars flip positive→negative
  Signal:             ↓ SELL
```

**Before writing any code, read `backend/strategies/base.py`.** Your class must follow that contract.

---

## Person 1 — MACD Math + Feature Engineering

**File:** `backend/strategies/macd_crossover.py` (create this file)

You own three functions. Person 2 depends on all of them — build each one carefully before pushing.

### Function 1: `compute_macd`

```python
def compute_macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
```

**Requirements:**

- Fast EMA: `close.ewm(span=fast_period, adjust=False).mean()`
- Slow EMA: `close.ewm(span=slow_period, adjust=False).mean()`
- MACD line = fast EMA − slow EMA
- Signal line = `macd_line.ewm(span=signal_period, adjust=False).mean()`
- Histogram = MACD line − signal line
- Return `(macd_line, signal_line, histogram)` on the same index as `close`
- First `slow_period` rows will be NaN — expected

### Function 2: `compute_features`

```python
def compute_features(data: pd.DataFrame) -> pd.DataFrame:
```

**Input:** DataFrame that already has `Close`, `macd`, `signal_line`, `histogram` columns (added by Person 2 before calling this).

**What to build:** Add five new columns that describe the _shape_ and _momentum_ of the MACD indicator — these are what the ML model trains on.

| Column to add    | Formula                                          | What it captures                         |
| ---------------- | ------------------------------------------------ | ---------------------------------------- |
| `macd_slope`     | `data['macd'].diff()`                            | Is MACD accelerating or decelerating?    |
| `hist_slope`     | `data['histogram'].diff()`                       | Is the histogram growing or shrinking?   |
| `price_momentum` | `data['Close'].pct_change(5)`                    | 5-bar price return                       |
| `volatility`     | `data['Close'].pct_change().rolling(20).std()`   | Rolling 20-bar return standard deviation |
| `hist_momentum`  | `data['histogram'] - data['histogram'].shift(5)` | Histogram change over 5 bars             |

Return the DataFrame with all five columns added. Do not drop rows — NaN rows at the start are handled by Person 2.

**Verify your work:** `compute_features` requires `macd`, `signal_line`, and `histogram` columns to already exist on the DataFrame — those come from `compute_macd`. To test locally, call `compute_macd` first and add the columns manually:

```python
macd_line, signal_line, histogram = compute_macd(data['Close'])
data['macd'] = macd_line
data['signal_line'] = signal_line
data['histogram'] = histogram
data = compute_features(data)
```

After this, `volatility` should be a small positive float (e.g. 0.008–0.015), `price_momentum` should oscillate positive and negative, and `macd_slope` should change sign around crossover points.

### Function 3: `compute_200_ema`

```python
def compute_200_ema(close: pd.Series) -> pd.Series:
```

**What it does:** Computes the 200-period Exponential Moving Average of closing prices. This is the long-term trend line used to determine whether the stock is in an uptrend or downtrend.

**Requirements:**
- Return `close.ewm(span=200, adjust=False).mean()`
- Unlike SMA, EWM produces a value for every row from the first bar onwards — there are no NaN rows. However, early values are unreliable because the EMA hasn't had enough price history to stabilize. Person 4's 220-bar minimum check ensures the test data always has sufficient history.
- Return a pd.Series on the same index as `close`

**Verify your work:** On 3+ years of SPY data, the 200 EMA should be a smooth, slowly-moving line well below the price during bull markets and above price during bear markets. It should not jump around — if it does, check that `adjust=False`.

**Resources:**

- [pandas ewm() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.ewm.html)
- [pandas diff() docs](https://pandas.pydata.org/docs/reference/api/pandas.Series.diff.html)
- [MACD explained (Investopedia)](https://www.investopedia.com/terms/m/macd.asp)

**Push before Person 2 starts.**

---

## Person 2 — Signal Logic + Regime Detection + ML Confidence Model

**File:** `backend/strategies/macd_crossover.py` (same file — add below Person 1's functions)

**Before you start:** `git pull origin main` to get Person 1's code.

**Install required libraries (if not already in requirements.txt):**

```bash
pip install scikit-learn
```

Add `scikit-learn` to `requirements.txt`.

You own three things: the strategy class, the regime detector, and the ML confidence model.

### Constructor

```python
class MACDCrossoverStrategy(BaseStrategy):
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        histogram_threshold: float = 0.0,
        zero_line_filter: bool = True,
        cooldown_bars: int = 5,
        use_regime_filter: bool = True,
        confidence_threshold: float = 0.55,
        use_200_ema_filter: bool = True,
    ):
        super().__init__(name="MACD Crossover", params={...})  # pass all 9 params
        self.model = None  # set by fit_confidence_model() before generate_signals()
```

### Method 1: `detect_regime`

```python
def detect_regime(self, data: pd.DataFrame) -> pd.Series:
```

Use K-means clustering (k=2) to classify each bar as "trending" (0) or "choppy" (1):

1. Build a 2-column feature matrix: `[[volatility, abs(price_momentum)]]` — drop rows where either is NaN
2. Fit `KMeans(n_clusters=2, random_state=42, n_init=10)` on the feature matrix
3. The trending cluster is the one with **lower mean volatility** — assign it label 0. The other cluster gets label 1. (Use `kmeans.cluster_centers_` to identify which cluster is which.)
4. Return a pd.Series of 0/1 values on the same index as `data`. Rows that were NaN get filled with 1 (choppy, conservative default).

```python
from sklearn.cluster import KMeans
```

### Method 2: `fit_confidence_model`

```python
def fit_confidence_model(self, train_df: pd.DataFrame) -> None:
```

Train a logistic regression on the training data to predict whether a trade will be profitable:

1. Call `compute_macd()` on `train_df['Close']`, then add the results as columns — you must do this before calling `compute_features` or it will crash:
   ```python
   macd_line, signal_line, histogram = compute_macd(train_df['Close'], ...)
   train_df = train_df.copy()
   train_df['macd'] = macd_line
   train_df['signal_line'] = signal_line
   train_df['histogram'] = histogram
   train_df = compute_features(train_df)
   ```
2. Build feature matrix `X` from the 5 feature columns: `['macd_slope', 'hist_slope', 'price_momentum', 'volatility', 'hist_momentum']`
3. Build target `y`: `(train_df['Close'].shift(-5) > train_df['Close']).astype(int)` — 1 if price is higher 5 bars later, 0 if lower. This is what we're trying to predict.
4. Drop rows where X or y is NaN (the first ~30 rows and last 5 rows)
5. Fit `LogisticRegression(max_iter=500)` on X and y
6. Store as `self.model`

```python
from sklearn.linear_model import LogisticRegression
```

**Note:** `fit_confidence_model` is called by Person 4 on the training data _before_ `generate_signals` is called on the test data. Never call it inside `generate_signals` — that would cause look-ahead bias.

### Method 3: `generate_signals`

```python
def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
```

1. Call `compute_macd()` on `data['Close']`, add `macd`, `signal_line`, `histogram` columns
2. Call `compute_features(data)` to add the 5 feature columns
3. Call `compute_200_ema(data['Close'])`, add as `ema_200` column
4. Detect crossovers using `.shift(1)`:
   - Bullish: `(prev_macd < prev_signal_line) & (curr_macd > curr_signal_line) & (histogram > histogram_threshold)` → raw signal = 1
   - Bearish: `(prev_macd > prev_signal_line) & (curr_macd < curr_signal_line) & (histogram < -histogram_threshold)` → raw signal = -1
   - Else → 0
5. Apply zero-line filter (if `zero_line_filter=True`): suppress bullish signals where `macd <= 0`, suppress bearish signals where `macd >= 0`
6. Apply 200 EMA filter (if `use_200_ema_filter=True`):
   - Suppress bullish signals where `data['Close'] < data['ema_200']` (price below long-term trend — don't buy into a downtrend)
   - Suppress bearish signals where `data['Close'] > data['ema_200']` (price above long-term trend — don't short an uptrend)
   - Note: EWM produces no NaN rows — Person 4's 220-bar minimum guarantees the EMA is reliable by the time `generate_signals` is called
7. Apply cooldown (if `cooldown_bars > 0`): iterate through signal column, zero out any signal that occurs within `cooldown_bars` of the previous signal
8. Apply regime filter (if `use_regime_filter=True`): call `self.detect_regime(data)`, add `regime` column. Set signal = 0 wherever `regime == 1` (choppy)
9. Apply confidence filter (if `self.model is not None`):
   - Build feature matrix from the 5 columns (fill NaN with 0 for inference)
   - Call `self.model.predict_proba(X)` — this returns `[[prob_0, prob_1], ...]`
   - For bullish signals (signal == 1): keep only where `prob_1 >= confidence_threshold`
   - For bearish signals (signal == -1): keep only where `prob_0 >= confidence_threshold` (probability of going down)
   - Add a `confidence` column: `prob_1` for bullish bars, `prob_0` for bearish bars, 0.0 for hold
10. Return the full DataFrame with all original columns plus: `macd`, `signal_line`, `histogram`, `macd_slope`, `hist_slope`, `price_momentum`, `volatility`, `hist_momentum`, `ema_200`, `regime`, `confidence`, `signal`

**Verify your work:**

- Run with all filters disabled — you should see raw crossover signals on every crossover
- Enable `use_200_ema_filter=True` only — bullish signals during downtrends (price below 200 EMA) should disappear
- Enable `use_regime_filter=True` only — signals during high-volatility choppy periods should disappear
- Enable all filters + call `fit_confidence_model` first — signal count should be the lowest, with a `confidence` column between 0 and 1

**Resources:**

- [scikit-learn KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)
- [scikit-learn LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)
- [pandas shift()](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.shift.html)

---

## Person 3 — Chart Builder + Regime Overlay

**File:** `frontend/ui/charts.py`

**Before you start:** `git pull origin main` to get Persons 1–2's code.

**What to build:** A function called `plot_macd_crossover` that takes the DataFrame output from Person 2 and returns a Plotly `Figure`.

```python
def plot_macd_crossover(data: pd.DataFrame) -> go.Figure:
```

### Panel 1 — Candlestick (top, 65% height)

- Standard OHLCV candlestick
- Green upward triangle markers (`marker_symbol='triangle-up'`) below candle lows at buy signal dates
- Red downward triangle markers (`marker_symbol='triangle-down'`) above candle highs at sell signal dates
- **200 EMA line:** Add a smooth line trace on the candlestick panel showing the 200 EMA:
  ```python
  go.Scatter(
      x=data.index, y=data['ema_200'],
      name='200 EMA', mode='lines',
      line=dict(color='#f0c040', width=1.5, dash='dot')
  )
  ```
  This golden dotted line shows the long-term trend. Price above it = uptrend, below it = downtrend. Skip NaN rows when plotting.
- **Regime overlay:** For each consecutive block of bars where `regime == 1` (choppy), add a shaded background rectangle using `fig.add_vrect()`:
  ```python
  fig.add_vrect(
      x0=start_date, x1=end_date,
      fillcolor='gray', opacity=0.10,
      layer='below', line_width=0,
      row=1, col=1
  )
  ```
  Group consecutive choppy bars into single rectangles (don't add one rect per bar — find the start and end of each choppy block). Trending periods have no fill.
- **Confidence annotations:** On each buy/sell signal marker, add a small text label showing the confidence score rounded to 2 decimal places. Use `mode='markers+text'` and `textposition='bottom center'` for buys, `'top center'` for sells. If `confidence` column is 0.0, don't add text.

### Panel 2 — MACD (bottom, 35% height)

- MACD line in `'#00b4d8'` (cyan)
- Signal line in `'#f4a261'` (orange)
- Histogram as bar chart — split into two traces:
  - Positive bars only (`histogram > 0`): `marker_color='rgba(0,200,100,0.6)'`
  - Negative bars only (`histogram < 0`): `marker_color='rgba(220,50,50,0.6)'`
- Horizontal dashed zero line: `fig.add_hline(y=0, line_dash='dash', line_color='gray', row=2, col=1)`
- Buy/sell markers mirrored at the MACD line values at those dates

### Layout requirements

- `make_subplots(rows=2, cols=1, row_heights=[0.65, 0.35], shared_xaxes=True, vertical_spacing=0.03)`
- Dark theme: `paper_bgcolor='#0a0e14'`, `plot_bgcolor='#0a0e14'`, `template='plotly_dark'`
- Disable range slider: `fig.update_xaxes(rangeslider_visible=False)`
- Title: `f"MACD Crossover — {data.index[0].date()} to {data.index[-1].date()}"`
- Return the Figure — do not call `fig.show()`

**Verify your work:** Call `fig.show()` locally on SPY output from Person 2. Confirm:

- Golden dotted 200 EMA line runs across the candlestick panel
- Gray background bands appear during choppy regime periods
- Confidence scores appear as text on signal markers
- Histogram bars are green/red split correctly
- Shared x-axis works across both panels

**Resources:**

- [Plotly subplots](https://plotly.com/python/subplots/)
- [Plotly add_vrect](https://plotly.com/python/horizontal-vertical-shapes/)
- [Plotly bar charts](https://plotly.com/python/bar-charts/)
- [Plotly candlestick](https://plotly.com/python/candlestick-charts/)

---

## Person 4 — Streamlit + Walk-Forward Validation

**File:** `frontend/streamlit_app.py`

You have two phases. Start Phase 1 right now.

### Phase 1: UI Layout (start now)

Add a "MACD Crossover Strategy" section inside the `elif page == "⚡ Strategy Builder":` block, below the RSI Divergence section.

**Left column controls:**

- Symbol text input (default "SPY", `key="macd_symbol"`)
- Start date picker (`key="macd_start"`)
- End date picker (`key="macd_end"`)

**Right column controls:**

- Fast period slider (5–50, default 12, `key="macd_fast"`)
- Slow period slider (10–100, default 26, `key="macd_slow"`)
- Signal period slider (3–20, default 9, `key="macd_signal"`)
- Histogram threshold (0.0–1.0, step 0.01, default 0.0, `key="macd_hist_thresh"`)
- Zero-line filter checkbox (default True, `key="macd_zero_filter"`, label: "Zero-line filter")
- Cooldown bars slider (0–20, default 5, `key="macd_cooldown"`, label: "Signal cooldown (bars)")
- Regime filter checkbox (default True, `key="macd_regime_filter"`, label: "Regime filter (K-means)")
- Confidence threshold slider (0.50–0.90, step 0.01, default 0.55, `key="macd_confidence"`, label: "ML confidence threshold")
- 200 EMA filter checkbox (default True, `key="macd_ema_filter"`, label: "200 EMA trend filter")

Add validation:

```python
if macd_fast >= macd_slow:
    st.warning("Fast period must be less than slow period.")
```

- "Run MACD Crossover" button (primary, `key="macd_run"`)
- Placeholder: `st.info("Backend wiring in progress — coming soon.")`

**Verify Phase 1:** Run the app, confirm all controls render below RSI section.

### Phase 2: Wiring + Walk-Forward Validation (after Persons 1–3 merge)

**Before you start:** `git pull origin main`

Inside the button click handler:

**Step 1 — Validate and fetch:**

```python
if macd_fast >= macd_slow:
    st.error("Fast period must be less than slow period.")
    st.stop()
data = fetch_ohlcv(symbol, start, end)
if len(data) < 220:
    st.error("Select a longer date range — at least 220 bars of data required for the 200 EMA to be meaningful. Try expanding your date range to cover 1+ year.")
    st.stop()
```

**Step 2 — Walk-forward split (70/30):**

```python
split_idx = int(len(data) * 0.70)
train_data = data.iloc[:split_idx].copy()
test_data  = data.iloc[split_idx:].copy()
```

Display the split to the user:

```python
st.caption(f"Training: {train_data.index[0].date()} → {train_data.index[-1].date()} ({len(train_data)} bars) | Test: {test_data.index[0].date()} → {test_data.index[-1].date()} ({len(test_data)} bars)")
```

**Step 3 — Fit ML model on training data, generate signals on test data:**

```python
strategy = MACDCrossoverStrategy(
    fast_period=macd_fast, slow_period=macd_slow,
    signal_period=macd_signal, histogram_threshold=macd_hist_thresh,
    zero_line_filter=macd_zero_filter, cooldown_bars=macd_cooldown,
    use_regime_filter=macd_regime_filter, confidence_threshold=macd_confidence,
    use_200_ema_filter=macd_ema_filter,
)
strategy.fit_confidence_model(train_data)   # train on historical only
result_df = strategy.generate_signals(test_data)  # evaluate on unseen data
```

**Step 4 — Chart:**

```python
fig = plot_macd_crossover(result_df)
st.plotly_chart(fig, use_container_width=True)
```

**Step 5 — Compute and display Sharpe ratio + max drawdown:**

```python
import numpy as np

# Strategy daily returns: signal * next-day close return
# Use shift(-1) to get the next day's return for each signal
next_day_return = result_df['Close'].pct_change().shift(-1)
strategy_returns = result_df['signal'] * next_day_return
strategy_returns = strategy_returns.dropna()

# Sharpe ratio (annualized, assuming 252 trading days)
sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)

# Max drawdown
cumulative = (1 + strategy_returns).cumprod()
rolling_max = cumulative.cummax()
drawdown = (cumulative - rolling_max) / rolling_max
max_drawdown = drawdown.min()  # most negative value
```

Display metrics in a clear panel:

```python
st.subheader("Out-of-Sample Performance (test set only)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Symbol", symbol.upper())
col2.metric("Buy Signals", int((result_df['signal'] == 1).sum()))
col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
col4.metric("Max Drawdown", f"{max_drawdown:.1%}")
st.caption("Metrics are computed on the out-of-sample test set only. The ML confidence model was trained on the training set and has never seen this data.")
```

**Step 6 — Strategy comparison panel:**

```python
st.session_state['macd_signals'] = result_df

available = {}
if 'macd_signals' in st.session_state:
    available['MACD Crossover'] = st.session_state['macd_signals']
if 'rsi_signals' in st.session_state:
    available['RSI Divergence'] = st.session_state['rsi_signals']
if 'bb_signals' in st.session_state:
    available['Bollinger Bands'] = st.session_state['bb_signals']

if len(available) >= 2:
    st.subheader("Strategy Comparison")
    rows = []
    for name, df in available.items():
        rows.append({
            'Strategy': name,
            'Buy Signals': int((df['signal'] == 1).sum()),
            'Sell Signals': int((df['signal'] == -1).sum()),
            'Date Range': f"{df.index[0].date()} → {df.index[-1].date()}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
```

**Step 7 — CSV export:**

```python
csv = result_df.to_csv(index=True).encode('utf-8')
st.download_button("Download Signal Data (CSV)", csv, f"macd_{symbol}.csv", "text/csv")
```

**Step 8 — Error handling:**
Wrap steps 1–7 in `try/except Exception as e: st.error(f"Error: {e}")`

**Verify Phase 2:** Run app, enter SPY with 3+ years of data. Confirm:

- Train/test split caption shows correct dates
- Chart renders on test period only
- Sharpe ratio and max drawdown display (Sharpe > 0 = strategy made money on average)
- ML confidence disclaimer is visible
- CSV download works

**Resources:**

- [Streamlit widgets](https://docs.streamlit.io/develop/api-reference/widgets)
- [st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [st.download_button](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button)
- [Sharpe ratio (Investopedia)](https://www.investopedia.com/terms/s/sharperatio.asp)
- [Max drawdown explained](https://www.investopedia.com/terms/m/maximum-drawdown.asp)

---

## Handoff to Backtesting Team

`st.session_state['macd_signals']` contains the **out-of-sample test set** DataFrame with:

| Column                         | Type  | What It Is                         |
| ------------------------------ | ----- | ---------------------------------- |
| Open, High, Low, Close, Volume | float | Raw OHLCV price data               |
| macd                           | float | MACD line                          |
| signal_line                    | float | Signal line (EMA of MACD)          |
| histogram                      | float | MACD − Signal                      |
| macd_slope                     | float | Rate of change of MACD             |
| hist_slope                     | float | Rate of change of histogram        |
| price_momentum                 | float | 5-bar price return                 |
| volatility                     | float | 20-bar rolling return std          |
| hist_momentum                  | float | Histogram change over 5 bars       |
| ema_200                        | float | 200-period EMA of close price      |
| regime                         | int   | 0 = trending, 1 = choppy (K-means) |
| confidence                     | float | ML model probability (0–1)         |
| signal                         | int   | 1 = buy, -1 = sell, 0 = hold       |
