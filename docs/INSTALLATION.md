# Installation Guide

Complete setup instructions for Login Monitor PRO.

---

## Prerequisites

### System Requirements
- macOS 10.15 Catalina or later
- Python 3.9 or later
- Homebrew package manager
- Internet connection
- Admin access to the Mac

### Required Software
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install imagesnap (webcam capture)
brew install imagesnap

# Install Python dependencies
pip3 install requests pillow watchdog pynput
```

---

## Installation Methods

### Method 1: One-Line Installer (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/your-org/login-monitor-pro/main/install.sh | bash
```

This will:
1. Download the latest version
2. Install dependencies
3. Configure LaunchAgents
4. Generate a pairing code
5. Start monitoring

### Method 2: Manual Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/login-monitor-pro.git
cd login-monitor-pro

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Run the setup wizard
python3 setup.py

# 4. Start monitoring
python3 screen_watcher.py &
python3 command_listener.py &
```

---

## Setup Wizard

The setup wizard (`setup.py`) will configure:

### 1. Supabase Connection
```
Enter Supabase URL: https://your-project.supabase.co
Enter Supabase Anon Key: eyJ...
```

### 2. Email Notifications (Optional)
```
Enable email notifications? [y/n]: y
SMTP Server: smtp.gmail.com
SMTP Port: 587
Email Address: your-email@gmail.com
Email Password: your-app-password
```

### 3. Device Registration
```
Registering device...
Your pairing code is: 123456
Use this code in the mobile app to pair.
```

---

## Granting Permissions

Login Monitor PRO requires several macOS permissions:

### 1. Accessibility Permission
Required for: Keystroke monitoring, screen control

```
System Settings → Privacy & Security → Accessibility
→ Add: Terminal (or your Python app)
```

### 2. Screen Recording Permission
Required for: Screenshots, screen monitoring

```
System Settings → Privacy & Security → Screen Recording
→ Add: Terminal (or your Python app)
```

### 3. Location Services
Required for: GPS location tracking

```
System Settings → Privacy & Security → Location Services
→ Enable for: Terminal (or your Python app)
```

### 4. Camera Permission
Required for: Photo capture

```
System Settings → Privacy & Security → Camera
→ Allow: Terminal (or your Python app)
```

### 5. Microphone Permission
Required for: Audio recording

```
System Settings → Privacy & Security → Microphone
→ Allow: Terminal (or your Python app)
```

### Request Permissions Script
```bash
python3 request_location_permission.py
python3 request_screen_permission.py
```

---

## LaunchAgent Configuration

Login Monitor PRO uses LaunchAgents to run automatically on login.

### Installed LaunchAgents

| File | Purpose |
|------|---------|
| `com.loginmonitor.screen.plist` | Screen lock/unlock detection |
| `com.loginmonitor.commands.plist` | Remote command listener |
| `com.loginmonitor.apptracker.plist` | App usage tracking |
| `com.loginmonitor.browser.plist` | Browser monitoring |
| `com.loginmonitor.files.plist` | File access monitoring |

### Manual LaunchAgent Control

```bash
# Load (start) a service
launchctl load ~/Library/LaunchAgents/com.loginmonitor.screen.plist

# Unload (stop) a service
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.screen.plist

# List running services
launchctl list | grep loginmonitor

# View logs
tail -f /tmp/loginmonitor-*.log
```

---

## Mobile App Setup

### 1. Install the App
- Download from Google Play (Android)
- Or build from source: `flutter build apk`

### 2. Create Account
- Open app → Sign Up
- Enter email and password
- Verify email

### 3. Pair Device
- Open app → Pair Device
- Enter the 6-digit code from Mac setup
- Device will appear in your device list

---

## Web Dashboard Setup

### Access Dashboard
- URL: https://web-dashboard-inky.vercel.app
- Login with same credentials as mobile app

### Self-Hosted Dashboard
```bash
cd web-dashboard
npm install
npm run build
npm start
```

---

## Verification

### Check Services Running
```bash
# Check all Login Monitor processes
ps aux | grep -E "screen_watcher|command_listener|app_tracker"

# Check LaunchAgents loaded
launchctl list | grep loginmonitor
```

### Test Photo Capture
```bash
python3 pro_monitor.py Test
```

### Test Remote Command
1. Open mobile app
2. Select device
3. Tap "Photo" command
4. Verify photo appears

---

## Uninstallation

```bash
# Run uninstall script
bash uninstall.sh
```

This will:
1. Stop all LaunchAgents
2. Remove LaunchAgent files
3. Remove configuration
4. Remove captured data (optional)

### Manual Uninstall
```bash
# Stop services
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.*.plist

# Remove LaunchAgents
rm ~/Library/LaunchAgents/com.loginmonitor.*.plist

# Remove config and data
rm -rf ~/.login-monitor
```

---

## Troubleshooting Installation

### Issue: "Permission denied"
```bash
chmod +x install.sh
sudo ./install.sh
```

### Issue: "imagesnap not found"
```bash
brew install imagesnap
export PATH="/opt/homebrew/bin:$PATH"
```

### Issue: "Python module not found"
```bash
pip3 install requests pillow watchdog pynput
```

### Issue: "Pairing code not working"
1. Check internet connection
2. Verify Supabase credentials
3. Try regenerating code: `python3 setup.py --regenerate-code`

### Issue: "Services not starting"
```bash
# Check logs
cat /tmp/loginmonitor-*.log

# Restart services
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.*.plist
launchctl load ~/Library/LaunchAgents/com.loginmonitor.*.plist
```

---

## Next Steps

1. [Configure DLP policies](DLP.md)
2. [Set up threat detection rules](FEATURES.md#threat-detection)
3. [Configure email notifications](CONFIGURATION.md#email)
4. [Learn dashboard features](DASHBOARD.md)
