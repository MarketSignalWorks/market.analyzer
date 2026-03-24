import pandas as pd
import numpy as np
from backend.strategies.base import BaseStrategy

def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    middle = close.rolling(window=window).mean()

    rolling_std = close.rolling(window=window).std()

    upper = middle + (num_std * rolling_std)
    lower = middle - (num_std * rolling_std)

    return middle, upper, lower


class BollingerBandsStrategy(BaseStrategy):
    def __init__(self, window: int = 20, num_std: float = 2.0):
        super().__init__(name = "Bollingger Bands", 
        params = {"window": window, "num_std": num_std})
        self.window = window
        self.num_std = num_std

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Close" not in df.columns:
            raise ValueError("Input DataFrame must have a 'Close' column")
        out = df.copy()

        middle, upper, lower = compute_bollinger_bands(
            close = out["Close"]. window = self.window, num_std = self.num_std)
        
        out["middle"] = middle
        out["upper"] = upper
        out["lower"] = lower
        