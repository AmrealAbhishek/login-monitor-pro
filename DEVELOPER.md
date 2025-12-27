# Login Monitor PRO - Developer Documentation

This document provides technical details for developers who want to understand, modify, or extend Login Monitor PRO.

---

## Architecture Overview

```
login-monitor/
├── install.sh              # One-click installer script
├── uninstall.sh            # Uninstaller script
├── config.json             # Runtime configuration
├── screen_watcher.py       # Main event detector (runs as LaunchAgent)
├── pro_monitor.py          # Core monitoring logic & notifications
├── telegram_bot.py         # Telegram bot for remote commands
├── login_monitor.py        # Legacy monitor (deprecated)
├── README.md               # User documentation
└── DEVELOPER.md            # This file
```

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        LaunchAgents                             │
├─────────────────────────────────────────────────────────────────┤
│  com.loginmonitor.screen.plist                                  │
│  └── screen_watcher.py (always running)                         │
│       └── Monitors screen lock/unlock/wake events               │
│       └── Triggers pro_monitor.py on events                     │
│                                                                 │
│  com.loginmonitor.telegram.plist                                │
│  └── telegram_bot.py (always running)                           │
│       └── Listens for Telegram commands                         │
│       └── Executes commands using pro_monitor.py                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      pro_monitor.py                             │
├─────────────────────────────────────────────────────────────────┤
│  SystemInfo     - Collects device info, location, battery       │
│  Capture        - Takes photos, records audio                   │
│  EmailNotifier  - Sends email notifications                     │
│  TelegramNotifier - Sends Telegram notifications                │
│  EventStore     - Stores events locally for offline queue       │
│  AntiTheft      - Lock, alarm, message functions                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. screen_watcher.py

The main event detector that runs continuously as a LaunchAgent.

**Key Features:**
- Uses macOS Quartz framework to detect screen state changes
- Monitors `CGSessionCopyCurrentDictionary()` for lock/unlock
- Implements cooldown to prevent duplicate triggers
- Spawns `pro_monitor.py` as subprocess for event handling

**How it works:**

```python
from Quartz import CGSessionCopyCurrentDictionary

def check_screen_state():
    session = CGSessionCopyCurrentDictionary()
    if session:
        locked = session.get('CGSSessionScreenIsLocked', False)
        on_console = session.get('kCGSSessionOnConsoleKey', True)
        return not locked and on_console
    return False
```

**Event Detection:**
- Polls screen state every 2 seconds
- Triggers on transition from locked → unlocked
- 10-second cooldown between triggers

### 2. pro_monitor.py

Core monitoring and notification logic.

**Classes:**

| Class | Purpose |
|-------|---------|
| `ConfigManager` | Loads/saves configuration |
| `SystemInfo` | Collects device information |
| `Capture` | Photo and audio capture |
| `EmailNotifier` | SMTP email sending |
| `TelegramNotifier` | Telegram API integration |
| `EventStore` | Local event storage |
| `AntiTheft` | Security features |
| `LoginMonitorPro` | Main orchestrator |

**SystemInfo Methods:**

```python
SystemInfo.get_hostname()      # Device hostname
SystemInfo.get_username()      # Current user
SystemInfo.get_local_ip()      # Local network IP
SystemInfo.get_public_ip()     # External IP via API
SystemInfo.get_location()      # GPS + IP-based fallback
SystemInfo.get_battery_status() # Battery percentage
SystemInfo.get_wifi_network()  # Connected WiFi SSID
SystemInfo.collect_all()       # All info combined
```

**Location Detection:**

Uses CoreLocation framework with IP-based fallback:

```python
from CoreLocation import CLLocationManager, kCLLocationAccuracyBest

class LocationDelegate(NSObject):
    def locationManager_didUpdateLocations_(self, manager, locations):
        location = locations[-1]
        lat = location.coordinate().latitude
        lon = location.coordinate().longitude
```

Fallback uses ipinfo.io API when GPS unavailable.

### 3. telegram_bot.py

Telegram bot for remote command execution.

**Command Processing:**

```python
def handle_command(self, command, args, chat_id):
    # Verify authorized chat_id
    if str(chat_id) != self.chat_id:
        return  # Ignore unauthorized users

    if command == "/photo":
        self.cmd_photo()
    elif command == "/location":
        self.cmd_location()
    # ... etc
```

**API Communication:**

Uses stdlib `urllib.request` (no external dependencies):

```python
def send_message(self, text):
    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    data = json.dumps({
        "chat_id": self.chat_id,
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)
```

**WiFi Detection (CoreWLAN):**

```python
from CoreWLAN import CWWiFiClient

client = CWWiFiClient.sharedWiFiClient()
interface = client.interface()
ssid = interface.ssid()
rssi = interface.rssiValue()
```

---

## Dependencies

### System Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| imagesnap | Camera capture | `brew install imagesnap` |
| sox | Audio recording | `brew install sox` |

### Python Dependencies

| Package | Purpose |
|---------|---------|
| `pyobjc-framework-Quartz` | Screen state detection |
| `pyobjc-framework-CoreLocation` | GPS location |
| `pyobjc-framework-CoreWLAN` | WiFi network info |
| `pyobjc-framework-Cocoa` | macOS integration |
| `cryptography` | Encrypted config (optional) |

**Install all:**
```bash
pip3 install pyobjc-framework-Quartz pyobjc-framework-CoreLocation \
             pyobjc-framework-CoreWLAN pyobjc-framework-Cocoa cryptography
```

---

## LaunchAgents

Located in `~/Library/LaunchAgents/`

### com.loginmonitor.screen.plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.screen</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/xxx/.login-monitor/screen_watcher.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

**Key Settings:**
- `RunAtLoad`: Starts on login
- `KeepAlive`: Restarts if crashed
- `EnvironmentVariables.PATH`: Includes Homebrew paths for imagesnap

### Managing LaunchAgents

```bash
# Load (start)
launchctl load ~/Library/LaunchAgents/com.loginmonitor.screen.plist

# Unload (stop)
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.screen.plist

# Check status
launchctl list | grep loginmonitor

# View logs
tail -f /tmp/loginmonitor-screen.log
```

---

## Configuration Schema

`config.json`:

```json
{
    "notification_email": "string (required)",
    "smtp": {
        "server": "string",
        "port": "integer",
        "sender_email": "string",
        "password": "string",
        "use_ssl": "boolean",
        "use_tls": "boolean"
    },
    "telegram": {
        "enabled": "boolean",
        "bot_token": "string",
        "chat_id": "string"
    },
    "features": {
        "multi_photo": "boolean",
        "photo_count": "integer (1-10)",
        "photo_delay": "integer (seconds)",
        "audio_recording": "boolean",
        "audio_duration": "integer (seconds)",
        "face_recognition": "boolean",
        "daily_summary": "boolean"
    },
    "cooldown_seconds": "integer"
}
```

---

## Event Storage

Events are stored as JSON in `~/.login-monitor/events/`:

```json
{
    "id": "uuid",
    "type": "login|unlock|wake",
    "timestamp": "ISO 8601",
    "hostname": "string",
    "username": "string",
    "local_ip": "string",
    "public_ip": "string",
    "location": {
        "latitude": "float",
        "longitude": "float",
        "accuracy_meters": "float",
        "source": "gps|ip",
        "city": "string"
    },
    "wifi": {
        "ssid": "string",
        "signal": "integer (dBm)"
    },
    "photos": ["path1", "path2"],
    "sent": {
        "email": "boolean",
        "telegram": "boolean"
    }
}
```

**Offline Queue:**

When internet unavailable:
1. Event saved with `sent.email = false`
2. Background process checks for unsent events
3. Sends when internet restored
4. Updates `sent` flags

---

## Camera Capture

Uses `imagesnap` for reliable background capture:

```python
def capture_photo():
    output_path = f"/tmp/capture_{time.time()}.jpg"
    subprocess.run([
        "/opt/homebrew/bin/imagesnap",
        "-q",           # Quiet mode
        "-w", "0.5",    # Warmup delay
        output_path
    ], capture_output=True)
    return output_path
```

**Why imagesnap vs OpenCV:**
- Works in LaunchAgent context
- Proper permission handling
- Lightweight (no heavy dependencies)
- Reliable camera detection

---

## Extending the Bot

### Adding a New Command

1. Add handler in `telegram_bot.py`:

```python
def handle_command(self, command, args, chat_id):
    # ... existing commands ...
    elif command == "/mycommand":
        self.cmd_mycommand(args)

def cmd_mycommand(self, args):
    # Implement your command
    result = do_something(args)
    self.send_message(f"Result: {result}")
```

2. Update `/help` command to document it

### Adding System Info

Add method to `SystemInfo` class in `pro_monitor.py`:

```python
@staticmethod
def get_my_info():
    # Collect information
    return {"key": "value"}
```

Call from `collect_all()` to include in status reports.

---

## Debugging

### Enable Verbose Logging

In any Python file, add:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Components Individually

```bash
# Test camera
/opt/homebrew/bin/imagesnap /tmp/test.jpg

# Test location
python3 -c "from pro_monitor import SystemInfo; print(SystemInfo.get_location())"

# Test WiFi
python3 -c "from CoreWLAN import CWWiFiClient; print(CWWiFiClient.sharedWiFiClient().interface().ssid())"

# Test Telegram
python3 -c "from telegram_bot import TelegramBot; bot = TelegramBot(); bot.send_message('Test')"
```

### Common Issues

**"CGSessionCopyCurrentDictionary returns None"**
- Quartz not imported correctly
- Running in unsupported context

**"imagesnap: command not found"**
- Use absolute path: `/opt/homebrew/bin/imagesnap`
- Or Intel Mac: `/usr/local/bin/imagesnap`

**"CoreLocation authorization denied"**
- Grant in System Preferences > Privacy > Location Services
- May need to add Python/Terminal to allowed apps

---

## Security Considerations

### Credentials Storage

Current: Plain text in `config.json` with 600 permissions

Better approach (implemented but optional):

```python
from cryptography.fernet import Fernet

class Encryption:
    @staticmethod
    def encrypt(data, key):
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()

    @staticmethod
    def decrypt(data, key):
        f = Fernet(key)
        return f.decrypt(data.encode()).decode()
```

### Chat ID Verification

All Telegram commands verify sender:

```python
if str(chat_id) != self.chat_id:
    log(f"Unauthorized: {chat_id}")
    return  # Silently ignore
```

### File Permissions

Installer sets restrictive permissions:

```bash
chmod 600 ~/.login-monitor/config.json
chmod 700 ~/.login-monitor/
```

---

## Testing

### Manual Testing Checklist

1. **Screen Lock/Unlock**
   - Lock screen (Cmd+Ctrl+Q)
   - Unlock
   - Verify email/Telegram received

2. **Telegram Commands**
   - `/photo` - Check photo received
   - `/location` - Verify coordinates
   - `/wifi` - Check SSID shown
   - `/alarm` - Hear sound
   - `/lock` - Screen locks
   - `/message Test` - See popup

3. **Offline Queue**
   - Disable WiFi
   - Trigger event
   - Enable WiFi
   - Verify delayed send

### Automated Tests

```python
# tests/test_system_info.py
import unittest
from pro_monitor import SystemInfo

class TestSystemInfo(unittest.TestCase):
    def test_hostname(self):
        hostname = SystemInfo.get_hostname()
        self.assertIsInstance(hostname, str)
        self.assertTrue(len(hostname) > 0)

    def test_local_ip(self):
        ip = SystemInfo.get_local_ip()
        self.assertRegex(ip, r'\d+\.\d+\.\d+\.\d+')
```

---

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

### Code Style

- Python 3.9+ compatible
- Use type hints where helpful
- Document public methods
- Handle exceptions gracefully
- Log errors but don't crash

---

## Future Improvements

- [ ] Windows/Linux support
- [ ] Face recognition alerts
- [ ] Web dashboard
- [ ] Cloud backup integration
- [ ] Geofencing alerts
- [ ] Multiple device management
- [ ] End-to-end encryption
- [ ] Two-factor authentication for Telegram
