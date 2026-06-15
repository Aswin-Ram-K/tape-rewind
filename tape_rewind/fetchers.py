"""
Tape Rewind — Data Fetchers.
"""
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

class DataFetcher:
    """Unified data fetcher for equities, crypto, and macro indicators."""
    
    def __init__(self):
        self._cache = {}

    def fetch_ticker(self, ticker: str, period: str = "5y", asset_class: str = "equity") -> pd.DataFrame:
        """Fetch OHLCV data for any asset."""
        cache_key = f"{ticker}_{period}_{asset_class}"
        if cache_key in self._cache:
            return self._cache[cache_key].copy()

        logger.info(f"Fetching {ticker} ({asset_class})...")
        df = yf.Ticker(ticker).history(period=period)
        
        if df.empty:
            logger.warning(f"  -> No data returned for {ticker}")
            return pd.DataFrame()
            
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index.name = "date"
        df.columns = [c.lower() for c in df.columns]
        df["date"] = df.index
        self._cache[cache_key] = df
        
        logger.info(f"  -> {len(df)} bars loaded.")
        return df.copy()

    def fetch_macro_spread(self) -> pd.DataFrame:
        """Fetch 10Y-2Y Treasury Yield Spread from FRED API."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            
            # Fetch 10Y
            params = {"series_id": "DGS10", "api_key": "***", "file_type": "json"}
            r1 = requests.get(url, params=params)
            if r1.status_code != 200:
                logger.warning("FRED API returned error for 10Y yield")
                return self._get_synthetic_spread()
            data10 = r1.json()["observations"]
            
            # Fetch 2Y
            params["series_id"] = "DGS2"
            r2 = requests.get(url, params=params)
            if r2.status_code != 200:
                logger.warning("FRED API returned error for 2Y yield")
                return self._get_synthetic_spread()
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
            
        except Exception as e:
            logger.warning(f"FRED API failed: {e}. Using synthetic data.")
            return self._get_synthetic_spread()

    def _get_synthetic_spread(self) -> pd.DataFrame:
        """Generate synthetic 10Y-2Y spread for testing."""
        dates = pd.date_range("2019-01-02", periods=500, freq="B")
        np.random.seed(42)
        spread = np.random.normal(0.02, 0.005, len(dates))
        return pd.DataFrame({"spread": spread}, index=dates)
