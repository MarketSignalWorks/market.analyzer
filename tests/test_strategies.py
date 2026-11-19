"""Smoke tests for all four strategies' generate_signals()."""
from __future__ import annotations

import pandas as pd

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
