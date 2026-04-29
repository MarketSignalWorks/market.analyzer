# STRATEX — Quant Stock Market Analyzer

A Streamlit + Flask app for building, backtesting, and comparing technical trading strategies on real market data. Four strategies are implemented end-to-end (Bollinger Bands, RSI Divergence, MACD Crossover, VWAP Reversion) with a SQL-backed backtest engine and reporting layer.

---

## Quick Launch (TL;DR)

```bash
# 1. Activate the virtual environment
source venv/bin/activate                 # mac / linux
# .\venv\Scripts\Activate.ps1            # windows powershell

# 2. Install dependencies
pip install -r requirements.txt

# 3a. Start the Flask backend  (Terminal 1)
python -m backend.app

# 3b. Start the Streamlit frontend  (Terminal 2)
streamlit run frontend/streamlit_app.py
```

Open **http://localhost:8501**. The sidebar LED should be **green ● Online** when the backend is running.

> **Streamlit-only mode:** if you skip step 3a, the Strategy Builder still works — the four strategies fetch data via yfinance and run locally. Pages that need the database (Library, Backtest Results, SQL Reports) will display a friendly offline message.

---

## Features

- **Dashboard** — Branded overview, strategy status cards, and live performance metrics.
- **Strategy Builder** — Four built-in strategies, each with their own controls, charts, and CSV signal export.
- **Strategy Library** — Browse, run, and delete saved strategies (backend-driven).
- **Backtest Results** — Equity curve, drawdown, monthly returns, full trade log.
- **SQL Reports** — Five preset analytical queries with visual comparisons.
- **Project Status** — At-a-glance build progress for every module in the codebase.

## Strategies

| Strategy | What it does | File |
| --- | --- | --- |
| **Bollinger Bands** | Mean reversion at statistical price extremes (μ ± k·σ) | [backend/strategies/bollinger_bands.py](backend/strategies/bollinger_bands.py) |
| **RSI Divergence** | Detects price/RSI divergence to spot momentum reversals | [backend/strategies/rsi_divergence.py](backend/strategies/rsi_divergence.py) |
| **MACD Crossover** | EMA crossovers + 200-EMA trend filter + ML confidence gate (logistic regression trained on the in-sample window) | [backend/strategies/macd_crossover.py](backend/strategies/macd_crossover.py) |
| **VWAP Reversion** | Mean reversion to VWAP with volume confirmation, K-means regime filter, fixed-holding-period exit | [backend/strategies/vwap_reversion.py](backend/strategies/vwap_reversion.py) |

Each strategy runs out-of-sample on a 70/30 train/test split and reports Sharpe ratio, max drawdown, and entry-signal count.

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | Streamlit, Plotly |
| Backend | Flask, Flask-SQLAlchemy, Flask-CORS |
| Database | SQLite (via SQLAlchemy) |
| Data | yfinance, pandas, numpy, pyarrow |
| ML | scikit-learn (KMeans regime, LogisticRegression confidence) |
| Tests | pytest |

## Project Structure

```
market.analyzer/
├── backend/
│   ├── app.py                       # Flask entry — registers blueprints, /api/health
│   ├── data/
│   │   └── fetcher.py               # yfinance OHLCV wrapper
│   ├── models/
│   │   └── models.py                # SQLAlchemy: Strategy, Backtest, Trade
│   ├── routes/
│   │   ├── meta.py                  # /api/templates, /api/symbols
│   │   ├── strategies.py            # CRUD on /api/strategies
│   │   ├── backtest.py              # POST /api/backtest, list, get-by-id
│   │   └── reports.py               # /api/reports/* (5 SQL reports + dashboard)
│   ├── strategies/
│   │   ├── base.py                  # BaseStrategy abstract class
│   │   ├── bollinger_bands.py
│   │   ├── rsi_divergence.py
│   │   ├── macd_crossover.py
│   │   ├── vwap_reversion.py
│   │   ├── registry.py              # Maps strategy types → classes
│   │   └── templates.py             # Default param sets per strategy
│   └── backtesting/
│       ├── engine.py                # Strategy execution loop
│       ├── portfolio.py             # Position + equity tracking
│       └── metrics.py               # Sharpe, drawdown, win rate, etc.
├── frontend/
│   ├── streamlit_app.py             # Entry — sidebar nav + 6 pages
│   └── ui/
│       └── charts.py                # Plotly candlestick + indicator overlays for each strategy
├── docs/
│   ├── signal/                      # Per-strategy implementation guides (one per teammate)
│   └── superpowers/                 # Design specs and refactor plans
├── sql/
│   └── example_queries.sql          # Reference queries for the SQL Reports page
├── tests/                           # pytest suite (9 smoke tests)
├── config.py                        # DATABASE_URI etc.
└── requirements.txt
```

## API Reference (Flask backend)

Base URL: `http://localhost:5000/api`

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Liveness probe |
| `/templates` | GET | List the 4 strategy templates |
| `/symbols` | GET | List available tickers |
| `/strategies` | GET / POST | List or create saved strategies |
| `/strategies/<id>` | GET / PUT / DELETE | Read, update, delete a strategy |
| `/backtest` | POST | Run a backtest, persist result, return equity curve + trades |
| `/backtests` | GET | List historical backtests |
| `/backtests/<id>` | GET | Fetch a single backtest with full payload |
| `/reports/dashboard-summary` | GET | Aggregates for the Dashboard page |
| `/reports/strategy-comparison` | GET | Per-strategy averages |
| `/reports/performance-by-symbol` | GET | Per-symbol breakdown |
| `/reports/time-analysis` | GET | Monthly aggregates |
| `/reports/top-performers` | GET | Top 10 backtests by return |
| `/reports/risk-metrics` | GET | Drawdown, Sharpe, return/drawdown |

## Tests

```bash
pytest tests/ -v
```

9 smoke tests cover all four strategies' `generate_signals()` output, all four chart functions' return-types and trace counts, and the VWAP holding-period invariant.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Sidebar LED is **red ● Offline** | Flask not running, or routes returning 404 | `python -m backend.app` in a second terminal |
| "Could not load templates" warning on Strategy Builder | Backend offline | Same as above — or just use the four strategies below it, they don't need the backend |
| `ModuleNotFoundError: flask_sqlalchemy` | New deps not installed after pull | `pip install -r requirements.txt` |
| Backend crashes on `from backend.models import db` | Old import path | `git pull origin main` to get the latest models module |
| Charts don't render | `plotly` outdated | `pip install --upgrade plotly` |
| Port 8501 / 5000 already in use | Previous server still running | Kill it: `lsof -ti :8501 \| xargs kill` (or `:5000`) |

## Contributing

The team works in role-based branches following the doc guides under [docs/signal/](docs/signal/). Each strategy is split across four roles:

| Role | Owns | File |
| --- | --- | --- |
| Person 1 | Math + features | `backend/strategies/<strategy>.py` (top) |
| Person 2 | Signal logic + filters | `backend/strategies/<strategy>.py` (class) |
| Person 3 | Charts | `frontend/ui/charts.py` |
| Person 4 | Streamlit wiring | `frontend/streamlit_app.py` |

Branches are named `<strategy>-<role>` (e.g., `vwap-charts`). PRs target `main` and are reviewed by the team lead before merge.

## Status

| Area | State |
| --- | --- |
| Bollinger Bands strategy | ✅ Done |
| RSI Divergence strategy | ✅ Done |
| MACD Crossover strategy | ✅ Done |
| VWAP Reversion strategy | ✅ Done |
| Flask backend (12 routes) | ✅ Done |
| SQL models + DB | ✅ Done |
| Backtesting engine | ✅ Done |
| Streamlit frontend | ✅ Done (6 pages) |
| Test suite | ✅ 9 tests passing |
