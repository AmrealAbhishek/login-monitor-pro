#!/usr/bin/env python3
"""
Suspicious Activity Detector for Login Monitor PRO
Detects suspicious activities and triggers automatic screenshots.
Monitors: USB activity, remote tools, VPN, unusual time, mass file operations, etc.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient


def get_base_dir() -> Path:
    return Path.home() / ".login-monitor"


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [SuspiciousDetector] {message}"
    print(log_msg, flush=True)
    try:
        log_file = Path("/tmp/loginmonitor-suspicious.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


@dataclass
class SuspiciousRule:
    """Suspicious activity rule"""
    id: str
    name: str
    description: str
    rule_type: str
    config: Dict
    severity: str = "high"
    action: str = "alert_screenshot"
    auto_screenshot: bool = True
    notify_immediately: bool = True
    enabled: bool = True


@dataclass
class SuspiciousEvent:
    """Detected suspicious event"""
    rule: SuspiciousRule
    details: Dict
    timestamp: datetime = field(default_factory=datetime.now)
    screenshot_url: Optional[str] = None


# Default sensitive apps that indicate potential data exfiltration
SENSITIVE_APPS = {
    # Remote access
    "TeamViewer": "remote_access",
    "AnyDesk": "remote_access",
    "VNC Viewer": "remote_access",
    "Remote Desktop": "remote_access",
    "LogMeIn": "remote_access",
    "Splashtop": "remote_access",
    "Chrome Remote Desktop": "remote_access",

    # File transfer
    "FileZilla": "file_transfer",
    "Cyberduck": "file_transfer",
    "Transmit": "file_transfer",
    "WinSCP": "file_transfer",

    # Screen recording
    "OBS": "screen_capture",
    "OBS Studio": "screen_capture",
    "QuickTime Player": "screen_capture",
    "ScreenFlow": "screen_capture",
    "Camtasia": "screen_capture",
    "Loom": "screen_capture",
    "Snagit": "screen_capture",

    # VPN clients
    "NordVPN": "vpn",
    "ExpressVPN": "vpn",
    "Surfshark": "vpn",
    "ProtonVPN": "vpn",
    "TunnelBear": "vpn",
    "OpenVPN": "vpn",
    "Viscosity": "vpn",

    # Torrent/P2P
    "Transmission": "p2p",
    "qBittorrent": "p2p",
    "uTorrent": "p2p",
    "BitTorrent": "p2p",

    # Browsers (private/tor)
    "Tor Browser": "privacy",
}


class USBMonitor:
    """Monitors USB device connections"""

    def __init__(self):
        self.known_devices: Set[str] = set()
        self._initial_scan()

    def _initial_scan(self):
        """Get initial list of USB devices"""
        try:
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self._extract_devices(data, self.known_devices)
        except Exception as e:
            log(f"Error scanning USB devices: {e}")

    def _extract_devices(self, data: Dict, devices: Set[str]):
        """Extract device identifiers from system_profiler output"""
        if isinstance(data, dict):
            if '_name' in data:
                name = data.get('_name', '')
                vendor = data.get('manufacturer', '')
                serial = data.get('serial_num', '')
                device_id = f"{name}|{vendor}|{serial}"
                if name and 'Hub' not in name:
                    devices.add(device_id)

            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    self._extract_devices(value, devices)

        elif isinstance(data, list):
            for item in data:
                self._extract_devices(item, devices)

    def check_new_devices(self) -> List[Dict]:
        """Check for newly connected USB devices"""
        new_devices = []
        current_devices: Set[str] = set()

        try:
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self._extract_devices(data, current_devices)

                # Find new devices
                for device_id in current_devices:
                    if device_id not in self.known_devices:
                        parts = device_id.split('|')
                        new_devices.append({
                            'name': parts[0],
                            'manufacturer': parts[1] if len(parts) > 1 else '',
                            'serial': parts[2] if len(parts) > 2 else ''
                        })

                self.known_devices = current_devices

        except Exception as e:
            log(f"Error checking USB devices: {e}")

        return new_devices


class AppMonitor:
    """Monitors running applications"""

    def __init__(self):
        self.running_apps: Set[str] = set()
        self._initial_scan()

    def _initial_scan(self):
        """Get initial list of running apps"""
        self.running_apps = self._get_running_apps()

    def _get_running_apps(self) -> Set[str]:
        """Get list of currently running applications"""
        apps = set()
        try:
            script = '''
            tell application "System Events"
                set appList to {}
                repeat with p in (every process whose background only is false)
                    set end of appList to name of p
                end repeat
                return appList
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for app in result.stdout.strip().split(', '):
                    apps.add(app.strip())
        except Exception:
            pass
        return apps

    def check_new_apps(self) -> List[Dict]:
        """Check for newly launched applications"""
        new_apps = []
        current_apps = self._get_running_apps()

        for app_name in current_apps:
            if app_name not in self.running_apps:
                # Check if it's a sensitive app
                category = SENSITIVE_APPS.get(app_name)
                if category:
                    new_apps.append({
                        'app_name': app_name,
                        'category': category
                    })

        self.running_apps = current_apps
        return new_apps


class NetworkMonitor:
    """Monitors network connections for VPN/proxy usage"""

    def __init__(self):
        self.baseline_interfaces: Set[str] = set()
        self._initial_scan()

    def _initial_scan(self):
        """Get initial network interfaces"""
        try:
            result = subprocess.run(
                ["ifconfig", "-l"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.baseline_interfaces = set(result.stdout.strip().split())
        except Exception:
            pass

    def check_vpn_connection(self) -> Optional[Dict]:
        """Check for new VPN/tunnel interfaces"""
        try:
            result = subprocess.run(
                ["ifconfig", "-l"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current_interfaces = set(result.stdout.strip().split())

                # Look for VPN-like interfaces
                vpn_patterns = ['utun', 'ppp', 'tap', 'tun', 'ipsec']

                for iface in current_interfaces - self.baseline_interfaces:
                    for pattern in vpn_patterns:
                        if pattern in iface.lower():
                            return {
                                'interface': iface,
                                'type': 'vpn_detected'
                            }

                self.baseline_interfaces = current_interfaces

        except Exception:
            pass

        return None


class FileActivityTracker:
    """Tracks file operation rates"""

    def __init__(self, window_minutes: int = 5, threshold: int = 50):
        self.window_minutes = window_minutes
        self.threshold = threshold
        self.operations: List[datetime] = []

    def record_operation(self):
        """Record a file operation"""
        now = datetime.now()
        self.operations.append(now)

        # Clean old entries
        cutoff = now - timedelta(minutes=self.window_minutes)
        self.operations = [op for op in self.operations if op > cutoff]

    def is_high_activity(self) -> bool:
        """Check if file activity exceeds threshold"""
        return len(self.operations) >= self.threshold

    def get_count(self) -> int:
        """Get current operation count"""
        return len(self.operations)


class SuspiciousActivityDetector:
    """Main suspicious activity detector"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.running = False
        self.rules: List[SuspiciousRule] = []
        self.client: Optional[SupabaseClient] = None
        self.device_id: Optional[str] = None

        # Monitors
        self.usb_monitor = USBMonitor()
        self.app_monitor = AppMonitor()
        self.network_monitor = NetworkMonitor()
        self.file_tracker = FileActivityTracker()

        self._init_supabase()
        self._load_rules()

    def _load_config(self) -> dict:
        config_file = self.base_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception as e:
                log(f"Error loading config: {e}")
        return {}

    def _init_supabase(self):
        supabase_config = self.config.get("supabase", {})
        if not supabase_config.get("url"):
            log("Supabase not configured")
            return

        try:
            self.client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config.get("anon_key", ""),
                service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
            )
            self.device_id = supabase_config.get("device_id")
            log(f"Supabase initialized, device: {self.device_id}")
        except Exception as e:
            log(f"Error initializing Supabase: {e}")

    def _load_rules(self):
        """Load suspicious activity rules from Supabase"""
        if not self.client:
            self._load_default_rules()
            return

        try:
            response = self.client._request(
                "GET",
                "/rest/v1/suspicious_activity_rules?enabled=eq.true&select=*",
                use_service_key=True
            )

            if response:
                self.rules = []
                for rule_data in response:
                    rule = SuspiciousRule(
                        id=rule_data['id'],
                        name=rule_data['name'],
                        description=rule_data.get('description', ''),
                        rule_type=rule_data['rule_type'],
                        config=rule_data.get('config', {}),
                        severity=rule_data.get('severity', 'high'),
                        action=rule_data.get('action', 'alert_screenshot'),
                        auto_screenshot=rule_data.get('auto_screenshot', True),
                        notify_immediately=rule_data.get('notify_immediately', True),
                        enabled=rule_data.get('enabled', True)
                    )
                    self.rules.append(rule)
                log(f"Loaded {len(self.rules)} suspicious activity rules")
            else:
                self._load_default_rules()

        except Exception as e:
            log(f"Error loading rules: {e}")
            self._load_default_rules()

    def _load_default_rules(self):
        """Load default rules"""
        self.rules = [
            SuspiciousRule(
                id="default-1",
                name="After Hours Access",
                description="Login between midnight and 6 AM",
                rule_type="unusual_time",
                config={"start_hour": 0, "end_hour": 6, "weekends": False},
                severity="high",
                action="alert_screenshot"
            ),
            SuspiciousRule(
                id="default-2",
                name="Remote Access Tools",
                description="TeamViewer, AnyDesk, VNC detected",
                rule_type="sensitive_app_launch",
                config={"apps": ["TeamViewer", "AnyDesk", "VNC Viewer", "Remote Desktop"]},
                severity="high",
                action="alert_screenshot"
            ),
            SuspiciousRule(
                id="default-3",
                name="USB Device Connected",
                description="External storage device connected",
                rule_type="usb_activity",
                config={"alert_on_connect": True},
                severity="high",
                action="alert_screenshot"
            ),
            SuspiciousRule(
                id="default-4",
                name="VPN Connection",
                description="VPN or tunnel interface detected",
                rule_type="vpn_connection",
                config={},
                severity="medium",
                action="alert"
            ),
            SuspiciousRule(
                id="default-5",
                name="Screen Recording Apps",
                description="OBS, Loom, or similar detected",
                rule_type="screen_capture_tool",
                config={"apps": ["OBS", "OBS Studio", "Loom", "ScreenFlow", "Camtasia"]},
                severity="medium",
                action="alert_screenshot"
            ),
        ]
        log(f"Loaded {len(self.rules)} default rules")

    def _is_unusual_time(self, config: Dict) -> bool:
        """Check if current time is unusual"""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday

        start_hour = config.get('start_hour', 0)
        end_hour = config.get('end_hour', 6)
        check_weekends = config.get('weekends', False)
        check_weekdays = config.get('weekdays', True)

        is_weekend = weekday >= 5

        if is_weekend and not check_weekends:
            return False
        if not is_weekend and not check_weekdays:
            return False

        if start_hour <= hour < end_hour:
            return True

        return False

    def _capture_screenshot(self, reason: str) -> Optional[str]:
        """Capture and upload screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.base_dir / "captured_images" / f"suspicious_{timestamp}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                ["/usr/sbin/screencapture", "-x", str(screenshot_path)],
                timeout=10
            )

            if screenshot_path.exists() and self.client and self.device_id:
                url = self.client.upload_file(
                    bucket="screenshots",
                    file_path=str(screenshot_path),
                    device_id=self.device_id
                )
                log(f"Screenshot captured: {reason}")
                return url

        except Exception as e:
            log(f"Error capturing screenshot: {e}")
        return None

    def _handle_event(self, event: SuspiciousEvent):
        """Handle a suspicious event"""
        rule = event.rule
        log(f"SUSPICIOUS: {rule.name} - {event.details}")

        # Capture screenshot if configured
        if rule.auto_screenshot and rule.action in ['alert_screenshot']:
            event.screenshot_url = self._capture_screenshot(rule.name)

        # Send alert to Supabase
        if self.client and self.device_id:
            try:
                alert_data = {
                    "device_id": self.device_id,
                    "alert_type": "suspicious_activity",
                    "severity": rule.severity,
                    "title": rule.name,
                    "description": f"{rule.description}\n\nDetails: {json.dumps(event.details, indent=2)}",
                    "metadata": {
                        "rule_id": rule.id,
                        "rule_type": rule.rule_type,
                        "details": event.details,
                        "screenshot_url": event.screenshot_url
                    },
                    "acknowledged": False
                }

                self.client._request(
                    "POST",
                    "/rest/v1/security_alerts",
                    alert_data,
                    use_service_key=True
                )
                log(f"Alert sent: {rule.name}")

                # Send push notification
                if rule.notify_immediately and rule.severity in ['critical', 'high']:
                    self._send_push_notification(event)

            except Exception as e:
                log(f"Error sending alert: {e}")

    def _send_push_notification(self, event: SuspiciousEvent):
        """Send push notification"""
        try:
            from fcm_sender import send_fcm_notification
            send_fcm_notification(
                device_id=self.device_id,
                title=f"Suspicious: {event.rule.name}",
                body=event.rule.description,
                data={
                    "type": "suspicious_activity",
                    "severity": event.rule.severity,
                    "rule_type": event.rule.rule_type
                }
            )
        except Exception as e:
            log(f"Error sending push: {e}")

    def _check_unusual_time_rules(self):
        """Check unusual time rules"""
        for rule in self.rules:
            if rule.rule_type == 'unusual_time' and rule.enabled:
                if self._is_unusual_time(rule.config):
                    event = SuspiciousEvent(
                        rule=rule,
                        details={
                            'current_hour': datetime.now().hour,
                            'current_day': datetime.now().strftime('%A')
                        }
                    )
                    self._handle_event(event)

    def _check_app_rules(self):
        """Check for sensitive app launches"""
        new_apps = self.app_monitor.check_new_apps()

        for app_info in new_apps:
            app_name = app_info['app_name']
            category = app_info['category']

            # Find matching rule
            for rule in self.rules:
                if rule.rule_type == 'sensitive_app_launch' and rule.enabled:
                    watched_apps = rule.config.get('apps', [])
                    if app_name in watched_apps:
                        event = SuspiciousEvent(
                            rule=rule,
                            details={
                                'app_name': app_name,
                                'category': category
                            }
                        )
                        self._handle_event(event)
                        break

                elif rule.rule_type == 'screen_capture_tool' and category == 'screen_capture':
                    watched_apps = rule.config.get('apps', list(k for k, v in SENSITIVE_APPS.items() if v == 'screen_capture'))
                    if app_name in watched_apps:
                        event = SuspiciousEvent(
                            rule=rule,
                            details={'app_name': app_name}
                        )
                        self._handle_event(event)
                        break

    def _check_usb_rules(self):
        """Check for USB device connections"""
        new_devices = self.usb_monitor.check_new_devices()

        for device in new_devices:
            for rule in self.rules:
                if rule.rule_type == 'usb_activity' and rule.enabled:
                    if rule.config.get('alert_on_connect', True):
                        event = SuspiciousEvent(
                            rule=rule,
                            details={
                                'device_name': device['name'],
                                'manufacturer': device['manufacturer'],
                                'serial': device['serial']
                            }
                        )
                        self._handle_event(event)
                        break

    def _check_vpn_rules(self):
        """Check for VPN connections"""
        vpn_info = self.network_monitor.check_vpn_connection()

        if vpn_info:
            for rule in self.rules:
                if rule.rule_type == 'vpn_connection' and rule.enabled:
                    event = SuspiciousEvent(
                        rule=rule,
                        details=vpn_info
                    )
                    self._handle_event(event)
                    break

    def record_file_operation(self):
        """Called by file_monitor to track file operations"""
        self.file_tracker.record_operation()

        # Check high activity rules
        if self.file_tracker.is_high_activity():
            for rule in self.rules:
                if rule.rule_type == 'high_file_activity' and rule.enabled:
                    threshold = rule.config.get('threshold', 50)
                    if self.file_tracker.get_count() >= threshold:
                        event = SuspiciousEvent(
                            rule=rule,
                            details={
                                'operation_count': self.file_tracker.get_count(),
                                'window_minutes': self.file_tracker.window_minutes
                            }
                        )
                        self._handle_event(event)
                        # Reset counter after alert
                        self.file_tracker.operations = []
                        break

    def _monitor_loop(self):
        """Main monitoring loop"""
        check_count = 0
        unusual_time_checked = False

        while self.running:
            try:
                # Check apps every 10 seconds
                self._check_app_rules()

                # Check USB every 30 seconds
                if check_count % 3 == 0:
                    self._check_usb_rules()

                # Check VPN every 60 seconds
                if check_count % 6 == 0:
                    self._check_vpn_rules()

                # Check unusual time once per session (on startup and midnight)
                current_hour = datetime.now().hour
                if not unusual_time_checked or current_hour == 0:
                    self._check_unusual_time_rules()
                    unusual_time_checked = True

                check_count += 1
                time.sleep(10)

            except Exception as e:
                log(f"Error in monitor loop: {e}")
                time.sleep(10)

    def run(self):
        """Start suspicious activity detection"""
        log("=" * 60)
        log("SUSPICIOUS ACTIVITY DETECTOR STARTED")
        log(f"Rules loaded: {len(self.rules)}")
        log(f"Sensitive apps monitored: {len(SENSITIVE_APPS)}")
        log("=" * 60)

        self.running = True
        self._monitor_loop()


def main():
    detector = SuspiciousActivityDetector()
    try:
        detector.run()
    except KeyboardInterrupt:
        log("Detector stopped")
        detector.running = False


if __name__ == "__main__":
    main()
