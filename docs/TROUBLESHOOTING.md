# Troubleshooting Guide

Common issues and solutions for Login Monitor PRO.

---

## Quick Diagnostics

### Check Service Status

```bash
# Check all services running
ps aux | grep -E "screen_watcher|command_listener|app_tracker|file_monitor"

# Check LaunchAgents
launchctl list | grep loginmonitor

# View recent logs
tail -50 /tmp/loginmonitor-*.log
```

### Test Basic Functionality

```bash
# Test photo capture
python3 pro_monitor.py Test

# Test location
python3 -c "from pro_monitor import SystemInfo; print(SystemInfo().get_location())"

# Test Supabase connection
python3 -c "from supabase_client import SupabaseClient; print(SupabaseClient().test_connection())"
```

---

## Common Issues

### 1. Services Not Starting

**Symptoms:**
- No events captured
- Commands not executing
- LaunchAgents not loaded

**Solutions:**

```bash
# Check for errors
cat /tmp/loginmonitor-screen.log

# Reload LaunchAgents
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.*.plist
launchctl load ~/Library/LaunchAgents/com.loginmonitor.*.plist

# Start manually for debugging
cd ~/.login-monitor
python3 screen_watcher.py
```

---

### 2. Photos Not Capturing

**Symptoms:**
- Events show but no photos
- "imagesnap not found" error
- Black/empty photos

**Solutions:**

```bash
# Install imagesnap
brew install imagesnap

# Test imagesnap directly
imagesnap -w 1 /tmp/test.jpg

# Check camera permission
# System Settings → Privacy → Camera → Enable for Terminal

# Add Homebrew to PATH
export PATH="/opt/homebrew/bin:$PATH"
```

---

### 3. Location Not Working

**Symptoms:**
- Location shows IP-based only
- "Unable to get GPS location" error
- Accuracy very low (>5000m)

**Solutions:**

```bash
# Request location permission
python3 request_location_permission.py

# Check Location Services
# System Settings → Privacy → Location Services
# → Enable for Terminal/Python

# Test location
python3 -c "
from CoreLocation import CLLocationManager
mgr = CLLocationManager.alloc().init()
mgr.requestWhenInUseAuthorization()
"
```

---

### 4. Push Notifications Not Received

**Symptoms:**
- No push notifications on app
- FCM errors in logs
- Token not updating

**Solutions:**

```bash
# Check FCM token in Supabase
curl -s "https://your-project.supabase.co/rest/v1/fcm_tokens?device_id=eq.xxx" \
  -H "apikey: your-key"

# Update FCM token
# Open Flutter app → Settings → Refresh Token

# Check firebase-service-account.json exists
cat ~/.login-monitor/firebase-service-account.json

# Test FCM manually
python3 fcm_sender.py --test
```

---

### 5. Commands Not Executing

**Symptoms:**
- Commands stay "pending"
- No result returned
- Timeout errors

**Solutions:**

```bash
# Check command_listener running
ps aux | grep command_listener

# Restart command_listener
pkill -f command_listener
cd ~/.login-monitor && python3 command_listener.py &

# Check Supabase Realtime
# Commands should execute instantly via WebSocket

# Check logs
tail -f /tmp/loginmonitor-commands.log
```

---

### 6. DLP Not Detecting

**Symptoms:**
- Clipboard events not logged
- USB events missing
- File events not captured

**Solutions:**

```bash
# Check DLP services running
ps aux | grep -E "clipboard_dlp|usb_dlp|file_monitor"

# Start DLP services
python3 clipboard_dlp.py &
python3 usb_dlp.py &
python3 file_monitor.py &

# Check Accessibility permission
# Required for clipboard monitoring

# Install watchdog for file monitoring
pip3 install watchdog

# Check pynput for keystroke
pip3 install pynput
```

---

### 7. Dashboard Shows No Data

**Symptoms:**
- Empty tables
- "No data" messages
- API errors

**Solutions:**

```bash
# Check RLS policies
# Data might be blocked by Row Level Security

# Test with service key (bypasses RLS)
curl -s "https://your-project.supabase.co/rest/v1/events?limit=5" \
  -H "apikey: service-role-key" \
  -H "Authorization: Bearer service-role-key"

# Add RLS policy for anon
psql -c "CREATE POLICY 'Allow read' ON table FOR SELECT TO anon USING (true);"
```

---

### 8. Email Not Sending

**Symptoms:**
- No email notifications
- SMTP errors in logs
- Authentication failed

**Solutions:**

```bash
# Check email config
cat ~/.login-monitor/config.json | grep -A10 email

# For Gmail: Use App Password, not regular password
# 1. Enable 2FA on Google Account
# 2. Generate App Password
# 3. Use App Password in config

# Test SMTP
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('email@gmail.com', 'app-password')
print('SMTP OK')
"
```

---

### 9. Screen Recording Permission

**Symptoms:**
- Screenshots are blank/black
- "Screen recording not permitted" error
- Only wallpaper captured

**Solutions:**

```bash
# Grant Screen Recording permission
# System Settings → Privacy → Screen Recording
# → Add Terminal or your Python app

# Reset permission (to trigger prompt again)
tccutil reset ScreenCapture

# Run from Terminal (inherits Terminal's permission)
cd ~/.login-monitor && python3 command_listener.py
```

---

### 10. Keystroke Logging Not Working

**Symptoms:**
- "Process not trusted" error
- Zero keystrokes logged
- pynput errors

**Solutions:**

```bash
# Install pynput
pip3 install pynput

# Grant Accessibility permission
# System Settings → Privacy → Accessibility
# → Add Terminal

# Test pynput
python3 -c "
from pynput import keyboard
def on_press(key):
    print(f'Key: {key}')
    return False
with keyboard.Listener(on_press=on_press) as l:
    l.join()
"
```

---

## Log Files

| Log | Location | Purpose |
|-----|----------|---------|
| Screen Watcher | /tmp/loginmonitor-screen.log | Login/unlock detection |
| Commands | /tmp/loginmonitor-commands.log | Remote command execution |
| App Tracker | /tmp/loginmonitor-apptracker.log | Productivity tracking |
| File Monitor | /tmp/loginmonitor-files.log | File access monitoring |
| SIEM | /tmp/loginmonitor-siem.log | SIEM integration |
| Browser | /tmp/loginmonitor-browser.log | Browser monitoring |

### View Logs

```bash
# View all logs
tail -f /tmp/loginmonitor-*.log

# View specific log
tail -f /tmp/loginmonitor-commands.log

# Search logs
grep -i error /tmp/loginmonitor-*.log
```

---

## Reinstallation

If all else fails, try a clean reinstall:

```bash
# 1. Stop all services
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.*.plist
pkill -f loginmonitor

# 2. Backup config
cp ~/.login-monitor/config.json ~/config-backup.json

# 3. Remove installation
rm -rf ~/.login-monitor
rm ~/Library/LaunchAgents/com.loginmonitor.*.plist

# 4. Fresh install
bash install.sh

# 5. Restore config
cp ~/config-backup.json ~/.login-monitor/config.json

# 6. Restart services
launchctl load ~/Library/LaunchAgents/com.loginmonitor.*.plist
```

---

## Getting Help

### Collect Debug Info

```bash
# System info
sw_vers
python3 --version
pip3 list | grep -E "requests|pillow|watchdog|pynput"

# Service status
launchctl list | grep loginmonitor
ps aux | grep -E "python.*monitor"

# Recent logs
tail -100 /tmp/loginmonitor-*.log > ~/debug-logs.txt

# Config (remove sensitive data)
cat ~/.login-monitor/config.json | grep -v "password\|key\|token"
```

### Report Issues

1. Collect debug info (above)
2. Open GitHub issue
3. Include:
   - macOS version
   - Python version
   - Error messages
   - Steps to reproduce
   - Debug logs (redact sensitive info)
