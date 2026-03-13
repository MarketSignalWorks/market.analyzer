import pandas as pd
import numpy as np

def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    middle = close.rolling(window=window).mean()

    rolling_std = close.rolling(window=window).std()

    upper = middle + (num_std * rolling_std)
    lower = middle - (num_std * rolling_std)

    return middle, upper, lower