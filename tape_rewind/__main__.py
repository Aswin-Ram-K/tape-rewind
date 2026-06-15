"""
Tape Rewind — Module entry point.
"""
import sys
import os

# Ensure we can import from the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tape_rewind.runner import run_phase1

if __name__ == "__main__":
    run_phase1()
