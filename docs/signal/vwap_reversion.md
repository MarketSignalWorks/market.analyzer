# VWAP Reversion — Full Guide

## Team Roles at a Glance

| Person | Role                                        | What You Own                                                                             | File(s)                                                         | Est. Time |
| ------ | ------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------- | --------- |
| **1**  | **VWAP Math + Volume Features**             | Rolling VWAP, deviation bands, volume ratio, typical price                               | `backend/strategies/vwap_reversion.py` (create this file)       | ~45 min   |
| **2**  | **Signal Logic + Regime Filter + Exit Rules** | Strategy class, volume confirmation, holding-period exits, ranging-market regime filter | `backend/strategies/vwap_reversion.py` (below Person 1's code)  | ~60 min   |
| **3**  | **Chart Builder + Volume Panel**            | Two-panel chart: candles with VWAP + bands on top, volume bars with moving avg on bottom | `frontend/ui/charts.py`                                         | ~45 min   |
| **4**  | **Streamlit + Walk-Forward Validation**     | UI controls, out-of-sample backtest, Sharpe + drawdown, strategy comparison panel        | `frontend/streamlit_app.py`                                     | ~60 min   |

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

**Merge order:** Person 1 → Person 2 → Person 3 → Person 4

**Note:** `fetch_ohlcv` is already built. Do not rebuild it.

---

## Git Workflow

| Person | Branch Name           |
| ------ | --------------------- |
| 1      | `vwap-math`           |
| 2      | `vwap-signal-logic`   |
| 3      | `vwap-charts`         |
| 4      | `vwap-streamlit-ui`   |

```bash
git checkout vwap-math           # Person 1
git checkout vwap-signal-logic   # Person 2
git checkout vwap-charts         # Person 3
git checkout vwap-streamlit-ui   # Person 4

git pull origin main
git add .
git commit -m "describe what you did"
git push origin your-branch-name
```

Open a PR on GitHub. Tag the team lead. Wait for approval before the next person starts.

---

## The Algorithm (Everyone Read This)

VWAP (Volume-Weighted Average Price) is the average price of an asset, weighted by how much volume traded at each price. It's the benchmark institutional traders use to measure their own execution — "did I buy above or below VWAP today?"

Retail traders flip it around: they use VWAP as a fair-value anchor. When price gets far away from VWAP on meaningful volume, statistical pressure tends to pull it back. That's the **mean reversion** thesis.

### Step 1: Compute Typical Price

```
Typical Price (TP) = (High + Low + Close) / 3
```

This smooths out noise from using `Close` alone.

### Step 2: Rolling VWAP

```
VWAP = sum(TP * Volume, N) / sum(Volume, N)    [default N = 20]
```

On daily bars, N=20 gives you a month of weighted average price. Price above VWAP = bulls in control. Price below VWAP = bears in control.

### Step 3: Deviation from VWAP

```
deviation = (Close - VWAP) / VWAP
```

Expressed as a percentage. Big positive number = overextended high. Big negative = overextended low.

### Step 4: Volume Ratio

```
avg_volume = Volume.rolling(20).mean()
volume_ratio = Volume / avg_volume
```

If `volume_ratio > volume_multiplier` (default 1.5), today's volume is meaningfully higher than usual. That's your confirmation that institutions are participating, not just retail noise.

### Step 5: Signal Logic

```
BULLISH (+1 — BUY):
  deviation < -deviation_threshold   (price well below VWAP)
  AND volume_ratio > volume_multiplier   (real volume)

BEARISH (−1 — SELL):
  deviation > +deviation_threshold   (price well above VWAP)
  AND volume_ratio > volume_multiplier

HOLD (0): otherwise
```

### Step 6: Holding Period Exit

Unlike MACD/RSI where you hold until the opposite signal fires, VWAP mean reversion uses a **fixed holding period**. After a buy signal, you exit automatically after `holding_period` bars (default 10) regardless of outcome. This prevents the strategy from "holding bags" when the mean reversion thesis fails.

### Step 7: Regime Filter

Mean reversion only works in **ranging markets**. In a strong trend, price can stay far from VWAP for weeks without reverting. Use the same K-means regime detector as the MACD strategy: trade only when the market is classified as "ranging" (low-volatility + low-momentum cluster).

### Visual Reference

```
  BULLISH REVERSION (BUY):
  ──────────────────────────────
  Price:   ─────╲
               ╲___         ← price dips well below VWAP
  VWAP:    ────────────
  Volume:  ▁▁▁▁▁██         ← spike confirms capitulation
                 ↑ BUY, exit in 10 bars

  BEARISH REVERSION (SELL):
  ──────────────────────────────
  Price:        ___╱──     ← price spikes well above VWAP
  VWAP:    ────────────
  Volume:  ▁▁▁▁██           ← spike confirms euphoria
                ↓ SELL, exit in 10 bars
```

**Before writing any code, read `backend/strategies/base.py`.** Your class must follow that contract.

---

## Person 1 — VWAP Math + Volume Features

**File:** `backend/strategies/vwap_reversion.py` (create this file)

You own three functions. Person 2 depends on all of them.

### Function 1: `compute_vwap`

```python
def compute_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 20,
) -> pd.Series:
```

**Requirements:**
- Typical price: `(high + low + close) / 3`
- Numerator: `(typical_price * volume).rolling(period).sum()`
- Denominator: `volume.rolling(period).sum()`
- VWAP = numerator / denominator
- Return a `pd.Series` on the same index as `close`
- First `period - 1` rows will be NaN — expected

### Function 2: `compute_vwap_bands`

```python
def compute_vwap_bands(
    vwap: pd.Series,
    deviation_threshold: float = 0.015,
) -> tuple[pd.Series, pd.Series]:
```

**Requirements:**
- `upper_band = vwap * (1 + deviation_threshold)`
- `lower_band = vwap * (1 - deviation_threshold)`
- Return `(upper_band, lower_band)` — useful for Person 3's chart overlay

### Function 3: `compute_volume_features`

```python
def compute_volume_features(
    volume: pd.Series,
    avg_period: int = 20,
) -> tuple[pd.Series, pd.Series]:
```

**What to build:**
- `avg_volume = volume.rolling(avg_period).mean()`
- `volume_ratio = volume / avg_volume`
- Return `(avg_volume, volume_ratio)`

**Verify your work:** On SPY, `volume_ratio` should hover around 1.0 on normal days and spike above 2.0 on major news days (Fed meetings, earnings).

**Push before Person 2 starts.**

**Resources:**
- [pandas rolling() docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html)
- [VWAP explained (Investopedia)](https://www.investopedia.com/terms/v/vwap.asp)
- [Mean reversion explained (Investopedia)](https://www.investopedia.com/terms/m/meanreversion.asp)

---

## Person 2 — Signal Logic + Regime Filter + Exit Rules

**File:** `backend/strategies/vwap_reversion.py` (same file — add below Person 1's functions)

**Before you start:** `git pull origin main` to get Person 1's code.

### Constructor

```python
class VWAPReversionStrategy(BaseStrategy):
    def __init__(
        self,
        vwap_period: int = 20,
        deviation_threshold: float = 0.015,   # 1.5%
        volume_multiplier: float = 1.5,
        holding_period: int = 10,
        use_regime_filter: bool = True,
    ):
        super().__init__(
            name="VWAP Reversion",
            params={
                "vwap_period": vwap_period,
                "deviation_threshold": deviation_threshold,
                "volume_multiplier": volume_multiplier,
                "holding_period": holding_period,
                "use_regime_filter": use_regime_filter,
            },
        )
        self.vwap_period = vwap_period
        self.deviation_threshold = deviation_threshold
        self.volume_multiplier = volume_multiplier
        self.holding_period = holding_period
        self.use_regime_filter = use_regime_filter
```

### Method 1: `detect_regime`

```python
from sklearn.cluster import KMeans

def detect_regime(self, data: pd.DataFrame) -> pd.Series:
```

K-means k=2 on `[volatility, abs(price_momentum)]`. Trending cluster (lower volatility) = label 0, choppy = label 1.

```python
features = data[['volatility', 'price_momentum']].copy()
features['price_momentum'] = features['price_momentum'].abs()
valid_mask = features.notna().all(axis=1)
X = features[valid_mask].values

kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
kmeans.fit(X)

trending_cluster = int(np.argmin(kmeans.cluster_centers_[:, 0]))
mapped_labels = np.where(kmeans.labels_ == trending_cluster, 0, 1)

regime = pd.Series(1, index=data.index, dtype=int)
regime[valid_mask] = mapped_labels
return regime
```

**For VWAP, you want the OPPOSITE of MACD.** Mean reversion only works in **choppy/ranging** markets, not trending ones. So in `generate_signals`, suppress signals where `regime == 0` (trending), NOT where `regime == 1`.

### Method 2: `generate_signals`

```python
def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
```

1. Compute VWAP: `compute_vwap(data['High'], data['Low'], data['Close'], data['Volume'], self.vwap_period)`
2. Compute bands: `compute_vwap_bands(vwap, self.deviation_threshold)` → store as `upper_band`, `lower_band`
3. Compute volume features: `compute_volume_features(data['Volume'])` → store `avg_volume`, `volume_ratio`
4. Compute deviation: `data['deviation'] = (data['Close'] - vwap) / vwap`
5. Compute `price_momentum` = `data['Close'].pct_change(5)` and `volatility` = `data['Close'].pct_change().rolling(20).std()` — needed for regime detection
6. Raw entry signals:
   - Bullish: `(data['deviation'] < -self.deviation_threshold) & (data['volume_ratio'] > self.volume_multiplier)` → +1
   - Bearish: `(data['deviation'] > self.deviation_threshold) & (data['volume_ratio'] > self.volume_multiplier)` → −1
7. Regime filter (if `use_regime_filter=True`): call `self.detect_regime(data)`, add `regime` column. Set signal = 0 where `regime == 0` (suppress in trends)
8. **Holding period exit logic** — this is the new part. Iterate through the signal column:
   - When you see a nonzero entry signal, record the index
   - For the next `holding_period - 1` bars, keep the signal (so the position stays "on")
   - After `holding_period` bars, force signal back to 0
   - If a new entry signal appears during the holding period, ignore it (don't stack trades)
9. Return the DataFrame with columns: original OHLCV + `vwap`, `upper_band`, `lower_band`, `avg_volume`, `volume_ratio`, `deviation`, `regime`, `signal`

   Also add a `volume_multiplier` column set to a constant `self.volume_multiplier` — Person 3 needs this to draw the spike markers without knowing what threshold was used:
   ```python
   data['volume_multiplier'] = self.volume_multiplier
   ```

**Pseudocode for the holding logic:**

```python
entry_signals = signal.copy()  # raw ±1 at entry bars, 0 elsewhere
final_signal = pd.Series(0, index=data.index)
i = 0
while i < len(entry_signals):
    if entry_signals.iloc[i] != 0:
        direction = entry_signals.iloc[i]
        end = min(i + self.holding_period, len(entry_signals))
        for j in range(i, end):
            final_signal.iloc[j] = direction
        i = end  # skip ahead past the holding window
    else:
        i += 1
```

**Verify your work:**
- Run with all filters disabled — signals fire on every deviation + volume spike
- Enable `use_regime_filter=True` — signals during strong trends should disappear
- Check the holding logic — a +1 at bar 100 should show +1 at bars 100–109, then 0 at bar 110

**Resources:**
- [scikit-learn KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)
- [pandas shift()](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.shift.html)
- [Holding period explained (Investopedia)](https://www.investopedia.com/terms/h/holdingperiod.asp)

---

## Person 3 — Chart Builder + Volume Panel

**File:** `frontend/ui/charts.py`

**Before you start:** `git pull origin main` to get Persons 1–2's code. **Add your function to the bottom of the existing file — do not replace it.**

```python
def plot_vwap_reversion(data: pd.DataFrame) -> go.Figure:
```

### Panel 1 — Candlestick (top, 65% height)

- Standard OHLCV candlestick
- **VWAP line:** purple solid line, `color='#a78bfa'`, `width=2`
- **Upper/lower bands:** thin dashed lines, `color='rgba(167,139,250,0.4)'`, `width=1`, `dash='dot'`
- Green upward triangles on entry bars where `signal == 1` (below the candle low at `data['Low'] * 0.993`)
- Red downward triangles on entry bars where `signal == -1` (above the candle high at `data['High'] * 1.007`)

**Important:** only mark the **entry** bar, not every bar of the holding period. Filter entries using `data['signal'].diff() != 0` to detect transitions from 0 → ±1.

### Panel 2 — Volume (bottom, 35% height)

- Bar chart of `data['Volume']`
  - Green bars where `Close > Open`: `marker_color='rgba(63,185,80,0.6)'`
  - Red bars where `Close <= Open`: `marker_color='rgba(255,107,107,0.6)'`
- **Average volume line:** `data['avg_volume']` in yellow, `color='#f0c040'`, `width=1.5`, `dash='dot'`
- **Volume spike markers:** on bars where `volume_ratio > volume_multiplier` AND there's a signal, add a small yellow star above the volume bar. Use `data['volume_multiplier']` for the threshold — Person 2 writes this column into the DataFrame so you don't have to hard-code it.

### Layout requirements

- `make_subplots(rows=2, cols=1, row_heights=[0.65, 0.35], shared_xaxes=True, vertical_spacing=0.03)`
- Dark theme: `paper_bgcolor='#0a0e14'`, `plot_bgcolor='#0a0e14'`, `template='plotly_dark'`
- Title: `f"VWAP Reversion — {data.index[0].date()} to {data.index[-1].date()}"`
- Disable range slider
- Return the Figure — do not call `fig.show()`

**Verify your work:** Call `fig.show()` locally on SPY output from Person 2. Confirm:
- Purple VWAP line runs across the candlestick panel with dashed upper/lower bands
- Entry triangles appear only at the first bar of each signal (not across the full holding period)
- Volume bars are green/red based on candle direction
- Yellow average volume dotted line is visible in the volume panel
- Yellow star markers appear on high-volume signal bars
- Shared x-axis works across both panels

**Resources:**
- [Plotly subplots](https://plotly.com/python/subplots/)
- [Plotly bar charts](https://plotly.com/python/bar-charts/)
- [Plotly candlestick](https://plotly.com/python/candlestick-charts/)

---

## Person 4 — Streamlit + Walk-Forward Validation

**File:** `frontend/streamlit_app.py`

Add a "VWAP Reversion Strategy" section below the MACD section inside `elif page == "⚡ Strategy Builder":`.

### Phase 1: UI Layout (start now)

**Left column:**
- Symbol text input (default "SPY", `key="vwap_symbol"`)
- Start date picker (`key="vwap_start"`)
- End date picker (`key="vwap_end"`)

**Right column:**
- VWAP period slider (5–50, default 20, `key="vwap_period"`)
- Deviation threshold slider (0.005–0.05, step 0.001, default 0.015, `key="vwap_dev"`, label "Deviation threshold (fraction)")
- Volume multiplier slider (1.0–3.0, step 0.1, default 1.5, `key="vwap_vol_mult"`)
- Holding period slider (3–30, default 10, `key="vwap_hold"`)
- Regime filter checkbox (default True, `key="vwap_regime"`, label "Regime filter (ranging-markets only)")

- "Run VWAP Reversion" button (primary, `key="vwap_run"`)
- Placeholder: `st.info("Backend wiring in progress — coming soon.")`

**Verify Phase 1:** Run the app, confirm all controls render below the MACD section. Sliders and checkbox should be interactive before any backend is wired.

### Phase 2: Wiring + Walk-Forward (after Persons 1–3 merge)

**Before you start:** `git pull origin main`

Inside the button handler, wrapped in `try/except Exception as e: st.error(f"Error: {e}")`:

**Note:** `import numpy as np` belongs at the top of `streamlit_app.py` with the other imports — not inside the button handler.

```python
from backend.data.fetcher import fetch_ohlcv
from backend.strategies.vwap_reversion import VWAPReversionStrategy
from frontend.ui.charts import plot_vwap_reversion

data = fetch_ohlcv(vwap_symbol, vwap_start, vwap_end)
if len(data) < 60:
    st.error("Select at least 60 bars of data.")
    st.stop()

# 70/30 split — no ML model to train, but still show out-of-sample performance
split_idx = int(len(data) * 0.70)
train_data = data.iloc[:split_idx].copy()
test_data  = data.iloc[split_idx:].copy()

st.caption(f"Training: {train_data.index[0].date()} → {train_data.index[-1].date()} ({len(train_data)} bars) | Test: {test_data.index[0].date()} → {test_data.index[-1].date()} ({len(test_data)} bars)")

strategy = VWAPReversionStrategy(
    vwap_period=vwap_period,
    deviation_threshold=vwap_dev,
    volume_multiplier=vwap_vol_mult,
    holding_period=vwap_hold,
    use_regime_filter=vwap_regime,
)
result_df = strategy.generate_signals(test_data)

fig = plot_vwap_reversion(result_df)
st.plotly_chart(fig, use_container_width=True)

next_day_return = result_df['Close'].pct_change().shift(-1)
strategy_returns = (result_df['signal'] * next_day_return).dropna()
sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
cumulative = (1 + strategy_returns).cumprod()
max_drawdown = ((cumulative - cumulative.cummax()) / cumulative.cummax()).min()

st.subheader("Out-of-Sample Performance")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Symbol", vwap_symbol.upper())
entries = int(((result_df['signal'] != 0) & (result_df['signal'].shift(1) == 0)).sum())  # entry bars only
col2.metric("Entry Signals", entries)
col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
col4.metric("Max Drawdown", f"{max_drawdown:.1%}")

st.session_state['vwap_signals'] = result_df

# Strategy comparison panel (4-way now)
available = {}
if 'vwap_signals' in st.session_state:
    available['VWAP Reversion'] = st.session_state['vwap_signals']
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

csv = result_df.to_csv(index=True).encode('utf-8')
st.download_button("Download Signal Data (CSV)", csv, f"vwap_{vwap_symbol}.csv", "text/csv")
```

**Verify Phase 2:** Run the app, enter SPY with 2+ years of data. Confirm:
- Train/test split caption shows correct dates
- Chart renders on the test period with VWAP + bands visible
- Entry triangles appear only at signal start bars, not across the full holding window
- Sharpe ratio and max drawdown display correctly
- CSV download works

**Resources:**
- [Streamlit widgets](https://docs.streamlit.io/develop/api-reference/widgets)
- [st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [st.download_button](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button)
- [Sharpe ratio (Investopedia)](https://www.investopedia.com/terms/s/sharperatio.asp)
- [Max drawdown explained (Investopedia)](https://www.investopedia.com/terms/m/maximum-drawdown.asp)

---

## Handoff to Backtesting Team

`st.session_state['vwap_signals']` contains the out-of-sample test set with:

| Column                         | Type  | What It Is                         |
| ------------------------------ | ----- | ---------------------------------- |
| Open, High, Low, Close, Volume | float | Raw OHLCV                          |
| vwap                           | float | Rolling VWAP                       |
| upper_band, lower_band         | float | VWAP ± deviation_threshold         |
| avg_volume                     | float | 20-bar rolling volume mean         |
| volume_ratio                   | float | Volume ÷ avg_volume                |
| deviation                      | float | (Close − VWAP) / VWAP              |
| regime                         | int   | 0 = trending, 1 = ranging          |
| volume_multiplier              | float | Threshold used for spike detection  |
| signal                         | int   | 1 = buy, −1 = sell, 0 = hold       |
