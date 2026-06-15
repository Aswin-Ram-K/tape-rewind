"""
Tape Rewind Dashboard — Clean start.
FastAPI server serving TradingView-style dashboard.
"""
import os
import sys
import json
from pathlib import Path

# Ensure package imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI(title="Tape Rewind Dashboard", version="1.0.0")

# CORS for cross-origin requests from the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Strategy Definitions ────────────────────────────────────────────────────

STRATEGIES = {
    "momentum": {
        "name": "Breakout Momentum",
        "description": "Buys when price breaks above N-day high with volume confirmation. Exits on breakdown.",
        "markets": ["SPY", "QQQ", "AAPL", "TSLA", "BTC-USD", "ETH-USD"],
        "entry": "Close > High[Lookback] AND Volume > AvgVol × Multiplier",
        "exit": "Close < Low[ExitLookback] OR StopLoss/TP triggered",
        "params": {
            "lookback": {"min": 5, "max": 60, "default": 20, "label": "Lookback Days"},
            "volume_mult": {"min": 1.0, "max": 3.0, "default": 1.2, "label": "Volume Multiplier"},
            "stop_loss": {"min": 0.03, "max": 0.15, "default": 0.05, "label": "Stop Loss %"},
            "take_profit": {"min": 0.05, "max": 0.30, "default": 0.10, "label": "Take Profit %"}
        }
    },
    "mean_reversion": {
        "name": "RSI Mean Reversion",
        "description": "Buys when RSI < 30 and price at lower Bollinger Band. Exits on RSI reversal or upper BB.",
        "markets": ["BTC-USD", "ETH-USD", "EUR-USD", "GLD", "UVXY"],
        "entry": "RSI(14) < 30 AND Close ≤ BB Lower(20, 2)",
        "exit": "RSI > 70 OR Close > SMA(20)",
        "params": {
            "rsi_period": {"min": 7, "max": 21, "default": 14, "label": "RSI Period"},
            "bb_std": {"min": 1.0, "max": 3.0, "default": 2.0, "label": "BB Std Dev"},
            "rsi_oversold": {"min": 20, "max": 35, "default": 30, "label": "Oversold Level"},
            "rsi_overbought": {"min": 65, "max": 80, "default": 70, "label": "Overbought Level"}
        }
    },
    "carry": {
        "name": "Trend Carry",
        "description": "Buys when 50-day SMA > 200-day SMA. Exits on death cross. Long-term trend follower.",
        "markets": ["SPY", "QQQ", "XLE", "GLD", "BTC-USD", "AAPL", "TSLA"],
        "entry": "SMA(50) > SMA(200) AND Close > SMA(50)",
        "exit": "SMA(50) < SMA(200)",
        "params": {
            "sma_fast": {"min": 20, "max": 100, "default": 50, "label": "Fast SMA Period"},
            "sma_slow": {"min": 100, "max": 300, "default": 200, "label": "Slow SMA Period"}
        }
    },
    "volatility": {
        "name": "Volatility Breakout",
        "description": "Buys on volatility expansion above 10-day high with volume surge. Fades on mean reversion.",
        "markets": ["UVXY", "GLD", "CL=F", "GC=F", "BTC-USD"],
        "entry": "Close > High[10] AND Volume > 2× AvgVol",
        "exit": "Close < SMA(10)",
        "params": {
            "lookback": {"min": 5, "max": 30, "default": 10, "label": "Breakout Lookback"},
            "volume_mult": {"min": 1.5, "max": 3.0, "default": 2.0, "label": "Volume Surge Multiplier"}
        }
    }
}

# ── Cached Data Store ──────────────────────────────────────────────────────

cached_data = {}

def get_or_fetch_data(ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch or return cached ticker data."""
    cache_key = f"{ticker}_{period}_{interval}"
    
    if cache_key in cached_data:
        return cached_data[cache_key].copy()
    
    print(f"Fetching {ticker}...")
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No data for {ticker}")
        
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index.name = "date"
        df.columns = [c.lower() for c in df.columns]
        df["date"] = df.index
        
        # Keep only last 500 bars for performance
        cached_data[cache_key] = df.tail(500)
        print(f"  ✓ {len(df.tail(500))} bars loaded.")
        return cached_data[cache_key].copy()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch {ticker}: {str(e)}")

# ── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/strategies")
def get_strategies():
    """Return all available strategies with their parameters."""
    return {"strategies": STRATEGIES}

@app.get("/api/asset/{ticker}/data")
def get_asset_data(ticker: str, limit: int = Query(200, le=500), period: str = "3mo"):
    """Get recent OHLCV data for an asset."""
    df = get_or_fetch_data(ticker, period=period)
    if len(df) < limit:
        limit = len(df)
    
    # Convert to list of dicts for JSON serialization
    data = []
    for _, row in df.tail(limit).iterrows():
        data.append({
            "date": str(row["date"]) if hasattr(row["date"], "strftime") else str(row["date"]),
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]) if pd.notna(row["volume"]) else 0
        })
    
    return {"ticker": ticker, "data": data}

@app.get("/api/strategies/{name}/analyze")
def analyze_strategy(name: str, ticker: str = "SPY"):
    """Run a simple backtest of the strategy on the ticker."""
    if name not in STRATEGIES:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    
    df = get_or_fetch_data(ticker)
    if len(df) < 50:
        raise HTTPException(status_code=400, detail="Not enough data for analysis")
    
    # Simple signal generation
    signals = []
    for i in range(50, len(df)):
        context = df.iloc[max(0, i-50):i+1]
        signal = generate_signal(name, context)
        signals.append(signal)
    
    # Calculate basic stats
    buy_signals = sum(1 for s in signals if s == 1)
    sell_signals = sum(1 for s in signals if s == -1)
    hold_signals = sum(1 for s in signals if s == 0)
    
    return {
        "strategy": name,
        "ticker": ticker,
        "total_bars": len(df),
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "hold_signals": hold_signals,
        "buy_pct": f"{buy_signals/len(signals)*100:.1f}%",
        "sell_pct": f"{sell_signals/len(signals)*100:.1f}%",
        "hold_pct": f"{hold_signals/len(signals)*100:.1f}%"
    }

def generate_signal(strategy_name: str, df: pd.DataFrame) -> int:
    """Generate trading signal (1=buy, -1=sell, 0=hold) based on strategy name."""
    if strategy_name == "momentum":
        return momentum_signal(df)
    elif strategy_name == "mean_reversion":
        return mean_reversion_signal(df)
    elif strategy_name == "carry":
        return carry_signal(df)
    elif strategy_name == "volatility":
        return volatility_signal(df)
    return 0

def momentum_signal(df: pd.DataFrame) -> int:
    """Simple momentum: buy if close > high of last 20 days."""
    lookback = 20
    if len(df) < lookback:
        return 0
    recent_high = df["high"].iloc[-lookback-1:-1].max()
    current_close = df["close"].iloc[-1]
    return 1 if current_close > recent_high else 0

def mean_reversion_signal(df: pd.DataFrame) -> int:
    """Simple mean reversion: buy if RSI < 30 and near lower BB."""
    if len(df) < 30:
        return 0
    # RSI approximation
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss if loss.iloc[-1] > 0 else 999
    rsi = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    sma = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()
    lower_bb = sma - 2 * std
    
    rsi_val = rsi.iloc[-1]
    lower_val = lower_bb.iloc[-1]
    current_close = df["close"].iloc[-1]
    
    if rsi_val < 30 and current_close <= lower_val * 1.02:
        return 1  # Oversold, buy
    return 0

def carry_signal(df: pd.DataFrame) -> int:
    """Simple carry: buy if fast SMA > slow SMA."""
    if len(df) < 200:
        return 0
    sma50 = df["close"].rolling(50).mean().iloc[-1]
    sma200 = df["close"].rolling(200).mean().iloc[-1]
    return 1 if sma50 > sma200 else 0

def volatility_signal(df: pd.DataFrame) -> int:
    """Simple vol breakout: buy if close > high of last 10 days."""
    if len(df) < 10:
        return 0
    recent_high = df["high"].iloc[-10:-1].max()
    current_close = df["close"].iloc[-1]
    return 1 if current_close > recent_high else 0

# ── Serve Dashboard HTML ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the main dashboard HTML."""
    html_path = Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    
    # Fallback if no HTML file
    return HTMLResponse(content="<h1>Tape Rewind Dashboard</h1><p>dashboard.html not found.</p>")

# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8002
    print(f"Starting Tape Rewind Dashboard on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
