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
