import pandas as pd
from backend.strategies.base import BaseStrategy

def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    middle = close.rolling(window=window).mean()

    rolling_std = close.rolling(window=window).std()

    upper = middle + (num_std * rolling_std)
    lower = middle - (num_std * rolling_std)

    return middle, upper, lower


class BollingerBandsStrategy(BaseStrategy):
    def __init__(self, window: int = 20, num_std: float = 2.0):
        super().__init__(name = "Bollinger Bands", 
        params = {"window": window, "num_std": num_std})
        self.window = window
        self.num_std = num_std

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        if "Close" not in data.columns:
            raise ValueError("Input DataFrame must have a 'Close' column")
        data = data.copy()

        middle, upper, lower = compute_bollinger_bands(
            data["Close"], self.window, self.num_std)
        
        data["middle"] = middle
        data["upper"] = upper
        data["lower"] = lower
        signal = pd.Series(0, index = data.index)
        
        buy_condition = (data["Close"].shift(1) >= lower.shift(1)) & (data["Close"] < lower)
        sell_condition = (data["Close"].shift(1) <= upper.shift(1)) & (data["Close"] > upper)
        signal[buy_condition] = 1
        signal[sell_condition] = -1
        data['signal'] = signal
        return data
