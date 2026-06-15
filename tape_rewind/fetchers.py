"""
Tape Rewind — Data Fetchers.
"""
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataFetcher:
    """Unified data fetcher for equities, crypto, and macro indicators."""
    
    def __init__(self):
        self.yf_cache = {}

    def fetch_equity(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        """Fetch equity OHLCV data."""
        if ticker not in self.yf_cache:
            logger.info(f"Fetching {ticker}...")
            df = yf.Ticker(ticker).history(period=period)
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index.name = "date"
            df.columns = [c.lower() for c in df.columns]
            df["date"] = df.index
            self.yf_cache[ticker] = df
            logger.info(f"  -> {len(df)} bars loaded.")
        else:
            df = self.yf_cache[ticker].copy()
        return df

    def fetch_crypto(self, symbol: str = "BTC-USD", period: str = "5y") -> pd.DataFrame:
        """Fetch crypto OHLCV data."""
        if symbol not in self.yf_cache:
            logger.info(f"Fetching {symbol}...")
            df = yf.Ticker(symbol).history(period=period)
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index.name = "date"
            df.columns = [c.lower() for c in df.columns]
            df["date"] = df.index
            self.yf_cache[symbol] = df
            logger.info(f"  -> {len(df)} bars loaded.")
        else:
            df = self.yf_cache[symbol].copy()
        return df

    def fetch_macro_spread(self) -> pd.DataFrame:
        """Fetch 10Y-2Y Treasury Yield Spread from FRED API."""
        # Public endpoint
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "DGS10",
            "api_key": "DEMO_KEY",  # Public demo key for FRED
            "file_type": "json"
        }
        
        # Fetch 10Y
        r1 = requests.get(url, params=params)
        if r1.status_code != 200: return pd.DataFrame()
        data10 = r1.json()["observations"]
        
        # Fetch 2Y
        params["series_id"] = "DGS2"
        r2 = requests.get(url, params=params)
        if r2.status_code != 200: return pd.DataFrame()
        data2 = r2.json()["observations"]
        
        # Process
        df10 = pd.DataFrame(data10)[["date", "value"]]
        df2 = pd.DataFrame(data2)[["date", "value"]]
        
        df10.columns = ["date", "v10"]
        df2.columns = ["date", "v2"]
        
        df = df10.merge(df2, on="date", how="inner")
        df["spread"] = df["v10"].astype(float) - df["v2"].astype(float)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        
        logger.info(f"  -> {len(df)} macro spread points loaded.")
        return df[["spread"]]
