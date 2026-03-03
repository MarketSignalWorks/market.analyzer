# Quant Stock Market Analyzer

A Streamlit-based dashboard for analyzing and backtesting algorithmic trading strategies. Features interactive visualizations, strategy configuration, and SQL-powered performance reporting.

## Features

- **Dashboard** - Overview of strategy performance with key metrics
- **Strategy Builder** - Configure trading strategies with customizable parameters
- **Strategy Library** - Save and manage multiple strategies
- **Backtest Results** - Visualize equity curves, drawdowns, and trade history
- **SQL Reports** - Analyze performance with complex queries (JOINs, aggregations, filtering)

## Tech Stack

- **Frontend:** Streamlit, Plotly
- **Backend:** Flask, SQLAlchemy, SQLite (in development)
- **Data:** Pandas, NumPy

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/quant-stockmarket-analyzer.git
cd quant-stockmarket-analyzer
```

### 2. Create a virtual environment
```bash
python -m venv venv
```

**Activate it:**
- **Windows PowerShell:** `.\venv\Scripts\Activate.ps1`
- **Windows CMD:** `venv\Scripts\activate.bat`
- **Mac/Linux:** `source venv/bin/activate`

### 3. Install dependencies
```bash
pip install streamlit plotly requests pandas
```

### 4. Run the frontend
```bash
python -m streamlit run frontend/streamlit_app.py
```

The app will open at **http://localhost:8501**

## Project Structure

```
quant-stockmarket-analyzer/
├── frontend/
│   └── streamlit_app.py    # Streamlit dashboard
├── backend/                 # (In development)
│   └── app.py
├── README.md
└── requirements.txt
```

## Screenshots

*Coming soon*

## Roadmap

- [ ] Complete Flask backend with backtesting engine
- [ ] Add real market data integration (Yahoo Finance)
- [ ] Implement additional trading strategies
- [ ] Add user authentication
