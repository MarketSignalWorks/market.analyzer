import pandas as pd
from backend.strategies.base import BaseStrategy
from sklearn.cluster import KMeans
import numpy as np

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


class VWAPReversionStrategy(BaseStrategy):
    def __init__(
        self,
        vwap_period: int = 20,
        deviation_threshold: float = 0.015,   # 1.5%
        volume_multiplier: float = 1.5,
        holding_period: int = 10,
        use_regime_filter: bool = True,
    ):
        super().__init__(
            name="VWAP Reversion",
            params={
                "vwap_period": vwap_period,
                "deviation_threshold": deviation_threshold,
                "volume_multiplier": volume_multiplier,
                "holding_period": holding_period,
                "use_regime_filter": use_regime_filter,
            },
        )
        self.vwap_period = vwap_period
        self.deviation_threshold = deviation_threshold
        self.volume_multiplier = volume_multiplier
        self.holding_period = holding_period
        self.use_regime_filter = use_regime_filter


    def detect_regime(self, data: pd.DataFrame) -> pd.Series:
        features = data[['volatility', 'price_momentum']].copy()
        features['price_momentum'] = features['price_momentum'].abs()
        valid_mask = features.notna().all(axis=1)
        X = features[valid_mask].values

        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        kmeans.fit(X)

        trending_cluster = int(np.argmin(kmeans.cluster_centers_[:, 0]))
        mapped_labels = np.where(kmeans.labels_ == trending_cluster, 0, 1)

        regime = pd.Series(1, index=data.index, dtype=int)
        regime[valid_mask] = mapped_labels

        return regime
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        vwap = compute_vwap(data["High"], data["Low"], data["Close"], data["Volume"], self.vwap_period)
        upper_band, lower_band = compute_vwap_bands(vwap, self.deviation_threshold)
        avg_volume, volume_ratio = compute_volume_features(data['Volume'])

        data["vwap"] = vwap
        data["upper_band"] = upper_band
        data["lower_band"] = lower_band
        data["avg_volume"] = avg_volume
        data["volume_ratio"] = volume_ratio
        data['deviation'] = (data['Close'] - vwap) / vwap
        data["price_momentum"] = data["Close"].pct_change(5)
        data["volatility"] = data["Close"].pct_change().rolling(20).std()

        bullish = (data['deviation'] < -self.deviation_threshold) & (data['volume_ratio'] > self.volume_multiplier)
        bearish = (data['deviation'] > self.deviation_threshold) & (data['volume_ratio'] > self.volume_multiplier)

        data["signal"] = 0
        data.loc[bullish, "signal"] = 1
        data.loc[bearish, "signal"] = -1

        if self.use_regime_filter:
            data["regime"] = self.detect_regime(data)
            data.loc[data["regime"] == 0, "signal"] = 0
        else:
            data["regime"] = 1

        data["volume_multiplier"] = self.volume_multiplier

        entry_signals = data["signal"].copy()
        final_signal = pd.Series(0, index=data.index)
        i = 0

        while i < len(entry_signals):

            if entry_signals.iloc[i] != 0:
                direction = entry_signals.iloc[i]

                end = min(
                    i + self.holding_period,
                    len(entry_signals)
                )

                for j in range(i, end):
                    final_signal.iloc[j] = direction

                i = end

            else:
                i += 1

        data["signal"] = final_signal

        return data







