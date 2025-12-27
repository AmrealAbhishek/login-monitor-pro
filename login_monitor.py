#!/usr/bin/env python3
"""
Login Monitor - Captures webcam image and sends email on login/wake events.
Supports macOS, Linux, and Windows.

Features:
- Captures webcam image on login/wake
- Sends email notification with image
- Gets public IP address
- Offline queue: saves events locally when no internet
- Auto-retry: sends pending events when internet is back
- Tracks sent/pending status for each event
"""

import os
import sys
import json
import smtplib
import platform
import subprocess
import tempfile
import shutil
import uuid
import urllib.request
import urllib.error
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from pathlib import Path

# Try to import cv2 (optional, used as fallback on non-Mac systems)
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# Try to import CoreLocation for GPS (macOS only)
try:
    import CoreLocation
    import objc
    HAS_CORELOCATION = True
except ImportError:
    HAS_CORELOCATION = False


SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
EVENTS_DIR = SCRIPT_DIR / "events"
IMAGES_DIR = SCRIPT_DIR / "captured_images"


def ensure_dirs():
    """Create necessary directories"""
    EVENTS_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)


def load_config():
    """Load configuration from config.json"""
    if not CONFIG_FILE.exists():
        print(f"Error: Config file not found at {CONFIG_FILE}")
        print("Please run: python3 setup.py to configure the tool")
        sys.exit(1)

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def check_internet():
    """Check if internet connection is available"""
    try:
        urllib.request.urlopen('https://www.google.com', timeout=5)
        return True
    except:
        return False


def get_public_ip():
    """Get public IP address"""
    services = [
        'https://api.ipify.org',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
        'https://checkip.amazonaws.com'
    ]

    for service in services:
        try:
            response = urllib.request.urlopen(service, timeout=5)
            return response.read().decode('utf-8').strip()
        except:
            continue

    return "Unknown (no internet)"


def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"


def get_gps_location():
    """Get GPS/location coordinates using macOS CoreLocation"""
    if platform.system() != "Darwin" or not HAS_CORELOCATION:
        return get_ip_based_location()

    try:
        # Create location manager
        manager = CoreLocation.CLLocationManager.alloc().init()

        # Request authorization
        manager.requestWhenInUseAuthorization()

        # Start updating location
        manager.startUpdatingLocation()

        # Wait for location (with timeout)
        import time
        timeout = 5
        start = time.time()

        while time.time() - start < timeout:
            location = manager.location()
            if location:
                lat = location.coordinate().latitude
                lon = location.coordinate().longitude
                accuracy = location.horizontalAccuracy()

                manager.stopUpdatingLocation()

                return {
                    'latitude': round(lat, 6),
                    'longitude': round(lon, 6),
                    'accuracy_meters': round(accuracy, 1),
                    'google_maps': f"https://www.google.com/maps?q={lat},{lon}",
                    'source': 'CoreLocation'
                }
            time.sleep(0.5)

        manager.stopUpdatingLocation()

    except Exception as e:
        print(f"CoreLocation error: {e}")

    # Fallback to IP-based location
    return get_ip_based_location()


def get_ip_based_location():
    """Get approximate location based on IP address"""
    try:
        # Try multiple IP geolocation services
        services = [
            'http://ip-api.com/json/',
            'https://ipapi.co/json/'
        ]

        for service in services:
            try:
                response = urllib.request.urlopen(service, timeout=5)
                data = json.loads(response.read().decode('utf-8'))

                # ip-api.com format
                if 'lat' in data and 'lon' in data:
                    lat, lon = data['lat'], data['lon']
                    city = data.get('city', 'Unknown')
                    region = data.get('regionName', '')
                    country = data.get('country', '')

                    return {
                        'latitude': lat,
                        'longitude': lon,
                        'accuracy_meters': 'City-level (~1-5 km)',
                        'city': city,
                        'region': region,
                        'country': country,
                        'google_maps': f"https://www.google.com/maps?q={lat},{lon}",
                        'source': 'IP Geolocation'
                    }

                # ipapi.co format
                if 'latitude' in data and 'longitude' in data:
                    lat, lon = data['latitude'], data['longitude']

                    return {
                        'latitude': lat,
                        'longitude': lon,
                        'accuracy_meters': 'City-level (~1-5 km)',
                        'city': data.get('city', 'Unknown'),
                        'region': data.get('region', ''),
                        'country': data.get('country_name', ''),
                        'google_maps': f"https://www.google.com/maps?q={lat},{lon}",
                        'source': 'IP Geolocation'
                    }

            except:
                continue

    except Exception as e:
        print(f"IP geolocation error: {e}")

    return {
        'latitude': 'Unknown',
        'longitude': 'Unknown',
        'accuracy_meters': 'Unknown',
        'google_maps': 'Unable to determine location',
        'source': 'Failed'
    }


def capture_image():
    """Capture image from webcam and save permanently"""
    ensure_dirs()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    image_filename = f"capture_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
    image_path = IMAGES_DIR / image_filename

    # On macOS, use imagesnap (handles permissions better)
    if platform.system() == "Darwin":
        return capture_with_imagesnap(str(image_path))

    # On other systems, use OpenCV
    return capture_with_opencv(str(image_path))


def capture_with_imagesnap(image_path):
    """Capture using imagesnap (macOS only)"""
    try:
        # Common locations for imagesnap
        imagesnap_paths = [
            "/opt/homebrew/bin/imagesnap",  # Apple Silicon Homebrew
            "/usr/local/bin/imagesnap",      # Intel Homebrew
            "imagesnap"                       # In PATH
        ]

        imagesnap_cmd = None
        for path in imagesnap_paths:
            if path == "imagesnap" or os.path.exists(path):
                imagesnap_cmd = path
                break

        if not imagesnap_cmd:
            print("Warning: imagesnap not installed. Install with: brew install imagesnap")
            return capture_with_opencv(image_path)

        # Capture image with imagesnap
        # -w 1.0 = warm-up time for camera
        result = subprocess.run(
            [imagesnap_cmd, "-w", "1.0", image_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and os.path.exists(image_path):
            print(f"Image captured with imagesnap: {image_path}")
            return image_path
        else:
            print(f"imagesnap failed: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("Warning: imagesnap timed out")
        return None
    except Exception as e:
        print(f"Warning: imagesnap error: {e}")
        return None


def capture_with_opencv(image_path):
    """Capture using OpenCV (cross-platform fallback)"""
    if not HAS_CV2:
        print("Warning: OpenCV not available")
        return None

    try:
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Warning: Could not open webcam")
            return None

        # Allow camera to warm up
        for _ in range(10):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("Warning: Could not capture image")
            return None

        cv2.imwrite(image_path, frame)
        print(f"Image captured with OpenCV: {image_path}")
        return image_path

    except Exception as e:
        print(f"Warning: OpenCV error: {e}")
        return None


def get_system_info():
    """Get system information for the notification"""
    print("Getting location...")
    location = get_gps_location()

    info = {
        'hostname': platform.node(),
        'os': platform.system(),
        'os_version': platform.version(),
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user': os.getenv('USER') or os.getenv('USERNAME') or 'Unknown',
        'local_ip': get_local_ip(),
        'public_ip': get_public_ip(),
        'location': location
    }

    return info


def save_event(event_type, sys_info, image_path):
    """Save event locally for tracking and offline queue"""
    ensure_dirs()

    event_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    event_data = {
        'id': event_id,
        'event_type': event_type,
        'timestamp': sys_info['time'],
        'hostname': sys_info['hostname'],
        'user': sys_info['user'],
        'os': sys_info['os'],
        'os_version': sys_info['os_version'],
        'local_ip': sys_info['local_ip'],
        'public_ip': sys_info['public_ip'],
        'location': sys_info.get('location', {}),
        'image_path': image_path,
        'status': 'pending',  # pending, sent, failed
        'send_attempts': 0,
        'last_attempt': None,
        'sent_at': None
    }

    event_file = EVENTS_DIR / f"{event_id}.json"
    with open(event_file, 'w') as f:
        json.dump(event_data, f, indent=2)

    print(f"Event saved: {event_id} (status: pending)")
    return event_id, event_data


def update_event_status(event_id, status, error=None):
    """Update event status in the local database"""
    event_file = EVENTS_DIR / f"{event_id}.json"

    if not event_file.exists():
        return

    with open(event_file, 'r') as f:
        event_data = json.load(f)

    event_data['status'] = status
    event_data['last_attempt'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    event_data['send_attempts'] += 1

    if status == 'sent':
        event_data['sent_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if error:
        event_data['last_error'] = str(error)

    with open(event_file, 'w') as f:
        json.dump(event_data, f, indent=2)

    print(f"Event {event_id} status updated: {status}")


def get_pending_events():
    """Get all pending events that haven't been sent"""
    ensure_dirs()
    pending = []

    for event_file in sorted(EVENTS_DIR.glob("*.json")):
        try:
            with open(event_file, 'r') as f:
                event_data = json.load(f)
            if event_data.get('status') == 'pending':
                pending.append(event_data)
        except:
            continue

    return pending


def send_email_for_event(config, event_data):
    """Send email notification for a specific event"""
    smtp_config = config['smtp']

    # Create message
    msg = MIMEMultipart()
    msg['From'] = smtp_config['sender_email']
    msg['To'] = config['notification_email']

    status_prefix = ""
    if event_data.get('send_attempts', 0) > 0:
        status_prefix = "[DELAYED] "

    msg['Subject'] = f"{status_prefix}[Login Monitor] {event_data['event_type']} detected on {event_data['hostname']}"

    # Get location data
    location = event_data.get('location', {})
    location_text = ""
    if location:
        location_text = f"""
LOCATION (FOR STOLEN DEVICE):
-----------------------------
Latitude: {location.get('latitude', 'Unknown')}
Longitude: {location.get('longitude', 'Unknown')}
Accuracy: {location.get('accuracy_meters', 'Unknown')}
City: {location.get('city', 'N/A')}
Region: {location.get('region', 'N/A')}
Country: {location.get('country', 'N/A')}
Source: {location.get('source', 'Unknown')}

>>> GOOGLE MAPS LINK:
{location.get('google_maps', 'Unable to determine')}
"""

    # Create email body
    body = f"""
{'='*50}
LOGIN/WAKE EVENT DETECTED
{'='*50}

Event Type: {event_data['event_type']}
Time: {event_data['timestamp']}
Event ID: {event_data['id']}

SYSTEM INFORMATION:
-------------------
Hostname: {event_data['hostname']}
User: {event_data['user']}
OS: {event_data['os']}

NETWORK INFORMATION:
--------------------
Local IP: {event_data['local_ip']}
Public IP: {event_data['public_ip']}
{location_text}
{'='*50}
{"Webcam image attached." if event_data.get('image_path') else "Could not capture webcam image."}
{'='*50}
"""

    msg.attach(MIMEText(body, 'plain'))

    # Attach image if available
    image_path = event_data.get('image_path')
    if image_path and os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            img_data = f.read()
            image = MIMEImage(img_data, name=os.path.basename(image_path))
            msg.attach(image)

    # Send email
    try:
        if smtp_config.get('use_ssl', True):
            server = smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port'])
        else:
            server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
            if smtp_config.get('use_tls', False):
                server.starttls()

        server.login(smtp_config['sender_email'], smtp_config['password'])
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {config['notification_email']}")
        return True, None
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False, str(e)


def process_pending_events(config):
    """Process all pending events and try to send them"""
    pending = get_pending_events()

    if not pending:
        print("No pending events to process.")
        return

    print(f"Found {len(pending)} pending event(s). Processing...")

    if not check_internet():
        print("No internet connection. Will retry later.")
        return

    for event_data in pending:
        event_id = event_data['id']
        print(f"Sending event: {event_id} ({event_data['event_type']} at {event_data['timestamp']})")

        success, error = send_email_for_event(config, event_data)

        if success:
            update_event_status(event_id, 'sent')
        else:
            update_event_status(event_id, 'pending', error)


def show_events_status():
    """Display status of all events"""
    ensure_dirs()

    events = []
    for event_file in sorted(EVENTS_DIR.glob("*.json")):
        try:
            with open(event_file, 'r') as f:
                events.append(json.load(f))
        except:
            continue

    if not events:
        print("No events recorded yet.")
        return

    print("\n" + "="*80)
    print("LOGIN MONITOR - EVENT LOG")
    print("="*80)
    print(f"{'Time':<20} {'Type':<10} {'Status':<10} {'Public IP':<15} {'User':<15}")
    print("-"*80)

    for e in events:
        status_icon = "✓" if e['status'] == 'sent' else "⏳" if e['status'] == 'pending' else "✗"
        print(f"{e['timestamp']:<20} {e['event_type']:<10} {status_icon} {e['status']:<8} {e['public_ip']:<15} {e['user']:<15}")

    print("-"*80)

    sent = len([e for e in events if e['status'] == 'sent'])
    pending = len([e for e in events if e['status'] == 'pending'])

    print(f"Total: {len(events)} | Sent: {sent} | Pending: {pending}")
    print("="*80 + "\n")


def main(event_type="Login"):
    """Main function - capture image, save event, and send notification"""
    print(f"\n{'='*50}")
    print(f"Login Monitor triggered - Event: {event_type}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # Load config
    config = load_config()

    # Capture image
    print("Capturing webcam image...")
    image_path = capture_image()
    if image_path:
        print(f"Image saved: {image_path}")

    # Get system info
    print("Gathering system information...")
    sys_info = get_system_info()
    print(f"Public IP: {sys_info['public_ip']}")
    print(f"Local IP: {sys_info['local_ip']}")

    # Save event locally (always, regardless of internet)
    event_id, event_data = save_event(event_type, sys_info, image_path)

    # Try to send notification
    print("\nChecking internet connection...")
    if check_internet():
        print("Internet available. Sending notification...")
        success, error = send_email_for_event(config, event_data)

        if success:
            update_event_status(event_id, 'sent')
        else:
            update_event_status(event_id, 'pending', error)
            print("Email queued for later delivery.")

        # Also try to send any previously pending events
        print("\nChecking for pending events...")
        process_pending_events(config)
    else:
        print("No internet connection. Event saved for later delivery.")
        print("The event will be sent automatically when internet is available.")

    print("\n" + "="*50)
    print("Done!")
    print("="*50 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--status":
            show_events_status()
        elif arg == "--retry":
            config = load_config()
            process_pending_events(config)
        elif arg == "--help":
            print("""
Login Monitor - Usage:
  python3 login_monitor.py [EVENT_TYPE]  - Record an event (Login, Wake, etc.)
  python3 login_monitor.py --status      - Show all events and their status
  python3 login_monitor.py --retry       - Retry sending pending events
  python3 login_monitor.py --help        - Show this help message
""")
        else:
            main(arg)
    else:
        main("Login")
