#!/usr/bin/env python3
"""Tape Rewind Dashboard — Server Launcher"""
import sys
import os
import signal
import subprocess
import time
from pathlib import Path

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    os.chdir(Path(__file__).parent)
    
    print(f"Starting Tape Rewind Dashboard on port {port}...")
    print(f"Access at: http://192.168.2.126:{port}")
    
    # Start the server
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", 
         "tape_rewind.dashboard.server:app",
         "--host", "0.0.0.0",
         "--port", str(port),
         "--log-level", "info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for it to start
    time.sleep(3)
    
    # Check if still running
    if proc.poll() is None:
        print(f"Dashboard started successfully (PID: {proc.pid})")
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            print("Dashboard stopped.")
    else:
        stdout, stderr = proc.communicate()
        print(f"Server failed to start:")
        print(f"STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")

if __name__ == "__main__":
    main()
