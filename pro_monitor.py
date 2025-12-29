#!/usr/bin/env python3
"""
Login Monitor PRO - Professional Anti-Theft & Security Monitoring
==================================================================

Features:
- Telegram instant notifications with photos
- Email notifications with full details
- GPS/Location tracking with Google Maps link
- Multiple photo capture (burst mode)
- Audio recording
- Battery & WiFi status
- Failed login detection
- Remote commands via Telegram
- Encrypted storage
- Face recognition (known vs unknown)
- Cloud backup to Google Drive
- Anti-theft: Alarm, Screen message
- Web dashboard
- Daily summary reports
- Stealth mode
"""

import os
import sys
import json
import smtplib
import platform
import subprocess
import uuid
import urllib.request
import urllib.error
import socket
import time
import threading
import hashlib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

# Cryptography for encrypted storage
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Telegram (legacy - kept for backwards compatibility)
try:
    import telegram
    from telegram import Bot
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

# Supabase (new notification backend)
try:
    from supabase_client import SupabaseNotifier, SupabaseClient
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

# FCM Push Notifications
try:
    from fcm_sender import send_event_notification
    HAS_FCM = True
except ImportError:
    HAS_FCM = False

# Threat Detection
try:
    from threat_detector import ThreatDetector
    HAS_THREAT_DETECTION = True
except ImportError:
    HAS_THREAT_DETECTION = False

# Audio recording
try:
    import pyaudio
    import wave
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# Face recognition
try:
    import face_recognition
    HAS_FACE_RECOGNITION = True
except ImportError:
    HAS_FACE_RECOGNITION = False

# CoreLocation for GPS (macOS)
try:
    import CoreLocation
    HAS_CORELOCATION = True
except ImportError:
    HAS_CORELOCATION = False

# OpenCV
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# ============================================================================
# CONFIGURATION
# ============================================================================

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
ENCRYPTED_CONFIG_FILE = SCRIPT_DIR / "config.enc"
KEY_FILE = SCRIPT_DIR / ".key"
EVENTS_DIR = SCRIPT_DIR / "events"
IMAGES_DIR = SCRIPT_DIR / "captured_images"
AUDIO_DIR = SCRIPT_DIR / "captured_audio"
FACES_DIR = SCRIPT_DIR / "known_faces"
LOG_FILE = SCRIPT_DIR / "monitor.log"

# Default settings
DEFAULT_CONFIG = {
    "notification_email": "",
    "smtp": {},
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": ""
    },
    "features": {
        "multi_photo": True,
        "photo_count": 3,
        "photo_delay": 2,
        "audio_recording": True,
        "audio_duration": 10,
        "face_recognition": True,
        "cloud_backup": False,
        "stealth_mode": False,
        "daily_summary": True,
        "summary_time": "09:00"
    },
    "security": {
        "encrypt_config": True,
        "encrypt_images": False
    }
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log(message: str, level: str = "INFO"):
    """Log message to file and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)

    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry + "\n")
    except:
        pass


def ensure_dirs():
    """Create necessary directories"""
    for d in [EVENTS_DIR, IMAGES_DIR, AUDIO_DIR, FACES_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ============================================================================
# ENCRYPTION MODULE
# ============================================================================

class Encryption:
    """Handle encryption of sensitive data"""

    @staticmethod
    def generate_key() -> bytes:
        """Generate a new encryption key"""
        return Fernet.generate_key()

    @staticmethod
    def get_or_create_key() -> bytes:
        """Get existing key or create new one"""
        if KEY_FILE.exists():
            return KEY_FILE.read_bytes()
        else:
            key = Encryption.generate_key()
            KEY_FILE.write_bytes(key)
            os.chmod(KEY_FILE, 0o600)  # Restrict access
            return key

    @staticmethod
    def encrypt(data: str) -> bytes:
        """Encrypt string data"""
        if not HAS_CRYPTO:
            return data.encode()
        key = Encryption.get_or_create_key()
        f = Fernet(key)
        return f.encrypt(data.encode())

    @staticmethod
    def decrypt(data: bytes) -> str:
        """Decrypt data to string"""
        if not HAS_CRYPTO:
            return data.decode()
        key = Encryption.get_or_create_key()
        f = Fernet(key)
        return f.decrypt(data).decode()

    @staticmethod
    def encrypt_file(file_path: Path, output_path: Path = None):
        """Encrypt a file"""
        if not HAS_CRYPTO:
            return
        if output_path is None:
            output_path = file_path.with_suffix(file_path.suffix + '.enc')

        data = file_path.read_bytes()
        key = Encryption.get_or_create_key()
        f = Fernet(key)
        encrypted = f.encrypt(data)
        output_path.write_bytes(encrypted)
        return output_path


# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================

class ConfigManager:
    """Manage configuration with optional encryption"""

    @staticmethod
    def load() -> dict:
        """Load configuration"""
        # Try encrypted config first
        if ENCRYPTED_CONFIG_FILE.exists() and HAS_CRYPTO:
            try:
                encrypted_data = ENCRYPTED_CONFIG_FILE.read_bytes()
                decrypted = Encryption.decrypt(encrypted_data)
                return json.loads(decrypted)
            except Exception as e:
                log(f"Failed to load encrypted config: {e}", "ERROR")

        # Fall back to plain config
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)

        return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(config: dict, encrypt: bool = False):
        """Save configuration"""
        if encrypt and HAS_CRYPTO:
            encrypted = Encryption.encrypt(json.dumps(config, indent=2))
            ENCRYPTED_CONFIG_FILE.write_bytes(encrypted)
            # Remove plain config if exists
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
        else:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)


# ============================================================================
# SYSTEM INFO COLLECTOR
# ============================================================================

class SystemInfo:
    """Collect system information"""

    @staticmethod
    def get_battery_status() -> dict:
        """Get battery information (macOS)"""
        if platform.system() != "Darwin":
            return {"available": False}

        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout

            # Parse battery info
            import re
            match = re.search(r'(\d+)%', output)
            percentage = int(match.group(1)) if match else None

            # Check actual charging state - "discharging" means not charging
            is_discharging = "discharging" in output.lower()
            is_charging = "charging" in output.lower() and not is_discharging
            is_on_ac = "ac power" in output.lower()

            return {
                "available": True,
                "percentage": percentage,
                "charging": is_charging or (is_on_ac and not is_discharging),
                "status": "Charging" if is_charging else ("AC Power" if is_on_ac else "On Battery")
            }
        except Exception as e:
            log(f"Battery status error: {e}", "ERROR")
            return {"available": False}

    @staticmethod
    def get_wifi_info() -> dict:
        """Get WiFi network information (macOS)"""
        if platform.system() != "Darwin":
            return {"available": False}

        try:
            # Try CoreWLAN first (best method, doesn't redact SSID)
            try:
                import objc
                from Foundation import NSBundle

                # Load CoreWLAN framework
                bundle = NSBundle.bundleWithPath_('/System/Library/Frameworks/CoreWLAN.framework')
                if bundle:
                    objc.loadBundle('CoreWLAN', bundle_path=bundle.bundlePath(), module_globals=globals())

                    # Get default WiFi interface
                    wifi_client = CWWiFiClient.sharedWiFiClient()
                    interface = wifi_client.interface()

                    if interface and interface.ssid():
                        return {
                            "available": True,
                            "ssid": interface.ssid(),
                            "bssid": interface.bssid() or "Unknown",
                            "channel": str(interface.wlanChannel().channelNumber()) if interface.wlanChannel() else "Unknown",
                            "rssi": str(interface.rssiValue()) + " dBm" if interface.rssiValue() else "Unknown"
                        }
            except Exception as e:
                log(f"CoreWLAN error: {e}", "WARNING")

            # Fallback: try system_profiler (SSID may be redacted)
            result = subprocess.run(
                ["system_profiler", "SPAirPortDataType", "-json"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                airport_data = data.get("SPAirPortDataType", [{}])[0]
                interfaces = airport_data.get("spairport_airport_interfaces", []) if isinstance(airport_data, dict) else []

                for iface in interfaces:
                    if not isinstance(iface, dict):
                        continue
                    status = iface.get("spairport_current_network_information", {})
                    if status and isinstance(status, dict):
                        ssid = status.get("_name", "Unknown")
                        # If SSID is redacted, try to get it differently
                        if ssid == "<redacted>" or not ssid:
                            ssid = "Connected (name hidden)"
                        return {
                            "available": True,
                            "ssid": ssid,
                            "channel": status.get("spairport_network_channel", "Unknown"),
                            "phy_mode": status.get("spairport_network_phymode", "Unknown"),
                            "security": status.get("spairport_security_mode", "Unknown")
                        }

            return {"available": False, "reason": "Not connected to WiFi"}

        except Exception as e:
            log(f"WiFi info error: {e}", "ERROR")
            return {"available": False}

    @staticmethod
    def get_public_ip() -> str:
        """Get public IP address"""
        services = [
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
            'https://icanhazip.com'
        ]

        for service in services:
            try:
                response = urllib.request.urlopen(service, timeout=5)
                return response.read().decode('utf-8').strip()
            except:
                continue
        return "Unknown"

    @staticmethod
    def get_local_ip() -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "Unknown"

    @staticmethod
    def get_location() -> dict:
        """Get GPS location"""
        # Try CoreLocation first (macOS)
        if platform.system() == "Darwin" and HAS_CORELOCATION:
            try:
                manager = CoreLocation.CLLocationManager.alloc().init()

                # Check authorization status
                auth_status = manager.authorizationStatus()
                # 0 = Not Determined, 1 = Restricted, 2 = Denied, 3 = Authorized Always, 4 = Authorized When In Use

                if auth_status == 2:  # Denied
                    log("Location Services DENIED - grant permission in System Settings > Privacy & Security > Location Services", "ERROR")
                    # Fall through to IP location
                elif auth_status == 0:  # Not determined
                    log("Requesting location authorization...")
                    manager.requestWhenInUseAuthorization()
                    time.sleep(2)  # Wait for user response
                    auth_status = manager.authorizationStatus()

                # Only proceed if authorized
                if auth_status >= 3:  # Authorized
                    manager.startUpdatingLocation()

                    timeout = 20  # Increased timeout for GPS lock
                    start = time.time()

                    while time.time() - start < timeout:
                        location = manager.location()
                        if location:
                            lat = location.coordinate().latitude
                            lon = location.coordinate().longitude
                            accuracy = location.horizontalAccuracy()

                            # Accept if accuracy is reasonable (< 5000m for initial, prefer < 100m)
                            if accuracy > 0 and accuracy < 5000:
                                manager.stopUpdatingLocation()
                                log(f"[INFO] GPS location acquired (accuracy: {accuracy}m)")

                                return {
                                    'latitude': round(lat, 6),
                                    'longitude': round(lon, 6),
                                    'accuracy_meters': round(accuracy, 1),
                                    'google_maps': f"https://www.google.com/maps?q={lat},{lon}",
                                    'source': 'GPS/CoreLocation'
                                }
                        time.sleep(0.5)

                    manager.stopUpdatingLocation()
                    log("GPS timeout - falling back to IP location", "WARNING")
                else:
                    log(f"Location not authorized (status: {auth_status}). Grant permission in System Settings > Privacy & Security > Location Services > Python/Terminal", "WARNING")

            except Exception as e:
                log(f"CoreLocation error: {e}", "ERROR")

        # Fallback to IP-based location
        try:
            response = urllib.request.urlopen('http://ip-api.com/json/', timeout=5)
            data = json.loads(response.read().decode('utf-8'))

            return {
                'latitude': data.get('lat'),
                'longitude': data.get('lon'),
                'accuracy_meters': 'City-level (~1-5 km)',
                'city': data.get('city'),
                'region': data.get('regionName'),
                'country': data.get('country'),
                'google_maps': f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}",
                'source': 'IP Geolocation'
            }
        except Exception as e:
            log(f"IP geolocation error: {e}", "ERROR")
            return {'source': 'Failed', 'error': str(e)}

    @staticmethod
    def collect_all() -> dict:
        """Collect all system information"""
        log("Collecting system information...")

        return {
            'hostname': platform.node(),
            'os': platform.system(),
            'os_version': platform.version(),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': os.getenv('USER') or os.getenv('USERNAME') or 'Unknown',
            'local_ip': SystemInfo.get_local_ip(),
            'public_ip': SystemInfo.get_public_ip(),
            'location': SystemInfo.get_location(),
            'battery': SystemInfo.get_battery_status(),
            'wifi': SystemInfo.get_wifi_info()
        }


# ============================================================================
# CAPTURE MODULE
# ============================================================================

class Capture:
    """Handle image and audio capture"""

    @staticmethod
    def capture_photos(count: int = 3, delay: float = 2.0) -> List[str]:
        """Capture multiple photos with delay"""
        ensure_dirs()
        photos = []

        log(f"Capturing {count} photos...")

        for i in range(count):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"capture_{timestamp}_{i+1}_{uuid.uuid4().hex[:6]}.jpg"
            filepath = IMAGES_DIR / filename

            # Use imagesnap on macOS
            if platform.system() == "Darwin":
                imagesnap_paths = [
                    "/opt/homebrew/bin/imagesnap",
                    "/usr/local/bin/imagesnap",
                ]

                imagesnap_cmd = None
                for path in imagesnap_paths:
                    if os.path.exists(path):
                        imagesnap_cmd = path
                        break

                if imagesnap_cmd:
                    try:
                        # Use longer warmup (2s) and timeout (30s) for camera initialization
                        result = subprocess.run(
                            [imagesnap_cmd, "-w", "2.0", str(filepath)],
                            capture_output=True, text=True, timeout=30
                        )
                        if filepath.exists() and filepath.stat().st_size > 0:
                            photos.append(str(filepath))
                            log(f"Photo {i+1}/{count} captured")
                        else:
                            log(f"Photo {i+1} not saved or empty", "WARN")
                    except subprocess.TimeoutExpired:
                        log(f"Photo {i+1} capture timeout", "ERROR")
                    except Exception as e:
                        log(f"Photo capture error: {e}", "ERROR")

            # Use OpenCV as fallback
            elif HAS_CV2:
                try:
                    cap = cv2.VideoCapture(0)
                    for _ in range(5):  # Warm up
                        cap.read()
                    ret, frame = cap.read()
                    cap.release()

                    if ret:
                        cv2.imwrite(str(filepath), frame)
                        photos.append(str(filepath))
                        log(f"Photo {i+1}/{count} captured")
                except Exception as e:
                    log(f"OpenCV capture error: {e}", "ERROR")

            if i < count - 1:
                time.sleep(delay)

        return photos

    @staticmethod
    def record_audio(duration: int = 10) -> Optional[str]:
        """Record audio for specified duration"""
        if not HAS_AUDIO:
            log("Audio recording not available (pyaudio not installed)", "WARNING")
            return None

        ensure_dirs()

        try:
            log(f"Recording {duration} seconds of audio...")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"audio_{timestamp}_{uuid.uuid4().hex[:6]}.wav"
            filepath = AUDIO_DIR / filename

            # Audio settings
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100

            p = pyaudio.PyAudio()

            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )

            frames = []

            for _ in range(0, int(RATE / CHUNK * duration)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)

            stream.stop_stream()
            stream.close()
            p.terminate()

            # Save as WAV
            wf = wave.open(str(filepath), 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            log(f"Audio recorded: {filepath}")
            return str(filepath)

        except Exception as e:
            log(f"Audio recording error: {e}", "ERROR")
            return None


# ============================================================================
# FACE RECOGNITION MODULE
# ============================================================================

class FaceRecognition:
    """Face recognition for known vs unknown users"""

    def __init__(self):
        self.known_faces = []
        self.known_names = []
        self.load_known_faces()

    def load_known_faces(self):
        """Load known faces from directory"""
        if not HAS_FACE_RECOGNITION:
            return

        ensure_dirs()

        for file in FACES_DIR.glob("*.jpg"):
            try:
                image = face_recognition.load_image_file(str(file))
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    self.known_faces.append(encodings[0])
                    self.known_names.append(file.stem)
                    log(f"Loaded known face: {file.stem}")
            except Exception as e:
                log(f"Error loading face {file}: {e}", "ERROR")

    def identify(self, image_path: str) -> dict:
        """Identify faces in image"""
        if not HAS_FACE_RECOGNITION:
            return {"available": False, "reason": "face_recognition not installed"}

        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)

            results = {
                "available": True,
                "face_count": len(face_locations),
                "faces": []
            }

            for encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_faces, encoding)
                name = "UNKNOWN"

                if True in matches:
                    match_index = matches.index(True)
                    name = self.known_names[match_index]

                results["faces"].append({
                    "name": name,
                    "is_known": name != "UNKNOWN"
                })

            # Check if any unknown faces
            results["has_unknown"] = any(f["name"] == "UNKNOWN" for f in results["faces"])

            return results

        except Exception as e:
            log(f"Face recognition error: {e}", "ERROR")
            return {"available": False, "error": str(e)}

    def add_known_face(self, image_path: str, name: str):
        """Add a new known face"""
        if not HAS_FACE_RECOGNITION:
            return False

        try:
            ensure_dirs()

            # Copy image to known faces directory
            import shutil
            dest = FACES_DIR / f"{name}.jpg"
            shutil.copy(image_path, dest)

            # Load the face
            image = face_recognition.load_image_file(str(dest))
            encodings = face_recognition.face_encodings(image)

            if encodings:
                self.known_faces.append(encodings[0])
                self.known_names.append(name)
                log(f"Added known face: {name}")
                return True

            return False

        except Exception as e:
            log(f"Error adding face: {e}", "ERROR")
            return False


# ============================================================================
# TELEGRAM MODULE
# ============================================================================

class TelegramNotifier:
    """Send notifications via Telegram"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send_message(self, text: str) -> bool:
        """Send text message"""
        if not self.enabled:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"}
            )

            urllib.request.urlopen(req, timeout=10)
            log("Telegram message sent")
            return True

        except Exception as e:
            log(f"Telegram error: {e}", "ERROR")
            return False

    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        """Send photo"""
        if not self.enabled:
            return False

        try:
            import urllib.parse

            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"

            # Use multipart form data
            boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]

            with open(photo_path, 'rb') as f:
                photo_data = f.read()

            body = []
            body.append(f'--{boundary}'.encode())
            body.append(f'Content-Disposition: form-data; name="chat_id"'.encode())
            body.append(b'')
            body.append(self.chat_id.encode())

            body.append(f'--{boundary}'.encode())
            body.append(f'Content-Disposition: form-data; name="caption"'.encode())
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
            log("Telegram photo sent")
            return True

        except Exception as e:
            log(f"Telegram photo error: {e}", "ERROR")
            return False

    def send_location(self, latitude: float, longitude: float) -> bool:
        """Send location"""
        if not self.enabled:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendLocation"
            data = {
                "chat_id": self.chat_id,
                "latitude": latitude,
                "longitude": longitude
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"}
            )

            urllib.request.urlopen(req, timeout=10)
            log("Telegram location sent")
            return True

        except Exception as e:
            log(f"Telegram location error: {e}", "ERROR")
            return False


# ============================================================================
# EMAIL MODULE
# ============================================================================

class EmailNotifier:
    """Send email notifications"""

    def __init__(self, config: dict):
        self.smtp_config = config.get('smtp', {})
        self.notification_email = config.get('notification_email', '')

    def send(self, event_data: dict, photos: List[str], audio_path: Optional[str] = None) -> bool:
        """Send email notification with all attachments"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['sender_email']
            msg['To'] = self.notification_email
            msg['Subject'] = f"[LOGIN MONITOR] {event_data['event_type']} - {event_data['hostname']}"

            # Build email body
            body = self._build_body(event_data)
            msg.attach(MIMEText(body, 'plain'))

            # Attach photos
            for i, photo in enumerate(photos):
                if os.path.exists(photo):
                    with open(photo, 'rb') as f:
                        img = MIMEImage(f.read())
                        img.add_header('Content-Disposition', 'attachment', filename=f'photo_{i+1}.jpg')
                        msg.attach(img)

            # Attach audio
            if audio_path and os.path.exists(audio_path):
                with open(audio_path, 'rb') as f:
                    audio = MIMEAudio(f.read(), _subtype='wav')
                    audio.add_header('Content-Disposition', 'attachment', filename='audio_recording.wav')
                    msg.attach(audio)

            # Send email
            if self.smtp_config.get('use_ssl', True):
                server = smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'])
            else:
                server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
                if self.smtp_config.get('use_tls', False):
                    server.starttls()

            server.login(self.smtp_config['sender_email'], self.smtp_config['password'])
            server.send_message(msg)
            server.quit()

            log("Email notification sent")
            return True

        except Exception as e:
            log(f"Email error: {e}", "ERROR")
            return False

    def _build_body(self, data: dict) -> str:
        """Build email body text"""
        location = data.get('location', {})
        battery = data.get('battery', {})
        wifi = data.get('wifi', {})
        face_info = data.get('face_recognition', {})

        body = f"""
{'='*60}
🚨 LOGIN/UNLOCK EVENT DETECTED 🚨
{'='*60}

EVENT DETAILS:
--------------
Type: {data['event_type']}
Time: {data['timestamp']}
Event ID: {data['id']}

SYSTEM:
-------
Hostname: {data['hostname']}
User: {data['user']}
OS: {data['os']}

NETWORK:
--------
Local IP: {data['local_ip']}
Public IP: {data['public_ip']}
"""

        if wifi.get('available'):
            body += f"""
WiFi Network: {wifi.get('ssid', 'Unknown')}
Signal Strength: {wifi.get('signal_strength', 'Unknown')} dBm
"""

        if battery.get('available'):
            body += f"""
BATTERY:
--------
Level: {battery.get('percentage', 'Unknown')}%
Status: {battery.get('status', 'Unknown')}
"""

        body += f"""
LOCATION (FOR THEFT RECOVERY):
------------------------------
Latitude: {location.get('latitude', 'Unknown')}
Longitude: {location.get('longitude', 'Unknown')}
Accuracy: {location.get('accuracy_meters', 'Unknown')}
City: {location.get('city', 'N/A')}
Source: {location.get('source', 'Unknown')}

📍 GOOGLE MAPS: {location.get('google_maps', 'Unable to determine')}
"""

        if face_info.get('available'):
            body += f"""
FACE RECOGNITION:
-----------------
Faces Detected: {face_info.get('face_count', 0)}
"""
            for face in face_info.get('faces', []):
                status = "✓ KNOWN" if face['is_known'] else "⚠️ UNKNOWN"
                body += f"  - {face['name']} ({status})\n"

        body += f"""
{'='*60}
Photos: {data.get('photo_count', 0)} attached
Audio: {'Yes' if data.get('audio_path') else 'No'}
{'='*60}
"""
        return body


# ============================================================================
# ANTI-THEFT MODULE
# ============================================================================

class AntiTheft:
    """Anti-theft features: alarm, screen message"""

    @staticmethod
    def play_alarm(duration: int = 30):
        """Play loud alarm sound"""
        if platform.system() != "Darwin":
            return

        log(f"Playing alarm for {duration} seconds...")

        # Play system alert sound repeatedly
        try:
            import threading

            def alarm_loop():
                end_time = time.time() + duration
                while time.time() < end_time:
                    subprocess.run(
                        ["afplay", "/System/Library/Sounds/Sosumi.aiff"],
                        capture_output=True
                    )
                    # Also set volume to max
                    subprocess.run(
                        ["osascript", "-e", "set volume output volume 100"],
                        capture_output=True
                    )

            thread = threading.Thread(target=alarm_loop)
            thread.start()

        except Exception as e:
            log(f"Alarm error: {e}", "ERROR")

    @staticmethod
    def show_screen_message(message: str = "This device has been reported stolen. Please contact the owner."):
        """Display full-screen message"""
        if platform.system() != "Darwin":
            return

        try:
            # Use AppleScript to show dialog
            script = f'''
            tell application "System Events"
                display dialog "{message}" buttons {{"OK"}} default button "OK" with icon stop giving up after 300
            end tell
            '''

            subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            log("Screen message displayed")

        except Exception as e:
            log(f"Screen message error: {e}", "ERROR")

    @staticmethod
    def lock_screen():
        """Lock the screen immediately"""
        if platform.system() == "Darwin":
            subprocess.run(
                ["pmset", "displaysleepnow"],
                capture_output=True
            )


# ============================================================================
# MAIN MONITOR CLASS
# ============================================================================

class LoginMonitorPro:
    """Main monitoring class"""

    def __init__(self):
        ensure_dirs()
        self.config = ConfigManager.load()

        # Initialize Supabase notifier (primary)
        self.supabase = None
        if HAS_SUPABASE:
            supabase_config = self.config.get('supabase', {})
            if supabase_config.get('url') and supabase_config.get('device_id'):
                self.supabase = SupabaseNotifier(
                    url=supabase_config.get('url', ''),
                    anon_key=supabase_config.get('anon_key', ''),
                    service_key=supabase_config.get('service_key', supabase_config.get('anon_key', '')),
                    device_id=supabase_config.get('device_id', '')
                )

        # Initialize Telegram notifier (legacy fallback)
        self.telegram = TelegramNotifier(
            self.config.get('telegram', {}).get('bot_token', ''),
            self.config.get('telegram', {}).get('chat_id', '')
        )

        self.email = EmailNotifier(self.config)
        self.face_recognition = FaceRecognition() if HAS_FACE_RECOGNITION else None

    def trigger(self, event_type: str = "Login"):
        """Main trigger function"""
        log(f"\n{'='*60}")
        log(f"LOGIN MONITOR PRO - Event: {event_type}")
        log(f"{'='*60}")

        features = self.config.get('features', {})

        # Collect system info
        sys_info = SystemInfo.collect_all()

        # Capture photos
        photo_count = features.get('photo_count', 3) if features.get('multi_photo', True) else 1
        photo_delay = features.get('photo_delay', 2)
        photos = Capture.capture_photos(count=photo_count, delay=photo_delay)

        # Record audio
        audio_path = None
        if features.get('audio_recording', False):
            audio_duration = features.get('audio_duration', 10)
            audio_path = Capture.record_audio(duration=audio_duration)

        # Face recognition
        face_info = {"available": False}
        if features.get('face_recognition', False) and photos and self.face_recognition:
            face_info = self.face_recognition.identify(photos[0])

        # Activity capture
        activity_data = {}
        try:
            from activity_monitor import trigger_on_event
            activity_report = trigger_on_event()
            activity_data = {
                "browser_history_count": activity_report.get("browser_history_count", 0),
                "recent_files_count": activity_report.get("recent_files_count", 0),
                "running_apps": activity_report.get("running_apps", []),
                "usb_devices": activity_report.get("usb_devices", []),
                "activity_screenshot": activity_report.get("screenshot")
            }
            log("Activity captured")
        except Exception as e:
            log(f"Activity capture error: {e}", "WARNING")

        # Create event data
        event_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        event_data = {
            'id': event_id,
            'event_type': event_type,
            'timestamp': sys_info['time'],
            'hostname': sys_info['hostname'],
            'user': sys_info['user'],
            'os': sys_info['os'],
            'local_ip': sys_info['local_ip'],
            'public_ip': sys_info['public_ip'],
            'location': sys_info['location'],
            'battery': sys_info['battery'],
            'wifi': sys_info['wifi'],
            'photos': photos,
            'photo_count': len(photos),
            'audio_path': audio_path,
            'face_recognition': face_info,
            'activity': activity_data,
            'status': 'pending'
        }

        # Save event
        event_file = EVENTS_DIR / f"{event_id}.json"
        with open(event_file, 'w') as f:
            json.dump(event_data, f, indent=2)
        log(f"Event saved: {event_id}")

        # Send notifications
        self._send_notifications(event_data, photos, audio_path)

        # Update event status
        event_data['status'] = 'sent'
        with open(event_file, 'w') as f:
            json.dump(event_data, f, indent=2)

        log(f"{'='*60}")
        log("Done!")
        log(f"{'='*60}\n")

    def _send_notifications(self, event_data: dict, photos: List[str], audio_path: Optional[str]):
        """Send all notifications"""
        location = event_data.get('location', {})

        # Send to Supabase (primary - for Flutter app)
        if self.supabase and self.supabase.enabled:
            try:
                result = self.supabase.send_event(event_data, photos)
                if result:
                    log("Supabase event sent")

                    # Send FCM push notification for instant mobile alert
                    if HAS_FCM:
                        try:
                            device_id = self.config.get('supabase', {}).get('device_id')
                            if device_id:
                                send_event_notification(
                                    device_id=device_id,
                                    event_type=event_data['event_type'],
                                    username=event_data.get('user'),
                                    hostname=event_data.get('hostname')
                                )
                        except Exception as fcm_err:
                            log(f"FCM notification error: {fcm_err}", "WARNING")

                    # Run threat detection analysis
                    if HAS_THREAT_DETECTION:
                        try:
                            detector = ThreatDetector(self.config)
                            threats = detector.analyze_event(event_data)
                            for threat in threats:
                                log(f"Threat detected: {threat.get('title')} (Severity: {threat.get('severity')})")
                                detector.execute_action(threat, event_data)
                        except Exception as threat_err:
                            log(f"Threat detection error: {threat_err}", "WARNING")
                else:
                    log("Supabase event failed", "WARNING")
            except Exception as e:
                log(f"Supabase error: {e}", "ERROR")

        # Send Telegram notification (legacy fallback)
        if self.telegram.enabled:
            # Build message
            msg = f"""
🚨 <b>{event_data['event_type'].upper()} DETECTED</b>

⏰ <b>Time:</b> {event_data['timestamp']}
💻 <b>Host:</b> {event_data['hostname']}
👤 <b>User:</b> {event_data['user']}

🌐 <b>Public IP:</b> {event_data['public_ip']}
📶 <b>WiFi:</b> {event_data.get('wifi', {}).get('ssid', 'Unknown')}
🔋 <b>Battery:</b> {event_data.get('battery', {}).get('percentage', 'N/A')}%

📍 <b>Location:</b>
{location.get('google_maps', 'Unknown')}
"""
            self.telegram.send_message(msg)

            # Send photos
            for photo in photos[:3]:  # Max 3 photos to Telegram
                self.telegram.send_photo(photo, f"📸 {event_data['event_type']} - {event_data['timestamp']}")

            # Send location
            if location.get('latitude') and location.get('longitude'):
                try:
                    self.telegram.send_location(float(location['latitude']), float(location['longitude']))
                except:
                    pass

        # Send email
        self.email.send(event_data, photos, audio_path)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def show_status():
    """Show current status and recent events"""
    ensure_dirs()

    print("\n" + "="*70)
    print("LOGIN MONITOR PRO - STATUS")
    print("="*70)

    # Check features
    print("\nFEATURE STATUS:")
    print(f"  Supabase:         {'✓' if HAS_SUPABASE else '✗'}")
    print(f"  Telegram:         {'✓' if HAS_TELEGRAM else '✗'}")
    print(f"  Encryption:       {'✓' if HAS_CRYPTO else '✗'}")
    print(f"  Face Recognition: {'✓' if HAS_FACE_RECOGNITION else '✗'}")
    print(f"  Audio Recording:  {'✓' if HAS_AUDIO else '✗'}")
    print(f"  CoreLocation:     {'✓' if HAS_CORELOCATION else '✗'}")
    print(f"  Threat Detection: {'✓' if HAS_THREAT_DETECTION else '✗'}")
    print(f"  FCM Push:         {'✓' if HAS_FCM else '✗'}")

    # Recent events
    events = list(EVENTS_DIR.glob("*.json"))
    events.sort(reverse=True)

    print(f"\nRECENT EVENTS ({len(events)} total):")
    print("-"*70)

    for event_file in events[:10]:
        try:
            with open(event_file, 'r') as f:
                event = json.load(f)
            status_icon = "✓" if event.get('status') == 'sent' else "⏳"
            print(f"  {status_icon} {event['timestamp']} | {event['event_type']:10} | {event['user']}")
        except:
            pass

    print("="*70 + "\n")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--status":
            show_status()
        elif arg == "--alarm":
            AntiTheft.play_alarm(30)
        elif arg == "--message":
            msg = sys.argv[2] if len(sys.argv) > 2 else "This device is stolen!"
            AntiTheft.show_screen_message(msg)
        elif arg == "--lock":
            AntiTheft.lock_screen()
        elif arg == "--help":
            print("""
Login Monitor PRO - Usage:
  python3 pro_monitor.py [EVENT]     - Trigger event (Login, Unlock, Wake, etc.)
  python3 pro_monitor.py --status    - Show status and recent events
  python3 pro_monitor.py --alarm     - Play alarm sound
  python3 pro_monitor.py --message   - Show screen message
  python3 pro_monitor.py --lock      - Lock screen
  python3 pro_monitor.py --help      - Show this help
""")
        else:
            monitor = LoginMonitorPro()
            monitor.trigger(arg)
    else:
        monitor = LoginMonitorPro()
        monitor.trigger("Login")


if __name__ == "__main__":
    main()
