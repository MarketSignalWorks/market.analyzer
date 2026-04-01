import os
from pathlib import Path
import pandas as pd
import yfinance as yf

# Set up the cache directory relative to this file
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical stock data for a given ticker and date range.
    Checks the local parquet cache first before querying yfinance.
    """
    cache_file = CACHE_DIR / f"{ticker}_{start_date}_{end_date}.parquet"
    
    # 1. Check if cached data exists
    if cache_file.exists():
        return pd.read_parquet(cache_file)
    
    # 2. Not cached, fetch from yfinance
    # yfinance automatically skips weekends and holidays
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    # Edge case: non-existent ticker or completely empty date range
    if df.empty:
        raise ValueError(f"No data found for ticker '{ticker}' between {start_date} and {end_date}.")
    
    # 3. Clean up the DataFrame
    # yfinance sometimes returns a MultiIndex for columns depending on the version/query.
    # Flatten it if necessary so we have simple column names.
    if isinstance(df.columns, pd.MultiIndex):
        # Usually level 0 is the metric (Close, Open) and level 1 is the ticker
        df.columns = df.columns.get_level_values(0)
        
    # Make sure we only grab the standard columns, capitalizing them as requested
    cols_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    missing_cols = [col for col in cols_to_keep if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns from yfinance: {missing_cols}")
        
    df = df[cols_to_keep]
    df.index.name = 'Date'
    
    # 4. Save to cache
    df.to_parquet(cache_file)
    
    return df


def fetch_benchmark(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches SPY benchmark data required for Alpha and Beta calculations.
    Returns the DataFrame using the same caching mechanism.
    """
    return fetch("SPY", start_date, end_date)
