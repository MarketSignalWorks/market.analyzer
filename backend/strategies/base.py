"""
Abstract base class for all trading strategies.
Every strategy should inherit from this and implement generate_signals().
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    def __init__(self, name: str, params: dict = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame with a 'signal' column (1 = buy, -1 = sell, 0 = hold)."""
        pass

    def get_params(self) -> dict:
        return self.params
