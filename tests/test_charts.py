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
