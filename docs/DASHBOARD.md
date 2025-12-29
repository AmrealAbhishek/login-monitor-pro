# Web Dashboard Guide

Complete guide to the Login Monitor PRO web dashboard.

---

## Access

**URL:** https://web-dashboard-inky.vercel.app

**Login:** Use the same credentials as the mobile app.

---

## Dashboard Overview

### Main Dashboard (/)

The home page provides a quick overview of all monitored devices.

```
┌─────────────────────────────────────────────────────────────┐
│  LOGIN MONITOR PRO                              [Settings]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │  Devices  │  │  Events   │  │  Alerts   │  │  Online  │ │
│  │    12     │  │   156     │  │     3     │  │    10    │ │
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘ │
│                                                             │
│  Recent Events                          Active Alerts       │
│  ├── Login - MacBook-Pro (2 min ago)   ├── Unusual login   │
│  ├── Unlock - iMac-Office (5 min ago)  └── Failed logins   │
│  └── Wake - MacBook-Air (10 min ago)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Quick Stats
- **Devices:** Total paired devices
- **Events:** Events today
- **Alerts:** Unacknowledged alerts
- **Online:** Currently online devices

---

## Navigation

### Sidebar Menu

| Menu Item | Description |
|-----------|-------------|
| Dashboard | Overview with stats |
| Devices | Manage Mac computers |
| Events | View all events |
| Security | Threat alerts |
| DLP | Data loss prevention |
| Productivity | App usage analytics |
| Remote | Send commands |
| Alerts | All security alerts |
| Admin | Configuration |
| Settings | User settings |

---

## Devices Page (/devices)

Manage all paired Mac computers.

### Device List

| Column | Description |
|--------|-------------|
| Hostname | Computer name |
| Status | Online/Offline indicator |
| Last Seen | Time since last activity |
| OS | macOS version |
| IP | Public IP address |
| Actions | Commands, Settings, Unpair |

### Device Actions

- **Photo** - Capture photo now
- **Location** - Get current location
- **Lock** - Lock screen
- **Alarm** - Play alarm
- **Settings** - Device configuration
- **Unpair** - Remove device

### Device Details

Click a device to see:
- Full device information
- Recent events
- Command history
- Location history

---

## Events Page (/events)

View all login/unlock/wake events.

### Event List

| Column | Description |
|--------|-------------|
| Time | Event timestamp |
| Type | Login/Unlock/Wake |
| Device | Hostname |
| User | Username |
| Location | City, Country |
| Photos | Photo count |

### Filters

- **Device:** Filter by device
- **Type:** Filter by event type
- **Date Range:** Select date range
- **Search:** Search by hostname, user, IP

### Event Details

Click an event to see:
- Full photos gallery
- Map with location
- System information
- Battery and WiFi status
- Face recognition results
- Audio playback (if recorded)

---

## Security Page (/security)

Monitor security threats and alerts.

### Alert Types

| Type | Severity | Description |
|------|----------|-------------|
| Unusual Time | HIGH | Login at 2-6 AM |
| New Location | MEDIUM | First-time IP/city |
| After Hours | LOW | Activity outside work hours |
| Failed Logins | HIGH | Multiple failed attempts |
| Unknown Face | HIGH | Unrecognized person |

### Alert Actions

- **Acknowledge** - Mark as reviewed
- **Investigate** - View full details
- **Take Action** - Lock, alarm, etc.

---

## DLP Page (/dlp)

Data Loss Prevention monitoring and policies.

### Tabs

#### USB & Devices
- USB connection events
- File transfers to USB
- Blocked/allowed actions

#### Clipboard
- Sensitive data copied
- Source/destination apps
- Reveal button for forensics

#### Shadow IT
- Unauthorized apps detected
- AI tools, file sharing, remote access
- Risk level indicators

#### File Transfers
- File access events
- Create/modify/delete operations
- Alert triggers

#### Keystrokes
- Start keystroke logging
- View keystroke sessions
- Duration selection

#### SIEM/Webhooks
- Configure integrations
- Splunk, Sentinel, Slack, Teams
- Test webhooks

---

## Productivity Page (/productivity)

Application usage and productivity analytics.

### Metrics

- **Productivity Score:** % of productive time
- **Active Time:** Total active time
- **Idle Time:** Time with no activity
- **Top Apps:** Most used applications

### Charts

- Daily productivity trend
- App category breakdown
- Activity heatmap
- Weekly comparison

### App Categories

| Category | Color | Examples |
|----------|-------|----------|
| Productive | Green | VS Code, Xcode, Office |
| Unproductive | Red | Netflix, YouTube, Games |
| Communication | Yellow | Slack, Teams, Zoom |
| Neutral | Gray | Finder, Settings |

---

## Remote Page (/remote)

Send commands to Mac computers.

### Available Commands

| Command | Description |
|---------|-------------|
| Photo | Capture webcam photo |
| Location | Get GPS location |
| Audio | Record audio |
| Alarm | Play alarm sound |
| Lock | Lock screen |
| Message | Display message |
| Screenshot | Capture screen |
| Status | Get device status |

### Command Execution

1. Select device from dropdown
2. Click command button
3. Wait for execution (real-time status)
4. View result (photo, location, etc.)

### Command History

- See recent commands
- View results
- Re-execute commands

---

## Admin Pages (/admin)

Configure rules and policies.

### Device Groups (/admin/groups)

Create groups for organizing devices:
- Engineering
- Sales
- Marketing
- Executive

### App Rules (/admin/apps)

Configure app policies:
- Productive apps (whitelist)
- Unproductive apps (track)
- Blocked apps (alert/block)

### File Rules (/admin/file-rules)

Create file monitoring rules:
- Extension patterns (*.pem, *.key)
- Filename patterns (*password*)
- Path patterns (/Users/*/secrets/*)
- Actions (alert, block, log)

### URL Rules (/admin/url-rules)

Configure browser policies:
- Domain blocking
- Category blocking
- Keyword alerts
- Allowed domains

### Activity Rules (/admin/activity-rules)

Configure activity-based triggers:
- After-hours alerts
- Unusual time alerts
- Location-based rules

---

## Settings Page (/settings)

User account and preferences.

### Profile
- Display name
- Email address
- Password change

### Notifications
- Email preferences
- Push notification settings
- Alert thresholds

### API
- API key management
- Webhook configuration

### Data
- Export events
- Delete account

---

## Dark Theme

The dashboard uses a cyberpunk-style dark theme:

- Background: Dark (#0a0a0a)
- Cards: Slightly lighter (#111)
- Accent: Blue/Cyan
- Alerts: Red, Orange, Yellow
- Text: White, Gray

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `g` + `d` | Go to Dashboard |
| `g` + `e` | Go to Events |
| `g` + `s` | Go to Security |
| `g` + `r` | Go to Remote |
| `/` | Focus search |
| `Esc` | Close modal |

---

## Real-Time Updates

The dashboard uses Supabase Realtime for live updates:

- New events appear instantly
- Device status updates automatically
- Command results show in real-time
- No need to refresh the page

---

## Mobile Responsive

The dashboard is fully responsive:

- Desktop: Full sidebar
- Tablet: Collapsible sidebar
- Mobile: Bottom navigation
