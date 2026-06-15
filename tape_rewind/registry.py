"""
Tape Rewind — Strategy Registry.
"""
from typing import Dict, Any, Callable, List, Optional

class StrategyRegistry:
    """Plugin registry for strategy management."""
    
    def __init__(self):
        self._strategies: Dict[str, dict] = {}

    def register(self, name: str, metadata: Optional[dict] = None):
        """
        Register a strategy. Can be used as:
            STRATEGIES.register("name", fn, metadata)  # Direct
            @STRATEGIES.register("name")               # Decorator
        """
        def decorator(fn: Callable):
            self._strategies[name] = {
                "fn": fn,
                "metadata": metadata or {
                    "name": name,
                    "description": f"{name} strategy",
                    "parameters": {}
                }
            }
            return fn
        return decorator

    def get(self, name: str) -> dict:
        """Get strategy and metadata by name."""
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found. Available: {list(self._strategies.keys())}")
        return self._strategies[name]

    def list(self) -> List[str]:
        """List all registered strategy names."""
        return list(self._strategies.keys())

# Global instance
STRATEGIES: StrategyRegistry = StrategyRegistry()
