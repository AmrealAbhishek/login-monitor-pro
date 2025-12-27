#!/usr/bin/env python3
"""
Failed Login Detector for Login Monitor PRO
=============================================

Monitors system logs for failed login attempts and sends alerts.
Works on macOS, Linux, and Windows.
"""

import os
import sys
import json
import subprocess
import platform
import time
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
LOG_FILE = SCRIPT_DIR / "failed_logins.log"

sys.path.insert(0, str(SCRIPT_DIR))


def log(message):
    """Log message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{timestamp}] {message}"
    print(entry)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(entry + "\n")
    except:
        pass


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


class FailedLoginDetector:
    """Detect failed login attempts"""

    def __init__(self):
        self.config = load_config()
        self.last_check = datetime.now()
        self.failed_count = 0
        self.alert_threshold = 3  # Alert after 3 failed attempts

    def check_macos(self):
        """Check macOS security log for failed logins"""
        try:
            # Use log command to query authentication failures
            result = subprocess.run([
                "log", "show",
                "--predicate", 'eventMessage CONTAINS "authentication failed" OR eventMessage CONTAINS "Failed to authenticate"',
                "--style", "compact",
                "--last", "5m"
            ], capture_output=True, text=True, timeout=30)

            failures = []
            for line in result.stdout.split('\n'):
                if 'failed' in line.lower() or 'authentication' in line.lower():
                    failures.append(line.strip())

            return failures

        except Exception as e:
            log(f"Error checking macOS logs: {e}")
            return []

    def check_linux(self):
        """Check Linux auth log for failed logins"""
        try:
            auth_logs = ['/var/log/auth.log', '/var/log/secure']

            failures = []
            for log_file in auth_logs:
                if os.path.exists(log_file):
                    result = subprocess.run([
                        "grep", "-i", "failed", log_file
                    ], capture_output=True, text=True, timeout=30)

                    for line in result.stdout.split('\n')[-10:]:  # Last 10 failures
                        if line.strip():
                            failures.append(line.strip())

            return failures

        except Exception as e:
            log(f"Error checking Linux logs: {e}")
            return []

    def check_windows(self):
        """Check Windows Security log for failed logins"""
        try:
            # PowerShell command to get failed login events
            ps_cmd = '''
            Get-WinEvent -FilterHashtable @{
                LogName='Security';
                Id=4625  # Failed login event
            } -MaxEvents 10 | Select-Object TimeCreated, Message | ConvertTo-Json
            '''

            result = subprocess.run([
                "powershell", "-Command", ps_cmd
            ], capture_output=True, text=True, timeout=30)

            if result.stdout:
                events = json.loads(result.stdout)
                return [f"{e['TimeCreated']}: Failed login" for e in events]

            return []

        except Exception as e:
            log(f"Error checking Windows logs: {e}")
            return []

    def check(self):
        """Check for failed logins based on OS"""
        system = platform.system()

        if system == "Darwin":
            return self.check_macos()
        elif system == "Linux":
            return self.check_linux()
        elif system == "Windows":
            return self.check_windows()

        return []

    def send_alert(self, failures):
        """Send alert for failed login attempts"""
        try:
            from pro_monitor import TelegramNotifier, EmailNotifier, SystemInfo, Capture

            # Capture photo of potential intruder
            photos = Capture.capture_photos(count=1, delay=0)

            # Get system info
            sys_info = SystemInfo.collect_all()

            # Build alert message
            alert_msg = f"""
🚨 FAILED LOGIN ATTEMPTS DETECTED! 🚨

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Host: {sys_info['hostname']}
Attempts: {len(failures)}

Recent failures:
"""
            for f in failures[:5]:
                alert_msg += f"• {f[:100]}...\n"

            alert_msg += f"""
Location: {sys_info['location'].get('google_maps', 'Unknown')}
Public IP: {sys_info['public_ip']}
"""

            # Send Telegram alert
            telegram_config = self.config.get('telegram', {})
            if telegram_config.get('enabled'):
                notifier = TelegramNotifier(
                    telegram_config.get('bot_token'),
                    telegram_config.get('chat_id')
                )
                notifier.send_message(alert_msg)

                if photos:
                    notifier.send_photo(photos[0], "📸 Potential intruder captured!")

            # Send email alert
            email_notifier = EmailNotifier(self.config)
            event_data = {
                'id': f"failed_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'event_type': 'FAILED_LOGIN_ALERT',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'hostname': sys_info['hostname'],
                'user': 'INTRUDER',
                'os': sys_info['os'],
                'local_ip': sys_info['local_ip'],
                'public_ip': sys_info['public_ip'],
                'location': sys_info['location'],
                'battery': sys_info.get('battery', {}),
                'wifi': sys_info.get('wifi', {}),
                'failed_attempts': failures[:5]
            }

            email_notifier.send(event_data, photos, None)
            log(f"Alert sent for {len(failures)} failed login attempts")

        except Exception as e:
            log(f"Failed to send alert: {e}")

    def run(self, interval=60):
        """Run continuous monitoring"""
        log("Failed Login Detector started")

        while True:
            try:
                failures = self.check()

                if failures:
                    log(f"Detected {len(failures)} failed login attempts")
                    self.failed_count += len(failures)

                    if self.failed_count >= self.alert_threshold:
                        self.send_alert(failures)
                        self.failed_count = 0  # Reset after alert

                time.sleep(interval)

            except KeyboardInterrupt:
                log("Detector stopped by user")
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(interval)


def main():
    print("="*60)
    print("LOGIN MONITOR PRO - Failed Login Detector")
    print("="*60)

    detector = FailedLoginDetector()

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        failures = detector.check()
        print(f"Found {len(failures)} failed attempts")
        for f in failures:
            print(f"  • {f}")
    else:
        detector.run()


if __name__ == "__main__":
    main()
