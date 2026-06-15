"""
Tape Rewind — 10-Metric Evaluation Suite.
"""
import numpy as np
import pandas as pd

def calculate_metrics(trades, equity_curve, regime_data=None):
    """
    Calculate the 10 metrics for a backtest.
    """
    if not trades:
        return {"status": "NO_TRADES"}

    # 1. Total Return
    final_cap = equity_curve.iloc[-1]
    start_cap = equity_curve.iloc[0]
    total_return = (final_cap - start_cap) / start_cap

    # 2. Win Rate
    wins = [t for t in trades if t["pnl"] > 0]
    win_rate = len(wins) / len(trades)

    # 3. Profit Factor
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else 999

    # 4. Max Drawdown
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_drawdown = np.min(drawdown)

    # 5. Sharpe Ratio
    daily_returns = np.diff(equity_curve) / equity_curve[:-1]
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
    avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
    avg_loss = np.mean([t["pnl"] for t in trades if t["pnl"] < 0]) if any(t["pnl"] < 0 for t in trades) else 1.0
    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # 8. Avg Trade Duration
    durations = [t["days"] for t in trades]
    avg_duration = np.mean(durations)

    # 9. Calmar Ratio
    calmar = total_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    # 10. Recovery Time (simplified: bars to recover from 50% of max DD)
    recovery_bars = 0
    if max_drawdown < -0.1: # If significant drawdown
        trough_idx = np.argmin(drawdown)
        trough_val = equity[trough_idx] * (1 + abs(max_drawdown) * 0.5)
        post_trough = equity[trough_idx:]
        recovered = post_trough >= trough_val
        if np.any(recovered):
            recovery_bars = np.argmax(recovered)

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
