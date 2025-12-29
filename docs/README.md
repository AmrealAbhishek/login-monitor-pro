# Login Monitor PRO - Documentation

## Enterprise Security & Anti-Theft Solution for macOS

Login Monitor PRO is a comprehensive security monitoring system designed for enterprises to protect Mac computers from theft, unauthorized access, and data loss.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Installation Guide](INSTALLATION.md) | Step-by-step setup instructions |
| [Features Overview](FEATURES.md) | Complete feature list |
| [Commands Reference](COMMANDS.md) | All available commands |
| [DLP Guide](DLP.md) | Data Loss Prevention features |
| [Dashboard Guide](DASHBOARD.md) | Web dashboard usage |
| [Mobile App Guide](MOBILE_APP.md) | Flutter app features |
| [Configuration](CONFIGURATION.md) | Config options & settings |
| [API Reference](API.md) | Database schema & API |
| [Use Cases](USE_CASES.md) | Enterprise use cases |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues & fixes |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     LOGIN MONITOR PRO                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   macOS      │    │    Web       │    │   Mobile     │      │
│  │   Agent      │    │  Dashboard   │    │    App       │      │
│  │  (Python)    │    │  (Next.js)   │    │  (Flutter)   │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             │                                   │
│                    ┌────────▼────────┐                          │
│                    │    Supabase     │                          │
│                    │   (Backend)     │                          │
│                    │  PostgreSQL +   │                          │
│                    │  Realtime +     │                          │
│                    │  Storage        │                          │
│                    └─────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. macOS Agent (Python)
- Runs on Mac computers
- Detects login/unlock/wake events
- Captures photos, audio, location
- Monitors file access, clipboard, apps
- Executes remote commands
- DLP enforcement

### 2. Web Dashboard (Next.js)
- Real-time device monitoring
- Security alerts & threats
- DLP policy management
- Remote command execution
- Productivity analytics
- Admin configuration

### 3. Mobile App (Flutter)
- Push notifications for events
- Remote commands (photo, lock, alarm)
- Event history & details
- Device location tracking
- Geofence management

### 4. Backend (Supabase)
- PostgreSQL database
- Real-time subscriptions
- File storage (photos, audio)
- User authentication
- Row-level security

---

## Feature Categories

### Security & Anti-Theft
- Login/unlock event detection
- Webcam photo capture
- GPS location tracking
- Face recognition
- Remote lock & alarm
- Failed login detection

### Data Loss Prevention (DLP)
- Clipboard monitoring (credit cards, SSN, API keys)
- USB file transfer control
- Shadow IT detection (AI tools, file sharing)
- File access monitoring
- Browser URL filtering
- Keystroke pattern analysis

### Productivity Monitoring
- Application usage tracking
- Productive vs unproductive time
- Idle time detection
- Activity reports
- Daily/weekly summaries

### Threat Detection
- Unusual time alerts (2-6 AM)
- New location detection
- After-hours activity
- Brute-force attack detection
- Suspicious activity monitoring

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| macOS Agent | Python 3.9+ |
| Web Dashboard | Next.js 14, TypeScript, Tailwind CSS |
| Mobile App | Flutter, Dart |
| Database | PostgreSQL (Supabase) |
| Real-time | Supabase Realtime |
| Storage | Supabase Storage |
| Push Notifications | Firebase Cloud Messaging |
| Email | SMTP (Gmail, custom) |

---

## System Requirements

### macOS Agent
- macOS 10.15 Catalina or later
- Python 3.9+
- Homebrew (for imagesnap)
- Internet connection

### Required Permissions
- Accessibility (for keyboard/screen monitoring)
- Screen Recording (for screenshots)
- Location Services (for GPS)
- Camera (for photo capture)
- Microphone (for audio recording)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/login-monitor-pro.git
cd login-monitor-pro

# 2. Run installation
bash install.sh

# 3. Follow the setup wizard
python3 setup.py

# 4. Pair with mobile app using the 6-digit code
```

See [Installation Guide](INSTALLATION.md) for detailed instructions.

---

## Support

- GitHub Issues: [Report a bug](https://github.com/your-org/login-monitor-pro/issues)
- Documentation: This folder
- Dashboard: https://web-dashboard-inky.vercel.app

---

## License

Proprietary - CyVigil Security Solutions

Copyright 2024-2025. All rights reserved.
