import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
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
    data = data.copy()
    data["macd_slope"] = data["macd"].diff()
    data["hist_slope"] = data["histogram"].diff()
    data["price_momentum"] = data['Close'].pct_change(5)
    data["volatility"] = data['Close'].pct_change().rolling(20).std()
    data["hist_momentum"] = data['histogram'] - data['histogram'].shift(5)
    return data


def compute_200_ema(close: pd.Series) -> pd.Series:
    return close.ewm(span=200, adjust=False).mean()


class MACDCrossoverStrategy(BaseStrategy):
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        histogram_threshold: float = 0.0,
        zero_line_filter: bool = True,
        cooldown_bars: int = 5,
        use_regime_filter: bool = True,
        confidence_threshold: float = 0.55,
        use_200_ema_filter: bool = True,
    ):
        super().__init__(
            name="MACD Crossover",
            params={
                "fast_period": fast_period,
                "slow_period": slow_period,
                "signal_period": signal_period,
                "histogram_threshold": histogram_threshold,
                "zero_line_filter": zero_line_filter,
                "cooldown_bars": cooldown_bars,
                "use_regime_filter": use_regime_filter,
                "confidence_threshold": confidence_threshold,
                "use_200_ema_filter": use_200_ema_filter,
            },
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.histogram_threshold = histogram_threshold
        self.zero_line_filter = zero_line_filter
        self.cooldown_bars = cooldown_bars
        self.use_regime_filter = use_regime_filter
        self.confidence_threshold = confidence_threshold
        self.use_200_ema_filter = use_200_ema_filter
        self.model = None

    def detect_regime(self, data: pd.DataFrame) -> pd.Series:
        feature_cols = ["volatility", "price_momentum"]
        features = data[feature_cols].copy()
        features["price_momentum"] = features["price_momentum"].abs()

        valid_mask = features.notna().all(axis=1)
        X = features[valid_mask].values

        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        kmeans.fit(X)

        center_volatilities = kmeans.cluster_centers_[:, 0]
        trending_cluster = int(np.argmin(center_volatilities))

        raw_labels = kmeans.labels_
        mapped_labels = np.where(raw_labels == trending_cluster, 0, 1)

        regime = pd.Series(1, index=data.index, dtype=int)
        regime[valid_mask] = mapped_labels
        return regime

    def fit_confidence_model(self, train_df: pd.DataFrame) -> None:
        macd_line, signal_line, histogram = compute_macd(
            train_df["Close"],
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            signal_period=self.signal_period,
        )

        train_df = train_df.copy()
        train_df["macd"] = macd_line
        train_df["signal_line"] = signal_line
        train_df["histogram"] = histogram
        train_df = compute_features(train_df)

        feature_cols = ["macd_slope", "hist_slope", "price_momentum", "volatility", "hist_momentum"]
        X = train_df[feature_cols]
        y = (train_df["Close"].shift(-5) > train_df["Close"]).astype(int)

        valid_mask = X.notna().all(axis=1) & y.notna()
        X = X[valid_mask]
        y = y[valid_mask]

        self.model = LogisticRegression(max_iter=500)
        self.model.fit(X, y)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()

        macd_line, signal_line, histogram = compute_macd(
            data["Close"],
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            signal_period=self.signal_period,
        )
        data["macd"] = macd_line
        data["signal_line"] = signal_line
        data["histogram"] = histogram
        data = compute_features(data)
        data["ema_200"] = compute_200_ema(data["Close"])

        prev_macd = data["macd"].shift(1)
        prev_signal = data["signal_line"].shift(1)
        curr_macd = data["macd"]
        curr_signal = data["signal_line"]

        bullish_cross = (
            (prev_macd < prev_signal) &
            (curr_macd > curr_signal) &
            (data["histogram"] > self.histogram_threshold)
        )
        bearish_cross = (
            (prev_macd > prev_signal) &
            (curr_macd < curr_signal) &
            (data["histogram"] < -self.histogram_threshold)
        )

        signal = pd.Series(0, index=data.index)
        signal[bullish_cross] = 1
        signal[bearish_cross] = -1

        if self.zero_line_filter:
            signal[(signal == 1) & (data["macd"] <= 0)] = 0
            signal[(signal == -1) & (data["macd"] >= 0)] = 0

        if self.use_200_ema_filter:
            signal[(signal == 1) & (data["Close"] < data["ema_200"])] = 0
            signal[(signal == -1) & (data["Close"] > data["ema_200"])] = 0

        if self.cooldown_bars > 0:
            signal_list = signal.tolist()
            last_signal_bar = -self.cooldown_bars - 1

            for i in range(len(signal_list)):
                if signal_list[i] != 0:
                    if (i - last_signal_bar) <= self.cooldown_bars:
                        signal_list[i] = 0
                    else:
                        last_signal_bar = i

            signal = pd.Series(signal_list, index=data.index)

        regime = pd.Series(0, index=data.index)
        if self.use_regime_filter:
            regime = self.detect_regime(data)
            signal[regime == 1] = 0

        data["regime"] = regime

        feature_cols = ["macd_slope", "hist_slope", "price_momentum", "volatility", "hist_momentum"]
        confidence = pd.Series(0.0, index=data.index)

        if self.model is not None:
            X_infer = data[feature_cols].fillna(0).values
            proba = self.model.predict_proba(X_infer)
            prob_up = pd.Series(proba[:, 1], index=data.index)
            prob_down = pd.Series(proba[:, 0], index=data.index)

            signal[(signal == 1) & (prob_up < self.confidence_threshold)] = 0
            signal[(signal == -1) & (prob_down < self.confidence_threshold)] = 0

            confidence[signal == 1] = prob_up[signal == 1]
            confidence[signal == -1] = prob_down[signal == -1]

        data["confidence"] = confidence
        data["signal"] = signal

        return data