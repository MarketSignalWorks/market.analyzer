import pandas as pd

def compute_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 20,
) -> pd.Series:
    typical_price = (high + low + close) / 3
    numerator = (typical_price * volume).rolling(period).sum()
    denominator = volume.rolling(period).sum()
    vwap = numerator / denominator
    return vwap

def compute_vwap_bands(
    vwap: pd.Series,
    deviation_threshold: float = 0.015,
) -> tuple[pd.Series, pd.Series]:
    upper_band = vwap * (1 + deviation_threshold)
    lower_band = vwap * (1 - deviation_threshold)
    return upper_band, lower_band

def compute_volume_features(
    volume: pd.Series,
    avg_period: int = 20,
) -> tuple[pd.Series, pd.Series]:
    avg_volume = volume.rolling(avg_period).mean()
    volume_ratio = volume / avg_volume
    return avg_volume, volume_ratio