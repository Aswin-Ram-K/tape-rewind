"""
Tape Rewind — Phase 1 Runner.
Tests the WFF engine, momentum strategy, and macro data.
"""
import pandas as pd
import numpy as np
from tape_rewind.fetchers import DataFetcher
from tape_rewind.engine import WalkForwardWFF
from tape_rewind.metrics import calculate_metrics
from tape_rewind.strategies.momentum import momentum_strategy

def run_phase1():
    print("=" * 60)
    print("  TAPE REWIND — Phase 1: Core Engine & Data")
    print("=" * 60)

    # 1. Fetch Data
    print("\n1. Fetching Data...")
    fetcher = DataFetcher()
    spy_df = fetcher.fetch_equity("SPY", period="5y")
    btc_df = fetcher.fetch_crypto("BTC-USD", period="5y")
    
    print("\n2. Fetching Macro Data (10Y-2Y Spread)...")
    macro_df = fetcher.fetch_macro_spread()
    if macro_df.empty:
        print("  Warning: FRED macro data not loaded (demo key limit).")
        macro_df = pd.DataFrame({
            "spread": np.random.normal(0.02, 0.005, 500)
        }, index=pd.date_range("2019-01-01", periods=500, freq="B"))
        print("  -> Using synthetic macro data for testing.")

    # 3. Initialize WFF Engine
    print("\n3. Initializing WFF Engine...")
    # 4 years train, 2 weeks test
    engine = WalkForwardWFF(
        initial_train_days=500, # 2 years of trading days for Phase 1 test
        test_window_days=14,
        strategy_fn=momentum_strategy,
    )

    # 4. Run Backtest
    print("\n4. Running WFF Backtest (SPY)...")
    results = engine.run(spy_df, {"lookback": 20})
    
    # 5. Evaluate
    print("\n5. Evaluating Results...")
    if "error" in results:
        print(f"  Error: {results['error']}")
        return

    print(f"  Total Windows Tested: {results['total_windows']}")
    
    # Print first few windows
    for i, w in enumerate(results["results"][:3]):
        print(f"  Window {i+1}: {w['start_date']} to {w['end_date']}")
        print(f"    Signals: {sum(w['signals'])} buy(s)")

    # 6. Summary Stats
    all_signals = []
    for w in results["results"]:
        all_signals.extend(w["signals"])
    
    total_buys = sum(all_signals)
    print(f"\n  Summary:")
    print(f"  Total Buy Signals: {total_buys} / {len(all_signals)} bars")
    print(f"  Macro Spread (Latest): {macro_df['spread'].iloc[-1]:.2f}%")
    
    print("\nPhase 1 Complete.")

if __name__ == "__main__":
    run_phase1()
