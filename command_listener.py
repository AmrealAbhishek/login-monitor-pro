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

            # Import capture function
            try:
                from pro_monitor import Capture
                photos = Capture.capture_photos(count=count, delay=1)
            except ImportError:
                # Fallback to imagesnap directly
                imagesnap = "/opt/homebrew/bin/imagesnap"
                if not os.path.exists(imagesnap):
                    imagesnap = "/usr/local/bin/imagesnap"

                for i in range(count):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    photo_path = BASE_DIR / "captured_images" / f"cmd_photo_{timestamp}_{i}.jpg"
                    photo_path.parent.mkdir(parents=True, exist_ok=True)

                    subprocess.run([imagesnap, "-w", "0.5", str(photo_path)],
                                   capture_output=True, timeout=10)
                    if photo_path.exists():
                        photos.append(str(photo_path))
                    time.sleep(1)

            # Upload photos
            photo_urls = []
            if photos and self.client and self.device_id:
                for photo in photos:
                    url = self.client.upload_file(self.device_id, photo, "photos")
                    if url:
                        photo_urls.append(url)

            return {
                "success": True,
                "photo_count": len(photos),
                "photo_urls": photo_urls
            }
        except Exception as e:
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

            # Get current user's UID for launchctl asuser
            uid_result = subprocess.run(["id", "-u"], capture_output=True, text=True)
            uid = uid_result.stdout.strip()

            # Use launchctl asuser to run in user's GUI session (has screen recording permission)
            result = subprocess.run(
                ["launchctl", "asuser", uid, "screencapture", "-x", str(screenshot_path)],
                capture_output=True, timeout=10
            )

            # Fallback: try direct screencapture
            if not screenshot_path.exists():
                subprocess.run(["screencapture", "-x", str(screenshot_path)],
                               capture_output=True, timeout=10)

            # Fallback: try via osascript
            if not screenshot_path.exists():
                applescript = f'do shell script "screencapture -x \'{screenshot_path}\'"'
                subprocess.run(["osascript", "-e", applescript],
                              capture_output=True, timeout=10)

            # Upload screenshot
            screenshot_url = None
            if screenshot_path.exists() and self.client and self.device_id:
                screenshot_url = self.client.upload_file(self.device_id, str(screenshot_path), "photos")

            return {
                "success": screenshot_path.exists(),
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
