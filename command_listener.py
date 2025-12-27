#!/usr/bin/env python3
"""
Command Listener for Login Monitor PRO
Polls Supabase for pending commands and executes them.
Replaces telegram_bot.py for the Supabase + Flutter architecture.
"""

import json
import os
import subprocess
import sys
import time
import socket
import platform
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient


def is_frozen():
    """Check if running as PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """Get base directory for data files"""
    if is_frozen():
        return Path.home() / ".login-monitor"
    return Path(__file__).parent


def get_script_dir():
    """Get directory containing scripts/executables"""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent


# Configuration paths
BASE_DIR = get_base_dir()
SCRIPT_DIR = get_script_dir()
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = Path("/tmp/loginmonitor-commands.log")


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg, flush=True)

    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


class CommandListener:
    """Listens for and executes commands from Supabase"""

    def __init__(self):
        self.config = self._load_config()
        self.client = None
        self.device_id = None
        self.poll_interval = 5  # seconds

        # Initialize Supabase client
        supabase_config = self.config.get("supabase", {})
        if supabase_config.get("url") and supabase_config.get("anon_key"):
            self.client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config["anon_key"],
                service_key=supabase_config.get("service_key", supabase_config["anon_key"])
            )
            self.device_id = supabase_config.get("device_id")

    def _load_config(self) -> dict:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    return json.load(f)
            except Exception as e:
                log(f"Error loading config: {e}")
        return {}

    def _save_config(self):
        """Save configuration to file"""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            log(f"Error saving config: {e}")

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    def cmd_photo(self, args: dict) -> dict:
        """Take a photo with the camera"""
        try:
            count = args.get("count", 1)
            photos = []

            log(f"[INFO] Capturing {count} photos...")

            # Find imagesnap
            imagesnap = None
            for path in ["/opt/homebrew/bin/imagesnap", "/usr/local/bin/imagesnap"]:
                if os.path.exists(path):
                    imagesnap = path
                    break

            if not imagesnap:
                log("[ERROR] imagesnap not found")
                return {"success": False, "error": "imagesnap not installed"}

            for i in range(count):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                photo_path = BASE_DIR / "captured_images" / f"capture_{timestamp}_{i+1}_{os.urandom(3).hex()}.jpg"
                photo_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    # Use longer warmup (2s) and timeout (30s) for camera initialization
                    result = subprocess.run(
                        [imagesnap, "-w", "2.0", str(photo_path)],
                        capture_output=True, text=True, timeout=30
                    )
                    if photo_path.exists() and photo_path.stat().st_size > 0:
                        photos.append(str(photo_path))
                        log(f"[INFO] Photo {i+1}/{count} captured")
                    else:
                        log(f"[WARN] Photo {i+1} not saved or empty")
                except subprocess.TimeoutExpired:
                    log(f"[ERROR] Photo {i+1} capture timeout")
                except Exception as e:
                    log(f"[ERROR] Photo {i+1} error: {e}")

                if i < count - 1:
                    time.sleep(1)

            # Upload photos
            photo_urls = []
            if photos and self.client and self.device_id:
                for photo in photos:
                    url = self.client.upload_file(self.device_id, photo, "photos")
                    if url:
                        photo_urls.append(url)
                        log(f"[INFO] Photo uploaded")

            return {
                "success": len(photos) > 0,
                "photo_count": len(photos),
                "photo_urls": photo_urls
            }
        except Exception as e:
            log(f"[ERROR] Photo command failed: {e}")
            return {"success": False, "error": str(e)}

    def cmd_location(self, args: dict) -> dict:
        """Get current GPS location"""
        try:
            from pro_monitor import SystemInfo
            location = SystemInfo.get_location()
            return {"success": True, "location": location}
        except Exception as e:
            # Fallback to IP-based location
            try:
                import urllib.request
                with urllib.request.urlopen("http://ip-api.com/json/", timeout=10) as r:
                    data = json.loads(r.read().decode())
                    return {
                        "success": True,
                        "location": {
                            "latitude": data.get("lat"),
                            "longitude": data.get("lon"),
                            "city": data.get("city"),
                            "region": data.get("regionName"),
                            "country": data.get("country"),
                            "source": "IP Geolocation"
                        }
                    }
            except:
                return {"success": False, "error": str(e)}

    def cmd_audio(self, args: dict) -> dict:
        """Record audio"""
        try:
            duration = args.get("duration", 10)

            from pro_monitor import Capture
            audio_path = Capture.record_audio(duration=duration)

            # Upload audio
            audio_url = None
            if audio_path and self.client and self.device_id:
                audio_url = self.client.upload_file(self.device_id, audio_path, "audio")

            return {
                "success": bool(audio_path),
                "duration": duration,
                "audio_url": audio_url
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_status(self, args: dict) -> dict:
        """Get device status"""
        try:
            from pro_monitor import SystemInfo

            return {
                "success": True,
                "status": {
                    "hostname": socket.gethostname(),
                    "user": os.getenv("USER"),
                    "platform": platform.platform(),
                    "local_ip": SystemInfo.get_local_ip(),
                    "public_ip": SystemInfo.get_public_ip(),
                    "battery": SystemInfo.get_battery_status(),
                    "wifi": SystemInfo.get_wifi_info(),
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_battery(self, args: dict) -> dict:
        """Get battery status"""
        try:
            from pro_monitor import SystemInfo
            battery = SystemInfo.get_battery_status()
            return {"success": True, "battery": battery}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_wifi(self, args: dict) -> dict:
        """Get WiFi info"""
        try:
            from pro_monitor import SystemInfo
            wifi = SystemInfo.get_wifi_info()
            return {"success": True, "wifi": wifi}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_ip(self, args: dict) -> dict:
        """Get IP addresses"""
        try:
            from pro_monitor import SystemInfo
            return {
                "success": True,
                "local_ip": SystemInfo.get_local_ip(),
                "public_ip": SystemInfo.get_public_ip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_screenshot(self, args: dict) -> dict:
        """Take a screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = BASE_DIR / "captured_images" / f"screenshot_{timestamp}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            # Method 1: Use screencapture command
            try:
                result = subprocess.run(
                    ["/usr/sbin/screencapture", "-x", str(screenshot_path)],
                    capture_output=True, timeout=15
                )
                if screenshot_path.exists() and screenshot_path.stat().st_size > 50000:
                    log("[INFO] Screenshot captured via screencapture")
            except Exception as e:
                log(f"[WARN] screencapture failed: {e}")

            # Method 2: Fallback to Quartz
            if not screenshot_path.exists() or screenshot_path.stat().st_size < 50000:
                if screenshot_path.exists():
                    screenshot_path.unlink()
                try:
                    import Quartz
                    from Quartz import CGWindowListCreateImage, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
                    from Quartz import CGImageDestinationCreateWithURL, CGImageDestinationAddImage, CGImageDestinationFinalize
                    from CoreFoundation import CFURLCreateWithFileSystemPath, kCFURLPOSIXPathStyle

                    image = CGWindowListCreateImage(
                        Quartz.CGRectInfinite,
                        kCGWindowListOptionOnScreenOnly,
                        kCGNullWindowID,
                        Quartz.kCGWindowImageDefault
                    )

                    if image:
                        url = CFURLCreateWithFileSystemPath(None, str(screenshot_path), kCFURLPOSIXPathStyle, False)
                        dest = CGImageDestinationCreateWithURL(url, "public.png", 1, None)
                        if dest:
                            CGImageDestinationAddImage(dest, image, None)
                            CGImageDestinationFinalize(dest)
                            log("[INFO] Screenshot captured via Quartz")
                except Exception as e:
                    log(f"[WARN] Quartz screenshot failed: {e}")

            # Upload screenshot
            screenshot_url = None
            if screenshot_path.exists() and self.client and self.device_id:
                screenshot_url = self.client.upload_file(self.device_id, str(screenshot_path), "photos")

            # Check if we got a real screenshot
            if not screenshot_path.exists():
                log("[ERROR] Screenshot failed - Screen Recording permission required")
                log("[ERROR] Add Python.app to System Settings > Privacy & Security > Screen Recording")
                log("[ERROR] Then log out and log back in for permission to take effect")
                return {
                    "success": False,
                    "error": "Screen Recording permission required. Add Python.app to Screen Recording in System Settings, then restart Mac."
                }

            return {
                "success": True,
                "screenshot_url": screenshot_url
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_alarm(self, args: dict) -> dict:
        """Play alarm sound"""
        try:
            duration = args.get("duration", 30)
            end_time = time.time() + duration

            while time.time() < end_time:
                subprocess.run(["afplay", "/System/Library/Sounds/Sosumi.aiff"],
                               capture_output=True)
                time.sleep(0.5)

            return {"success": True, "duration": duration}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_lock(self, args: dict) -> dict:
        """Lock the screen"""
        try:
            subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
            return {"success": True, "message": "Screen locked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_message(self, args: dict) -> dict:
        """Show a message dialog"""
        try:
            message = args.get("message", "Alert from Login Monitor")
            title = args.get("title", "Login Monitor PRO")

            script = f'''
            display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK" with icon caution
            '''
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return {"success": True, "message_shown": message}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_activity(self, args: dict) -> dict:
        """Get recent activity"""
        try:
            from activity_monitor import ActivityMonitor
            monitor = ActivityMonitor()
            hours = args.get("hours", 1) if args else 1
            activity = monitor.get_activity_summary(hours=hours)
            return {"success": True, "activity": activity}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_addface(self, args: dict) -> dict:
        """Add a known face"""
        try:
            name = args.get("name", "owner")

            from pro_monitor import Capture, FaceRecognition
            photos = Capture.capture_photos(count=1, delay=0)

            if photos:
                result = FaceRecognition.add_known_face(photos[0], name)
                return {"success": result, "name": name}

            return {"success": False, "error": "Failed to capture photo"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_faces(self, args: dict) -> dict:
        """List known faces"""
        try:
            faces_dir = BASE_DIR / "known_faces"
            if not faces_dir.exists():
                return {"success": True, "faces": []}

            faces = [f.stem for f in faces_dir.glob("*.jpg")]
            return {"success": True, "faces": faces}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # NEW ADVANCED COMMANDS (v3.0)
    # =========================================================================

    def cmd_findme(self, args: dict) -> dict:
        """Find My Mac - Play loud alarm and stream location"""
        try:
            import threading

            duration = args.get("duration", 60)
            log(f"[INFO] Find My Mac activated for {duration} seconds")

            # Set max volume
            subprocess.run(["osascript", "-e", "set volume output volume 100"],
                          capture_output=True)

            # Start location streaming in background
            def stream_location():
                end_time = time.time() + duration
                while time.time() < end_time:
                    try:
                        location_result = self.cmd_location({})
                        if location_result.get("success") and self.client and self.device_id:
                            self.client.send_event(self.device_id, {
                                "event_type": "FindMe",
                                "location": location_result.get("location", {}),
                                "timestamp": datetime.now().isoformat()
                            })
                    except:
                        pass
                    time.sleep(30)  # Send location every 30 seconds

            location_thread = threading.Thread(target=stream_location, daemon=True)
            location_thread.start()

            # Play alarm
            end_time = time.time() + duration
            alarm_sounds = [
                "/System/Library/Sounds/Sosumi.aiff",
                "/System/Library/Sounds/Funk.aiff",
                "/System/Library/Sounds/Glass.aiff"
            ]

            while time.time() < end_time:
                for sound in alarm_sounds:
                    if time.time() >= end_time:
                        break
                    subprocess.run(["afplay", sound], capture_output=True)

            return {"success": True, "duration": duration, "message": "Find My Mac completed"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_stopfind(self, args: dict) -> dict:
        """Stop Find My Mac alarm"""
        try:
            # Kill any running afplay processes
            subprocess.run(["pkill", "-f", "afplay"], capture_output=True)
            return {"success": True, "message": "Find My Mac stopped"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_listusb(self, args: dict) -> dict:
        """List connected USB devices"""
        try:
            from usb_monitor import USBMonitor
            monitor = USBMonitor()
            devices = monitor.list_devices()
            return {"success": True, "devices": devices, "count": len(devices)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_whitelistusb(self, args: dict) -> dict:
        """Add USB device to whitelist"""
        try:
            from usb_monitor import USBMonitor, USBDevice
            monitor = USBMonitor()

            vendor_id = args.get("vendor_id")
            product_id = args.get("product_id")
            name = args.get("name", "Unknown Device")

            if not vendor_id or not product_id:
                return {"success": False, "error": "vendor_id and product_id required"}

            device = USBDevice(vendor_id, product_id, name)
            monitor.add_to_whitelist(device)

            return {"success": True, "message": f"Added {name} to USB whitelist"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_listnetworks(self, args: dict) -> dict:
        """List whitelisted WiFi networks"""
        try:
            from network_monitor import NetworkMonitor
            monitor = NetworkMonitor()
            networks = monitor.list_known_networks()
            current = monitor.get_current_wifi()

            return {
                "success": True,
                "networks": networks,
                "current_network": current.get("ssid") if current else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_whitelistnetwork(self, args: dict) -> dict:
        """Add WiFi network to whitelist"""
        try:
            from network_monitor import NetworkMonitor
            monitor = NetworkMonitor()

            ssid = args.get("ssid")

            if not ssid:
                # Use current network if not specified
                current = monitor.get_current_wifi()
                if current:
                    ssid = current.get("ssid")

            if not ssid:
                return {"success": False, "error": "ssid required or connect to a network"}

            monitor.add_to_whitelist(ssid)
            return {"success": True, "message": f"Added '{ssid}' to WiFi whitelist"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_setgeofence(self, args: dict) -> dict:
        """Create a geofence"""
        try:
            from geofence_monitor import GeofenceMonitor
            monitor = GeofenceMonitor()

            name = args.get("name", "My Location")
            lat = args.get("lat") or args.get("latitude")
            lon = args.get("lon") or args.get("longitude")
            radius = args.get("radius", 500)

            if not lat or not lon:
                # Use current location if not specified
                location_result = self.cmd_location({})
                if location_result.get("success"):
                    loc = location_result.get("location", {})
                    lat = loc.get("latitude")
                    lon = loc.get("longitude")

            if not lat or not lon:
                return {"success": False, "error": "latitude and longitude required"}

            geofence = monitor.add_geofence(name, float(lat), float(lon), int(radius))

            return {
                "success": True,
                "geofence": geofence.to_dict(),
                "message": f"Geofence '{name}' created"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_removegeofence(self, args: dict) -> dict:
        """Remove a geofence"""
        try:
            from geofence_monitor import GeofenceMonitor
            monitor = GeofenceMonitor()

            geofence_id = args.get("id")
            if not geofence_id:
                return {"success": False, "error": "geofence id required"}

            monitor.remove_geofence(geofence_id)
            return {"success": True, "message": "Geofence removed"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_listgeofences(self, args: dict) -> dict:
        """List all geofences"""
        try:
            from geofence_monitor import GeofenceMonitor
            monitor = GeofenceMonitor()
            geofences = monitor.list_geofences()

            return {"success": True, "geofences": geofences, "count": len(geofences)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_generatereport(self, args: dict) -> dict:
        """Generate a security report"""
        try:
            from report_generator import ReportGenerator
            generator = ReportGenerator()

            report_type = args.get("type", "daily")
            summary = generator.generate_report(report_type)
            html_path = generator.generate_html_report(summary)

            return {
                "success": True,
                "report_type": report_type,
                "total_events": summary.get("total_events", 0),
                "security_alerts": len(summary.get("security_alerts", [])),
                "html_path": html_path
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_backup(self, args: dict) -> dict:
        """Create a manual backup"""
        try:
            from threat_backup import ThreatBackup
            backup = ThreatBackup()

            result = backup.create_backup(trigger_event="Manual")
            return result if result else {"success": False, "error": "Backup failed"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_armmotion(self, args: dict) -> dict:
        """Arm or disarm motion detection"""
        try:
            from motion_detector import MotionDetector
            detector = MotionDetector()

            enabled = args.get("enabled", True)
            detector.arm(enabled)

            return {
                "success": True,
                "motion_armed": enabled,
                "message": f"Motion detection {'armed' if enabled else 'disarmed'}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_appusage(self, args: dict) -> dict:
        """Get app usage summary"""
        try:
            from app_tracker import AppTracker
            tracker = AppTracker()

            hours = args.get("hours", 24)
            summary = tracker.get_usage_summary(hours=hours)

            return {"success": True, "usage": summary}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_listreports(self, args: dict) -> dict:
        """List all generated reports"""
        try:
            from report_generator import ReportGenerator
            generator = ReportGenerator()
            reports = generator.list_reports()

            return {"success": True, "reports": reports, "count": len(reports)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_listbackups(self, args: dict) -> dict:
        """List all local backups"""
        try:
            from threat_backup import ThreatBackup
            backup = ThreatBackup()
            backups = backup.list_backups()

            return {"success": True, "backups": backups, "count": len(backups)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # MAIN LOOP
    # =========================================================================

    def execute_command(self, command: dict):
        """Execute a single command"""
        cmd_name = command.get("command", "").lower()
        args = command.get("args", {})
        cmd_id = command.get("id")

        log(f"Executing command: {cmd_name} (args: {args})")

        # Mark as executing
        if self.client and cmd_id:
            self.client.update_command_status(cmd_id, "executing")

        # Command handlers
        handlers = {
            # Original commands
            "photo": self.cmd_photo,
            "location": self.cmd_location,
            "audio": self.cmd_audio,
            "status": self.cmd_status,
            "battery": self.cmd_battery,
            "wifi": self.cmd_wifi,
            "ip": self.cmd_ip,
            "screenshot": self.cmd_screenshot,
            "alarm": self.cmd_alarm,
            "lock": self.cmd_lock,
            "message": self.cmd_message,
            "activity": self.cmd_activity,
            "addface": self.cmd_addface,
            "faces": self.cmd_faces,
            # New v3.0 commands
            "findme": self.cmd_findme,
            "stopfind": self.cmd_stopfind,
            "listusb": self.cmd_listusb,
            "whitelistusb": self.cmd_whitelistusb,
            "listnetworks": self.cmd_listnetworks,
            "whitelistnetwork": self.cmd_whitelistnetwork,
            "setgeofence": self.cmd_setgeofence,
            "removegeofence": self.cmd_removegeofence,
            "listgeofences": self.cmd_listgeofences,
            "generatereport": self.cmd_generatereport,
            "backup": self.cmd_backup,
            "armmotion": self.cmd_armmotion,
            "appusage": self.cmd_appusage,
            "listreports": self.cmd_listreports,
            "listbackups": self.cmd_listbackups,
        }

        handler = handlers.get(cmd_name)
        if handler:
            result = handler(args)
        else:
            result = {"success": False, "error": f"Unknown command: {cmd_name}"}

        log(f"Command result: {result.get('success', False)}")

        # Update command status
        if self.client and cmd_id:
            status = "completed" if result.get("success") else "failed"
            result_url = result.pop("photo_urls", [None])[0] if "photo_urls" in result else None
            if not result_url:
                result_url = result.pop("audio_url", None)
            if not result_url:
                result_url = result.pop("screenshot_url", None)

            self.client.update_command_status(cmd_id, status, result, result_url)

    def run(self):
        """Main polling loop"""
        log("=" * 60)
        log("LOGIN MONITOR - COMMAND LISTENER")
        log("=" * 60)

        if not self.client:
            log("ERROR: Supabase not configured!")
            log("Please run Setup to configure Supabase connection.")
            return

        if not self.device_id:
            log("ERROR: Device not registered!")
            log("Please run Setup to register this device.")
            return

        log(f"Device ID: {self.device_id}")
        log(f"Poll interval: {self.poll_interval} seconds")
        log("-" * 60)
        log("Listening for commands...")

        while True:
            try:
                # Update device status (heartbeat)
                self.client.update_device_status(self.device_id)

                # Get pending commands
                commands = self.client.get_pending_commands(self.device_id)

                for cmd in commands:
                    self.execute_command(cmd)

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                log("Command listener stopped by user")
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(self.poll_interval)


def main():
    listener = CommandListener()
    listener.run()


if __name__ == "__main__":
    main()
