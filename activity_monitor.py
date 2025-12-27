#!/usr/bin/env python3
"""
Activity Monitor for Login Monitor PRO
Tracks system activity to detect unauthorized access and data theft.

Features:
- File access logging (opened, modified, copied, deleted)
- USB device monitoring (connections and file transfers)
- Application usage tracking
- Browser history capture
- Periodic screenshots
- Clipboard activity (copy/paste events)
"""

import os
import sys
import json
import time
import sqlite3
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Configuration
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
ACTIVITY_DIR = SCRIPT_DIR / "activity_logs"
SCREENSHOTS_DIR = SCRIPT_DIR / "activity_screenshots"

# Ensure directories exist
ACTIVITY_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def log(message, level="INFO"):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}", flush=True)


def load_config():
    """Load configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


class ActivityLog:
    """Manages activity logging to JSON files"""

    def __init__(self):
        self.today_file = ACTIVITY_DIR / f"activity_{datetime.now().strftime('%Y%m%d')}.json"
        self.activities = self._load_today()

    def _load_today(self):
        """Load today's activity log"""
        if self.today_file.exists():
            try:
                with open(self.today_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"date": datetime.now().strftime('%Y-%m-%d'), "events": []}

    def add(self, event_type, data):
        """Add an activity event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.activities["events"].append(event)
        self._save()
        return event

    def _save(self):
        """Save activity log"""
        with open(self.today_file, 'w') as f:
            json.dump(self.activities, f, indent=2)

    def get_recent(self, count=50):
        """Get recent activities"""
        return self.activities["events"][-count:]

    def get_by_type(self, event_type, count=20):
        """Get activities by type"""
        filtered = [e for e in self.activities["events"] if e["type"] == event_type]
        return filtered[-count:]


class FileAccessMonitor:
    """
    Monitors file access using macOS FSEvents or periodic scanning.
    Tracks: opens, modifications, deletions, copies to external drives.
    """

    def __init__(self, activity_log):
        self.activity_log = activity_log
        self.watched_dirs = [
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home() / "Pictures",
        ]
        self.file_snapshots = {}
        self.last_scan = None

    def take_snapshot(self):
        """Take snapshot of watched directories"""
        snapshot = {}
        for watch_dir in self.watched_dirs:
            if watch_dir.exists():
                for file_path in watch_dir.rglob("*"):
                    if file_path.is_file():
                        try:
                            stat = file_path.stat()
                            snapshot[str(file_path)] = {
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                                "accessed": stat.st_atime
                            }
                        except:
                            pass
        return snapshot

    def detect_changes(self):
        """Detect file changes since last snapshot"""
        if not self.file_snapshots:
            self.file_snapshots = self.take_snapshot()
            self.last_scan = datetime.now()
            return []

        changes = []
        new_snapshot = self.take_snapshot()

        # Check for new and modified files
        for path, info in new_snapshot.items():
            if path not in self.file_snapshots:
                changes.append({
                    "action": "created",
                    "path": path,
                    "size": info["size"]
                })
            elif info["modified"] > self.file_snapshots[path]["modified"]:
                changes.append({
                    "action": "modified",
                    "path": path,
                    "size": info["size"]
                })
            elif info["accessed"] > self.file_snapshots[path]["accessed"]:
                changes.append({
                    "action": "accessed",
                    "path": path,
                    "size": info["size"]
                })

        # Check for deleted files
        for path in self.file_snapshots:
            if path not in new_snapshot:
                changes.append({
                    "action": "deleted",
                    "path": path
                })

        self.file_snapshots = new_snapshot
        self.last_scan = datetime.now()

        # Log changes
        for change in changes:
            self.activity_log.add("file_access", change)

        return changes

    def get_recent_files(self, minutes=30):
        """Get recently accessed files using mdfind"""
        try:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

            # Use mdfind to find recently modified files
            result = subprocess.run([
                "mdfind", "-onlyin", str(Path.home()),
                f"kMDItemFSContentChangeDate >= $time.iso({cutoff_str})"
            ], capture_output=True, text=True, timeout=30)

            files = []
            for line in result.stdout.strip().split('\n'):
                if line and Path(line).exists():
                    try:
                        stat = Path(line).stat()
                        files.append({
                            "path": line,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "size": stat.st_size
                        })
                    except:
                        pass

            return files[:50]  # Limit to 50
        except Exception as e:
            log(f"Error getting recent files: {e}", "ERROR")
            return []


class USBMonitor:
    """
    Monitors USB device connections and potential file transfers.
    """

    def __init__(self, activity_log):
        self.activity_log = activity_log
        self.known_devices = set()
        self.volume_snapshots = {}

    def get_connected_volumes(self):
        """Get list of mounted volumes"""
        volumes = []
        volumes_path = Path("/Volumes")

        for vol in volumes_path.iterdir():
            if vol.name != "Macintosh HD" and vol.is_dir():
                try:
                    # Get volume info
                    result = subprocess.run(
                        ["diskutil", "info", str(vol)],
                        capture_output=True, text=True, timeout=5
                    )

                    vol_info = {
                        "name": vol.name,
                        "path": str(vol),
                        "is_external": "External" in result.stdout or "USB" in result.stdout
                    }

                    # Get volume size
                    for line in result.stdout.split('\n'):
                        if "Total Size:" in line:
                            vol_info["size"] = line.split(":")[-1].strip()

                    volumes.append(vol_info)
                except:
                    volumes.append({"name": vol.name, "path": str(vol), "is_external": True})

        return volumes

    def check_new_devices(self):
        """Check for newly connected USB devices"""
        current_volumes = {v["name"] for v in self.get_connected_volumes()}

        new_devices = current_volumes - self.known_devices
        removed_devices = self.known_devices - current_volumes

        events = []

        for device in new_devices:
            event = {
                "action": "connected",
                "device": device,
                "path": f"/Volumes/{device}"
            }
            events.append(event)
            self.activity_log.add("usb_device", event)
            log(f"USB connected: {device}")

        for device in removed_devices:
            event = {
                "action": "disconnected",
                "device": device
            }
            events.append(event)
            self.activity_log.add("usb_device", event)
            log(f"USB disconnected: {device}")

        self.known_devices = current_volumes
        return events

    def monitor_volume_changes(self, volume_path):
        """Monitor file changes on a specific volume"""
        vol_path = Path(volume_path)
        if not vol_path.exists():
            return []

        current_files = {}
        for f in vol_path.rglob("*"):
            if f.is_file():
                try:
                    current_files[str(f)] = f.stat().st_mtime
                except:
                    pass

        if volume_path not in self.volume_snapshots:
            self.volume_snapshots[volume_path] = current_files
            return []

        # Check for new files (potential copies TO USB)
        new_files = []
        for path, mtime in current_files.items():
            if path not in self.volume_snapshots[volume_path]:
                new_files.append({
                    "action": "file_copied_to_usb",
                    "volume": vol_path.name,
                    "file": path,
                    "time": datetime.fromtimestamp(mtime).isoformat()
                })

        self.volume_snapshots[volume_path] = current_files

        for event in new_files:
            self.activity_log.add("usb_transfer", event)

        return new_files


class AppUsageMonitor:
    """
    Monitors application usage.
    """

    def __init__(self, activity_log):
        self.activity_log = activity_log
        self.last_active_app = None
        self.app_usage = defaultdict(int)  # app -> seconds

    def get_active_app(self):
        """Get currently active application"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                return frontApp
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except:
            return None

    def get_running_apps(self):
        """Get list of running applications"""
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of every process whose background only is false'],
                capture_output=True, text=True, timeout=5
            )
            apps = result.stdout.strip().split(", ")
            return [a.strip() for a in apps if a.strip()]
        except:
            return []

    def track_app_switch(self):
        """Track application switches"""
        current_app = self.get_active_app()

        if current_app and current_app != self.last_active_app:
            event = {
                "action": "app_switch",
                "from_app": self.last_active_app,
                "to_app": current_app
            }
            self.activity_log.add("app_usage", event)
            self.last_active_app = current_app
            return event

        return None

    def get_app_launch_history(self):
        """Get recent app launches from system logs"""
        try:
            # Get apps launched in last hour
            result = subprocess.run([
                "log", "show", "--predicate",
                'subsystem == "com.apple.launchservices"',
                "--last", "1h", "--style", "compact"
            ], capture_output=True, text=True, timeout=30)

            launches = []
            for line in result.stdout.split('\n'):
                if "LSOpen" in line or "launch" in line.lower():
                    launches.append(line[:100])  # Truncate

            return launches[-20:]  # Last 20
        except:
            return []


class BrowserHistoryMonitor:
    """
    Captures browser history from Safari and Chrome.
    """

    def __init__(self, activity_log):
        self.activity_log = activity_log
        self.last_check = {}

    def get_safari_history(self, limit=50):
        """Get recent Safari history"""
        history = []
        db_path = Path.home() / "Library/Safari/History.db"

        if not db_path.exists():
            return history

        try:
            # Copy database to avoid locking issues
            temp_db = "/tmp/safari_history_temp.db"
            subprocess.run(["cp", str(db_path), temp_db], capture_output=True)

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    datetime(visit_time + 978307200, 'unixepoch', 'localtime') as visit_date,
                    url,
                    title
                FROM history_visits
                JOIN history_items ON history_visits.history_item = history_items.id
                ORDER BY visit_time DESC
                LIMIT ?
            """, (limit,))

            for row in cursor.fetchall():
                history.append({
                    "browser": "Safari",
                    "time": row[0],
                    "url": row[1],
                    "title": row[2] or "No title"
                })

            conn.close()
            os.remove(temp_db)
        except Exception as e:
            log(f"Error reading Safari history: {e}", "ERROR")

        return history

    def get_chrome_history(self, limit=50):
        """Get recent Chrome history"""
        history = []
        db_path = Path.home() / "Library/Application Support/Google/Chrome/Default/History"

        if not db_path.exists():
            return history

        try:
            # Copy database to avoid locking issues
            temp_db = "/tmp/chrome_history_temp.db"
            subprocess.run(["cp", str(db_path), temp_db], capture_output=True)

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as visit_date,
                    url,
                    title
                FROM urls
                ORDER BY last_visit_time DESC
                LIMIT ?
            """, (limit,))

            for row in cursor.fetchall():
                history.append({
                    "browser": "Chrome",
                    "time": row[0],
                    "url": row[1],
                    "title": row[2] or "No title"
                })

            conn.close()
            os.remove(temp_db)
        except Exception as e:
            log(f"Error reading Chrome history: {e}", "ERROR")

        return history

    def get_all_history(self, limit=30):
        """Get combined browser history"""
        safari = self.get_safari_history(limit)
        chrome = self.get_chrome_history(limit)

        # Combine and sort by time
        all_history = safari + chrome
        all_history.sort(key=lambda x: x.get("time", ""), reverse=True)

        return all_history[:limit]

    def capture_current_history(self):
        """Capture and log current browser history"""
        history = self.get_all_history(20)

        for entry in history:
            self.activity_log.add("browser_history", entry)

        return history


class ScreenshotMonitor:
    """
    Takes periodic screenshots during activity.
    """

    def __init__(self, activity_log):
        self.activity_log = activity_log
        self.screenshot_interval = 60  # seconds
        self.last_screenshot = None

    def take_screenshot(self, reason="periodic"):
        """Take a screenshot using multiple methods"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshot_{timestamp}.png"
            filepath = SCREENSHOTS_DIR / filename

            # Method 1: Try screencapture command
            result = subprocess.run([
                "screencapture", "-x", "-t", "png", str(filepath)
            ], capture_output=True, timeout=10)

            # Method 2: Use keyboard shortcut (Cmd+Shift+3) via AppleScript
            if not filepath.exists() or filepath.stat().st_size == 0:
                # Simulate Cmd+Shift+3 to take screenshot to Desktop
                shortcut_script = '''
                tell application "System Events"
                    keystroke "3" using {command down, shift down}
                end tell
                delay 1
                '''
                subprocess.run(["osascript", "-e", shortcut_script], capture_output=True, timeout=10)

                # Find the latest screenshot on Desktop
                import glob
                desktop = os.path.expanduser("~/Desktop")
                screenshots = glob.glob(f"{desktop}/Screenshot*.png") + glob.glob(f"{desktop}/Screen Shot*.png")
                if screenshots:
                    latest = max(screenshots, key=os.path.getctime)
                    # Move it to our folder
                    import shutil
                    shutil.move(latest, str(filepath))
                    log(f"Screenshot via keyboard shortcut: {filename}")

            # Method 3: Try screencapture with user interaction flag
            if not filepath.exists() or filepath.stat().st_size == 0:
                result = subprocess.run([
                    "screencapture", "-i", "-x", str(filepath)
                ], capture_output=True, timeout=15)

            if filepath.exists() and filepath.stat().st_size > 0:
                self.last_screenshot = filepath

                event = {
                    "action": "screenshot",
                    "file": str(filepath),
                    "reason": reason,
                    "size": filepath.stat().st_size
                }
                self.activity_log.add("screenshot", event)
                log(f"Screenshot saved: {filename}")
                return str(filepath)
            else:
                log("Screenshot failed - Screen Recording permission required. Add Terminal to System Settings > Privacy > Screen Recording", "ERROR")
        except Exception as e:
            log(f"Screenshot error: {e}", "ERROR")

        return None

    def get_recent_screenshots(self, count=10):
        """Get list of recent screenshots"""
        screenshots = sorted(SCREENSHOTS_DIR.glob("*.jpg"), reverse=True)
        return [str(s) for s in screenshots[:count]]

    def cleanup_old_screenshots(self, days=7):
        """Delete screenshots older than X days"""
        cutoff = datetime.now() - timedelta(days=days)

        for screenshot in SCREENSHOTS_DIR.glob("*.jpg"):
            try:
                if datetime.fromtimestamp(screenshot.stat().st_mtime) < cutoff:
                    screenshot.unlink()
                    log(f"Deleted old screenshot: {screenshot.name}")
            except:
                pass


class ClipboardMonitor:
    """
    Monitors clipboard activity (copy/paste events).
    Logs WHEN clipboard was used, not WHAT was copied (for privacy).
    """

    def __init__(self, activity_log):
        self.activity_log = activity_log
        self.last_change_count = 0

    def get_clipboard_change_count(self):
        """Get clipboard change count"""
        try:
            script = '''
            use framework "AppKit"
            return (current application's NSPasteboard's generalPasteboard()'s changeCount()) as integer
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip())
        except:
            return 0

    def check_clipboard_activity(self):
        """Check if clipboard was used"""
        current_count = self.get_clipboard_change_count()

        if current_count > self.last_change_count:
            events_count = current_count - self.last_change_count

            # Get clipboard content type (not content itself)
            content_type = self.get_clipboard_type()

            event = {
                "action": "clipboard_used",
                "changes": events_count,
                "content_type": content_type
            }
            self.activity_log.add("clipboard", event)
            self.last_change_count = current_count
            return event

        return None

    def get_clipboard_type(self):
        """Get type of clipboard content (not the content itself)"""
        try:
            script = '''
            use framework "AppKit"
            set pb to current application's NSPasteboard's generalPasteboard()
            set types to pb's types() as list
            return types as text
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )

            types = result.stdout.strip().lower()

            if "png" in types or "image" in types or "tiff" in types:
                return "image"
            elif "file" in types:
                return "file"
            elif "rtf" in types or "html" in types:
                return "rich_text"
            elif "string" in types or "text" in types:
                return "text"
            else:
                return "unknown"
        except:
            return "unknown"


class ActivityMonitor:
    """
    Main activity monitor that coordinates all sub-monitors.
    """

    def __init__(self):
        self.activity_log = ActivityLog()
        self.file_monitor = FileAccessMonitor(self.activity_log)
        self.usb_monitor = USBMonitor(self.activity_log)
        self.app_monitor = AppUsageMonitor(self.activity_log)
        self.browser_monitor = BrowserHistoryMonitor(self.activity_log)
        self.screenshot_monitor = ScreenshotMonitor(self.activity_log)
        self.clipboard_monitor = ClipboardMonitor(self.activity_log)

        self.running = False
        self.config = load_config()

    def start_monitoring(self):
        """Start all monitors"""
        self.running = True

        log("Activity Monitor started")
        log(f"Monitoring directories: {[str(d) for d in self.file_monitor.watched_dirs]}")

        # Take initial snapshot
        self.file_monitor.take_snapshot()
        self.usb_monitor.check_new_devices()

        # Take initial screenshot
        self.screenshot_monitor.take_screenshot("session_start")

        # Main monitoring loop
        screenshot_counter = 0

        while self.running:
            try:
                # Check file changes (every 30 seconds)
                self.file_monitor.detect_changes()

                # Check USB devices (every 5 seconds)
                self.usb_monitor.check_new_devices()

                # Monitor external volumes for file copies
                for vol in self.usb_monitor.get_connected_volumes():
                    if vol.get("is_external"):
                        self.usb_monitor.monitor_volume_changes(vol["path"])

                # Track app switches
                self.app_monitor.track_app_switch()

                # Check clipboard
                self.clipboard_monitor.check_clipboard_activity()

                # Periodic screenshot (every 5 minutes)
                screenshot_counter += 1
                if screenshot_counter >= 60:  # 60 * 5 seconds = 5 minutes
                    self.screenshot_monitor.take_screenshot("periodic")
                    screenshot_counter = 0

                time.sleep(5)  # Main loop interval

            except KeyboardInterrupt:
                log("Activity Monitor stopped by user")
                break
            except Exception as e:
                log(f"Monitor error: {e}", "ERROR")
                time.sleep(5)

    def stop_monitoring(self):
        """Stop all monitors"""
        self.running = False
        self.screenshot_monitor.take_screenshot("session_end")
        log("Activity Monitor stopped")

    def get_activity_summary(self, hours=1):
        """Get summary of recent activity"""
        events = self.activity_log.get_recent(200)
        cutoff = datetime.now() - timedelta(hours=hours)

        recent = [e for e in events if datetime.fromisoformat(e["timestamp"]) > cutoff]

        summary = {
            "period": f"Last {hours} hour(s)",
            "total_events": len(recent),
            "file_access": len([e for e in recent if e["type"] == "file_access"]),
            "usb_events": len([e for e in recent if e["type"] in ["usb_device", "usb_transfer"]]),
            "app_switches": len([e for e in recent if e["type"] == "app_usage"]),
            "clipboard_uses": len([e for e in recent if e["type"] == "clipboard"]),
            "screenshots": len([e for e in recent if e["type"] == "screenshot"]),
            "events": recent[-20:]  # Last 20 events
        }

        return summary

    def get_suspicious_activity(self):
        """Identify potentially suspicious activities"""
        events = self.activity_log.get_recent(500)
        suspicious = []

        for event in events:
            data = event.get("data", {})

            # Large file copied to USB
            if event["type"] == "usb_transfer":
                suspicious.append({
                    "reason": "File copied to external drive",
                    "details": data.get("file", "Unknown"),
                    "time": event["timestamp"]
                })

            # Sensitive directories accessed
            if event["type"] == "file_access":
                path = data.get("path", "").lower()
                if any(s in path for s in ["password", "secret", "key", "credential", "token", "ssh", ".env"]):
                    suspicious.append({
                        "reason": "Sensitive file accessed",
                        "details": data.get("path", "Unknown"),
                        "time": event["timestamp"]
                    })

            # Multiple files deleted
            if event["type"] == "file_access" and data.get("action") == "deleted":
                suspicious.append({
                    "reason": "File deleted",
                    "details": data.get("path", "Unknown"),
                    "time": event["timestamp"]
                })

        return suspicious


def trigger_on_event():
    """Called when a login/unlock event occurs - captures activity snapshot"""
    monitor = ActivityMonitor()

    log("=" * 60)
    log("ACTIVITY CAPTURE - Triggered by login/unlock event")
    log("=" * 60)

    # Take screenshot
    screenshot = monitor.screenshot_monitor.take_screenshot("login_event")

    # Capture browser history
    history = monitor.browser_monitor.capture_current_history()

    # Get recent files
    recent_files = monitor.file_monitor.get_recent_files(minutes=60)

    # Get running apps
    running_apps = monitor.app_monitor.get_running_apps()

    # Check USB devices
    usb_devices = monitor.usb_monitor.get_connected_volumes()

    report = {
        "timestamp": datetime.now().isoformat(),
        "screenshot": screenshot,
        "browser_history_count": len(history),
        "recent_files_count": len(recent_files),
        "running_apps": running_apps,
        "usb_devices": [v["name"] for v in usb_devices if v.get("is_external")],
        "recent_files": recent_files[:10],  # Top 10
        "browser_history": history[:10]  # Top 10
    }

    # Save report
    report_file = ACTIVITY_DIR / f"event_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    log(f"Activity report saved: {report_file}")

    return report


def main():
    """Main entry point"""
    print("=" * 60)
    print("LOGIN MONITOR PRO - Activity Monitor")
    print("=" * 60)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "capture":
            # One-time capture (called on login events)
            report = trigger_on_event()
            print(f"\nCaptured:")
            print(f"  - Screenshot: {report.get('screenshot', 'None')}")
            print(f"  - Browser history entries: {report.get('browser_history_count', 0)}")
            print(f"  - Recent files: {report.get('recent_files_count', 0)}")
            print(f"  - Running apps: {len(report.get('running_apps', []))}")
            print(f"  - USB devices: {report.get('usb_devices', [])}")

        elif command == "summary":
            # Show summary
            monitor = ActivityMonitor()
            summary = monitor.get_activity_summary(hours=1)
            print(f"\nActivity Summary ({summary['period']}):")
            print(f"  Total events: {summary['total_events']}")
            print(f"  File accesses: {summary['file_access']}")
            print(f"  USB events: {summary['usb_events']}")
            print(f"  App switches: {summary['app_switches']}")
            print(f"  Clipboard uses: {summary['clipboard_uses']}")

        elif command == "suspicious":
            # Show suspicious activity
            monitor = ActivityMonitor()
            suspicious = monitor.get_suspicious_activity()
            print(f"\nSuspicious Activities: {len(suspicious)}")
            for s in suspicious[:10]:
                print(f"  [{s['time']}] {s['reason']}: {s['details'][:50]}")

        elif command == "history":
            # Show browser history
            monitor = ActivityMonitor()
            history = monitor.browser_monitor.get_all_history(20)
            print(f"\nRecent Browser History:")
            for h in history:
                print(f"  [{h['browser']}] {h['time']}: {h['title'][:40]}")
                print(f"       {h['url'][:60]}...")

        elif command == "daemon":
            # Run as continuous daemon
            monitor = ActivityMonitor()
            monitor.start_monitoring()

        else:
            print(f"Unknown command: {command}")
            print("Usage: python3 activity_monitor.py [capture|summary|suspicious|history|daemon]")
    else:
        # Default: one-time capture
        trigger_on_event()


if __name__ == "__main__":
    main()
