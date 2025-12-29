#!/usr/bin/env python3
"""
File Monitor for Login Monitor PRO
Monitors file system access and triggers alerts for sensitive files.
Uses FSEvents on macOS for real-time file system monitoring.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import fnmatch
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: watchdog not installed. Run: pip3 install watchdog")

from supabase_client import SupabaseClient


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [FileMonitor] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-files.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


@dataclass
class FileRule:
    """Represents a sensitive file rule"""
    id: str
    name: str
    rule_type: str  # path_pattern, extension, filename_pattern, content_keyword
    pattern: str
    severity: str
    action: str  # alert, alert_screenshot, block, log_only
    enabled: bool = True

    def matches(self, file_path: str) -> bool:
        """Check if file path matches this rule"""
        path = Path(file_path)
        file_name = path.name.lower()
        extension = path.suffix.lower()

        patterns = [p.strip().lower() for p in self.pattern.split(',')]

        if self.rule_type == 'extension':
            # Match file extensions
            for pat in patterns:
                if not pat.startswith('.'):
                    pat = '.' + pat
                if extension == pat:
                    return True

        elif self.rule_type == 'filename_pattern':
            # Match filename patterns (wildcard)
            for pat in patterns:
                if fnmatch.fnmatch(file_name, pat):
                    return True

        elif self.rule_type == 'path_pattern':
            # Match full path patterns
            full_path = str(file_path).lower()
            for pat in patterns:
                if fnmatch.fnmatch(full_path, pat):
                    return True

        elif self.rule_type == 'content_keyword':
            # Content matching would require reading the file
            # For now, just match in filename
            for pat in patterns:
                if pat in file_name:
                    return True

        return False


@dataclass
class FileAccessEvent:
    """Represents a file access event"""
    file_path: str
    file_name: str
    file_extension: str
    access_type: str
    app_name: Optional[str] = None
    bundle_id: Optional[str] = None
    destination: Optional[str] = None
    file_size: Optional[int] = None
    user_name: Optional[str] = None
    hostname: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    matched_rule: Optional[FileRule] = None


class SensitiveFileHandler(FileSystemEventHandler):
    """Handles file system events and checks against rules"""

    def __init__(self, monitor: 'FileMonitor'):
        super().__init__()
        self.monitor = monitor
        self.recent_events: Dict[str, datetime] = {}
        self.debounce_seconds = 2  # Ignore duplicate events within this window

    def _should_process(self, path: str) -> bool:
        """Check if we should process this event (debouncing)"""
        now = datetime.now()

        # Skip hidden files and system directories
        if '/.' in path or path.startswith('.'):
            return False

        # Skip common noise directories
        skip_patterns = [
            '/Library/Caches',
            '/Library/Logs',
            '/Library/Preferences',
            '/.Trash',
            '/node_modules/',
            '/.git/',
            '/__pycache__/',
            '/venv/',
            '/.venv/',
        ]
        for pattern in skip_patterns:
            if pattern in path:
                return False

        # Debounce: skip if we just processed this path
        if path in self.recent_events:
            if (now - self.recent_events[path]).total_seconds() < self.debounce_seconds:
                return False

        self.recent_events[path] = now

        # Clean old entries
        cutoff = now - timedelta(seconds=self.debounce_seconds * 2)
        self.recent_events = {k: v for k, v in self.recent_events.items() if v > cutoff}

        return True

    def _get_access_type(self, event: FileSystemEvent) -> str:
        """Determine access type from event"""
        if event.event_type == 'created':
            return 'create'
        elif event.event_type == 'modified':
            return 'modify'
        elif event.event_type == 'deleted':
            return 'delete'
        elif event.event_type == 'moved':
            return 'move'
        else:
            return 'open'

    def on_any_event(self, event: FileSystemEvent):
        """Handle any file system event"""
        if event.is_directory:
            return

        path = event.src_path
        if not self._should_process(path):
            return

        access_type = self._get_access_type(event)

        # For move events, track destination
        destination = None
        if hasattr(event, 'dest_path'):
            destination = event.dest_path

        self.monitor.process_file_event(path, access_type, destination)


class FileMonitor:
    """Main file monitoring class"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.running = False
        self.rules: List[FileRule] = []
        self.client: Optional[SupabaseClient] = None
        self.device_id: Optional[str] = None
        self.observer: Optional[Observer] = None
        self.event_queue: List[FileAccessEvent] = []
        self.queue_lock = threading.Lock()

        self._init_supabase()
        self._load_rules()

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

    def _init_supabase(self):
        """Initialize Supabase client"""
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
        """Load sensitive file rules from Supabase"""
        if not self.client:
            self._load_default_rules()
            return

        try:
            # Fetch rules from Supabase
            response = self.client._request(
                "GET",
                "/rest/v1/sensitive_file_rules?enabled=eq.true&select=*",
                use_service_key=True
            )

            if response:
                self.rules = []
                for rule_data in response:
                    rule = FileRule(
                        id=rule_data['id'],
                        name=rule_data['name'],
                        rule_type=rule_data['rule_type'],
                        pattern=rule_data['pattern'],
                        severity=rule_data.get('severity', 'medium'),
                        action=rule_data.get('action', 'alert'),
                        enabled=rule_data.get('enabled', True)
                    )
                    self.rules.append(rule)

                log(f"Loaded {len(self.rules)} file monitoring rules from Supabase")
            else:
                self._load_default_rules()

        except Exception as e:
            log(f"Error loading rules from Supabase: {e}")
            self._load_default_rules()

    def _load_default_rules(self):
        """Load default rules if Supabase is unavailable"""
        self.rules = [
            FileRule(
                id="default-1",
                name="Password Files",
                rule_type="filename_pattern",
                pattern="*password*,*passwd*,*credential*",
                severity="critical",
                action="alert_screenshot"
            ),
            FileRule(
                id="default-2",
                name="Secret Keys",
                rule_type="extension",
                pattern=".pem,.key,.p12,.pfx",
                severity="critical",
                action="alert_screenshot"
            ),
            FileRule(
                id="default-3",
                name="Database Files",
                rule_type="extension",
                pattern=".sql,.db,.sqlite,.sqlite3,.bak",
                severity="high",
                action="alert"
            ),
            FileRule(
                id="default-4",
                name="Confidential Folders",
                rule_type="path_pattern",
                pattern="*/Confidential/*,*/Private/*,*/Sensitive/*,*/Secret/*",
                severity="high",
                action="alert_screenshot"
            ),
            FileRule(
                id="default-5",
                name="Financial Documents",
                rule_type="filename_pattern",
                pattern="*financial*,*salary*,*payroll*,*invoice*,*budget*",
                severity="medium",
                action="alert"
            ),
        ]
        log(f"Loaded {len(self.rules)} default file monitoring rules")

    def _get_active_app(self) -> Tuple[Optional[str], Optional[str]]:
        """Get currently active application"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                return name of frontApp & "|" & bundle identifier of frontApp
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    return parts[0], parts[1] if parts[1] != 'missing value' else None
                return parts[0], None
        except Exception:
            pass
        return None, None

    def _capture_screenshot(self, reason: str) -> Optional[str]:
        """Capture screenshot and upload to Supabase"""
        try:
            # Capture screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.base_dir / "captured_images" / f"file_alert_{timestamp}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                ["/usr/sbin/screencapture", "-x", str(screenshot_path)],
                timeout=10
            )

            if screenshot_path.exists() and self.client and self.device_id:
                # Upload to Supabase Storage
                url = self.client.upload_file(
                    bucket="screenshots",
                    file_path=str(screenshot_path),
                    device_id=self.device_id
                )
                log(f"Screenshot captured for: {reason}")
                return url

        except Exception as e:
            log(f"Error capturing screenshot: {e}")

        return None

    def process_file_event(self, file_path: str, access_type: str, destination: str = None):
        """Process a file event and check against rules"""
        path = Path(file_path)

        # Get file info
        try:
            file_size = path.stat().st_size if path.exists() else None
        except:
            file_size = None

        # Get active app
        app_name, bundle_id = self._get_active_app()

        # Create event
        import socket
        event = FileAccessEvent(
            file_path=file_path,
            file_name=path.name,
            file_extension=path.suffix,
            access_type=access_type,
            app_name=app_name,
            bundle_id=bundle_id,
            destination=destination,
            file_size=file_size,
            user_name=os.getenv("USER", "unknown"),
            hostname=socket.gethostname()
        )

        # Check against rules
        for rule in self.rules:
            if rule.matches(file_path):
                event.matched_rule = rule
                log(f"ALERT: {rule.name} triggered by {file_path} ({access_type})")
                self._handle_alert(event, rule)
                break

        # Queue event for batch upload
        with self.queue_lock:
            self.event_queue.append(event)

    def _handle_alert(self, event: FileAccessEvent, rule: FileRule):
        """Handle a triggered alert"""
        screenshot_url = None

        # Capture screenshot if required
        if rule.action in ['alert_screenshot']:
            screenshot_url = self._capture_screenshot(f"{rule.name}: {event.file_name}")

        # Send alert to Supabase
        if self.client and self.device_id:
            try:
                # Create security alert
                alert_data = {
                    "device_id": self.device_id,
                    "alert_type": "sensitive_file_access",
                    "severity": rule.severity,
                    "title": f"{rule.name}: {event.file_name}",
                    "description": f"Sensitive file accessed: {event.file_path}\nAccess type: {event.access_type}\nApp: {event.app_name or 'Unknown'}",
                    "metadata": {
                        "file_path": event.file_path,
                        "file_name": event.file_name,
                        "access_type": event.access_type,
                        "app_name": event.app_name,
                        "bundle_id": event.bundle_id,
                        "rule_id": rule.id,
                        "rule_name": rule.name
                    },
                    "acknowledged": False
                }

                self.client._request(
                    "POST",
                    "/rest/v1/security_alerts",
                    alert_data,
                    use_service_key=True
                )
                log(f"Alert sent to Supabase: {rule.name}")

                # Send FCM push notification for critical/high alerts
                if rule.severity in ['critical', 'high']:
                    self._send_push_notification(event, rule)

            except Exception as e:
                log(f"Error sending alert: {e}")

    def _send_push_notification(self, event: FileAccessEvent, rule: FileRule):
        """Send push notification for critical alerts"""
        try:
            from fcm_sender import send_fcm_notification
            send_fcm_notification(
                device_id=self.device_id,
                title=f"File Alert: {rule.name}",
                body=f"{event.file_name} accessed by {event.app_name or 'Unknown'}",
                data={
                    "type": "file_alert",
                    "severity": rule.severity,
                    "file_path": event.file_path
                }
            )
        except Exception as e:
            log(f"Error sending push notification: {e}")

    def _sync_events(self):
        """Sync queued events to Supabase"""
        if not self.client or not self.device_id:
            return

        with self.queue_lock:
            if not self.event_queue:
                return
            events_to_sync = self.event_queue[:50]  # Batch of 50
            self.event_queue = self.event_queue[50:]

        for event in events_to_sync:
            try:
                event_data = {
                    "device_id": self.device_id,
                    "file_path": event.file_path,
                    "file_name": event.file_name,
                    "file_extension": event.file_extension,
                    "file_size_bytes": event.file_size,
                    "access_type": event.access_type,
                    "destination": event.destination,
                    "app_name": event.app_name,
                    "bundle_id": event.bundle_id,
                    "user_name": event.user_name,
                    "hostname": event.hostname,
                    "triggered_alert": event.matched_rule is not None,
                    "alert_severity": event.matched_rule.severity if event.matched_rule else None,
                    "rule_id": event.matched_rule.id if event.matched_rule and not event.matched_rule.id.startswith('default') else None
                }

                self.client._request(
                    "POST",
                    "/rest/v1/file_access_events",
                    event_data,
                    use_service_key=True
                )

            except Exception as e:
                log(f"Error syncing event: {e}")

    def _sync_loop(self):
        """Background thread for syncing events"""
        while self.running:
            time.sleep(30)  # Sync every 30 seconds
            try:
                self._sync_events()
            except Exception as e:
                log(f"Error in sync loop: {e}")

    def _reload_rules_loop(self):
        """Background thread for reloading rules"""
        while self.running:
            time.sleep(300)  # Reload rules every 5 minutes
            try:
                self._load_rules()
            except Exception as e:
                log(f"Error reloading rules: {e}")

    def run(self):
        """Start file monitoring"""
        if not WATCHDOG_AVAILABLE:
            log("ERROR: watchdog package not installed. Install with: pip3 install watchdog")
            return

        log("=" * 60)
        log("FILE MONITOR STARTED")
        log(f"Monitoring rules: {len(self.rules)}")
        log("=" * 60)

        self.running = True

        # Paths to monitor
        monitor_paths = [
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home() / "Dropbox",
            Path.home() / "OneDrive",
            Path.home() / "Google Drive",
        ]

        # Filter to existing paths
        monitor_paths = [p for p in monitor_paths if p.exists()]

        # Start watchdog observer
        self.observer = Observer()
        handler = SensitiveFileHandler(self)

        for path in monitor_paths:
            log(f"Watching: {path}")
            self.observer.schedule(handler, str(path), recursive=True)

        self.observer.start()

        # Start background threads
        sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        sync_thread.start()

        rules_thread = threading.Thread(target=self._reload_rules_loop, daemon=True)
        rules_thread.start()

        log("File monitoring active. Press Ctrl+C to stop.")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            log("Stopping file monitor...")
            self.running = False
            self.observer.stop()

        self.observer.join()
        log("File monitor stopped.")


def main():
    monitor = FileMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
