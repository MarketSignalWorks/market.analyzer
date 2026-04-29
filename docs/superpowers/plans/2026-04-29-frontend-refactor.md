# Frontend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take STRATEX from a 1,217-line monolithic Streamlit app with duplicated strategy blocks and dead CSS to a clean, tested, demo-ready project — while preserving every existing strategy's signal logic and SQL.

**Architecture:** Four sequential waves. Wave 0 adds a pytest safety net before any code is moved. Wave 1 is additive polish (no file moves). Wave 2 splits the monolith into `frontend/ui/{theme,api_client,strategy_runner,comparison}.py` plus `frontend/ui/pages/*.py`, and converts the four-strategy vertical stack into `st.tabs(...)` with a single persistent comparison panel. Wave 3 updates docs and triages the stale PR. Each wave is one git commit, allowing isolated review/revert.

**Tech Stack:** Streamlit 1.40+, Plotly 5.x, pandas 2.x, scikit-learn 1.5+, pytest 8.x. Python 3.12.

**Spec:** [docs/superpowers/specs/2026-04-29-frontend-refactor-design.md](../specs/2026-04-29-frontend-refactor-design.md)

---

## File Structure

### Created
| Path | Responsibility |
| --- | --- |
| `tests/__init__.py` | Marks `tests/` as a package |
| `tests/conftest.py` | Shared fixtures: synthetic OHLCV DataFrames |
| `tests/test_strategies.py` | Smoke tests for all 4 `generate_signals()` |
| `tests/test_charts.py` | Smoke tests for all 4 `plot_*` |
| `tests/test_api_client.py` | Backend-down graceful-degradation tests |
| `frontend/ui/theme.py` | `COLORS` dict + `inject_theme()` CSS |
| `frontend/ui/api_client.py` | All Flask API wrappers + `is_backend_up()` |
| `frontend/ui/strategy_runner.py` | `run_strategy(...)` — kills 4× duplication |
| `frontend/ui/comparison.py` | `render_strategy_comparison()` |
| `frontend/ui/pages/__init__.py` | Page registry dict |
| `frontend/ui/pages/dashboard.py` | Dashboard page body |
| `frontend/ui/pages/strategy_builder.py` | Strategy Builder with 4 tabs |
| `frontend/ui/pages/strategy_library.py` | Strategy Library page body |
| `frontend/ui/pages/backtest_results.py` | Backtest Results page body |
| `frontend/ui/pages/sql_reports.py` | SQL Reports page body |

### Modified
| Path | Change |
| --- | --- |
| `frontend/streamlit_app.py` | Slimmed from 1,217 → ~150 lines: imports, sidebar, page router only |
| `requirements.txt` | Add version bounds + `pytest` |
| `README.md` | Rewrite with current state |

### Deleted
| Path | Reason |
| --- | --- |
| `frontend/ui/sidebar.py` | Empty `# TODO` stub |
| `frontend/ui/results.py` | Empty `# TODO` stub |

---

## Wave 0 — Test Safety Net

### Task 0.1: Add pytest dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add pytest to requirements**

```text
streamlit
plotly
requests
pandas
numpy
flask
sqlalchemy
yfinance
scikit-learn
pytest
```

- [ ] **Step 2: Install**

```bash
./venv/bin/pip install pytest --quiet
```

Expected: silent success.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "build: add pytest to requirements"
```

---

### Task 0.2: Create test infrastructure

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`

- [ ] **Step 1: Create empty package marker**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Write `tests/conftest.py`**

```python
"""Shared fixtures for STRATEX tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """250 business days of synthetic OHLCV. Deterministic via seed=0."""
    rng = np.random.default_rng(seed=0)
    n = 250
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.standard_normal(n))
    high = close + np.abs(rng.standard_normal(n))
    low = close - np.abs(rng.standard_normal(n))
    open_ = close + rng.standard_normal(n) * 0.1
    volume = (rng.random(n) * 5_000_000 + 1_000_000).astype(int)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


@pytest.fixture
def long_synthetic_ohlcv() -> pd.DataFrame:
    """500 business days — needed by MACD (200-EMA filter requires 220+ bars)."""
    rng = np.random.default_rng(seed=1)
    n = 500
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.standard_normal(n))
    high = close + np.abs(rng.standard_normal(n))
    low = close - np.abs(rng.standard_normal(n))
    open_ = close + rng.standard_normal(n) * 0.1
    volume = (rng.random(n) * 5_000_000 + 1_000_000).astype(int)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )
```

- [ ] **Step 3: Verify pytest discovery**

Run: `./venv/bin/pytest tests/ -v --collect-only`

Expected: "collected 0 items" (no tests yet, but no errors).

- [ ] **Step 4: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "test: add pytest infrastructure with synthetic OHLCV fixtures"
```

---

### Task 0.3: Strategy smoke tests

**Files:**
- Create: `tests/test_strategies.py`

- [ ] **Step 1: Write the failing test file**

```python
"""Smoke tests for all four strategies' generate_signals()."""
from __future__ import annotations

import pandas as pd
import pytest

from backend.strategies.bollinger_bands import BollingerBandsStrategy
from backend.strategies.rsi_divergence import RSIDivergenceStrategy
from backend.strategies.macd_crossover import MACDCrossoverStrategy
from backend.strategies.vwap_reversion import VWAPReversionStrategy


VALID_SIGNALS = {-1, 0, 1}


def _assert_signal_schema(result: pd.DataFrame, required_cols: set[str]) -> None:
    assert isinstance(result, pd.DataFrame)
    missing = required_cols - set(result.columns)
    assert not missing, f"Missing columns: {missing}"
    assert set(result["signal"].unique()).issubset(VALID_SIGNALS)


def test_bollinger_bands_signals(synthetic_ohlcv: pd.DataFrame) -> None:
    strategy = BollingerBandsStrategy()
    result = strategy.generate_signals(synthetic_ohlcv.copy())
    _assert_signal_schema(result, {"signal"})


def test_rsi_divergence_signals(synthetic_ohlcv: pd.DataFrame) -> None:
    strategy = RSIDivergenceStrategy()
    result = strategy.generate_signals(synthetic_ohlcv.copy())
    _assert_signal_schema(result, {"signal"})


def test_macd_crossover_signals(long_synthetic_ohlcv: pd.DataFrame) -> None:
    strategy = MACDCrossoverStrategy(use_200_ema_filter=True, use_regime_filter=False)
    split = int(len(long_synthetic_ohlcv) * 0.7)
    train = long_synthetic_ohlcv.iloc[:split].copy()
    test = long_synthetic_ohlcv.iloc[split:].copy()
    strategy.fit_confidence_model(train)
    result = strategy.generate_signals(test)
    _assert_signal_schema(result, {"signal"})


def test_vwap_reversion_signals(synthetic_ohlcv: pd.DataFrame) -> None:
    strategy = VWAPReversionStrategy(use_regime_filter=False)
    result = strategy.generate_signals(synthetic_ohlcv.copy())
    required = {
        "vwap", "upper_band", "lower_band",
        "avg_volume", "volume_ratio", "deviation",
        "regime", "volume_multiplier", "signal",
    }
    _assert_signal_schema(result, required)


def test_vwap_holding_period_max_run(synthetic_ohlcv: pd.DataFrame) -> None:
    """VWAP signal should never stay nonzero for more than holding_period bars."""
    holding = 10
    strategy = VWAPReversionStrategy(holding_period=holding, use_regime_filter=False)
    result = strategy.generate_signals(synthetic_ohlcv.copy())
    s = result["signal"].values
    i, max_run = 0, 0
    while i < len(s):
        if s[i] != 0:
            j = i
            while j < len(s) and s[j] == s[i]:
                j += 1
            max_run = max(max_run, j - i)
            i = j
        else:
            i += 1
    assert max_run <= holding, f"VWAP signal run {max_run} exceeds holding_period {holding}"
```

- [ ] **Step 2: Run tests — expect all to PASS (we're testing existing code)**

Run: `./venv/bin/pytest tests/test_strategies.py -v`

Expected: 5 passed.

If any fail, the existing strategy has a real bug — surface it but do NOT alter strategy code (that's out of scope per spec).

- [ ] **Step 3: Commit**

```bash
git add tests/test_strategies.py
git commit -m "test: add smoke tests for all four strategies"
```

---

### Task 0.4: Chart smoke tests

**Files:**
- Create: `tests/test_charts.py`

- [ ] **Step 1: Write the test file**

```python
"""Smoke tests for chart functions in frontend/ui/charts.py."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from backend.strategies.bollinger_bands import BollingerBandsStrategy
from backend.strategies.rsi_divergence import RSIDivergenceStrategy
from backend.strategies.macd_crossover import MACDCrossoverStrategy
from backend.strategies.vwap_reversion import VWAPReversionStrategy
from frontend.ui.charts import (
    plot_bollinger_bands,
    plot_rsi_divergence,
    plot_macd_crossover,
    plot_vwap_reversion,
)


def _trace_names(fig: go.Figure) -> set[str]:
    return {t.name for t in fig.data if t.name}


def test_plot_bollinger_returns_figure(synthetic_ohlcv: pd.DataFrame) -> None:
    df = BollingerBandsStrategy().generate_signals(synthetic_ohlcv.copy())
    fig = plot_bollinger_bands(df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_plot_rsi_returns_figure(synthetic_ohlcv: pd.DataFrame) -> None:
    df = RSIDivergenceStrategy().generate_signals(synthetic_ohlcv.copy())
    fig = plot_rsi_divergence(df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_plot_macd_returns_figure(long_synthetic_ohlcv: pd.DataFrame) -> None:
    strat = MACDCrossoverStrategy(use_200_ema_filter=True, use_regime_filter=False)
    split = int(len(long_synthetic_ohlcv) * 0.7)
    strat.fit_confidence_model(long_synthetic_ohlcv.iloc[:split].copy())
    df = strat.generate_signals(long_synthetic_ohlcv.iloc[split:].copy())
    fig = plot_macd_crossover(df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_plot_vwap_returns_figure(synthetic_ohlcv: pd.DataFrame) -> None:
    df = VWAPReversionStrategy(use_regime_filter=False).generate_signals(synthetic_ohlcv.copy())
    fig = plot_vwap_reversion(df)
    assert isinstance(fig, go.Figure)
    expected = {"Price", "VWAP", "Upper Band", "Lower Band",
                "Long Entry", "Short Entry", "Volume", "Avg Volume", "Vol Spike"}
    assert expected.issubset(_trace_names(fig))
```

- [ ] **Step 2: Run tests**

Run: `./venv/bin/pytest tests/test_charts.py -v`

Expected: 4 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_charts.py
git commit -m "test: add smoke tests for all four plot functions"
```

---

## Wave 1 — Polish (Additive)

### Task 1.1: Remove dead CSS

**Files:**
- Modify: `frontend/streamlit_app.py:32-111` (CSS block)

- [ ] **Step 1: Verify the CSS classes are actually unused**

Run:
```bash
grep -rE "metric-card|metric-value|metric-label|section-header|section-icon|strategy-card|strategy-name|strategy-type|sql-display|type-badge" frontend/ backend/
```

Expected: only matches are inside the `<style>` block of `streamlit_app.py` itself — confirming nothing renders these classes.

- [ ] **Step 2: Replace the entire CSS block**

In `frontend/streamlit_app.py`, replace lines 25–122 (the `st.markdown("""<style>...""", unsafe_allow_html=True)` call) with:

```python
st.markdown("""
<style>
    .stApp { background-color: #0a0e14; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .css-1d391kg { background-color: #0d1117; }
</style>
""", unsafe_allow_html=True)
```

- [ ] **Step 3: Verify app still launches and tests still pass**

Run: `./venv/bin/pytest tests/ -v`

Expected: 9 passed (5 strategies + 4 charts).

Manual check (optional): `./venv/bin/streamlit run frontend/streamlit_app.py` — confirm dark theme still applies.

- [ ] **Step 4: Commit**

```bash
git add frontend/streamlit_app.py
git commit -m "style: remove unused CSS classes from streamlit_app"
```

---

### Task 1.2: Unify icon style

**Files:**
- Modify: `frontend/streamlit_app.py` — sidebar nav (line 208) and tab labels (line 799)

- [ ] **Step 1: Replace nav radio options**

Find:
```python
        ["◉ Dashboard", "⚡ Strategy Builder", "◫ Strategy Library", "◈ Backtest Results", "◇ SQL Reports"],
```

Replace with:
```python
        ["◉ Dashboard", "⚡ Strategy Builder", "▦ Strategy Library", "▣ Backtest Results", "▤ SQL Reports"],
```

- [ ] **Step 2: Update each `elif page == "..."` to match**

Find and replace:
- `elif page == "◫ Strategy Library":` → `elif page == "▦ Strategy Library":`
- `elif page == "◈ Backtest Results":` → `elif page == "▣ Backtest Results":`
- `elif page == "◇ SQL Reports":` → `elif page == "▤ SQL Reports":`

- [ ] **Step 3: Drop emoji from tab labels**

Find:
```python
        tab1, tab2, tab3 = st.tabs(["📈 Equity Curve", "📉 Drawdown", "📊 Monthly Returns"])
```

Replace with:
```python
        tab1, tab2, tab3 = st.tabs(["Equity Curve", "Drawdown", "Monthly Returns"])
```

- [ ] **Step 4: Run tests**

Run: `./venv/bin/pytest tests/ -v`

Expected: 9 passed (icon changes don't touch logic).

- [ ] **Step 5: Commit**

```bash
git add frontend/streamlit_app.py
git commit -m "style: unify nav glyphs and drop emoji from tab labels"
```

---

### Task 1.3: Empty-state messages

**Files:**
- Modify: `frontend/streamlit_app.py` — Strategy Library page, Backtest Results page

- [ ] **Step 1: Strengthen Strategy Library empty state**

Find the Strategy Library page (starts at `elif page == "▦ Strategy Library":`). Locate the section that handles the case when `strategies` is empty (or no strategy selected). Add at the appropriate place:

```python
    if not strategies:
        st.info("No strategies saved yet. Strategies are saved automatically when you run a backtest from Strategy Builder.")
```

- [ ] **Step 2: Strengthen Backtest Results empty state**

Find the Backtest Results page (starts at `elif page == "▣ Backtest Results":`). Locate the early-exit when no backtest has run. Replace any silent `return` or empty render with:

```python
    if not backtests:
        st.info("No backtests yet. Run one from Strategy Builder to populate this page.")
        st.stop()
```

- [ ] **Step 3: Run tests**

Run: `./venv/bin/pytest tests/ -v`

Expected: 9 passed.

- [ ] **Step 4: Commit**

```bash
git add frontend/streamlit_app.py
git commit -m "feat: add empty-state messages for Strategy Library and Backtest Results"
```

---

### Task 1.4: Delete empty stubs

**Files:**
- Delete: `frontend/ui/sidebar.py`
- Delete: `frontend/ui/results.py`

- [ ] **Step 1: Verify they're not imported**

Run:
```bash
grep -rE "from frontend\.ui\.(sidebar|results)|import frontend\.ui\.(sidebar|results)" .
```

Expected: zero matches.

- [ ] **Step 2: Delete**

```bash
rm frontend/ui/sidebar.py frontend/ui/results.py
```

- [ ] **Step 3: Run tests**

Run: `./venv/bin/pytest tests/ -v`

Expected: 9 passed.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove unused empty UI stub files"
```

---

## Wave 2 — Restructure

### Task 2.1: Create theme module

**Files:**
- Create: `frontend/ui/theme.py`

- [ ] **Step 1: Write `theme.py`**

```python
"""Centralized theme: color constants + CSS injection."""
from __future__ import annotations

import streamlit as st

COLORS: dict[str, str] = {
    "bg":          "#0a0e14",
    "card":        "#0d1117",
    "border":      "rgba(255,255,255,0.08)",
    "accent":      "#00d4aa",
    "positive":    "#3fb950",
    "negative":    "#ff6b6b",
    "vwap_purple": "#a78bfa",
    "vol_yellow":  "#f0c040",
}

_CSS = """
<style>
    .stApp { background-color: %(bg)s; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .css-1d391kg { background-color: %(card)s; }
</style>
""" % COLORS


def inject_theme() -> None:
    """Apply STRATEX dark theme. Call once near app start."""
    st.markdown(_CSS, unsafe_allow_html=True)
```

- [ ] **Step 2: Verify imports**

Run: `./venv/bin/python -c "from frontend.ui.theme import COLORS, inject_theme; print(COLORS['accent'])"`

Expected: `#00d4aa`

- [ ] **Step 3: Commit**

```bash
git add frontend/ui/theme.py
git commit -m "feat: add centralized theme module"
```

---

### Task 2.2: Create api_client module + tests

**Files:**
- Create: `frontend/ui/api_client.py`
- Create: `tests/test_api_client.py`

- [ ] **Step 1: Write `tests/test_api_client.py` first (TDD)**

```python
"""Tests for the Flask API client wrapper."""
from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from frontend.ui import api_client


def test_is_backend_up_returns_false_on_connection_error() -> None:
    with patch("frontend.ui.api_client.requests.get",
               side_effect=requests.exceptions.ConnectionError):
        api_client.is_backend_up.clear()  # bust streamlit cache
        assert api_client.is_backend_up() is False


def test_fetch_dashboard_summary_returns_empty_dict_when_offline() -> None:
    with patch("frontend.ui.api_client.requests.get",
               side_effect=requests.exceptions.ConnectionError):
        api_client.fetch_dashboard_summary.clear()
        assert api_client.fetch_dashboard_summary() == {}


def test_fetch_strategies_returns_empty_list_when_offline() -> None:
    with patch("frontend.ui.api_client.requests.get",
               side_effect=requests.exceptions.ConnectionError):
        api_client.fetch_strategies.clear()
        assert api_client.fetch_strategies() == []


def test_fetch_dashboard_summary_returns_parsed_json_on_success() -> None:
    class FakeResponse:
        status_code = 200
        def json(self) -> dict:
            return {"active_strategies": 4, "total_backtests": 10}
    with patch("frontend.ui.api_client.requests.get", return_value=FakeResponse()):
        api_client.fetch_dashboard_summary.clear()
        assert api_client.fetch_dashboard_summary() == {"active_strategies": 4, "total_backtests": 10}
```

- [ ] **Step 2: Run tests — expect failure (module doesn't exist)**

Run: `./venv/bin/pytest tests/test_api_client.py -v`

Expected: ImportError on `frontend.ui.api_client`.

- [ ] **Step 3: Write `frontend/ui/api_client.py`**

```python
"""Flask backend API client with graceful-degradation behavior."""
from __future__ import annotations

import requests
import streamlit as st

API_BASE = "http://localhost:5000/api"
_TIMEOUT = 0.5


@st.cache_data(ttl=30)
def is_backend_up() -> bool:
    """Lightweight liveness probe. Cached for 30s to avoid hammering."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=_TIMEOUT)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


@st.cache_data(ttl=60)
def fetch_templates() -> dict:
    try:
        return requests.get(f"{API_BASE}/templates", timeout=2).json()
    except requests.exceptions.RequestException:
        return {}


@st.cache_data(ttl=60)
def fetch_symbols() -> list:
    try:
        return requests.get(f"{API_BASE}/symbols", timeout=2).json()
    except requests.exceptions.RequestException:
        return []


@st.cache_data(ttl=10)
def fetch_strategies() -> list:
    try:
        return requests.get(f"{API_BASE}/strategies", timeout=2).json()
    except requests.exceptions.RequestException:
        return []


@st.cache_data(ttl=10)
def fetch_dashboard_summary() -> dict:
    try:
        return requests.get(f"{API_BASE}/reports/dashboard-summary", timeout=2).json()
    except requests.exceptions.RequestException:
        return {}


@st.cache_data(ttl=30)
def fetch_report(endpoint: str) -> list:
    try:
        return requests.get(f"{API_BASE}{endpoint}", timeout=2).json()
    except requests.exceptions.RequestException:
        return []


def run_backtest(config: dict) -> dict | None:
    try:
        return requests.post(f"{API_BASE}/backtest", json=config, timeout=10).json()
    except requests.exceptions.RequestException as e:
        st.error(f"Backtest failed: {e}")
        return None


def save_strategy(strategy: dict) -> dict | None:
    try:
        return requests.post(f"{API_BASE}/strategies", json=strategy, timeout=5).json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to save strategy: {e}")
        return None


def delete_strategy(strategy_id: int) -> bool:
    try:
        r = requests.delete(f"{API_BASE}/strategies/{strategy_id}", timeout=5)
        return r.status_code == 204
    except requests.exceptions.RequestException:
        return False


def render_offline_banner_if_needed() -> None:
    if not is_backend_up():
        st.warning(
            "⚠ Backend offline — some features unavailable. "
            "Run `python backend/app.py` to enable Dashboard, Strategy Library, "
            "Backtest Results, and SQL Reports."
        )
```

- [ ] **Step 4: Run tests — expect pass**

Run: `./venv/bin/pytest tests/test_api_client.py -v`

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/ui/api_client.py tests/test_api_client.py
git commit -m "feat: extract API client with backend-down detection"
```

---

### Task 2.3: Create strategy_runner module

**Files:**
- Create: `frontend/ui/strategy_runner.py`

- [ ] **Step 1: Write `strategy_runner.py`**

```python
"""Shared strategy runner: split → fit → generate → plot → metrics → store → CSV.

Eliminates the ~80-line block duplicated across all four strategies.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def run_strategy(
    *,
    strategy,
    data: pd.DataFrame,
    plot_fn: Callable[[pd.DataFrame], go.Figure],
    name: str,
    session_key: str,
    csv_prefix: str,
    symbol: str,
    min_bars: int,
    train_split: float = 0.70,
    pre_fit: bool = False,
) -> None:
    """Render a strategy's full backtest UI. Caller passes a configured strategy.

    min_bars: 60 for BB/RSI/VWAP, 220 for MACD (200-EMA filter requirement).
    pre_fit:  True for MACD (calls strategy.fit_confidence_model(train_data)).
    """
    if len(data) < min_bars:
        st.error(f"Select at least {min_bars} bars of data.")
        return

    split_idx = int(len(data) * train_split)
    train_data = data.iloc[:split_idx].copy()
    test_data = data.iloc[split_idx:].copy()

    st.caption(
        f"Training: {train_data.index[0].date()} → {train_data.index[-1].date()} "
        f"({len(train_data)} bars) | "
        f"Test: {test_data.index[0].date()} → {test_data.index[-1].date()} "
        f"({len(test_data)} bars)"
    )

    if pre_fit:
        strategy.fit_confidence_model(train_data)

    result_df = strategy.generate_signals(test_data)

    fig = plot_fn(result_df)
    st.plotly_chart(fig, use_container_width=True)

    next_day_return = result_df["Close"].pct_change().shift(-1)
    strategy_returns = (result_df["signal"] * next_day_return).dropna()

    if strategy_returns.std() > 0:
        sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    cumulative = (1 + strategy_returns).cumprod()
    if len(cumulative) > 0:
        max_drawdown = ((cumulative - cumulative.cummax()) / cumulative.cummax()).min()
    else:
        max_drawdown = 0.0

    st.subheader("Out-of-Sample Performance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Symbol", symbol.upper())
    entries = int(((result_df["signal"] != 0) & (result_df["signal"].shift(1) == 0)).sum())
    col2.metric("Entry Signals", entries)
    col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col4.metric("Max Drawdown", f"{max_drawdown:.1%}")

    st.session_state[session_key] = result_df

    csv = result_df.to_csv(index=True).encode("utf-8")
    st.download_button(
        f"Download {name} Signal Data (CSV)",
        csv,
        f"{csv_prefix}_{symbol}.csv",
        "text/csv",
        key=f"dl_{csv_prefix}",
    )
```

- [ ] **Step 2: Verify imports**

Run: `./venv/bin/python -c "from frontend.ui.strategy_runner import run_strategy; print('ok')"`

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add frontend/ui/strategy_runner.py
git commit -m "feat: extract run_strategy helper to kill 4x duplication"
```

---

### Task 2.4: Create comparison module

**Files:**
- Create: `frontend/ui/comparison.py`

- [ ] **Step 1: Write `comparison.py`**

```python
"""Cross-strategy comparison panel — single instance below the tabs."""
from __future__ import annotations

import pandas as pd
import streamlit as st

_STRATEGY_LABELS: dict[str, str] = {
    "bb_signals":   "Bollinger Bands",
    "rsi_signals":  "RSI Divergence",
    "macd_signals": "MACD Crossover",
    "vwap_signals": "VWAP Reversion",
}


def render_strategy_comparison() -> None:
    """Render the strategy comparison table when 2+ strategies have been run.

    Reads st.session_state — no network/API calls.
    """
    available: dict[str, pd.DataFrame] = {
        label: st.session_state[key]
        for key, label in _STRATEGY_LABELS.items()
        if key in st.session_state
    }
    if len(available) < 2:
        return

    st.markdown("---")
    st.subheader("Strategy Comparison")
    rows = []
    for label, df in available.items():
        rows.append({
            "Strategy": label,
            "Buy Signals": int((df["signal"] == 1).sum()),
            "Sell Signals": int((df["signal"] == -1).sum()),
            "Date Range": f"{df.index[0].date()} → {df.index[-1].date()}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
```

- [ ] **Step 2: Verify imports**

Run: `./venv/bin/python -c "from frontend.ui.comparison import render_strategy_comparison; print('ok')"`

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add frontend/ui/comparison.py
git commit -m "feat: extract render_strategy_comparison single-instance helper"
```

---

### Task 2.5: Create page modules — Dashboard

**Files:**
- Create: `frontend/ui/pages/__init__.py`
- Create: `frontend/ui/pages/dashboard.py`

- [ ] **Step 1: Create package marker**

```bash
mkdir -p frontend/ui/pages
touch frontend/ui/pages/__init__.py
```

- [ ] **Step 2: Write `dashboard.py`**

Copy the body of the existing `if page == "◉ Dashboard":` block from `streamlit_app.py:224-279` into a function. Replace `fetch_dashboard_summary()` and `fetch_strategies()` calls with imports from `api_client`.

```python
"""Dashboard page — overview of strategy performance."""
from __future__ import annotations

import streamlit as st

from frontend.ui import api_client


def render() -> None:
    api_client.render_offline_banner_if_needed()
    st.title("Dashboard")
    st.markdown("Overview of your trading strategy performance")

    summary = api_client.fetch_dashboard_summary()
    strategies = api_client.fetch_strategies()

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Strategies", summary.get("active_strategies", 0))
    col2.metric("Total Backtests", summary.get("total_backtests", 0))
    col3.metric("Symbols Tested", summary.get("symbols_tested", 0))
    col4.metric("Total Trades", f"{summary.get('total_trades', 0):,}")

    st.markdown("---")
    st.subheader("Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Return", f"{summary.get('avg_return', 0):+.1f}%")
    col2.metric("Best Return", f"{summary.get('best_return', 0):+.1f}%")
    col3.metric("Avg Sharpe", f"{summary.get('avg_sharpe', 0):.2f}")
    col4.metric("Avg Win Rate", f"{summary.get('avg_win_rate', 0):.1f}%")

    if strategies:
        st.markdown("---")
        st.subheader("Recent Strategies")
        for strategy in strategies[:5]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{strategy['name']}**")
                st.caption(strategy["strategy_type"].replace("_", " ").title())
            with col2:
                st.caption(strategy["created_at"][:10])
            st.markdown("---")

    if not summary or summary.get("total_backtests", 0) == 0:
        st.info("No backtests yet. Create a strategy and run your first backtest from Strategy Builder.")
```

- [ ] **Step 3: Verify imports**

Run: `./venv/bin/python -c "from frontend.ui.pages.dashboard import render; print('ok')"`

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add frontend/ui/pages/__init__.py frontend/ui/pages/dashboard.py
git commit -m "feat: extract Dashboard page to its own module"
```

---

### Task 2.6: Create page module — Strategy Builder (the main payoff)

**Files:**
- Create: `frontend/ui/pages/strategy_builder.py`

- [ ] **Step 1: Write `strategy_builder.py`**

This is the largest single change in the refactor. The existing 4-strategy vertical stack collapses into 4 tabs, each one ~30 lines (down from ~80).

```python
"""Strategy Builder page — 4 strategy tabs + persistent comparison."""
from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from backend.data.fetcher import fetch_ohlcv
from backend.strategies.bollinger_bands import BollingerBandsStrategy
from backend.strategies.rsi_divergence import RSIDivergenceStrategy
from backend.strategies.macd_crossover import MACDCrossoverStrategy
from backend.strategies.vwap_reversion import VWAPReversionStrategy
from frontend.ui.charts import (
    plot_bollinger_bands,
    plot_rsi_divergence,
    plot_macd_crossover,
    plot_vwap_reversion,
)
from frontend.ui.comparison import render_strategy_comparison
from frontend.ui.strategy_runner import run_strategy


def _date_inputs(prefix: str, default_days: int = 730) -> tuple:
    symbol = st.text_input("Symbol", value="SPY", key=f"{prefix}_symbol")
    start = st.date_input("Start Date",
                          value=datetime.now() - timedelta(days=default_days),
                          key=f"{prefix}_start")
    end = st.date_input("End Date", value=datetime.now(), key=f"{prefix}_end")
    return symbol, start, end


def _bollinger_tab() -> None:
    st.markdown("Trade reversals at statistical price extremes (mean ± k·σ).")
    left, right = st.columns(2)
    with left:
        symbol, start, end = _date_inputs("bb")
    with right:
        period = st.slider("Period", 5, 50, 20, key="bb_period")
        std_dev = st.slider("Standard Deviations", 1.0, 3.0, 2.0, 0.1, key="bb_std")
    if st.button("Run Bollinger Bands", type="primary", key="bb_run"):
        try:
            data = fetch_ohlcv(symbol, start, end)
            run_strategy(
                strategy=BollingerBandsStrategy(period=period, num_std_dev=std_dev),
                data=data,
                plot_fn=plot_bollinger_bands,
                name="Bollinger Bands",
                session_key="bb_signals",
                csv_prefix="bb",
                symbol=symbol,
                min_bars=60,
            )
        except Exception as e:
            st.error(f"Error: {e}")


def _rsi_tab() -> None:
    st.markdown("Detect momentum divergences between price and RSI to spot reversals.")
    left, right = st.columns(2)
    with left:
        symbol, start, end = _date_inputs("rsi")
    with right:
        period = st.slider("RSI Period", 5, 30, 14, key="rsi_period")
        overbought = st.slider("Overbought", 60, 90, 70, key="rsi_ob")
        oversold = st.slider("Oversold", 10, 40, 30, key="rsi_os")
    if st.button("Run RSI Divergence", type="primary", key="rsi_run"):
        try:
            data = fetch_ohlcv(symbol, start, end)
            run_strategy(
                strategy=RSIDivergenceStrategy(
                    period=period, overbought=overbought, oversold=oversold,
                ),
                data=data,
                plot_fn=plot_rsi_divergence,
                name="RSI Divergence",
                session_key="rsi_signals",
                csv_prefix="rsi",
                symbol=symbol,
                min_bars=60,
            )
        except Exception as e:
            st.error(f"Error: {e}")


def _macd_tab() -> None:
    st.markdown("Trade EMA crossovers, with 200-EMA trend filter and ML confidence gating.")
    left, right = st.columns(2)
    with left:
        symbol, start, end = _date_inputs("macd")
    with right:
        fast = st.slider("Fast Period", 5, 50, 12, key="macd_fast")
        slow = st.slider("Slow Period", 10, 100, 26, key="macd_slow")
        sig_p = st.slider("Signal Period", 3, 20, 9, key="macd_signal")
        hist_th = st.slider("Histogram Threshold", 0.0, 1.0, 0.0, 0.01, key="macd_hist")
        zero_filter = st.checkbox("Zero-line filter", True, key="macd_zero")
        cooldown = st.slider("Signal cooldown (bars)", 0, 20, 5, key="macd_cool")
        regime_filter = st.checkbox("Regime filter (K-means)", True, key="macd_regime")
        confidence = st.slider("ML confidence threshold", 0.50, 0.90, 0.55, 0.01, key="macd_conf")
        ema_filter = st.checkbox("200 EMA trend filter", True, key="macd_ema")
    if fast >= slow:
        st.warning("Fast period must be less than slow period.")
    if st.button("Run MACD Crossover", type="primary", key="macd_run"):
        if fast >= slow:
            st.error("Fast period must be less than slow period.")
            return
        try:
            data = fetch_ohlcv(symbol, start, end)
            run_strategy(
                strategy=MACDCrossoverStrategy(
                    fast_period=fast, slow_period=slow, signal_period=sig_p,
                    histogram_threshold=hist_th, zero_line_filter=zero_filter,
                    cooldown_bars=cooldown, use_regime_filter=regime_filter,
                    confidence_threshold=confidence, use_200_ema_filter=ema_filter,
                ),
                data=data,
                plot_fn=plot_macd_crossover,
                name="MACD Crossover",
                session_key="macd_signals",
                csv_prefix="macd",
                symbol=symbol,
                min_bars=220,
                pre_fit=True,
            )
        except Exception as e:
            st.error(f"Error: {e}")


def _vwap_tab() -> None:
    st.markdown(
        "Trade mean reversion when price deviates from VWAP on above-average volume. "
        "Exits after a fixed holding period."
    )
    left, right = st.columns(2)
    with left:
        symbol, start, end = _date_inputs("vwap")
    with right:
        period = st.slider("VWAP Period", 5, 50, 20, key="vwap_period")
        dev = st.slider("Deviation threshold (fraction)", 0.005, 0.05, 0.015, 0.001, key="vwap_dev")
        vol_mult = st.slider("Volume Multiplier", 1.0, 3.0, 1.5, 0.1, key="vwap_vol_mult")
        hold = st.slider("Holding Period (bars)", 3, 30, 10, key="vwap_hold")
        regime = st.checkbox("Regime filter (ranging-markets only)", True, key="vwap_regime")
    if st.button("Run VWAP Reversion", type="primary", key="vwap_run"):
        try:
            data = fetch_ohlcv(symbol, start, end)
            run_strategy(
                strategy=VWAPReversionStrategy(
                    vwap_period=period, deviation_threshold=dev,
                    volume_multiplier=vol_mult, holding_period=hold,
                    use_regime_filter=regime,
                ),
                data=data,
                plot_fn=plot_vwap_reversion,
                name="VWAP Reversion",
                session_key="vwap_signals",
                csv_prefix="vwap",
                symbol=symbol,
                min_bars=60,
            )
        except Exception as e:
            st.error(f"Error: {e}")


def render() -> None:
    st.title("Strategy Builder")
    st.markdown("Configure and backtest trading strategies.")

    tab_bb, tab_rsi, tab_macd, tab_vwap = st.tabs(
        ["Bollinger Bands", "RSI Divergence", "MACD Crossover", "VWAP Reversion"]
    )
    with tab_bb:
        _bollinger_tab()
    with tab_rsi:
        _rsi_tab()
    with tab_macd:
        _macd_tab()
    with tab_vwap:
        _vwap_tab()

    render_strategy_comparison()
```

- [ ] **Step 2: Verify imports**

Run: `./venv/bin/python -c "from frontend.ui.pages.strategy_builder import render; print('ok')"`

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add frontend/ui/pages/strategy_builder.py
git commit -m "feat: rebuild Strategy Builder with tabs and shared runner"
```

---

### Task 2.7: Create remaining page modules

**Files:**
- Create: `frontend/ui/pages/strategy_library.py`
- Create: `frontend/ui/pages/backtest_results.py`
- Create: `frontend/ui/pages/sql_reports.py`

For each page: copy the body of the existing `elif page == "...":` block from `streamlit_app.py` into a `render()` function in the new module, replacing all `requests.get(...)` and `fetch_*` calls with imports from `api_client`. Add `api_client.render_offline_banner_if_needed()` at the top of each `render()`.

- [ ] **Step 1: Strategy Library**

Find the existing block at `frontend/streamlit_app.py:833-...` (starts with `elif page == "▦ Strategy Library":`). Copy its body, dedent, wrap in `render()`. Replace `fetch_strategies()` with `api_client.fetch_strategies()` and `delete_strategy(...)` with `api_client.delete_strategy(...)`.

```python
"""Strategy Library page — saved-strategy browser."""
from __future__ import annotations

import streamlit as st

from frontend.ui import api_client


def render() -> None:
    api_client.render_offline_banner_if_needed()
    st.title("Strategy Library")
    st.markdown("Browse and manage your saved strategies")

    strategies = api_client.fetch_strategies()
    if not strategies:
        st.info("No strategies saved yet. Strategies are saved automatically when you run a backtest from Strategy Builder.")
        return

    # [Copy the existing body verbatim from streamlit_app.py — replacing
    # delete_strategy(...) with api_client.delete_strategy(...).]
```

> **NOTE for executor:** Open `frontend/streamlit_app.py` and copy lines from the start of the Strategy Library block to the start of the next `elif`. Paste into the placeholder above, dedent by 4 spaces (since it was inside `elif:`), and swap function names as noted.

- [ ] **Step 2: Backtest Results**

Same pattern. Add empty-state guard (already done in Wave 1.3 inside the monolith — port it):

```python
"""Backtest Results page."""
from __future__ import annotations

import streamlit as st

from frontend.ui import api_client


def render() -> None:
    api_client.render_offline_banner_if_needed()
    st.title("Backtest Results")
    backtests = api_client.fetch_report("/reports/backtests")
    if not backtests:
        st.info("No backtests yet. Run one from Strategy Builder to populate this page.")
        return

    # [Copy the existing body verbatim from streamlit_app.py.]
```

- [ ] **Step 3: SQL Reports**

```python
"""SQL Reports page."""
from __future__ import annotations

import streamlit as st

from frontend.ui import api_client


def render() -> None:
    api_client.render_offline_banner_if_needed()
    st.title("SQL Reports")
    if not api_client.is_backend_up():
        st.error("SQL Reports require the Flask backend. Start it with `python backend/app.py`.")
        return

    # [Copy the existing body verbatim from streamlit_app.py.]
```

- [ ] **Step 4: Verify imports**

Run:
```bash
./venv/bin/python -c "
from frontend.ui.pages.strategy_library import render as r1
from frontend.ui.pages.backtest_results import render as r2
from frontend.ui.pages.sql_reports import render as r3
print('ok')
"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add frontend/ui/pages/strategy_library.py frontend/ui/pages/backtest_results.py frontend/ui/pages/sql_reports.py
git commit -m "feat: extract Library, Backtest Results, SQL Reports into page modules"
```

---

### Task 2.8: Slim streamlit_app.py to a router

**Files:**
- Modify: `frontend/streamlit_app.py` (replace the entire file)

- [ ] **Step 1: Replace `streamlit_app.py` with a thin router**

```python
"""STRATEX — Trading Strategy Assistant. Streamlit entry point."""
from __future__ import annotations

import streamlit as st

from frontend.ui.theme import inject_theme
from frontend.ui.pages import dashboard, strategy_builder, strategy_library, backtest_results, sql_reports

st.set_page_config(
    page_title="STRATEX - Trading Strategy Assistant",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

PAGES = {
    "◉ Dashboard":          dashboard.render,
    "⚡ Strategy Builder":   strategy_builder.render,
    "▦ Strategy Library":   strategy_library.render,
    "▣ Backtest Results":   backtest_results.render,
    "▤ SQL Reports":        sql_reports.render,
}

with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span style="font-size: 1.5rem; color: #00d4aa;">◈</span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 700; letter-spacing: 0.1em;">STRATEX</span>
        </div>
        <p style="color: #ffffff; font-size: 0.875rem; margin-bottom: 2rem;">Trading Strategy Assistant</p>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    st.markdown("---")
    st.markdown(
        '<p style="color: #ffffff; font-size: 0.75rem; text-align: center;">'
        "Built with Flask + Streamlit<br>SQL-Powered Analytics</p>",
        unsafe_allow_html=True,
    )

PAGES[page]()
```

- [ ] **Step 2: Verify line count**

Run: `wc -l frontend/streamlit_app.py`

Expected: under 60 lines (well below the 250 target).

- [ ] **Step 3: Run the full test suite**

Run: `./venv/bin/pytest tests/ -v`

Expected: 13 passed (5 strategies + 4 charts + 4 api_client).

- [ ] **Step 4: Manual smoke test**

```bash
./venv/bin/streamlit run frontend/streamlit_app.py
```

Click each nav item. Click each strategy tab. Run one strategy (e.g., VWAP on SPY 2-year window) and verify chart renders, metrics show, CSV downloads. Run a second strategy and verify Strategy Comparison panel appears below the tabs.

- [ ] **Step 5: Commit**

```bash
git add frontend/streamlit_app.py
git commit -m "refactor: slim streamlit_app to a thin page router"
```

---

## Wave 3 — Documentation + Cleanup

### Task 3.1: Version-bound requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Replace contents**

```text
streamlit>=1.40,<2.0
plotly>=5.20,<6.0
pandas>=2.2,<3.0
numpy>=1.26,<2.0
scikit-learn>=1.5,<2.0
yfinance>=0.2.40
flask>=3.0,<4.0
sqlalchemy>=2.0,<3.0
requests>=2.31
pytest>=8.0,<9.0
```

- [ ] **Step 2: Verify install still works**

Run: `./venv/bin/pip install -r requirements.txt --quiet`

Expected: silent success.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "build: version-bound dependencies to prevent silent breakage"
```

---

### Task 3.2: Rewrite README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace with the new README**

```markdown
# STRATEX — Trading Strategy Assistant

A Streamlit + Flask app for building, backtesting, and comparing technical trading strategies on real market data.

## Strategies

- **Bollinger Bands** — mean reversion at price extremes (mean ± k·σ).
- **RSI Divergence** — detects momentum divergences between price and RSI to spot reversals.
- **MACD Crossover** — EMA crossover with 200-EMA trend filter, K-means regime detection, and an ML confidence gate trained on the in-sample window.
- **VWAP Reversion** — fades large deviations from rolling VWAP when volume confirms; fixed holding-period exit; ranging-market regime filter.

Each strategy runs out-of-sample on a 70/30 train/test split and reports Sharpe ratio, max drawdown, and entry-signal count.

## Quickstart (Streamlit only)

The Strategy Builder works without the Flask backend.

```bash
pip install -r requirements.txt
streamlit run frontend/streamlit_app.py
```

Open http://localhost:8501. Navigate to **Strategy Builder**, pick a strategy tab, hit **Run**.

## Full setup (with Flask backend)

The Dashboard, Strategy Library, Backtest Results, and SQL Reports pages require the Flask backend.

```bash
# Terminal 1
python backend/app.py

# Terminal 2
streamlit run frontend/streamlit_app.py
```

## Project layout

```
backend/
├── app.py                # Flask entry
├── data/fetcher.py       # yfinance wrapper
├── models/models.py      # SQLAlchemy models
├── strategies/           # Bollinger, RSI, MACD, VWAP + base class
└── backtesting/          # engine, portfolio, metrics
frontend/
├── streamlit_app.py      # entry — sidebar + page router (~60 lines)
└── ui/
    ├── theme.py          # COLORS + inject_theme()
    ├── api_client.py     # backend wrappers + offline detection
    ├── strategy_runner.py
    ├── comparison.py
    ├── charts.py         # all plot_* functions
    └── pages/            # one module per page
docs/
├── signal/               # per-strategy implementation guides
└── superpowers/          # design specs and plans
sql/                      # schema + seed scripts
tests/                    # pytest suite
```

## Tests

```bash
pytest tests/ -v
```

13 smoke tests cover all four strategies, all four chart functions, and the API client's graceful-degradation behavior.

## Contributing

See `docs/signal/<strategy>.md` for the per-strategy spec each contributor implements. Branches follow `<strategy>-<role>` (e.g., `vwap-charts`). PRs target `main`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for current state"
```

---

### Task 3.3: Triage stale PR #12

**Files:** none — this is a GitHub action.

- [ ] **Step 1: Inspect PR #12**

Run: `gh pr view 12 --json files,additions,deletions,mergeable`

- [ ] **Step 2: Compare against main**

Run: `gh pr diff 12 | head -100`

- [ ] **Step 3: Post a triage comment**

```bash
gh pr comment 12 --body "$(cat <<'EOF'
This PR has been open since 2026-04-01 and is now stale. Since it was opened, main has received:
- Four strategy implementations (Bollinger, RSI, MACD, VWAP)
- A frontend refactor (theme, api_client, strategy_runner, page split)
- A pytest test suite

Recommended path:
1. Rebase onto current main and resolve conflicts, OR
2. Close this PR and re-extract the still-relevant pieces (data fetcher improvements, integration tests) into a fresh branch against the new structure.

@<author> please advise.
EOF
)"
```

- [ ] **Step 4: No commit needed** — this is a GitHub-only action.

---

## Final Verification

- [ ] **Step 1: Full test suite**

Run: `./venv/bin/pytest tests/ -v --cov=frontend.ui --cov=backend.strategies --cov-report=term-missing`

Expected: 13+ passed.

- [ ] **Step 2: Line-count target**

Run: `wc -l frontend/streamlit_app.py`

Expected: ≤ 250 (target was 250; actual likely ~60).

- [ ] **Step 3: Dead-CSS grep**

Run: `grep -rE "metric-card|strategy-card|sql-display" frontend/`

Expected: zero matches.

- [ ] **Step 4: Manual end-to-end**

```bash
./venv/bin/streamlit run frontend/streamlit_app.py
```

- Click each of the 5 nav items — each renders without errors (offline banner expected on backend-dependent pages)
- Strategy Builder → run all 4 strategies on SPY 2024-01-01 to 2026-01-01
- Verify Strategy Comparison panel appears once, below the tabs, listing all 4 strategies
- Verify CSV downloads for each strategy

- [ ] **Step 5: Push branch + open PR**

```bash
git push -u origin <branch-name>
gh pr create --title "refactor(frontend): tests + page split + tab-based Strategy Builder" --body "$(cat <<'EOF'
## Summary
Wave 0–3 of the frontend refactor per [docs/superpowers/specs/2026-04-29-frontend-refactor-design.md](docs/superpowers/specs/2026-04-29-frontend-refactor-design.md).

- Wave 0: pytest safety net (13 tests, all green)
- Wave 1: dead-CSS removal, icon unification, empty-state messages, stub deletion
- Wave 2: theme/api_client/strategy_runner/comparison modules + per-page modules + tabs in Strategy Builder; streamlit_app.py shrinks from 1,217 → ~60 lines
- Wave 3: README rewrite, version-bound requirements, stale-PR triage comment on #12

No strategy logic or SQL was modified.

## Test plan
- [x] `pytest tests/ -v` → 13 passed
- [x] `wc -l frontend/streamlit_app.py` → ≤ 250
- [x] Dead-CSS grep → zero matches
- [ ] Manual: run all 4 strategies, verify comparison panel, verify CSV downloads
EOF
)"
```

---

## Self-Review Checklist (after writing the plan)

- [x] Spec coverage: every wave/section in the spec maps to one or more tasks
- [x] No placeholders ("TBD", "implement later") — all code shown literally
- [x] Type/name consistency across tasks: `run_strategy` signature in 2.3 matches calls in 2.6
- [x] Each task ends with a commit step
- [x] No commit message uses `Co-Authored-By` (per user's CLAUDE.md)

