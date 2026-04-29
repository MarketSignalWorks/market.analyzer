# Frontend Refactor + Polish — Design Spec

**Date:** 2026-04-29
**Scope:** UI, structure, tests, docs. Explicitly **excludes** SQL implementation and signal logic.
**Constraint:** All four strategies (Bollinger, RSI, MACD, VWAP) are merged on `main`. Person 4's VWAP wiring (PR #20) was the last blocker; the Strategy Builder is now safe to restructure.

---

## Goal

Take a working but messy STRATEX app and turn it into a clean, demo-ready, refactor-friendly project without altering strategy math or SQL.

## Non-goals

- Changing any strategy's signal generation logic
- Modifying SQL queries or schemas in `sql/`
- Replacing Streamlit with another framework
- Adding new strategies

---

## Current state (problems being solved)

| Area | Problem |
| --- | --- |
| `frontend/streamlit_app.py` | 1,217-line monolith: CSS + API helpers + 5 pages all in one file |
| Strategy Builder section | Same ~80-line block duplicated 4× (Bollinger / RSI / MACD / VWAP); each does fetch → 70/30 split → Sharpe + drawdown → comparison panel → CSV download |
| 4-way Strategy Comparison panel | Lives inside each strategy's button handler; rebuilt 4× and only renders after a button click |
| Custom CSS | `.metric-card`, `.strategy-card`, `.sql-display`, `.section-header` defined but **never applied** anywhere — pure dead code |
| Icon style | Mixed glyphs in nav (`◈ ⚡ ◇ ◫ ◉`) and emoji in tabs (`📈 📉 📊`) |
| `frontend/ui/sidebar.py`, `frontend/ui/results.py` | Empty `# TODO` stubs that have lived in the repo since day one |
| Backend dependency | 4 of 5 pages hard-fail when Flask at `localhost:5000` is down — silent `requests.exceptions.ConnectionError` for the user |
| Test coverage | One file (`backend/backtesting/test_portfolio.py`) — strategies and chart functions have zero tests |
| README | 72 lines, written before any of the strategies were built |
| Stale PR #12 | Open since 2026-04-01, status `mergeable: UNKNOWN` — needs triage |
| `requirements.txt` | All 9 packages unpinned — environment will drift |

---

## Architecture after refactor

```
frontend/
├── streamlit_app.py          # entry point, ~250 lines
│                             # imports + page router; each page is a function call
├── ui/
│   ├── theme.py              # NEW — centralized CSS + color constants
│   ├── api_client.py         # NEW — wraps requests calls; surfaces backend-down state
│   ├── strategy_runner.py    # NEW — run_strategy(strategy, data, name, key) helper
│   ├── comparison.py         # NEW — render_strategy_comparison() (single instance)
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── strategy_builder.py
│   │   ├── strategy_library.py
│   │   ├── backtest_results.py
│   │   └── sql_reports.py
│   └── charts.py             # unchanged (Aryan's PR #19 already shipped)
└── ...

tests/
├── __init__.py
├── test_strategies.py        # NEW — smoke test per strategy
├── test_charts.py            # NEW — each plot_* returns Figure with expected traces
└── test_api_client.py        # NEW — graceful-degradation behavior
```

Empty stubs `frontend/ui/sidebar.py` and `frontend/ui/results.py` are deleted (replaced by the more specific modules above).

---

## Wave 0 — Test safety net (do FIRST)

Goal: catch regressions during Wave 2 refactor.

### `tests/test_strategies.py`

For each of the 4 strategies, build a 250-bar synthetic OHLCV DataFrame and assert:

- `generate_signals(df)` returns a DataFrame
- Required columns are present (per each strategy's spec — e.g., VWAP has `vwap`, `upper_band`, `lower_band`, `avg_volume`, `volume_ratio`, `deviation`, `regime`, `volume_multiplier`, `signal`)
- `signal` column values are a subset of `{-1, 0, 1}`
- For VWAP only: max consecutive run length of nonzero signal ≤ `holding_period`

### `tests/test_charts.py`

For each of `plot_bollinger_bands`, `plot_rsi_divergence`, `plot_macd_crossover`, `plot_vwap_reversion`:

- Build the strategy output, pass to plot function
- Assert returned object is `plotly.graph_objects.Figure`
- Assert expected trace names are present (e.g., VWAP has `Price, VWAP, Upper Band, Lower Band, Long Entry, Short Entry, Volume, Avg Volume, Vol Spike`)

### `tests/test_api_client.py`

- Mock `requests.get` to raise `ConnectionError`; assert `api_client.fetch_dashboard_summary()` returns sentinel `{}` not exception
- Mock 200 response; assert it returns parsed JSON

**Pass criteria:** `pytest tests/` exits 0 before Wave 1 begins.

---

## Wave 1 — Low-risk polish (additive, no file moves)

### 1.1 Backend-down banner

Add to top of every page that calls the Flask API:

```python
if not api_client.is_backend_up():
    st.warning("⚠ Backend offline — showing cached/empty data. Run `python backend/app.py` to enable full features.")
```

`api_client.is_backend_up()` does a lightweight HEAD on `/api/health` with `timeout=0.5`, caches result for 30 s.

### 1.2 Dead CSS removal

Delete from the `<style>` block in `streamlit_app.py`:

- `.metric-card`, `.metric-value`, `.metric-value.positive/.negative/.cyan`, `.metric-label`
- `.section-header`, `.section-icon`
- `.strategy-card`, `.strategy-name`, `.strategy-type`
- `.sql-display`, `.type-badge`

(Verified by `grep -r "metric-card\|strategy-card\|sql-display" frontend/` returning zero hits.)

Keep: `.stApp` background, sidebar styling, `#MainMenu`/`footer` hide rules.

### 1.3 Icon unification

Replace mixed glyphs/emoji with a single set:

| Page | Before | After |
| --- | --- | --- |
| Dashboard | `◉` | `◉` (keep — clean glyph) |
| Strategy Builder | `⚡` | `⚡` |
| Strategy Library | `◫` | `▦` (cleaner box glyph) |
| Backtest Results | `◈` | `▣` |
| SQL Reports | `◇` | `▤` |
| Equity Curve tab | `📈` | drop emoji, label only |
| Drawdown tab | `📉` | drop emoji |
| Monthly Returns tab | `📊` | drop emoji |

Rationale: terminal-themed monospace glyphs in nav, no emoji in tabs — consistent with `JetBrains Mono` typography choice.

### 1.4 Empty-state messages

Each page gets a meaningful empty state:

- **Dashboard:** when `total_backtests == 0`, show "Run your first backtest from Strategy Builder to populate this view." (already partial — formalize)
- **Strategy Library:** "No strategies saved. Strategies are saved automatically when you run a backtest from Strategy Builder."
- **Backtest Results:** "No backtests yet. Run one from Strategy Builder."
- **SQL Reports:** "Backend offline — SQL reports require the Flask API." (when offline)

### 1.5 Stub cleanup

Delete `frontend/ui/sidebar.py` and `frontend/ui/results.py` (both are pure `# TODO` files). Their responsibilities will be filled by the new modules in Wave 2.

---

## Wave 2 — Strategy Builder restructure

### 2.1 Extract `run_strategy()` helper

`frontend/ui/strategy_runner.py`:

```python
def run_strategy(
    *,
    strategy,                      # any subclass of BaseStrategy
    data: pd.DataFrame,            # full fetched OHLCV
    plot_fn,                       # one of the plot_* functions
    name: str,                     # display name e.g. "VWAP Reversion"
    session_key: str,              # session_state key e.g. "vwap_signals"
    csv_prefix: str,               # CSV filename prefix e.g. "vwap"
    symbol: str,                   # ticker for CSV/metric label
    min_bars: int,                 # per-strategy minimum: 60 for BB/RSI/VWAP, 220 for MACD (200-EMA)
    train_split: float = 0.70,
    pre_fit: bool = False,         # MACD's confidence model needs strategy.fit_confidence_model(train_data)
) -> None:
    """One-stop runner: split → (optional fit) → generate → plot → metrics → store → CSV."""
```

Replaces the 4 duplicated ~80-line blocks. Each strategy's button handler becomes ~10 lines.

### 2.2 Tabs instead of vertical stack

In `pages/strategy_builder.py`:

```python
tab_bb, tab_rsi, tab_macd, tab_vwap = st.tabs(
    ["Bollinger Bands", "RSI Divergence", "MACD Crossover", "VWAP Reversion"]
)
```

Each tab contains only its parameter inputs and the run button. The runner output renders inside the same tab.

### 2.3 Single persistent comparison panel

`frontend/ui/comparison.py`:

```python
def render_strategy_comparison() -> None:
    """Renders below the tabs. Reads session_state for any signals already computed.
    Displays automatically when 2+ strategies have been run."""
```

Called once at the bottom of `pages/strategy_builder.py` — replaces 4 duplicated copies inside button handlers.

### 2.4 Page split

Move each page's body to `frontend/ui/pages/<name>.py`. The new `streamlit_app.py` becomes:

```python
# imports + sidebar + theme injection only
page = st.sidebar.radio("Navigation", PAGES.keys())
PAGES[page]()  # calls the appropriate page function
```

Target: `streamlit_app.py` ≤ 250 lines.

### 2.5 Theme module

`frontend/ui/theme.py`:

```python
COLORS = {
    "bg":          "#0a0e14",
    "card":        "#0d1117",
    "border":      "rgba(255,255,255,0.08)",
    "accent":      "#00d4aa",
    "positive":    "#3fb950",
    "negative":    "#ff6b6b",
    "vwap_purple": "#a78bfa",
    "vol_yellow":  "#f0c040",
}

def inject_theme() -> None:
    """st.markdown the (now small) CSS block once at app start."""
```

All charts and pages read colors from `COLORS` instead of hard-coded hex.

---

## Wave 3 — Documentation + cleanup

### 3.1 README rewrite

Sections:

1. **What this is** — STRATEX, four strategies, signal generation + backtesting
2. **Strategies** — one-paragraph each: Bollinger, RSI Divergence, MACD Crossover, VWAP Reversion
3. **Quickstart** — `pip install -r requirements.txt && streamlit run frontend/streamlit_app.py` (Streamlit-only path; backend is optional)
4. **Full setup** — Flask backend instructions for Dashboard / Library / Backtest Results / SQL Reports
5. **Project layout** — directory tree
6. **Tests** — `pytest tests/`
7. **Screenshot** — one image of the Strategy Builder with VWAP running

### 3.2 PR #12 triage

- `gh pr view 12 --json files,additions,deletions`
- Read the changes; identify what overlaps with current main
- Add a comment proposing rebase-or-close based on findings
- Do **not** merge without team owner approval

### 3.3 Version-bound requirements.txt

Major-version upper bounds prevent silent breakage when a dependency releases a new major. Loose enough to accept patch/minor updates.

```
streamlit>=1.40,<2.0
plotly>=5.20,<6.0
pandas>=2.2,<3.0
numpy>=1.26,<2.0
scikit-learn>=1.5,<2.0
yfinance>=0.2.40
flask>=3.0,<4.0
sqlalchemy>=2.0,<3.0
requests>=2.31
```

---

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Refactor breaks existing button-click flows | Wave 0 tests catch chart trace count + signal schema; manual smoke test of each tab before commit |
| Teammates have local branches touching `streamlit_app.py` | Coordinate timing — refactor PR is a single commit, easy to rebase against |
| `st.tabs` rerenders all tabs on any input change — could be slow with 4 strategies | All inputs are cheap; only fetching/computation happens on button click |
| Backend-up check adds 0.5 s latency on every page load | Cache result for 30 s via `@st.cache_data(ttl=30)` |

## Success criteria

- [ ] `pytest tests/` passes (Wave 0)
- [ ] `streamlit_app.py` ≤ 250 lines (down from 1,217)
- [ ] `grep -r "metric-card\|strategy-card\|sql-display" frontend/` returns zero hits
- [ ] All 4 strategies runnable from their respective tabs without errors
- [ ] Strategy Comparison panel renders once, below the tabs, when 2+ strategies have been run
- [ ] App launches and is usable with backend offline (with warning banner)
- [ ] README quickstart works for someone with a fresh clone
- [ ] Each commit corresponds to one wave (0, 1, 2, 3) — easy to review and revert independently

---

## Out of scope (parking lot)

Things noticed but not addressed in this refactor:

- Persisting backtest results in DB (currently session-state only) — backend team's domain
- Broker integration / live trading
- Walk-forward optimization across multiple symbols simultaneously
- Strategy parameter optimization (grid search / Bayesian)
- Real-time data via WebSocket
