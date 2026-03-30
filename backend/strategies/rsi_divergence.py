import pandas as pd
from backend.strategies.base import BaseStrategy

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower = 0)
    losses = (-delta).clip(lower = 0)
    avg_gain = gains.ewm(com = period - 1, min_periods = period).mean()
    avg_loss = losses.ewm(com = period - 1, min_periods = period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

class RSIDivergenceStrategy(BaseStrategy):
    def __init__(
        self,
        rsi_period: int = 14,
        divergence_window: int = 5,
        overbought: int = 70,
        oversold: int = 30,
    ):
        super().__init__(
            name="RSI Divergence",
            params={
                "rsi_period": rsi_period,
                "divergence_window": divergence_window,
                "overbought": overbought,
                "oversold": oversold,
            }
        )
        self.rsi_period        = rsi_period
        self.divergence_window = divergence_window
        self.overbought        = overbought
        self.oversold          = oversold

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data  = data.copy()
        close = data['Close']
        rsi   = compute_rsi(close, self.rsi_period)
        data['rsi'] = rsi
        w = self.divergence_window
        bullish = (
            (close < close.shift(w)) &
            (rsi   > rsi.shift(w))   &
            (rsi   < self.oversold)
        )
        bearish = (
            (close > close.shift(w)) &
            (rsi   < rsi.shift(w))   &
            (rsi   > self.overbought)
        )

        signal = pd.Series(0, index=data.index)
        signal[bullish] =  1
        signal[bearish] = -1
        data['signal'] = signal
        return data

