import pandas as pd
from backend.strategies.base import BaseStrategy

def compute_macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = close.ewm(span=fast_period, adjust=False).mean()
    slow_ema = close.ewm(span=slow_period, adjust=False).mean()

    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    return (macd_line, signal_line, histogram)

    
def compute_features(data: pd.DataFrame) -> pd.DataFrame:
    data["macd_slope"] = data["macd"].diff()
    data["hist_slope"] = data["histogram"].diff()
    data["price_momentum"] = data['Close'].pct_change(5)
    data["volatility"] = data['Close'].pct_change().rolling(20).std()
    data["hist_momentum"] = data['histogram'] - data['histogram'].shift(5)

    return data


def compute_200_ema(close: pd.Series) -> pd.Series:
    return close.ewm(span=200, adjust=False).mean()

