"""
Tape Rewind — Strategy Registry.
"""
from typing import Dict, Any

STRATEGIES = {}

def register_strategy(name):
    def decorator(fn):
        STRATEGIES[name] = fn
        return fn
    return decorator
