import pandas as pd
import yfinance as yf

def fetch_ohlcv(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, start=start_date, end=end_date)

        if df.empty:
            return pd.DataFrame()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        df = df[required_cols]

        df = df.dropna()

        return df

    except Exception:
        return pd.DataFrame()
