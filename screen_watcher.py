#!/usr/bin/env python3
"""
Screen Watcher for macOS - Monitors for screen unlock and wake events.
Uses Quartz to detect screen lock/unlock state changes.
Triggers on: First boot, Login, Unlock, Wake
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from datetime import datetime

try:
    import Quartz
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False
    print("Warning: Quartz not available, using fallback detection")


def is_frozen():
    """Check if running as PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """Get base directory for data files"""
    if is_frozen():
        return Path.home() / ".login-monitor"
    return Path(__file__).parent


def get_monitor_path():
    """Get path to pro_monitor executable/script"""
    if is_frozen():
        # When frozen, pro_monitor is in the same MacOS directory
        bundle_dir = Path(sys.executable).parent
        return str(bundle_dir / "pro_monitor")
    return str(Path(__file__).parent / "pro_monitor.py")


def get_python_path():
    """Get Python path (None if frozen)"""
    if is_frozen():
        return None
    return "/Library/Developer/CommandLineTools/usr/bin/python3"


SCRIPT_DIR = get_base_dir()
MONITOR_SCRIPT = get_monitor_path()
PYTHON_PATH = get_python_path()

# Track last trigger to prevent duplicates
last_trigger_time = 0
COOLDOWN = 10  # seconds between triggers
STARTUP_DELAY = 15  # seconds to wait on boot for network/camera


def log(message):
    """Print timestamped log message"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def wait_for_network(timeout=30):
    """Wait for network connectivity"""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            time.sleep(2)
    return False


def run_monitor(event_type):
    """Run the login monitor script"""
    global last_trigger_time

    current_time = time.time()
    if current_time - last_trigger_time < COOLDOWN:
        log(f"Skipping {event_type} - cooldown active ({int(COOLDOWN - (current_time - last_trigger_time))}s remaining)")
        return

    last_trigger_time = current_time
    log(f">>> TRIGGERING MONITOR: {event_type}")

    try:
        # Build command based on whether we're frozen or not
        if is_frozen():
            # Running as frozen executable - call pro_monitor directly
            cmd = [MONITOR_SCRIPT, event_type]
        else:
            # Running as script - use Python interpreter
            cmd = [PYTHON_PATH, MONITOR_SCRIPT, event_type]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                log(f"  {line}")
        if result.stderr:
            log(f"  STDERR: {result.stderr[:200]}")
    except Exception as e:
        log(f"Error running monitor: {e}")


def is_screen_locked():
    """Check if screen is locked using Quartz"""
    if not HAS_QUARTZ:
        return None

    try:
        session = Quartz.CGSessionCopyCurrentDictionary()
        if session:
            return bool(session.get('CGSSessionScreenIsLocked', 0))
        return None
    except Exception as e:
        log(f"Error checking screen state: {e}")
        return None


def watch_screen_state():
    """Watch for screen lock/unlock by polling screen state"""
    log("Screen watcher started")
    log(f"Quartz available: {HAS_QUARTZ}")
    log(f"Cooldown: {COOLDOWN} seconds")
    log("Monitoring for: Boot, Login, Unlock events")
    log("-" * 50)

    # Wait for system to be ready (network, camera, etc.)
    log(f"Waiting {STARTUP_DELAY}s for system startup...")
    time.sleep(STARTUP_DELAY)

    # Wait for network
    log("Checking network connectivity...")
    if wait_for_network(30):
        log("Network available")
    else:
        log("Network not available - will retry sending later")

    was_locked = None
    first_run = True

    while True:
        try:
            is_locked = is_screen_locked()

            if is_locked is not None:
                # First run - trigger on boot/login if screen is unlocked
                if was_locked is None:
                    was_locked = is_locked
                    log(f"Initial screen state: {'LOCKED' if is_locked else 'UNLOCKED'}")

                    # FIRST BOOT: If screen starts unlocked, this is a fresh login
                    if not is_locked and first_run:
                        log("*** FIRST BOOT/LOGIN DETECTED ***")
                        run_monitor("Login")
                        first_run = False

                # Detect unlock (was locked, now unlocked)
                elif was_locked == True and is_locked == False:
                    log("*** SCREEN UNLOCK DETECTED ***")
                    run_monitor("Unlock")

                # Detect lock (for logging only)
                elif was_locked == False and is_locked == True:
                    log("Screen locked (waiting for unlock)")

                was_locked = is_locked

            time.sleep(1)  # Check every 1 second for faster detection

        except KeyboardInterrupt:
            log("Screen watcher stopped by user")
            break
        except Exception as e:
            log(f"Error in main loop: {e}")
            time.sleep(5)


def main():
    log("=" * 60)
    log("LOGIN MONITOR - SCREEN WATCHER")
    log("=" * 60)

    if not HAS_QUARTZ:
        log("ERROR: Quartz framework not available!")
        log("Install with: pip3 install pyobjc-framework-Quartz")
        sys.exit(1)

    watch_screen_state()


if __name__ == "__main__":
    main()
