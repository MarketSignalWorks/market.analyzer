"""
OHLCV data fetcher backed by yfinance, with on-disk Parquet caching.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _to_iso(value) -> str:
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def _cache_path(symbol: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"{symbol.upper()}_{start}_{end}.parquet"


def fetch_ohlcv(symbol: str, start_date, end_date) -> pd.DataFrame:
    """Return a DataFrame indexed by date with Open/High/Low/Close/Volume."""
    if not symbol:
        return pd.DataFrame()

    symbol = symbol.strip().upper()
    start_iso = _to_iso(start_date)
    end_iso = _to_iso(end_date)

    cache_file = _cache_path(symbol, start_iso, end_iso)
    if cache_file.exists():
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            cache_file.unlink(missing_ok=True)

    try:
        df = yf.download(
            symbol,
            start=start_iso,
            end=end_iso,
            progress=False,
            auto_adjust=False,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[required].dropna()

        try:
            df.to_parquet(cache_file)
        except Exception:
            pass

        return df

    except Exception:
        return pd.DataFrame()


def fetch_benchmark(start_date, end_date, symbol: str = "SPY") -> pd.Series:
    """Return a close-price Series for the benchmark over the window."""
    df = fetch_ohlcv(symbol, start_date, end_date)
    if df.empty:
        return pd.Series(dtype=float)
    return df["Close"]
