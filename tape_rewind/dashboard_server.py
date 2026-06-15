"""
Tape Rewind — Dashboard API Server.
Serves the dashboard frontend and provides backtesting/trade data.
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

from tape_rewind.fetchers import DataFetcher
from tape_rewind.engine import WalkForwardWFF
from tape_rewind.metrics import calculate_metrics
from tape_rewind.strategies.impl import STRATEGY_MAP

app = FastAPI(title="Tape Rewind Dashboard")

@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open("frontend/index.html", "r") as f:
        return f.read()

@app.get("/api/strategies")
def list_strategies():
    """Return all available strategies."""
    return {k: {"name": v().name, "description": v().description, "markets": v().markets} for k, v in STRATEGY_MAP.items()}

@app.get("/api/tickers")
def list_tickers():
    """Return supported tickers by strategy."""
    tickers = set()
    for v in STRATEGY_MAP.values():
        tickers.update(v().markets)
    return {"tickers": sorted(list(tickers))}

@app.get("/api/data/{ticker}")
def get_ticker_data(ticker: str, period: str = "5y"):
    """Fetch OHLCV data for a ticker."""
    try:
        fetcher = DataFetcher()
        df = fetcher.fetch_ticker(ticker, period=period)
        if df.empty:
            raise HTTPException(404, f"No data for {ticker}")
        
        return {
            "dates": df["date"].astype(str).tolist(),
            "open": df["open"].tolist(),
            "high": df["high"].tolist(),
            "low": df["low"].tolist(),
            "close": df["close"].tolist(),
            "volume": df["volume"].tolist()
        }
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/backtest/{ticker}/{strategy}")
def run_backtest(ticker: str, strategy: str, params: str = "{}"):
    """Run a backtest for a ticker/strategy combo."""
    import json
    try:
        user_params = json.loads(params)
    except:
        user_params = {}
    
    if strategy not in STRATEGY_MAP:
        raise HTTPException(404, f"Strategy {strategy} not found")
    
    try:
        fetcher = DataFetcher()
        df = fetcher.fetch_ticker(ticker)
        if df.empty:
            raise HTTPException(404, f"No data for {ticker}")
        
        strategy_obj = STRATEGY_MAP[strategy]()
        engine = WalkForwardWFF(
            initial_train_days=252,  # 1 year for faster dashboard tests
            test_window_days=20,
            strategy_fn=strategy_obj.execute,
            context_len=200,
            stop_loss=0.05,
            take_profit=0.10,
        )
        
        results = engine.run(df, user_params)
        
        if "error" in results:
            raise HTTPException(400, results["error"])
        
        # Calculate metrics from trades
        trades = []
        equity = [100000.0]
        capital = 100000.0
        position = None
        
        for i in range(len(df)):
            price = df["close"].iloc[i]
            signal = results["signals"][i] if i < len(results["signals"]) else 0
            
            if position and signal != 0:
                pnl = (price - position["entry"]) / position["entry"]
                if pnl > 0 or abs(pnl) > 0.05:
                    capital += position["shares"] * price * pnl
                    trades.append({
                        "entry": position["entry"],
                        "exit": price,
                        "pnl_pct": round(pnl * 100, 2),
                        "days_held": i - position["day"],
                        "entry_date": str(df.index[position["day"]]).split(" ")[0],
                        "exit_date": str(df.index[i]).split(" ")[0],
                        "ticker": ticker,
                        "strategy": strategy_obj.name
                    })
                    position = None
            
            if signal == 1 and not position:
                position = {
                    "entry": price,
                    "shares": 100,
                    "day": i
                }
            
            equity.append(capital if position is None else capital + position["shares"] * price * 0.001)
        
        metrics = calculate_metrics(trades, equity, 100000.0)
        
        return {
            "strategy": strategy_obj.name,
            "ticker": ticker,
            "trades": trades,
            "equity_curve": equity[-len(df):],
            "metrics": metrics,
            "windows": results["total_windows"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))
