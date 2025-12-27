#!/usr/bin/env python3
"""
Intruder Detector for Login Monitor PRO
Monitors failed login attempts and triggers alerts when threshold is breached.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

# Configuration
FAILED_ATTEMPT_THRESHOLD = 3  # Number of failures before alert
TIME_WINDOW_MINUTES = 5  # Time window to count failures
CHECK_INTERVAL_SECONDS = 30  # How often to check for new failures


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [IntruderDetector] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-intruder.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


class IntruderDetector:
    """Monitors for failed login attempts"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.failed_attempts: List[Dict] = []
        self.last_check_time = datetime.now()
        self.alerted_windows: set = set()  # Prevent duplicate alerts

    def _load_config(self) -> dict:
        """Load configuration from file"""
        config_file = self.base_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception as e:
                log(f"Error loading config: {e}")
        return {}

    def get_failed_login_attempts(self) -> List[Dict]:
        """Get recent failed login attempts from system logs"""
        attempts = []

        try:
            # Use log show to get authentication failures
            # Look for failed authentications in the last TIME_WINDOW_MINUTES
            since_time = (datetime.now() - timedelta(minutes=TIME_WINDOW_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")

            result = subprocess.run(
                [
                    "log", "show",
                    "--predicate", 'subsystem == "com.apple.authorization" AND eventMessage CONTAINS[c] "failed"',
                    "--style", "json",
                    "--start", since_time,
                    "--last", "1h"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout:
                # Parse log entries (simplified - actual parsing may need adjustment)
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'authentication' in line.lower() and 'failed' in line.lower():
                        attempts.append({
                            "timestamp": datetime.now().isoformat(),
                            "message": line[:200],
                            "source": "authorization"
                        })

            # Also check for screensaver/login failures
            result2 = subprocess.run(
                [
                    "log", "show",
                    "--predicate", 'eventMessage CONTAINS[c] "authentication failed" OR eventMessage CONTAINS[c] "incorrect password"',
                    "--style", "compact",
                    "--start", since_time,
                    "--last", "1h"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result2.returncode == 0 and result2.stdout:
                lines = result2.stdout.strip().split('\n')
                for line in lines:
                    if line.strip() and ('failed' in line.lower() or 'incorrect' in line.lower()):
                        attempts.append({
                            "timestamp": datetime.now().isoformat(),
                            "message": line[:200],
                            "source": "system"
                        })

        except subprocess.TimeoutExpired:
            log("Timeout checking system logs")
        except Exception as e:
            log(f"Error checking failed logins: {e}")

        return attempts

    def check_for_intrusions(self) -> Optional[Dict]:
        """Check if failed login threshold has been breached"""
        current_attempts = self.get_failed_login_attempts()

        if not current_attempts:
            return None

        # Count unique failures in time window
        now = datetime.now()
        window_key = now.strftime("%Y%m%d%H%M")[:11]  # 10-minute window key

        # Skip if we already alerted for this window
        if window_key in self.alerted_windows:
            return None

        attempt_count = len(current_attempts)

        log(f"Found {attempt_count} failed attempts in last {TIME_WINDOW_MINUTES} minutes")

        if attempt_count >= FAILED_ATTEMPT_THRESHOLD:
            self.alerted_windows.add(window_key)

            # Clean up old window keys (keep last 10)
            if len(self.alerted_windows) > 10:
                self.alerted_windows = set(list(self.alerted_windows)[-10:])

            return {
                "event_type": "Intruder",
                "failed_attempts": attempt_count,
                "threshold": FAILED_ATTEMPT_THRESHOLD,
                "time_window_minutes": TIME_WINDOW_MINUTES,
                "attempts": current_attempts[:5],  # Include first 5 attempts
                "timestamp": now.isoformat()
            }

        return None

    def trigger_alert(self, intrusion_data: Dict) -> bool:
        """Trigger intruder alert - capture photo and send event"""
        try:
            from supabase_client import SupabaseClient
            from pro_monitor import Capture

            log("INTRUSION DETECTED! Capturing photo and sending alert...")

            # Capture photo of intruder
            photos = []
            try:
                photo_paths = Capture.capture_photos(count=1, delay=0)
                if photo_paths:
                    photos = photo_paths
            except Exception as e:
                log(f"Failed to capture photo: {e}")

            # Send event to Supabase
            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if supabase_config.get("url") and supabase_config.get("device_id"):
                client = SupabaseClient(
                    url=supabase_config["url"],
                    anon_key=supabase_config.get("anon_key", ""),
                    service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
                )

                result = client.send_event(
                    device_id=supabase_config["device_id"],
                    event_data=intrusion_data,
                    photos=photos
                )

                if result.get("success"):
                    log(f"Intruder alert sent successfully! Event ID: {result.get('event_id')}")
                    return True
                else:
                    log(f"Failed to send alert: {result.get('error')}")
            else:
                log("Supabase not configured, skipping alert")

            return False

        except Exception as e:
            log(f"Error triggering alert: {e}")
            return False

    def run(self):
        """Main monitoring loop"""
        log("=" * 60)
        log("INTRUDER DETECTOR STARTED")
        log(f"Threshold: {FAILED_ATTEMPT_THRESHOLD} failures in {TIME_WINDOW_MINUTES} minutes")
        log("=" * 60)

        while True:
            try:
                intrusion = self.check_for_intrusions()

                if intrusion:
                    log(f"ALERT: {intrusion['failed_attempts']} failed attempts detected!")
                    self.trigger_alert(intrusion)

                time.sleep(CHECK_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                log("Intruder detector stopped by user")
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    detector = IntruderDetector()
    detector.run()


if __name__ == "__main__":
    main()
