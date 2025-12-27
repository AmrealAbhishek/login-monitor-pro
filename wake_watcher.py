#!/usr/bin/env python3
"""
Wake Watcher for macOS - Monitors for wake from sleep events.
Uses IOKit power management notifications.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MONITOR_SCRIPT = SCRIPT_DIR / "login_monitor.py"
PYTHON_PATH = "/Library/Developer/CommandLineTools/usr/bin/python3"


def run_monitor():
    """Run the login monitor script"""
    subprocess.run([PYTHON_PATH, str(MONITOR_SCRIPT), "Wake"])


def watch_for_wake():
    """Watch for wake events using pmset log"""
    print("Wake watcher started...")

    # Track the last wake time to prevent duplicate triggers
    last_trigger = 0
    cooldown = 60  # seconds

    # Use pmset -g log to monitor power events
    process = subprocess.Popen(
        ["pmset", "-g", "log"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Read existing log to get to the end
    while True:
        line = process.stdout.readline()
        if not line:
            break

    # Now monitor for new wake events
    # We need to periodically check the log
    last_check = ""

    while True:
        try:
            # Get the latest power log entry
            result = subprocess.run(
                ["pmset", "-g", "log"],
                capture_output=True,
                text=True,
                timeout=10
            )

            log = result.stdout

            # Look for wake events in the log
            if log != last_check:
                lines = log.split('\n')
                for line in lines[-20:]:  # Check last 20 lines
                    if "Wake" in line and "DarkWake" not in line:
                        current_time = time.time()
                        if current_time - last_trigger > cooldown:
                            print(f"Wake detected: {line}")
                            run_monitor()
                            last_trigger = current_time
                            break

                last_check = log

            time.sleep(5)  # Check every 5 seconds

        except KeyboardInterrupt:
            print("Wake watcher stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    watch_for_wake()
