"""
Tape Rewind — Dashboard Frontend.
TradingView-style dark theme dashboard for backtest visualization.
"""
from pathlib import Path

static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)

html_content = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tape Rewind — Backtest Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-primary: #131722;
            --bg-secondary: #1e222d;
            --bg-tertiary: #2a2e39;
            --border: #363a45;
            --text-primary: #d1d4dc;
            --text-secondary: #787b86;
            --accent: #2962ff;
            --green: #26a69a;
            --red: #ef5350;
            --yellow: #ffca28;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow: hidden;
        }
        
        .header {
            background: var(--bg-secondary);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }
        
        .logo {
            font-size: 20px;
            font-weight: 700;
            color: var(--accent);
        }
        
        .controls {
            display: flex;
            gap: 10px;
        }
        
        select, button {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border);
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
        }
        
        button.primary {
            background: var(--accent);
            border-color: var(--accent);
            font-weight: 600;
        }
        
        button.primary:hover {
            background: #1e54c7;
        }
        
        .main {
            display: grid;
            grid-template-columns: 1fr 300px;
            grid-template-rows: 2fr 1fr;
            height: calc(100vh - 56px);
            gap: 2px;
            background: var(--border);
        }
        
        .chart-panel {
            background: var(--bg-primary);
            position: relative;
            grid-column: 1;
            grid-row: 1;
        }
        
        #priceChart {
            width: 100%;
            height: 100%;
        }
        
        .metrics {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(30, 34, 45, 0.95);
            padding: 12px;
            border-radius: 6px;
            font-size: 13px;
            min-width: 200px;
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
        }
        
        .sidebar {
            background: var(--bg-secondary);
            grid-column: 2;
            grid-row: 1 / 3;
            display: flex;
            flex-direction: column;
        }
        
        .sidebar-header {
            padding: 12px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }
        
        .trade-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }
        
        .trade-item {
            background: var(--bg-primary);
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
            border-left: 3px solid;
        }
        
        .trade-item.win { border-left-color: var(--green); }
        .trade-item.loss { border-left-color: var(--red); }
        
        .trade-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        
        .bottom-panel {
            background: var(--bg-primary);
            grid-column: 1;
            grid-row: 2;
            position: relative;
        }
        
        #equityChart {
            width: 100%;
            height: 100%;
        }
        
        .loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--bg-secondary);
            padding: 20px 40px;
            border-radius: 8px;
            display: none;
        }
        
        .loading.active { display: block; }
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
    
    <div class="main">
        <div class="chart-panel">
            <canvas id="priceChart"></canvas>
            <div class="metrics" id="metrics">
                <div class="metric-row">
                    <span>Total Return:</span>
                    <span id="totalReturn">—</span>
                </div>
                <div class="metric-row">
                    <span>Win Rate:</span>
                    <span id="winRate">—</span>
                </div>
                <div class="metric-row">
                    <span>Max DD:</span>
                    <span id="maxDrawdown">—</span>
                </div>
                <div class="metric-row">
                    <span>Trades:</span>
                    <span id="totalTrades">—</span>
                </div>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="sidebar-header">📋 Trade Log</div>
            <div class="trade-list" id="tradeLog">
                <div style="padding: 20px; text-align: center; color: var(--text-secondary);">
                    Run a backtest to see trades
                </div>
            </div>
        </div>
        
        <div class="bottom-panel">
            <canvas id="equityChart"></canvas>
        </div>
    </div>
    
    <div class="loading" id="loading">⏳ Loading...</div>
    
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
            document.getElementById('totalReturn').textContent = (m.total_return * 100).toFixed(2) + '%';
            document.getElementById('winRate').textContent = (m.win_rate * 100).toFixed(1) + '%';
            document.getElementById('maxDrawdown').textContent = (m.max_drawdown * 100).toFixed(2) + '%';
            document.getElementById('totalTrades').textContent = m.total_trades;
        }
        
        function drawPriceChart(data) {
            const ctx = document.getElementById('priceChart').getContext('2d');
            
            if (priceChart) priceChart.destroy();
            
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.date),
                    datasets: [{
                        label: 'Price',
                        data: data.map(d => d.close),
                        borderColor: '#2962ff',
                        backgroundColor: 'rgba(41, 98, 255, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { 
                            display: true, 
                            ticks: { color: '#787b86' } 
                        },
                        y: { 
                            display: true, 
                            ticks: { color: '#787b86' } 
                        }
                    }
                }
            });
        }
        
        function drawEquityCurve(data) {
            const ctx = document.getElementById('equityChart').getContext('2d');
            
            if (equityChart) equityChart.destroy();
            
            equityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map((_, i) => i),
                    datasets: [{
                        label: 'Equity',
                        data: data,
                        borderColor: '#26a69a',
                        backgroundColor: 'rgba(38, 166, 154, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { 
                            display: true, 
                            ticks: { color: '#787b86' } 
                        }
                    }
                }
            });
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
                        <span>${win ? '+' : ''}${t.pnl_usd.toFixed(2)}</span>
                    </div>
                    <div style="font-size: 12px; color: #787b86;">
                        ${t.entry_date} → ${t.exit_date} (${t.days_held}d)
                    </div>
                `;
                container.appendChild(div);
            });
        }
        
        // Auto-run on load
        window.onload = () => {
            setTimeout(runBacktest, 500);
        };
    </script>
</body>
</html>"""

static_dir.write_text(html_content, encoding='utf-8')
