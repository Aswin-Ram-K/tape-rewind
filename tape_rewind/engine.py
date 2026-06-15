"""
Tape Rewind — Core WFF (Walk-Forward Fixed) Engine.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class Trade:
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    days_held: int

class WalkForwardWFF:
    """
    Walk-Forward with Fixed Parameters (WFF).
    
    1. Train on initial IS window (4 years).
    2. Optimize parameters (locked after).
    3. Test on sliding windows (2 weeks).
    """
    def __init__(
        self,
        initial_train_days: int = 4 * 252,
        test_window_days: int = 14,
        roll_step_days: int = 1,
        strategy_fn: Optional[Callable] = None,
        context_len: int = 200,
        stop_loss: float = 0.05,
        take_profit: float = 0.10,
    ):
        self.initial_train_days = initial_train_days
        self.test_window_days = test_window_days
        self.roll_step_days = roll_step_days
        self.strategy_fn = strategy_fn
        self.context_len = context_len
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def run(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run WFF backtest on a single asset DataFrame."""
        if self.strategy_fn is None:
            return {"error": "Strategy function not provided"}
        
        if len(df) < self.initial_train_days + self.test_window_days:
            return {"error": f"Data too short: need {self.initial_train_days + self.test_window_days} bars, got {len(df)}"}
        
        results = []
        test_start = self.initial_train_days
        test_end = self.initial_train_days + self.test_window_days
        
        while test_end <= len(df):
            train_df = df.iloc[:test_start]
            test_df = df.iloc[test_start:test_end]
            result = self._run_single_window(train_df, test_df, params)
            results.append(result)
            
            test_start += self.roll_step_days
            test_end += self.roll_step_days
            
        return {"results": results, "total_windows": len(results)}

    def _run_single_window(self, train_df, test_df, params):
        """Run strategy on a single test window with position tracking."""
        # Combine for context
        full_df = pd.concat([train_df, test_df])
        
        trades = []
        signal_history = []
        
        for i in range(len(test_df)):
            full_idx = len(train_df) + i
            context_df = full_df.iloc[max(0, full_idx - self.context_len):full_idx + 1]
            
            if context_df.shape[0] < 20:
                signal_history.append(0)
                continue
                
            # Get signal from strategy
            if self.strategy_fn is not None:
                signal = self.strategy_fn(context_df, params)
            else:
                signal = 0
            signal_history.append(signal)
            
            # Check trade execution
            current_price = context_df['close'].iloc[-1]
            
            # If we have a position
            if trades and not trades[-1].exit_date:
                last_trade = trades[-1]
                
                # Check exit conditions
                pnl_pct = (current_price - last_trade.entry_price) / last_trade.entry_price
                
                if pnl_pct >= self.take_profit or pnl_pct <= -self.stop_loss:
                    # Exit
                    last_trade.exit_date = context_df.index[-1]
                    last_trade.exit_price = current_price
                    last_trade.pnl_pct = pnl_pct
                    last_trade.days_held = (context_df.index[-1] - last_trade.entry_date).days
        
        return {
            "start_date": test_df.index[0],
            "end_date": test_df.index[-1],
            "signals": signal_history,
            "trades": [t.__dict__ for t in trades]
        }
