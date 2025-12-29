#!/usr/bin/env python3
"""
CyVigil Keystroke Logger
=========================
Privacy-respecting keystroke logging for enterprise security.
Logs keystroke counts and patterns, not individual keystrokes by default.

IMPORTANT: Requires Accessibility permission in System Settings.
"""

import os
import sys
import json
import time
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict

import requests

# Try to import pynput for keystroke capture
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False
    print("Warning: pynput not installed. Install with: pip3 install pynput")
    print("Also grant Accessibility permission to Terminal/Python in System Settings.")

# Configuration
CONFIG_PATH = Path.home() / ".login-monitor" / "config.json"
LOG_PATH = "/tmp/loginmonitor-keystroke.log"

# Flush interval (how often to send data to Supabase)
FLUSH_INTERVAL = 60  # seconds


def log(message: str):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(log_line + '\n')
    except Exception:
        pass


class KeystrokeLogger:
    """Privacy-respecting keystroke logger."""

    def __init__(self):
        self.config = self._load_config()
        self.device_id = self.config.get("device_id", "")
        self.supabase_url = self.config.get("supabase_url", "")
        self.supabase_key = self.config.get("supabase_key", "")

        # Keystroke settings
        dlp_config = self.config.get("dlp", {})
        self.enabled = dlp_config.get("keystroke_logging", True)
        self.log_full_keystrokes = dlp_config.get("log_full_keystrokes", False)  # Privacy option
        self.log_special_keys = dlp_config.get("log_special_keys", True)

        # Current session data
        self.current_app = ""
        self.current_window = ""
        self.session_start = datetime.now()
        self.keystroke_count = 0
        self.keystroke_buffer = []  # Only used if log_full_keystrokes is True
        self.special_keys = defaultdict(int)  # Count of special keys

        # Lock for thread safety
        self.lock = threading.Lock()

        # Listener
        self.listener = None

        log(f"Keystroke Logger initialized. Device: {self.device_id[:8] if self.device_id else 'unknown'}...")
        log(f"Full keystroke logging: {'ENABLED' if self.log_full_keystrokes else 'DISABLED (privacy mode)'}")

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading config: {e}")
        return {}

    def _get_active_app(self) -> tuple:
        """Get the currently active application."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                set windowTitle to ""
                try
                    tell process frontApp
                        set windowTitle to name of front window
                    end tell
                end try
                return frontApp & "|||" & windowTitle
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split('|||')
                app_name = parts[0] if parts else ""
                window_title = parts[1] if len(parts) > 1 else ""
                return app_name, window_title
        except Exception:
            pass

        return "", ""

    def _send_to_supabase(self, table: str, data: dict) -> bool:
        """Send data to Supabase."""
        if not self.supabase_url or not self.supabase_key:
            return False

        try:
            response = requests.post(
                f"{self.supabase_url}/rest/v1/{table}",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=data,
                timeout=10
            )
            return response.status_code in (200, 201)
        except Exception as e:
            log(f"Supabase error: {e}")
            return False

    def _flush_session(self):
        """Flush current session data to Supabase."""
        with self.lock:
            if self.keystroke_count == 0:
                return

            # Prepare keystroke data
            keystrokes_text = ""
            if self.log_full_keystrokes and self.keystroke_buffer:
                # Join keystrokes (for investigation mode)
                keystrokes_text = ''.join(self.keystroke_buffer)
                # Limit to 10000 chars
                if len(keystrokes_text) > 10000:
                    keystrokes_text = keystrokes_text[:10000] + "...[truncated]"

            session_data = {
                "device_id": self.device_id,
                "app_name": self.current_app,
                "window_title": self.current_window[:500] if self.current_window else "",
                "keystrokes": keystrokes_text if self.log_full_keystrokes else None,
                "keystroke_count": self.keystroke_count,
                "special_keys": dict(self.special_keys) if self.special_keys else None,
                "start_time": self.session_start.isoformat(),
                "end_time": datetime.now().isoformat()
            }

            success = self._send_to_supabase("keystroke_logs", session_data)

            if success:
                log(f"Flushed session: {self.current_app} - {self.keystroke_count} keystrokes")
            else:
                log(f"Failed to flush session")

            # Reset session
            self.session_start = datetime.now()
            self.keystroke_count = 0
            self.keystroke_buffer = []
            self.special_keys = defaultdict(int)

    def _on_key_press(self, key):
        """Handle key press event."""
        if not self.enabled:
            return

        with self.lock:
            # Check if app changed
            current_app, current_window = self._get_active_app()
            if current_app != self.current_app:
                # Flush previous session
                if self.keystroke_count > 0:
                    # Release lock temporarily for flush
                    self.lock.release()
                    self._flush_session()
                    self.lock.acquire()

                self.current_app = current_app
                self.current_window = current_window
                self.session_start = datetime.now()

            # Count keystroke
            self.keystroke_count += 1

            # Handle key types
            try:
                if hasattr(key, 'char') and key.char:
                    # Regular character
                    if self.log_full_keystrokes:
                        self.keystroke_buffer.append(key.char)
                else:
                    # Special key
                    key_name = str(key).replace('Key.', '')

                    if self.log_special_keys:
                        self.special_keys[key_name] += 1

                    if self.log_full_keystrokes:
                        if key == keyboard.Key.space:
                            self.keystroke_buffer.append(' ')
                        elif key == keyboard.Key.enter:
                            self.keystroke_buffer.append('\n')
                        elif key == keyboard.Key.tab:
                            self.keystroke_buffer.append('\t')
                        elif key == keyboard.Key.backspace:
                            if self.keystroke_buffer:
                                self.keystroke_buffer.pop()
                        else:
                            self.keystroke_buffer.append(f'[{key_name}]')

            except Exception as e:
                pass

    def _flush_timer(self):
        """Periodic flush timer."""
        while True:
            time.sleep(FLUSH_INTERVAL)
            try:
                self._flush_session()
            except Exception as e:
                log(f"Flush error: {e}")

    def run(self):
        """Start keystroke logging."""
        if not HAS_PYNPUT:
            log("ERROR: pynput not installed. Cannot start keystroke logger.")
            log("Install with: pip3 install pynput")
            return

        log("Keystroke Logger starting...")
        log("NOTE: Requires Accessibility permission in System Settings > Privacy & Security > Accessibility")

        # Start flush timer thread
        flush_thread = threading.Thread(target=self._flush_timer, daemon=True)
        flush_thread.start()

        # Get initial app
        self.current_app, self.current_window = self._get_active_app()

        try:
            # Start keyboard listener
            with keyboard.Listener(on_press=self._on_key_press) as listener:
                self.listener = listener
                log("Keystroke listener started successfully")
                listener.join()

        except Exception as e:
            log(f"Keystroke listener error: {e}")
            log("Make sure Accessibility permission is granted to Terminal/Python")
            log("System Settings > Privacy & Security > Accessibility")


def check_accessibility_permission():
    """Check if Accessibility permission is granted."""
    try:
        # Try to create a simple event tap
        from Quartz import (
            CGEventTapCreate, kCGSessionEventTap, kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly, CGEventMaskBit, kCGEventKeyDown
        )

        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            CGEventMaskBit(kCGEventKeyDown),
            lambda *args: None,
            None
        )

        if tap is None:
            return False
        return True

    except Exception:
        return False


def main():
    """Entry point."""
    if not HAS_PYNPUT:
        print("ERROR: pynput not installed")
        print("Install with: pip3 install pynput")
        sys.exit(1)

    # Check accessibility permission
    try:
        from Quartz import CGEventTapCreate
        has_quartz = True
    except ImportError:
        has_quartz = False

    if has_quartz:
        if not check_accessibility_permission():
            print("\n" + "="*60)
            print("ACCESSIBILITY PERMISSION REQUIRED")
            print("="*60)
            print("\nTo enable keystroke logging:")
            print("1. Open System Settings")
            print("2. Go to Privacy & Security > Accessibility")
            print("3. Click the + button")
            print("4. Add Terminal.app (or your Python installation)")
            print("5. Restart this script")
            print("\nOpening System Settings...")

            subprocess.run([
                'open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'
            ])
            sys.exit(1)

    logger = KeystrokeLogger()
    logger.run()


if __name__ == "__main__":
    main()
