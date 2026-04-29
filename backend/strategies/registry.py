"""
Maps the `strategy_type` keys exposed in templates.py to the concrete
strategy classes that implement them.
"""

from .bollinger_bands import BollingerBandsStrategy
from .macd_crossover import MACDCrossoverStrategy
from .rsi_divergence import RSIDivergenceStrategy
from .vwap_reversion import VWAPReversionStrategy

STRATEGY_CLASSES = {
    "bollinger_bands": BollingerBandsStrategy,
    "macd_crossover": MACDCrossoverStrategy,
    "rsi_divergence": RSIDivergenceStrategy,
    "vwap_reversion": VWAPReversionStrategy,
}


def build_strategy(strategy_type: str, parameters: dict):
    """Instantiate a strategy by type, passing parameters as kwargs."""
    cls = STRATEGY_CLASSES.get(strategy_type)
    if cls is None:
        raise ValueError(f"Unknown strategy_type: {strategy_type}")
    return cls(**(parameters or {}))
