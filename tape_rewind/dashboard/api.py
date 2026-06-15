"""
Tape Rewind — Dashboard Backend (FastAPI).
TradingView-style dashboard for backtest visualization.
"""
import sys
import os
import logging
from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np

from tape_rewind.fetchers import DataFetcher
from tape_rewind.engine import WalkForwardWFF
from tape_rewind.metrics import calculate_metrics
from tape_rewind.registry import STRATEGIES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Tape Rewind Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory and serve
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)

# Serve static files
try:
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except:
    pass

# Global state
_state = {
    "current_asset": "SPY",
    "current_strategy": "momentum",
    "period": "5y",
}

fetcher = DataFetcher()
engine = None


def _get_or_create_engine():
    global engine
    from tape_rewind.strategies.momentum import MomentumStrategy
    if engine is None:
        engine = WalkForwardWFF(
            initial_train_days=4 * 252,
            test_window_days=14,
            strategy_fn=MomentumStrategy().__call__,
            context_len=200,
            stop_loss=0.05,
            take_profit=0.10,
        )
    return engine


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dashboard HTML."""
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tape Rewind — Backtest Dashboard</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #131722;
            color: #d1d4dc;
            overflow: hidden;
        }
        
        .header {
            background: #1e222d;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #2a2e39;
        }
        
        .logo { font-size: 18px; font-weight: 700; color: #2962ff; }
        
        .controls { display: flex; gap: 10px; }
        
        select, button {
            background: #2a2e39;
            color: #d1d4dc;
            border: 1px solid #363a45;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 13px;
        }
        
        button.primary {
            background: #2962ff;
            border-color: #2962ff;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }
        
        button.primary:hover { background: #1e54c7; }
        
        .container {
            display: grid;
            grid-template-columns: 1fr 320px;
            grid-template-rows: 1fr 200px;
            height: calc(100vh - 53px);
            gap: 2px;
            background: #2a2e39;
        }
        
        .chart-area {
            background: #131722;
            position: relative;
            grid-column: 1;
            grid-row: 1;
        }
        
        #priceChart { width: 100%; height: 100%; }
        
        .metrics-panel {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(30, 34, 45, 0.95);
            padding: 12px;
            border-radius: 6px;
            font-size: 12px;
            min-width: 180px;
        }
        
        .metric { display: flex; justify-content: space-between; margin-bottom: 6px; }
        .metric-label { color: #787b86; }
        .metric-value { font-weight: 600; }
        .positive { color: #26a69a; }
        .negative { color: #ef5350; }
        
        .sidebar {
            background: #1e222d;
            grid-column: 2;
            grid-row: 1 / 3;
            display: flex;
            flex-direction: column;
        }
        
        .sidebar-header {
            padding: 12px;
            border-bottom: 1px solid #2a2e39;
            font-weight: 600;
        }
        
        .trade-log {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }
        
        .trade-item {
            background: #131722;
            padding: 10px;
            margin-bottom: 6px;
            border-radius: 4px;
            border-left: 3px solid;
        }
        
        .trade-item.win { border-left-color: #26a69a; }
        .trade-item.loss { border-left-color: #ef5350; }
        
        .trade-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        
        .trade-dates { font-size: 11px; color: #787b86; }
        
        .bottom-panel {
            background: #1e222d;
            grid-column: 1;
            grid-row: 2;
        }
        
        #equityChart { width: 100%; height: calc(100% - 30px); }
        
        .loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(30, 34, 45, 0.95);
            padding: 20px 30px;
            border-radius: 8px;
            display: none;
        }
        
        .loading.active { display: block; }
        
        .trade-log::-webkit-scrollbar { width: 6px; }
        .trade-log::-webkit-scrollbar-track { background: #131722; }
        .trade-log::-webkit-scrollbar-thumb { background: #363a45; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">📊 TAPE REWIND</div>
        <div class="controls">
            <select id="asset">
                <option value="SPY">SPY</option>
                <option value="QQQ">QQQ</option>
                <option value="AAPL">AAPL</option>
                <option value="BTC-USD">BTC-USD</option>
            </select>
            <select id="strategy">
                <option value="momentum">Momentum</option>
            </select>
            <select id="period">
                <option value="2y">2Y</option>
                <option value="5y" selected>5Y</option>
                <option value="10y">10Y</option>
            </select>
            <button class="primary" onclick="runBacktest()">RUN</button>
        </div>
    </div>
    
    <div class="container">
        <div class="chart-area">
            <div id="priceChart"></div>
            <div class="metrics-panel" id="metrics">
                <div class="metric">
                    <span class="metric-label">Total Return:</span>
                    <span class="metric-value" id="totalReturn">—</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Win Rate:</span>
                    <span class="metric-value" id="winRate">—</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Max Drawdown:</span>
                    <span class="metric-value" id="maxDrawdown">—</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Trades:</span>
                    <span class="metric-value" id="totalTrades">—</span>
                </div>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="sidebar-header">📋 Trade Logbook</div>
            <div class="trade-log" id="tradeLog">
                <div style="padding: 20px; text-align: center; color: #787b86;">
                    Run a backtest to see trades
                </div>
            </div>
        </div>
        
        <div class="bottom-panel">
            <div style="padding: 8px 12px; font-weight: 600;">Equity Curve</div>
            <div id="equityChart"></div>
        </div>
    </div>
    
    <div class="loading" id="loading">
        ⏳ Running backtest...
    </div>
    
    <script>
        let priceChart, equityChart;
        
        async function runBacktest() {
            const loading = document.getElementById('loading');
            loading.classList.add('active');
            
            try {
                const res = await fetch('/api/backtest', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        asset: document.getElementById('asset').value,
                        strategy: document.getElementById('strategy').value,
                        period: document.getElementById('period').value
                    })
                });
                
                const data = await res.json();
                
                if (data.error) {
                    alert(data.error);
                    return;
                }
                
                updateMetrics(data.metrics);
                drawPriceChart(data.price_data);
                drawEquityCurve(data.equity_curve);
                updateTradeLog(data.trades);
                
            } catch (e) {
                alert('Error: ' + e.message);
            } finally {
                loading.classList.remove('active');
            }
        }
        
        function updateMetrics(m) {
            const tr = document.getElementById('totalReturn');
            tr.textContent = (m.total_return * 100).toFixed(2) + '%';
            tr.className = 'metric-value ' + (m.total_return > 0 ? 'positive' : 'negative');
            
            document.getElementById('winRate').textContent = (m.win_rate * 100).toFixed(1) + '%';
            document.getElementById('maxDrawdown').textContent = (m.max_drawdown * 100).toFixed(2) + '%';
            document.getElementById('totalTrades').textContent = m.total_trades;
        }
        
        function drawPriceChart(data) {
            const container = document.getElementById('priceChart');
            
            if (priceChart) priceChart.dispose();
            
            priceChart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: container.clientHeight,
                layout: {
                    background: { color: '#131722' },
                    textColor: '#d1d4dc',
                },
                grid: {
                    vertLines: { color: '#2a2e39' },
                    horzLines: { color: '#2a2e39' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                },
                timeScale: {
                    borderColor: '#2a2e39',
                },
            });
            
            const candleSeries = priceChart.addCandlestickSeries({
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderDownColor: '#ef5350',
                borderUpColor: '#26a69a',
                wickDownColor: '#ef5350',
                wickUpColor: '#26a69a',
            });
            
            const candles = data.map(d => ({
                time: d.date,
                open: d.open,
                high: d.high,
                low: d.low,
                close: d.close
            }));
            
            candleSeries.setData(candles);
            priceChart.timeScale().fitContent();
        }
        
        function drawEquityCurve(data) {
            const container = document.getElementById('equityChart');
            
            if (equityChart) equityChart.dispose();
            
            equityChart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: container.clientHeight,
                layout: {
                    background: { color: '#131722' },
                    textColor: '#d1d4dc',
                },
                grid: {
                    vertLines: { color: '#2a2e39' },
                    horzLines: { color: '#2a2e39' },
                },
            });
            
            const lineSeries = equityChart.addLineSeries({
                color: '#26a69a',
                lineWidth: 2,
            });
            
            const equityData = data.map((val, i) => ({
                time: i,
                value: val
            }));
            
            lineSeries.setData(equityData);
        }
        
        function updateTradeLog(trades) {
            const container = document.getElementById('tradeLog');
            container.innerHTML = '';
            
            trades.forEach(t => {
                const win = t.pnl_pct > 0;
                const div = document.createElement('div');
                div.className = 'trade-item ' + (win ? 'win' : 'loss');
                div.innerHTML = `
                    <div class="trade-header">
                        <span>${t.entry_price} → ${t.exit_price}</span>
                        <span style="color: ${win ? '#26a69a' : '#ef5350'}; font-weight: 600;">
                            ${win ? '+' : ''}${t.pnl_usd.toFixed(2)}
                        </span>
                    </div>
                    <div class="trade-dates">
                        ${t.entry_date} → ${t.exit_date} (${t.days_held}d)
                    </div>
                `;
                container.appendChild(div);
            });
        }
        
        // Load strategies on init
        async function loadStrategies() {
            try {
                const res = await fetch('/api/strategies');
                const data = await res.json();
                const select = document.getElementById('strategy');
                
                if (data.strategies) {
                    data.strategies.forEach(strat => {
                        const option = document.createElement('option');
                        option.value = strat;
                        option.textContent = strat.charAt(0).toUpperCase() + strat.slice(1);
                        select.appendChild(option);
                    });
                }
            } catch (e) {
                console.error('Failed to load strategies:', e);
            }
        }
        
        window.addEventListener('resize', () => {
            if (priceChart) {
                const container = document.getElementById('priceChart');
                priceChart.resize(container.clientWidth, container.clientHeight);
            }
            if (equityChart) {
                const container = document.getElementById('equityChart');
                equityChart.resize(container.clientWidth, container.clientHeight);
            }
        });
        
        // Auto-run on load
        window.onload = () => {
            loadStrategies();
            setTimeout(runBacktest, 500);
        };
    </script>
</body>
</html>""")


@app.get("/api/strategies")
def get_strategies():
    """List all available strategies."""
    return {"strategies": STRATEGIES.list()}


@app.get("/api/assets")
def get_assets():
    """List common US market assets."""
    return {
        "equities": ["SPY", "QQQ", "IWM", "AAPL", "TSLA", "NVDA", "META", "AMZN", "MSFT", "GOOGL"],
        "crypto": ["BTC-USD", "ETH-USD", "SOL-USD"],
        "commodities": ["GC=F", "CL=F", "GLD", "SLV"],
        "forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
        "etfs": ["XLE", "XLF", "XLK", "XLI", "XLV", "XLU"],
    }


class BacktestRequest(BaseModel):
    asset: str = "SPY"
    strategy: str = "momentum"
    period: str = "5y"


@app.post("/api/backtest")
def run_backtest(request: BacktestRequest):
    """Run backtest and return data for dashboard."""
    try:
        # Fetch data
        df = fetcher.fetch_ticker(request.asset, period=request.period)
        
        if df.empty:
            raise HTTPException(status_code=400, detail=f"No data for {request.asset}")
        
        # Get strategy function
        strat = STRATEGIES.get(request.strategy)
        if not strat or "fn" not in strat:
            raise HTTPException(status_code=404, detail=f"Strategy '{request.strategy}' not found")
        
        # Update engine
        engine = _get_or_create_engine()
        engine.strategy_fn = strat["fn"]
        
        # Run backtest
        result = engine.run(df, {})
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Process results for dashboard
        trades = []
        equity_curve = []
        price_data = []
        
        # Build price data (last 100 bars)
        for i in range(min(100, len(df))):
            row = df.iloc[i]
            price_data.append({
                "date": str(df.index[i].date()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            })
        
        # Extract trades from windows
        capital = 100000.0
        position = None
        
        for i, window in enumerate(result["results"]):
            start_i = i * 14  # Approximate start in df
            end_i = (i + 1) * 14
            
            if start_i >= len(df):
                break
                
            window_df = df.iloc[start_i:min(end_i, len(df))]
            signals = window.get("signals", [])
            
            for j in range(len(window_df)):
                if start_i + j >= len(df):
                    break
                    
                signal = signals[j] if j < len(signals) else 0
                price = float(window_df.iloc[j]["close"])
                dt = str(df.index[start_i + j].date())
                
                # Buy signal
                if signal > 0 and not position:
                    position = {
                        "entry_date": dt,
                        "entry_price": price,
                    }
                
                # Sell signal
                elif signal < 0 and position:
                    pnl_pct = (price - position["entry_price"]) / position["entry_price"]
                    pnl_usd = pnl_pct * (capital * 0.95)
                    
                    days_held = 0
                    try:
                        entry_dt = pd.to_datetime(position["entry_date"])
                        exit_dt = pd.to_datetime(dt)
                        days_held = max(1, (exit_dt - entry_dt).days)
                    except:
                        days_held = 1
                    
                    trades.append({
                        "entry_date": position["entry_date"],
                        "exit_date": dt,
                        "entry_price": round(position["entry_price"], 2),
                        "exit_price": round(price, 2),
                        "pnl_pct": round(pnl_pct, 4),
                        "pnl_usd": round(pnl_usd, 2),
                        "days_held": days_held,
                    })
                    
                    capital += pnl_usd
                    position = None
                
                equity_curve.append(round(capital, 2))
        
        # Calculate metrics
        if trades:
            metrics = calculate_metrics(trades, equity_curve)
        else:
            metrics = {"total_return": 0.0, "win_rate": 0.0, "total_trades": 0}
        
        return {
            "asset": request.asset,
            "strategy": request.strategy,
            "period": request.period,
            "metrics": metrics,
            "trades": trades[-20:],
            "equity_curve": equity_curve[-50:],
            "price_data": price_data,
            "total_backtest_bars": len(df),
            "total_windows": result["total_windows"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health():
    return {"status": "ok", "strategies": STRATEGIES.list()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
