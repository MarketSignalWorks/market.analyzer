"""
Global configuration for STRATEX
"""

# Backtesting defaults
INITIAL_CAPITAL = 100_000
DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE = "2024-12-31"
COMMISSION = 0.001  # 0.1%

# API
API_HOST = "0.0.0.0"
API_PORT = 5000

# Database
DATABASE_URI = "sqlite:///data/stratex.db"
