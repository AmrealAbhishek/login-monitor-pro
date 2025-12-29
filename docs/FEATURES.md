# Features Overview

Complete list of Login Monitor PRO features.

---

## Table of Contents

1. [Core Monitoring](#core-monitoring)
2. [Anti-Theft Features](#anti-theft-features)
3. [Threat Detection](#threat-detection)
4. [Data Loss Prevention](#data-loss-prevention)
5. [Productivity Monitoring](#productivity-monitoring)
6. [Notifications & Alerts](#notifications--alerts)
7. [Remote Commands](#remote-commands)
8. [Reporting & Analytics](#reporting--analytics)

---

## Core Monitoring

### Event Detection
| Event Type | Description | Trigger |
|------------|-------------|---------|
| Login | User logs into Mac | System authentication |
| Unlock | Screen unlocked | Password/TouchID entry |
| Wake | Mac wakes from sleep | Lid open, key press |
| Custom | Manual trigger | API/command |

### Data Captured Per Event

| Data | Description | Source |
|------|-------------|--------|
| Timestamp | Event time (IST) | System clock |
| Hostname | Computer name | System |
| Username | Logged-in user | System |
| Local IP | Internal network IP | Network |
| Public IP | External IP address | ip-api.com |
| Location | GPS coordinates | CoreLocation |
| City/Country | Reverse geocoded | IP geolocation |
| Photos | Webcam captures | imagesnap/OpenCV |
| Audio | Microphone recording | PyAudio |
| Battery | Charge %, AC status | IOKit |
| WiFi | SSID, signal strength | CoreWLAN |
| Face Recognition | Known/unknown faces | face_recognition |

### Multi-Photo Capture
- Configurable photo count (1-10)
- Delay between photos (0.5-5 seconds)
- Burst mode for better facial capture
- Auto-brightness adjustment

### Audio Recording
- Configurable duration (5-60 seconds)
- WAV format output
- Ambient sound capture
- Voice recording capability

---

## Anti-Theft Features

### Remote Lock
Lock the Mac screen immediately from mobile app or dashboard.

```
Command: lock
Result: Screen locks, requires password to unlock
```

### Alarm
Play loud alarm sound to locate or deter theft.

```
Command: alarm
Duration: 30 seconds (configurable)
Volume: Maximum
Sound: System alert sound
```

### Screen Message
Display full-screen message on the Mac.

```
Command: message
Parameters: {"text": "This device is stolen. Contact: 555-1234"}
Display: Modal dialog, stays on screen
```

### Location Tracking
Real-time GPS location with map visualization.

```
Command: location
Response: {
  "latitude": 28.6139,
  "longitude": 77.2090,
  "accuracy": 10,
  "city": "New Delhi",
  "country": "India",
  "google_maps_link": "https://maps.google.com/..."
}
```

### Find My Mac
Locate device on map with:
- Current GPS coordinates
- Address (reverse geocoded)
- Accuracy radius
- Last update time
- Location history

### Geofencing
Create virtual boundaries and get alerts when device enters/exits.

```python
Geofence: {
  "name": "Office",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "radius_meters": 500,
  "trigger_on": ["exit", "enter"]
}
```

---

## Threat Detection

### Unusual Time Detection
Alerts on logins during suspicious hours.

| Time Range | Severity | Action |
|------------|----------|--------|
| 2:00 AM - 6:00 AM | HIGH | Alert + Screenshot |
| 12:00 AM - 2:00 AM | MEDIUM | Alert |
| 6:00 AM - 9:00 AM | LOW | Log only |

### New Location Detection
Detects first-time login from unknown IP/city.

```
Trigger: Login from IP not seen before
Data: IP, City, Country, ISP
Action: Alert + Store as known location
```

### After-Hours Detection
Alerts on activity outside business hours.

```python
Config: {
  "work_start": "09:00",
  "work_end": "18:00",
  "work_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
  "alert_weekends": true
}
```

### Failed Login Detection
Monitors brute-force attack attempts.

| Threshold | Time Window | Action |
|-----------|-------------|--------|
| 3 failures | 5 minutes | Screenshot + Alert |
| 5 failures | 5 minutes | Screenshot + Lock |
| 10 failures | 10 minutes | Screenshot + Lock + Alarm |

### Suspicious Activity Detection
Monitors for potentially malicious activities.

| Activity | Severity | Action |
|----------|----------|--------|
| Remote access tool (TeamViewer, AnyDesk) | HIGH | Alert |
| VPN connection | MEDIUM | Log |
| Mass file operations (>100 files/min) | HIGH | Alert + Screenshot |
| USB device connected | MEDIUM | Log |
| Unusual app launch | LOW | Log |

### Face Recognition
Identifies known vs unknown persons.

```python
Features:
- Known face database (add trusted users)
- Unknown face detection (potential intruder)
- Multiple face detection per image
- Face matching confidence score
```

---

## Data Loss Prevention

See [DLP Guide](DLP.md) for detailed information.

### Quick Summary

| DLP Feature | What It Monitors | Actions |
|-------------|------------------|---------|
| Clipboard | Credit cards, SSN, API keys, passwords | Alert, Block |
| USB | File transfers to external drives | Alert, Block, Log |
| Files | Sensitive file access (.pem, .env, .key) | Alert, Screenshot |
| Browser | URL visits, blocked domains | Block, Alert, Log |
| Shadow IT | Unauthorized apps (ChatGPT, Dropbox) | Alert, Block |
| Keystrokes | Typing patterns (not content) | Log |

---

## Productivity Monitoring

### Application Tracking
Monitors foreground application usage.

| Category | Example Apps | Classification |
|----------|--------------|----------------|
| Productive | VS Code, Xcode, Terminal, Office | Green |
| Unproductive | Netflix, YouTube, Games, Social | Red |
| Communication | Slack, Teams, Zoom, Email | Yellow |
| Neutral | Finder, System Settings | Gray |

### Metrics Captured

| Metric | Description | Calculation |
|--------|-------------|-------------|
| Active Time | Time app in foreground | Continuous tracking |
| Idle Time | No keyboard/mouse activity | 5-minute threshold |
| Productivity Score | Productive / Total time | Percentage |
| App Switches | How often user changes apps | Count per hour |

### Idle Detection
- 5-minute idle threshold
- Keyboard/mouse activity tracking
- Excludes idle time from productivity

### Activity Reports
- Daily productivity summary
- Weekly trend analysis
- App usage breakdown
- Peak productivity hours

---

## Notifications & Alerts

### Notification Channels

| Channel | Use Case | Latency |
|---------|----------|---------|
| FCM Push | Mobile app alerts | Instant |
| Email | Detailed event reports | 1-5 seconds |
| Telegram | Quick alerts with photos | 1-3 seconds |
| Dashboard | Real-time monitoring | Real-time |
| Webhook | SIEM integration | 1-5 seconds |

### Email Notifications
Detailed email with:
- Event summary
- Photo attachments (multiple)
- Audio attachment
- Location with map link
- System information
- Face recognition results

### Push Notifications
Instant mobile alerts with:
- Event type
- Device name
- Quick action buttons
- Deep link to event details

### Telegram Notifications
- Text message with event details
- Photo attachment
- Location sharing
- Interactive commands

---

## Remote Commands

### Available Commands

| Command | Description | Returns |
|---------|-------------|---------|
| `photo` | Capture webcam photo | Photo URL |
| `location` | Get GPS location | Coordinates, address |
| `audio` | Record audio | Audio URL |
| `alarm` | Play alarm sound | Success/failure |
| `lock` | Lock screen | Success/failure |
| `message` | Display message | Success/failure |
| `status` | Get device status | Battery, WiFi, location |
| `screenshot` | Capture screen | Screenshot URL |
| `apps` | List running apps | App list |
| `wifi` | Get WiFi info | SSID, signal |
| `battery` | Get battery status | %, charging |

### Command Execution Flow

```
1. User sends command (app/dashboard)
2. Command inserted to Supabase
3. Mac receives via Realtime
4. Mac executes command
5. Result updated in Supabase
6. App/dashboard shows result
```

### Command Status

| Status | Description |
|--------|-------------|
| pending | Command queued |
| executing | Command running |
| completed | Success |
| failed | Error occurred |

---

## Reporting & Analytics

### Report Types

| Report | Frequency | Contents |
|--------|-----------|----------|
| Daily | Every 24 hours | Events, alerts, app usage |
| Weekly | Every Monday | Trends, threats, productivity |
| Monthly | 1st of month | Summary, statistics, graphs |

### Report Contents
- Total events by type
- Security alerts summary
- Threat detection results
- App usage breakdown
- Productivity score trends
- DLP incidents
- Top applications used
- Login patterns

### Export Formats
- PDF (formatted report)
- CSV (raw data)
- JSON (API)
- Email delivery

### Scheduled Reports
```python
Config: {
  "daily_report": true,
  "weekly_report": true,
  "monthly_report": true,
  "recipients": ["admin@company.com", "security@company.com"],
  "send_time": "09:00"
}
```

---

## Feature Matrix

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Event Detection | ✓ | ✓ | ✓ |
| Photo Capture | 1 | 5 | Unlimited |
| Audio Recording | ✗ | ✓ | ✓ |
| Face Recognition | ✗ | ✓ | ✓ |
| Location Tracking | ✓ | ✓ | ✓ |
| Remote Lock | ✓ | ✓ | ✓ |
| Alarm | ✓ | ✓ | ✓ |
| DLP - Clipboard | ✗ | ✓ | ✓ |
| DLP - USB | ✗ | ✓ | ✓ |
| DLP - Files | ✗ | ✓ | ✓ |
| Shadow IT | ✗ | ✓ | ✓ |
| Productivity | ✗ | ✓ | ✓ |
| Geofencing | ✗ | ✓ | ✓ |
| SIEM Integration | ✗ | ✗ | ✓ |
| Custom Rules | ✗ | ✗ | ✓ |
| API Access | ✗ | ✗ | ✓ |
| Devices | 1 | 5 | Unlimited |
