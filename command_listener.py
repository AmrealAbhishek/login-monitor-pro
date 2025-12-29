#!/usr/bin/env python3
"""
Command Listener for Login Monitor PRO
Uses Supabase Realtime for instant command execution.
Replaces telegram_bot.py for the Supabase + Flutter architecture.
"""

import json
import os
import subprocess
import sys
import time
import socket
import platform
import threading
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient

# Try to import supabase for Realtime support
try:
    from supabase._async.client import create_client as create_async_client
    import asyncio
    REALTIME_AVAILABLE = True
except ImportError:
    REALTIME_AVAILABLE = False


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
        """Record audio with multiple fallback methods"""
        try:
            duration = args.get("duration", 10)
            audio_path = None

            # Method 1: Try PyAudio via pro_monitor
            try:
                from pro_monitor import Capture
                audio_path = Capture.record_audio(duration=duration)
                if audio_path:
                    log(f"[INFO] Audio recorded via PyAudio")
            except Exception as e:
                log(f"[WARN] PyAudio failed: {e}")

            # Method 2: Fallback to sox/rec command
            if not audio_path:
                try:
                    # Check if sox is installed
                    sox_paths = ["/opt/homebrew/bin/rec", "/usr/local/bin/rec", "/usr/bin/rec"]
                    rec_cmd = None
                    for path in sox_paths:
                        if os.path.exists(path):
                            rec_cmd = path
                            break

                    if not rec_cmd:
                        # Try to find via which
                        result = subprocess.run(["which", "rec"], capture_output=True, text=True)
                        if result.returncode == 0:
                            rec_cmd = result.stdout.strip()

                    if rec_cmd:
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        audio_file = BASE_DIR / "captured_audio" / f"audio_{timestamp}.wav"
                        audio_file.parent.mkdir(parents=True, exist_ok=True)

                        log(f"[INFO] Recording {duration}s audio via sox...")
                        result = subprocess.run(
                            [rec_cmd, "-q", str(audio_file), "trim", "0", str(duration)],
                            capture_output=True,
                            timeout=duration + 10
                        )

                        if audio_file.exists() and audio_file.stat().st_size > 1000:
                            audio_path = str(audio_file)
                            log(f"[INFO] Audio recorded via sox: {audio_path}")
                        else:
                            log("[WARN] sox recording failed or file too small")
                    else:
                        log("[WARN] sox/rec not found - install with: brew install sox")
                except subprocess.TimeoutExpired:
                    log("[ERROR] Audio recording timeout")
                except Exception as e:
                    log(f"[ERROR] sox recording error: {e}")

            # Method 3: Fallback to ffmpeg
            if not audio_path:
                try:
                    ffmpeg_paths = ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
                    ffmpeg_cmd = None
                    for path in ffmpeg_paths:
                        if os.path.exists(path):
                            ffmpeg_cmd = path
                            break

                    if ffmpeg_cmd:
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        audio_file = BASE_DIR / "captured_audio" / f"audio_{timestamp}.wav"
                        audio_file.parent.mkdir(parents=True, exist_ok=True)

                        log(f"[INFO] Recording {duration}s audio via ffmpeg...")
                        result = subprocess.run([
                            ffmpeg_cmd, "-y", "-f", "avfoundation",
                            "-i", ":0", "-t", str(duration),
                            "-acodec", "pcm_s16le", str(audio_file)
                        ], capture_output=True, timeout=duration + 10)

                        if audio_file.exists() and audio_file.stat().st_size > 1000:
                            audio_path = str(audio_file)
                            log(f"[INFO] Audio recorded via ffmpeg: {audio_path}")
                except Exception as e:
                    log(f"[WARN] ffmpeg recording error: {e}")

            # Upload audio if captured
            audio_url = None
            if audio_path and self.client and self.device_id:
                audio_url = self.client.upload_file(self.device_id, audio_path, "audio")

            if audio_path:
                return {
                    "success": True,
                    "duration": duration,
                    "audio_url": audio_url
                }
            else:
                return {
                    "success": False,
                    "error": "Audio recording failed. Install PyAudio (pip3 install pyaudio) or sox (brew install sox)"
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

    def cmd_stop(self, args: dict) -> dict:
        """Universal stop command - stops all running actions (alarm, findme, audio recording)"""
        try:
            stopped = []

            # Stop alarm/findme sounds (afplay)
            result = subprocess.run(["pkill", "-f", "afplay"], capture_output=True)
            if result.returncode == 0:
                stopped.append("alarm/sound")

            # Stop sox/rec audio recording
            result = subprocess.run(["pkill", "-f", "rec"], capture_output=True)
            if result.returncode == 0:
                stopped.append("audio (rec)")

            # Stop any Python audio recording (SoundDevice/PyAudio based)
            result = subprocess.run(["pkill", "-f", "sounddevice"], capture_output=True)
            if result.returncode == 0:
                stopped.append("audio (sounddevice)")

            message = f"Stopped: {', '.join(stopped)}" if stopped else "No active commands to stop"

            return {
                "success": True,
                "stopped": stopped,
                "message": message
            }
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
        """List WiFi networks - current connection and whitelisted networks"""
        try:
            from network_monitor import NetworkMonitor
            monitor = NetworkMonitor()
            whitelisted = monitor.list_known_networks()
            current = monitor.get_current_wifi()

            # Get current network info
            current_info = None
            if current:
                current_ssid = current.get("ssid", "")
                current_info = {
                    "ssid": current_ssid,
                    "bssid": current.get("bssid", ""),
                    "channel": current.get("channel", ""),
                    "security": current.get("security", ""),
                    "rssi": current.get("rssi", ""),
                    "is_whitelisted": current_ssid in whitelisted
                }

            return {
                "success": True,
                "current_network": current_info,
                "whitelisted_networks": whitelisted,
                "whitelisted_count": len(whitelisted),
                "tip": "Use 'whitelistnetwork' command to add current network to whitelist"
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
        """Get app usage summary with current running apps"""
        try:
            from app_tracker import AppTracker
            tracker = AppTracker()

            hours = args.get("hours", 24)
            summary = tracker.get_usage_summary(hours=hours)

            # Check for error in summary
            if "error" in summary:
                return {"success": False, "error": summary["error"]}

            # Add currently running apps
            running_apps = tracker.get_running_apps()

            return {
                "success": True,
                "usage": {
                    "period_hours": summary.get("period_hours", hours),
                    "apps": summary.get("apps", []),
                    "running_apps": running_apps,
                    "running_count": len(running_apps),
                    "generated_at": summary.get("generated_at")
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_productivity(self, args: dict) -> dict:
        """Get productivity score and breakdown"""
        try:
            from app_tracker import ProductivityTracker, IdleDetector
            from pathlib import Path

            db_path = Path.home() / ".login-monitor" / "app_usage.db"
            tracker = ProductivityTracker(db_path)

            date = args.get("date")  # Optional: specific date (YYYY-MM-DD)
            period = args.get("period", "today")  # today, weekly

            if period == "weekly":
                summary = tracker.get_weekly_summary()
                return {
                    "success": True,
                    "productivity": summary
                }
            else:
                # Today's score
                score_data = tracker.calculate_productivity_score(date)

                # Add current idle status
                idle_seconds = IdleDetector.get_idle_time()
                score_data["current_idle_seconds"] = idle_seconds
                score_data["is_currently_idle"] = idle_seconds >= 300

                return {
                    "success": True,
                    "productivity": score_data
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_idle(self, args: dict) -> dict:
        """Get current idle time"""
        try:
            from app_tracker import IdleDetector

            idle_seconds = IdleDetector.get_idle_time()

            return {
                "success": True,
                "idle_seconds": idle_seconds,
                "idle_formatted": self._format_duration(idle_seconds),
                "is_idle": idle_seconds >= 300  # 5 minutes threshold
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

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
    # DATA PROTECTION COMMANDS (Enterprise)
    # =========================================================================

    def cmd_lock_with_message(self, args: dict) -> dict:
        """Lock the device and display a custom security message"""
        try:
            message = args.get("message", "This device is protected by CyVigil Security")
            title = args.get("title", "Security Alert")

            log(f"[INFO] Locking device with message: {message}")

            # Lock the screen first
            subprocess.run(["pmset", "displaysleepnow"], capture_output=True)

            # Show persistent alert dialog
            script = f'''
            tell application "System Events"
                display alert "{title}" message "{message}" as critical buttons {{"OK"}} giving up after 300
            end tell
            '''
            subprocess.Popen(["osascript", "-e", script],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Log to Supabase protection_actions table (if available)
            if self.client and self.device_id:
                try:
                    self.client.client.table("protection_actions").insert({
                        "device_id": self.device_id,
                        "action_type": "lock",
                        "triggered_by": "manual",
                        "status": "completed",
                        "result": {"message": message}
                    }).execute()
                except:
                    pass  # Table may not exist yet

            return {
                "success": True,
                "action": "lock_with_message",
                "message": message
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_wipe_confirmation_code(self) -> str:
        """Generate a device-specific wipe confirmation code"""
        import hashlib
        # Use device_id + fixed salt to create confirmation code
        data = f"{self.device_id}:CyVigil:WipeConfirm"
        return hashlib.sha256(data.encode()).hexdigest()[:8].upper()

    def cmd_get_wipe_code(self, args: dict) -> dict:
        """Get the confirmation code needed for remote wipe"""
        try:
            code = self._get_wipe_confirmation_code()
            return {
                "success": True,
                "wipe_code": code,
                "warning": "This code is required to perform a remote wipe. Keep it secure!"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_remote_wipe(self, args: dict) -> dict:
        """
        Remote wipe - Delete user data with confirmation required

        REQUIRES confirmation code from cmd_get_wipe_code

        This will delete:
        - ~/Documents
        - ~/Desktop
        - ~/Downloads
        - ~/.login-monitor/captured_images
        - ~/.login-monitor/captured_audio
        """
        try:
            import shutil

            confirmation = args.get("confirmation", "").upper()
            expected_code = self._get_wipe_confirmation_code()

            # Verify confirmation code
            if confirmation != expected_code:
                log(f"[SECURITY] Remote wipe rejected - invalid confirmation code")
                return {
                    "success": False,
                    "error": "Invalid confirmation code. Use 'get_wipe_code' command to get the correct code.",
                    "hint": "Remote wipe requires confirmation to prevent accidental data loss"
                }

            log("[WARNING] Remote wipe initiated with valid confirmation code")

            # Record action before wiping
            if self.client and self.device_id:
                try:
                    self.client.client.table("protection_actions").insert({
                        "device_id": self.device_id,
                        "action_type": "wipe",
                        "triggered_by": "manual",
                        "status": "executing",
                        "result": {"initiated_at": datetime.now().isoformat()}
                    }).execute()
                except:
                    pass

            # Directories to wipe
            wipe_targets = [
                Path.home() / "Documents",
                Path.home() / "Desktop",
                Path.home() / "Downloads",
                BASE_DIR / "captured_images",
                BASE_DIR / "captured_audio",
            ]

            wiped = []
            failed = []

            for target in wipe_targets:
                try:
                    if target.exists():
                        if target.is_dir():
                            shutil.rmtree(target, ignore_errors=True)
                        else:
                            target.unlink()
                        # Recreate empty directory
                        target.mkdir(parents=True, exist_ok=True)
                        wiped.append(str(target))
                        log(f"[WIPE] Wiped: {target}")
                except Exception as e:
                    failed.append({"path": str(target), "error": str(e)})
                    log(f"[WIPE] Failed: {target} - {e}")

            # Update action status
            if self.client and self.device_id:
                try:
                    self.client.client.table("protection_actions").update({
                        "status": "completed",
                        "completed_at": datetime.now().isoformat(),
                        "result": {"wiped": wiped, "failed": failed}
                    }).eq("device_id", self.device_id).eq("action_type", "wipe").eq("status", "executing").execute()
                except:
                    pass

            # Lock device after wipe
            subprocess.run(["pmset", "displaysleepnow"], capture_output=True)

            return {
                "success": True,
                "action": "remote_wipe",
                "wiped": wiped,
                "failed": failed,
                "message": "Device wiped and locked"
            }

        except Exception as e:
            log(f"[ERROR] Remote wipe error: {e}")
            return {"success": False, "error": str(e)}

    def cmd_disable_usb(self, args: dict) -> dict:
        """Disable USB mass storage devices (requires admin privileges)"""
        try:
            # Note: This requires sudo/admin privileges
            # We can only attempt to unmount existing USB drives
            result = subprocess.run(
                ["diskutil", "list", "-plist", "external"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                import plistlib
                plist = plistlib.loads(result.stdout.encode())
                disks = plist.get("WholeDisks", [])

                ejected = []
                for disk in disks:
                    try:
                        subprocess.run(["diskutil", "eject", disk],
                                      capture_output=True, timeout=10)
                        ejected.append(disk)
                    except:
                        pass

                return {
                    "success": True,
                    "action": "disable_usb",
                    "ejected_disks": ejected,
                    "note": "External USB drives ejected. Full USB blocking requires admin privileges."
                }

            return {"success": True, "message": "No external USB drives found"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_enable_usb(self, args: dict) -> dict:
        """Re-enable USB devices (placeholder - requires re-plugging devices)"""
        return {
            "success": True,
            "message": "USB enabled. Re-plug devices to reconnect."
        }

    def cmd_install_app(self, args: dict) -> dict:
        """Install application remotely via Homebrew or direct download.

        Args:
            app_name: Name of app (Homebrew cask name or URL to .dmg/.pkg)
            source: 'brew' (default), 'dmg', or 'pkg'
            url: Direct download URL for dmg/pkg
            sudo_password: Required for some installations
        """
        app_name = args.get("app_name", "").strip()
        source = args.get("source", "brew").lower()
        url = args.get("url", "")

        if not app_name and not url:
            return {"success": False, "error": "app_name or url required"}

        log(f"Installing app: {app_name or url} via {source}")

        try:
            if source == "brew":
                # Install via Homebrew cask
                result = subprocess.run(
                    ["/opt/homebrew/bin/brew", "install", "--cask", app_name],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": f"{app_name} installed successfully via Homebrew",
                        "output": result.stdout
                    }
                else:
                    # Try regular brew install if cask fails
                    result2 = subprocess.run(
                        ["/opt/homebrew/bin/brew", "install", app_name],
                        capture_output=True, text=True, timeout=600
                    )
                    if result2.returncode == 0:
                        return {
                            "success": True,
                            "message": f"{app_name} installed successfully via Homebrew",
                            "output": result2.stdout
                        }
                    return {
                        "success": False,
                        "error": f"Brew install failed: {result.stderr or result2.stderr}"
                    }

            elif source == "dmg" and url:
                # Download and mount DMG
                dmg_path = Path("/tmp") / f"{app_name or 'app'}.dmg"

                # Download
                log(f"Downloading DMG from {url}")
                download = subprocess.run(
                    ["curl", "-L", "-o", str(dmg_path), url],
                    capture_output=True, timeout=600
                )
                if download.returncode != 0:
                    return {"success": False, "error": "Download failed"}

                # Mount DMG
                mount = subprocess.run(
                    ["hdiutil", "attach", str(dmg_path), "-nobrowse"],
                    capture_output=True, text=True, timeout=60
                )
                if mount.returncode != 0:
                    return {"success": False, "error": f"Mount failed: {mount.stderr}"}

                # Find mounted volume
                volume_line = [l for l in mount.stdout.split('\n') if '/Volumes/' in l]
                if not volume_line:
                    return {"success": False, "error": "Could not find mounted volume"}

                volume_path = volume_line[0].split('/Volumes/')[-1]
                volume_path = f"/Volumes/{volume_path.split()[0] if ' ' in volume_path else volume_path}"

                # Find .app in volume
                apps = list(Path(volume_path).glob("*.app"))
                if apps:
                    app_path = apps[0]
                    dest = Path("/Applications") / app_path.name

                    # Copy to Applications
                    subprocess.run(["cp", "-R", str(app_path), str(dest)], timeout=120)

                    # Unmount
                    subprocess.run(["hdiutil", "detach", volume_path], capture_output=True)

                    # Cleanup
                    dmg_path.unlink(missing_ok=True)

                    return {
                        "success": True,
                        "message": f"{app_path.name} installed to /Applications"
                    }
                else:
                    subprocess.run(["hdiutil", "detach", volume_path], capture_output=True)
                    return {"success": False, "error": "No .app found in DMG"}

            elif source == "pkg" and url:
                # Download and install PKG
                pkg_path = Path("/tmp") / f"{app_name or 'app'}.pkg"

                # Download
                log(f"Downloading PKG from {url}")
                download = subprocess.run(
                    ["curl", "-L", "-o", str(pkg_path), url],
                    capture_output=True, timeout=600
                )
                if download.returncode != 0:
                    return {"success": False, "error": "Download failed"}

                # Install PKG (requires sudo - may prompt or use stored credentials)
                install = subprocess.run(
                    ["sudo", "-n", "installer", "-pkg", str(pkg_path), "-target", "/"],
                    capture_output=True, text=True, timeout=300
                )

                # Cleanup
                pkg_path.unlink(missing_ok=True)

                if install.returncode == 0:
                    return {
                        "success": True,
                        "message": f"Package installed successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Installation failed: {install.stderr}",
                        "note": "PKG installation may require admin privileges"
                    }

            else:
                return {"success": False, "error": f"Invalid source: {source}. Use 'brew', 'dmg', or 'pkg'"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Installation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_uninstall_app(self, args: dict) -> dict:
        """Uninstall application.

        Args:
            app_name: Name of app to uninstall
            source: 'brew' (for Homebrew apps) or 'app' (for /Applications)
        """
        app_name = args.get("app_name", "").strip()
        source = args.get("source", "app").lower()

        if not app_name:
            return {"success": False, "error": "app_name required"}

        try:
            if source == "brew":
                result = subprocess.run(
                    ["/opt/homebrew/bin/brew", "uninstall", "--cask", app_name],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    return {"success": True, "message": f"{app_name} uninstalled via Homebrew"}
                # Try regular uninstall
                result2 = subprocess.run(
                    ["/opt/homebrew/bin/brew", "uninstall", app_name],
                    capture_output=True, text=True, timeout=120
                )
                if result2.returncode == 0:
                    return {"success": True, "message": f"{app_name} uninstalled via Homebrew"}
                return {"success": False, "error": result.stderr or result2.stderr}

            else:
                # Remove from /Applications
                app_path = Path("/Applications") / f"{app_name}.app"
                if not app_path.exists():
                    # Try case-insensitive search
                    for app in Path("/Applications").glob("*.app"):
                        if app.stem.lower() == app_name.lower():
                            app_path = app
                            break

                if app_path.exists():
                    subprocess.run(["rm", "-rf", str(app_path)], timeout=60)
                    return {"success": True, "message": f"{app_path.name} removed from /Applications"}
                else:
                    return {"success": False, "error": f"App not found: {app_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_list_apps(self, args: dict) -> dict:
        """List installed applications."""
        try:
            apps = []

            # List /Applications
            for app in sorted(Path("/Applications").glob("*.app")):
                apps.append({
                    "name": app.stem,
                    "path": str(app),
                    "source": "app"
                })

            # List Homebrew casks
            try:
                result = subprocess.run(
                    ["/opt/homebrew/bin/brew", "list", "--cask"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    for cask in result.stdout.strip().split('\n'):
                        if cask:
                            apps.append({
                                "name": cask,
                                "source": "brew"
                            })
            except:
                pass

            return {
                "success": True,
                "apps": apps,
                "count": len(apps)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_shell(self, args: dict) -> dict:
        """Execute a shell command and return the output.

        For IT admin diagnostics: ifconfig, ping, reboot, etc.

        Args:
            cmd: The shell command to execute
            timeout: Timeout in seconds (default: 60)
            sudo: Whether to use sudo (default: false)
        """
        try:
            cmd = args.get("cmd", "").strip()
            timeout = int(args.get("timeout", 60))
            use_sudo = args.get("sudo", False)

            if not cmd:
                return {"success": False, "error": "No command specified"}

            # Security: Block dangerous patterns
            dangerous = ["rm -rf /", "> /dev/sda", "dd if=", "mkfs", ":(){:|:&};:"]
            for pattern in dangerous:
                if pattern in cmd.lower():
                    return {"success": False, "error": f"Command blocked for safety: {pattern}"}

            log(f"[SHELL] Executing: {cmd}")

            # Build command
            if use_sudo:
                # Use sudo -n (non-interactive) - requires NOPASSWD in sudoers
                full_cmd = f"sudo -n {cmd}"
            else:
                full_cmd = cmd

            # Execute
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.home())
            )

            stdout = result.stdout[:50000] if result.stdout else ""  # Limit output
            stderr = result.stderr[:10000] if result.stderr else ""

            return {
                "success": result.returncode == 0,
                "command": cmd,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "output": stdout or stderr  # Combined for easy display
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": cmd
            }
        except Exception as e:
            return {"success": False, "error": str(e), "command": cmd}

    def cmd_reboot(self, args: dict) -> dict:
        """Reboot the system (requires sudo NOPASSWD)."""
        try:
            log("[SHELL] Rebooting system...")

            # Use sudo -n for non-interactive sudo
            result = subprocess.run(
                ["sudo", "-n", "shutdown", "-r", "now"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                # Fallback: try osascript restart
                result = subprocess.run([
                    "osascript", "-e",
                    'tell application "System Events" to restart'
                ], capture_output=True, text=True, timeout=10)

            return {
                "success": True,
                "message": "Reboot initiated"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_shutdown(self, args: dict) -> dict:
        """Shutdown the system (requires sudo NOPASSWD)."""
        try:
            log("[SHELL] Shutting down system...")

            result = subprocess.run(
                ["sudo", "-n", "shutdown", "-h", "now"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                # Fallback: try osascript
                result = subprocess.run([
                    "osascript", "-e",
                    'tell application "System Events" to shut down'
                ], capture_output=True, text=True, timeout=10)

            return {
                "success": True,
                "message": "Shutdown initiated"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # REMOTE DESKTOP (VNC) COMMANDS
    # =========================================================================

    def cmd_vnc_start(self, args: dict) -> dict:
        """Start VNC remote desktop with websocket proxy and tunnel.

        Returns a URL that can be used with noVNC to connect.
        """
        try:
            import signal

            vnc_port = 5900
            ws_port = args.get("ws_port", 6080)

            # Check if Screen Sharing is enabled (use netstat as lsof needs sudo)
            result = subprocess.run(
                ["netstat", "-an"],
                capture_output=True, text=True
            )
            if f".{vnc_port}" not in result.stdout:
                return {
                    "success": False,
                    "error": "Screen Sharing not enabled. Enable it in System Settings > General > Sharing > Screen Sharing"
                }

            log(f"[VNC] Starting remote desktop on ws_port {ws_port}")

            # Kill any existing websockify/cloudflared processes
            subprocess.run(["pkill", "-f", "websockify"], capture_output=True)
            subprocess.run(["pkill", "-f", "cloudflared.*tunnel.*vnc"], capture_output=True)
            time.sleep(1)

            # Start websockify (WebSocket to VNC proxy)
            websockify_path = Path.home() / "Library/Python/3.9/bin/websockify"
            if not websockify_path.exists():
                websockify_path = "websockify"  # Try PATH

            ws_process = subprocess.Popen(
                [str(websockify_path), str(ws_port), f"localhost:{vnc_port}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            log(f"[VNC] websockify started on port {ws_port} (PID: {ws_process.pid})")

            time.sleep(2)

            # Start cloudflared tunnel
            tunnel_process = subprocess.Popen(
                ["/opt/homebrew/bin/cloudflared", "tunnel", "--url", f"http://localhost:{ws_port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True
            )

            # Wait for tunnel URL
            tunnel_url = None
            start_time = time.time()
            while time.time() - start_time < 30:
                line = tunnel_process.stdout.readline()
                if "trycloudflare.com" in line:
                    # Extract URL
                    import re
                    match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        tunnel_url = match.group(0)
                        log(f"[VNC] Tunnel URL: {tunnel_url}")
                        break
                if tunnel_process.poll() is not None:
                    break

            if not tunnel_url:
                return {
                    "success": False,
                    "error": "Failed to create tunnel. Check cloudflared installation."
                }

            # Store process info for later cleanup
            vnc_state = {
                "ws_pid": ws_process.pid,
                "tunnel_pid": tunnel_process.pid,
                "tunnel_url": tunnel_url,
                "ws_port": ws_port
            }

            # Save state to file
            state_file = BASE_DIR / "vnc_state.json"
            with open(state_file, "w") as f:
                json.dump(vnc_state, f)

            # Update device with VNC URL
            if self.client and self.device_id:
                try:
                    self.client.client.table("devices").update({
                        "vnc_url": tunnel_url
                    }).eq("id", self.device_id).execute()
                except:
                    pass

            return {
                "success": True,
                "vnc_url": tunnel_url,
                "ws_port": ws_port,
                "message": f"VNC ready at {tunnel_url}"
            }

        except Exception as e:
            log(f"[VNC] Error: {e}")
            return {"success": False, "error": str(e)}

    def cmd_vnc_stop(self, args: dict) -> dict:
        """Stop VNC remote desktop session."""
        try:
            log("[VNC] Stopping remote desktop")

            # Kill websockify
            subprocess.run(["pkill", "-f", "websockify"], capture_output=True)

            # Kill cloudflared tunnel
            subprocess.run(["pkill", "-f", "cloudflared.*tunnel"], capture_output=True)

            # Remove state file
            state_file = BASE_DIR / "vnc_state.json"
            if state_file.exists():
                state_file.unlink()

            # Clear VNC URL from device
            if self.client and self.device_id:
                try:
                    self.client.client.table("devices").update({
                        "vnc_url": None
                    }).eq("id", self.device_id).execute()
                except:
                    pass

            return {
                "success": True,
                "message": "VNC session stopped"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cmd_vnc_status(self, args: dict) -> dict:
        """Get VNC session status."""
        try:
            state_file = BASE_DIR / "vnc_state.json"

            if not state_file.exists():
                return {
                    "success": True,
                    "active": False,
                    "message": "No active VNC session"
                }

            with open(state_file) as f:
                state = json.load(f)

            # Check if processes are still running
            ws_running = subprocess.run(
                ["kill", "-0", str(state.get("ws_pid", 0))],
                capture_output=True
            ).returncode == 0

            tunnel_running = subprocess.run(
                ["kill", "-0", str(state.get("tunnel_pid", 0))],
                capture_output=True
            ).returncode == 0

            if ws_running and tunnel_running:
                return {
                    "success": True,
                    "active": True,
                    "vnc_url": state.get("tunnel_url"),
                    "ws_port": state.get("ws_port")
                }
            else:
                # Clean up stale state
                state_file.unlink()
                return {
                    "success": True,
                    "active": False,
                    "message": "VNC session expired"
                }

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
            "stop": self.cmd_stop,  # Universal stop command
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
            # Productivity commands
            "productivity": self.cmd_productivity,
            "idle": self.cmd_idle,
            # Data protection commands
            "lock_with_message": self.cmd_lock_with_message,
            "lockwithmessage": self.cmd_lock_with_message,  # Alternative without underscore
            "get_wipe_code": self.cmd_get_wipe_code,
            "getwipecode": self.cmd_get_wipe_code,
            "remote_wipe": self.cmd_remote_wipe,
            "remotewipe": self.cmd_remote_wipe,
            "disable_usb": self.cmd_disable_usb,
            "disableusb": self.cmd_disable_usb,
            "enable_usb": self.cmd_enable_usb,
            "enableusb": self.cmd_enable_usb,
            # App management commands
            "install_app": self.cmd_install_app,
            "installapp": self.cmd_install_app,
            "uninstall_app": self.cmd_uninstall_app,
            "uninstallapp": self.cmd_uninstall_app,
            "list_apps": self.cmd_list_apps,
            "listapps": self.cmd_list_apps,
            # Remote shell commands
            "shell": self.cmd_shell,
            "exec": self.cmd_shell,
            "run": self.cmd_shell,
            "reboot": self.cmd_reboot,
            "restart": self.cmd_reboot,
            "shutdown": self.cmd_shutdown,
            "poweroff": self.cmd_shutdown,
            # Remote desktop (VNC) commands
            "vnc_start": self.cmd_vnc_start,
            "vncstart": self.cmd_vnc_start,
            "remote_desktop": self.cmd_vnc_start,
            "vnc_stop": self.cmd_vnc_stop,
            "vncstop": self.cmd_vnc_stop,
            "vnc_status": self.cmd_vnc_status,
            "vncstatus": self.cmd_vnc_status,
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

    def on_realtime_command(self, payload):
        """Callback when a command is received via Realtime"""
        try:
            # Payload is a dict with 'data' containing the event info
            if isinstance(payload, dict) and 'data' in payload:
                data = payload['data']
                record = data.get('record', {})
                event_type = data.get('type')

                # event_type is an enum, convert to string for comparison
                event_type_str = str(event_type) if event_type else ''

                # Check if this is an INSERT and command is pending
                if 'INSERT' in event_type_str.upper() or 'insert' in event_type_str.lower():
                    if record and record.get('status') == 'pending':
                        log(f"[REALTIME] >>> Executing: {record.get('command')}")
                        self.execute_command(record)
                        return

            # Fallback: try other formats
            if hasattr(payload, 'data'):
                data = payload.data
                record = data.get('record', {})
                if record and record.get('status') == 'pending':
                    log(f"[REALTIME] >>> Executing: {record.get('command')}")
                    self.execute_command(record)

        except Exception as e:
            import traceback
            log(f"[REALTIME] Error: {e}")

    def heartbeat_loop(self):
        """Background thread to update device heartbeat"""
        while self.running:
            try:
                self.client.update_device_status(self.device_id)
            except Exception as e:
                log(f"[HEARTBEAT] Error: {e}")
            time.sleep(30)

    def process_pending_commands(self):
        """Process any pending commands on startup"""
        try:
            commands = self.client.get_pending_commands(self.device_id)
            for cmd in commands:
                self.execute_command(cmd)
            if commands:
                log(f"[STARTUP] Processed {len(commands)} pending commands")
        except Exception as e:
            log(f"[STARTUP] Error: {e}")

    def run(self):
        """Main loop using Supabase Realtime for instant command execution"""
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
        self.running = True

        # Process any pending commands first
        self.process_pending_commands()

        # Start heartbeat in background thread (NOT daemon - keeps running)
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=False)
        heartbeat_thread.start()
        log("[HEARTBEAT] Background thread started")

        # Try Realtime mode first with auto-reconnect
        if REALTIME_AVAILABLE:
            max_retries = 999999  # Essentially infinite retries
            retry_count = 0
            while self.running and retry_count < max_retries:
                try:
                    asyncio.run(self.run_realtime())
                except KeyboardInterrupt:
                    log("Command listener stopped by user")
                    self.running = False
                    break
                except Exception as e:
                    retry_count += 1
                    log(f"[REALTIME] Disconnected: {e}")
                    log(f"[REALTIME] Reconnecting in 10 seconds... (attempt {retry_count})")
                    time.sleep(10)

            if self.running:
                log("[REALTIME] Max retries reached, falling back to polling mode...")
                self.run_polling()
        else:
            log("[INFO] Realtime not available, using polling mode")
            self.run_polling()

    async def run_realtime(self):
        """Async Realtime listener with connection monitoring"""
        supabase_config = self.config.get("supabase", {})

        # Create async client
        realtime_client = await create_async_client(
            supabase_config["url"],
            supabase_config["anon_key"]
        )

        # Subscribe to commands channel
        channel = realtime_client.channel('commands-channel')

        # Track last activity for watchdog
        self._last_realtime_activity = time.time()

        def handle_insert(payload):
            """Handle INSERT event"""
            self._last_realtime_activity = time.time()
            self.on_realtime_command(payload)

        channel.on_postgres_changes(
            event='INSERT',
            schema='public',
            table='commands',
            filter=f'device_id=eq.{self.device_id}',
            callback=handle_insert
        )

        await channel.subscribe()
        self._last_realtime_activity = time.time()

        log("-" * 60)
        log("[REALTIME] Connected via WebSocket")
        log("[REALTIME] Commands execute INSTANTLY!")
        log("-" * 60)

        # Keep alive with watchdog - reconnect if no activity for 5 minutes
        # (Supabase sends heartbeats, so no activity means disconnected)
        WATCHDOG_TIMEOUT = 300  # 5 minutes

        while self.running:
            await asyncio.sleep(30)  # Check every 30 seconds

            # Update heartbeat via REST API (independent of WebSocket)
            try:
                self.client.update_device_status(self.device_id)
            except Exception as e:
                log(f"[REALTIME] Heartbeat error: {e}")

            # Check if Realtime is still alive
            time_since_activity = time.time() - self._last_realtime_activity
            if time_since_activity > WATCHDOG_TIMEOUT:
                log(f"[REALTIME] No activity for {int(time_since_activity)}s - forcing reconnect")
                raise Exception("Watchdog timeout - Realtime appears disconnected")

    def run_polling(self):
        """Fallback polling mode"""
        log(f"[POLLING] Interval: {self.poll_interval} seconds")
        log("-" * 60)
        log("Listening for commands (polling)...")

        while self.running:
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
                self.running = False
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(self.poll_interval)


def main():
    listener = CommandListener()
    listener.run()


if __name__ == "__main__":
    main()
