"""
Tape Rewind — Momentum Strategy.
"""
import numpy as np
import pandas as pd
from ..registry import STRATEGIES

@STRATEGIES.register("momentum")
class MomentumStrategy:
    """Breakout momentum with entry/exit signals."""
    
    def __init__(self, lookback: int = 20, volume_mult: float = 1.2):
        self.lookback = lookback
        self.volume_mult = volume_mult

    def __call__(self, window: pd.DataFrame, params: dict) -> int:
        """Return: 1=Buy, -1=Sell, 0=Hold."""
        lookback = params.get("lookback", self.lookback)
        volume_mult = params.get("volume_mult", self.volume_mult)
        
        if len(window) < lookback + 5:
            return 0

        current = window['close'].iloc[-1]
        high = window['close'].iloc[-lookback-1:-1].max()
        low = window['close'].iloc[-lookback-1:-1].min()
        
        if current > high:
            return 1  # Buy
        if current < low:
            return -1  # Sell
        
        return 0  # Hold
