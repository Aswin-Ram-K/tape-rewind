"""
Tape Rewind — Momentum Strategy.
"""
import numpy as np
import pandas as pd
from ..registry import register_strategy

@register_strategy("momentum")
def momentum_strategy(window: 'pd.DataFrame', params: dict):
    """
    Simple breakout momentum strategy.
    Buys when price breaks above N-day high.
    """
    lookback = params.get("lookback", 20)
    if len(window) < lookback:
        return 0

    current = window["close"].iloc[-1]
    high = window["close"].iloc[-lookback-1:-1].max()
    
    if current > high:
        return 1  # Buy signal
    return 0
