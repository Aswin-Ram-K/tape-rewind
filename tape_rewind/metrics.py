"""
Tape Rewind — Metrics Evaluation Suite.
"""
import numpy as np
import pandas as pd

def calculate_metrics(trades: list, equity_curve: list, starting_capital: float = 100000) -> dict:
    """
    Calculate 10 metrics from trades and equity curve.
    
    Parameters
    ----------
    trades : list[dict] - Each trade has 'pnl_pct', 'days_held'
    equity_curve : list[float] - Portfolio value over time
    starting_capital : float - Initial capital
    
    Returns
    -------
    dict - All 10 metrics
    """
    if not trades:
        return {
            "total_return": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "win_loss_ratio": 0.0,
            "avg_duration": 0.0,
            "calmar_ratio": 0.0,
            "recovery_bars": 0,
            "total_trades": 0,
            "status": "NO_TRADES"
        }

    # 1. Total Return
    final_cap = equity_curve[-1] if equity_curve else starting_capital
    total_return = (final_cap - starting_capital) / starting_capital

    # 2. Win Rate
    wins = [t for t in trades if t['pnl_pct'] > 0]
    win_rate = len(wins) / len(trades)

    # 3. Profit Factor
    gross_win = sum(t['pnl_pct'] for t in wins)
    gross_loss = abs(sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else 999.0

    # 4. Max Drawdown (from equity curve)
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_drawdown = float(np.min(drawdown))

    # 5. Sharpe Ratio (annualized)
    daily_returns = np.diff(equity) / equity[:-1]
    daily_returns = daily_returns[np.isfinite(daily_returns)]
    if len(daily_returns) > 1 and np.std(daily_returns) > 0:
        sharpe = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252)
    else:
        sharpe = 0.0

    # 6. Sortino Ratio
    downside = daily_returns[daily_returns < 0]
    downside_std = np.std(downside) if len(downside) > 0 else 1.0
    if len(daily_returns) > 1 and downside_std > 0:
        sortino = (np.mean(daily_returns) / downside_std) * np.sqrt(252)
    else:
        sortino = 0.0

    # 7. Win/Loss Ratio
    avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] < 0]) if any(t['pnl_pct'] < 0 for t in trades) else 0
    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # 8. Avg Duration
    durations = [t['days_held'] for t in trades]
    avg_duration = float(np.mean(durations))

    # 9. Calmar Ratio
    calmar = total_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    # 10. Recovery Time (bars to recover from peak after max drawdown)
    recovery_bars = 0
    if max_drawdown < -0.05:  # If significant drawdown occurred
        trough_idx = int(np.argmin(drawdown))
        peak_value = equity[trough_idx] * (1 + abs(max_drawdown))
        post_trough = equity[trough_idx:]
        recovered = post_trough >= peak_value
        if np.any(recovered):
            recovery_bars = int(np.argmax(recovered))

    return {
        "total_return": round(total_return, 4),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown": round(max_drawdown, 4),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "win_loss_ratio": round(win_loss_ratio, 4),
        "avg_duration": round(avg_duration, 1),
        "calmar_ratio": round(calmar, 4),
        "recovery_bars": int(recovery_bars),
        "total_trades": len(trades)
    }
