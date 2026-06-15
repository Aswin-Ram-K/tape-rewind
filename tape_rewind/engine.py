"""
Tape Rewind — Core WFF (Walk-Forward Fixed) Engine.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Callable

class WalkForwardWFF:
    """
    Walk-Forward with Fixed Parameters (WFF).
    
    1. Train on initial IS window (4 years).
    2. Optimize parameters (locked after).
    3. Test on sliding windows (2 weeks).
    """
    def __init__(
        self,
        initial_train_days: int = 4 * 365,
        test_window_days: int = 14,
        roll_step_days: int = 1,
        strategy_fn=None,
    ):
        self.initial_train_days = initial_train_days
        self.test_window_days = test_window_days
        self.roll_step_days = roll_step_days
        self.strategy_fn = strategy_fn

    def run(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run WFF backtest on a single asset DataFrame."""
        if self.strategy_fn is None:
            return {"error": "Strategy function not provided"}

        # 1. IS Training (Initial Training)
        train_end = self.initial_train_days
        train_df = df.iloc[:train_end]
        
        # 2. Lock parameters (in a real scenario, we optimize here, 
        # but for now we pass them in or lock them).
        # For this phase, params are provided externally.
        
        results = []
        
        # 3. Sliding OOS Test
        test_start = train_end
        test_end = train_end + self.test_window_days
        
        while test_end <= len(df):
            test_df = df.iloc[test_start:test_end]
            result = self._run_single_window(train_df, test_df, params)
            results.append(result)
            
            # Slide
            test_start += self.roll_step_days
            test_end += self.roll_step_days
            
        return {"results": results, "total_windows": len(results)}

    def _run_single_window(self, train_df, test_df, params):
        """Run strategy on a single test window."""
        # Combine train and test for indicator calculation context
        full_df = pd.concat([train_df, test_df])
        
        # Calculate indicators based on full history up to test window end
        # We use the strategy function which takes the window as context
        signals = []
        if self.strategy_fn is None:
            raise ValueError("Strategy function not provided")

        for i in range(len(test_df)):
            # Context window: last N days from the full history
            # This prevents look-ahead bias while providing necessary context
            context_len = max(50, len(test_df))
            full_idx = len(train_df) + i
            context_df = full_df.iloc[max(0, full_idx - context_len):full_idx + 1]
            
            if context_df.shape[0] < 20:
                signals.append(0)
                continue
                
            signal = self.strategy_fn(context_df, params)
            signals.append(signal)
            
        return {
            "start_date": test_df.index[0],
            "end_date": test_df.index[-1],
            "signals": signals,
            "returns": test_df['close'].pct_change().dropna().tolist()
        }
