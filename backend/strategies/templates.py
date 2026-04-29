"""
Strategy templates surfaced by the /api/templates endpoint.

Each template defines its display name, description, and a parameter
schema that the Streamlit Strategy Builder uses to render inputs.
Parameter `type` is one of: "int", "float", "select".
"""

TEMPLATES = {
    "macd_crossover": {
        "name": "MACD Crossover",
        "description": (
            "Trend-following strategy using the MACD line crossing its signal line. "
            "Optional 200 EMA, zero-line, and ML-confidence regime filters."
        ),
        "parameters": {
            "fast_period": {
                "type": "int", "min": 5, "max": 50, "default": 12,
                "description": "Fast EMA period",
            },
            "slow_period": {
                "type": "int", "min": 10, "max": 100, "default": 26,
                "description": "Slow EMA period",
            },
            "signal_period": {
                "type": "int", "min": 3, "max": 20, "default": 9,
                "description": "Signal line EMA period",
            },
            "histogram_threshold": {
                "type": "float", "min": 0.0, "max": 1.0, "default": 0.0,
                "description": "Minimum histogram magnitude to trigger",
            },
        },
    },
    "bollinger_bands": {
        "name": "Bollinger Bands",
        "description": (
            "Mean-reversion strategy. Buys when price pierces the lower band and "
            "sells when it tags the upper band."
        ),
        "parameters": {
            "window": {
                "type": "int", "min": 5, "max": 50, "default": 20,
                "description": "Moving average window (bars)",
            },
            "num_std": {
                "type": "float", "min": 1.0, "max": 3.0, "default": 2.0,
                "description": "Standard-deviation multiplier",
            },
        },
    },
    "rsi_divergence": {
        "name": "RSI Divergence",
        "description": (
            "Detects bullish/bearish divergences between price and RSI to anticipate "
            "reversals."
        ),
        "parameters": {
            "rsi_period": {
                "type": "int", "min": 5, "max": 30, "default": 14,
                "description": "RSI lookback period",
            },
            "divergence_window": {
                "type": "int", "min": 3, "max": 20, "default": 5,
                "description": "Window for divergence detection",
            },
            "overbought": {
                "type": "int", "min": 60, "max": 90, "default": 70,
                "description": "Overbought threshold",
            },
            "oversold": {
                "type": "int", "min": 10, "max": 40, "default": 30,
                "description": "Oversold threshold",
            },
        },
    },
    "vwap_reversion": {
        "name": "VWAP Reversion",
        "description": (
            "Mean-reversion strategy using VWAP. Enters when price deviates "
            "meaningfully from VWAP on elevated volume."
        ),
        "parameters": {
            "vwap_period": {
                "type": "int", "min": 5, "max": 50, "default": 20,
                "description": "VWAP rolling window",
            },
            "deviation_threshold": {
                "type": "float", "min": 0.005, "max": 0.05, "default": 0.015,
                "description": "Fractional deviation from VWAP",
            },
            "volume_multiplier": {
                "type": "float", "min": 1.0, "max": 3.0, "default": 1.5,
                "description": "Volume must exceed multiplier × avg volume",
            },
            "holding_period": {
                "type": "int", "min": 3, "max": 30, "default": 10,
                "description": "Bars to hold before exit",
            },
        },
    },
}


# Curated symbol universe surfaced by /api/symbols.
SYMBOLS = [
    "SPY", "QQQ", "DIA", "IWM",
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    "JPM", "BAC", "GS",
    "XOM", "CVX",
    "JNJ", "PFE",
]
