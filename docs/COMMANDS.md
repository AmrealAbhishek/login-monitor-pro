# Commands Reference

Complete reference for all Login Monitor PRO commands.

---

## Remote Commands (via App/Dashboard)

Send these commands from the mobile app or web dashboard.

### Photo Capture

```
Command: photo
Arguments: {
  "count": 3,        // Number of photos (1-10)
  "delay": 1.0       // Delay between photos (seconds)
}
Result: {
  "success": true,
  "photos": ["url1", "url2", "url3"]
}
```

### Location Request

```
Command: location
Arguments: {}
Result: {
  "success": true,
  "latitude": 28.6139,
  "longitude": 77.2090,
  "accuracy": 10,
  "city": "New Delhi",
  "country": "India",
  "google_maps_link": "https://maps.google.com/..."
}
```

### Audio Recording

```
Command: audio
Arguments: {
  "duration": 30    // Duration in seconds (5-60)
}
Result: {
  "success": true,
  "audio_url": "https://storage.supabase.co/..."
}
```

### Alarm

```
Command: alarm
Arguments: {
  "duration": 30    // Duration in seconds (default: 30)
}
Result: {
  "success": true,
  "message": "Alarm played for 30 seconds"
}
```

### Screen Lock

```
Command: lock
Arguments: {}
Result: {
  "success": true,
  "message": "Screen locked"
}
```

### Display Message

```
Command: message
Arguments: {
  "text": "Your message here"
}
Result: {
  "success": true,
  "message": "Message displayed"
}
```

### Device Status

```
Command: status
Arguments: {}
Result: {
  "success": true,
  "battery": {"percentage": 85, "charging": true},
  "wifi": {"ssid": "Office-5G", "signal": -45},
  "location": {"city": "New Delhi", "country": "India"},
  "uptime": "2 days, 5 hours"
}
```

### Screenshot

```
Command: screenshot
Arguments: {}
Result: {
  "success": true,
  "screenshot_url": "https://storage.supabase.co/..."
}
```

### WiFi Info

```
Command: wifi
Arguments: {}
Result: {
  "success": true,
  "ssid": "Office-5G",
  "bssid": "AA:BB:CC:DD:EE:FF",
  "signal_strength": -45,
  "channel": 36
}
```

### Battery Status

```
Command: battery
Arguments: {}
Result: {
  "success": true,
  "percentage": 85,
  "charging": true,
  "ac_power": true,
  "time_remaining": "2:30"
}
```

### Running Apps

```
Command: apps
Arguments: {}
Result: {
  "success": true,
  "apps": ["Safari", "Terminal", "VS Code", "Slack"]
}
```

### Keystroke Logging

```
Command: keystroke
Arguments: {
  "duration": 5,      // Duration in minutes (1-60)
  "full_log": false   // Log content (investigation mode)
}
Result: {
  "success": true,
  "message": "Keystroke logging started for 5 minutes"
}
```

### Stop Keystroke

```
Command: keystroke_stop
Arguments: {}
Result: {
  "success": true,
  "message": "Keystroke logging stopped"
}
```

### Install App (Homebrew)

```
Command: install_app
Arguments: {
  "app_name": "rectangle"
}
Result: {
  "success": true,
  "message": "rectangle installed successfully"
}
```

### Uninstall App

```
Command: uninstall_app
Arguments: {
  "app_name": "rectangle"
}
Result: {
  "success": true,
  "message": "rectangle uninstalled"
}
```

### Shell Command

```
Command: shell
Arguments: {
  "command": "uptime"
}
Result: {
  "success": true,
  "output": "22:30 up 2 days, 5:30, 3 users"
}
```

### VNC Start

```
Command: vnc_start
Arguments: {}
Result: {
  "success": true,
  "message": "Screen Sharing enabled"
}
```

---

## CLI Commands (Terminal)

Run these commands directly on the Mac.

### Pro Monitor

```bash
# Trigger events
python3 pro_monitor.py Login
python3 pro_monitor.py Unlock
python3 pro_monitor.py Wake
python3 pro_monitor.py "Custom Event"

# Utility commands
python3 pro_monitor.py --status         # Show status
python3 pro_monitor.py --alarm          # Play alarm
python3 pro_monitor.py --message "Hi"   # Show message
python3 pro_monitor.py --lock           # Lock screen
python3 pro_monitor.py --help           # Show help
```

### Service Management

```bash
# Start services
python3 screen_watcher.py &
python3 command_listener.py &
python3 app_tracker.py &
python3 file_monitor.py &
python3 clipboard_dlp.py &

# Check running services
ps aux | grep -E "python.*monitor|watcher|tracker|dlp"

# View logs
tail -f /tmp/loginmonitor-*.log
```

### LaunchAgent Management

```bash
# Load service
launchctl load ~/Library/LaunchAgents/com.loginmonitor.screen.plist

# Unload service
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.screen.plist

# List loaded services
launchctl list | grep loginmonitor

# Check service status
launchctl print gui/$(id -u)/com.loginmonitor.screen
```

### Setup Commands

```bash
# Run setup wizard
python3 setup.py

# Check permissions
python3 check_permissions.py

# Request permissions
python3 request_location_permission.py
python3 request_screen_permission.py

# Regenerate pairing code
python3 setup.py --regenerate-code
```

### DLP Commands

```bash
# Start DLP monitors
python3 clipboard_dlp.py &
python3 usb_dlp.py &
python3 file_monitor.py &
python3 shadow_it_detector.py &
python3 browser_monitor.py &

# Start keystroke monitoring
python3 keystroke_logger.py &
```

---

## Telegram Bot Commands

Send these commands to the Telegram bot.

```
/photo              - Capture and send webcam photo
/location           - Send current GPS location
/wifi               - Show current WiFi network
/battery            - Show battery status
/alarm              - Play alarm sound (30 sec)
/lock               - Lock screen immediately
/message [text]     - Display message on screen
/status             - Show device status
/screenshot         - Capture and send screenshot
/help               - Show available commands
```

---

## loginmonitor CLI

The `loginmonitor` command-line tool.

```bash
# Start services
loginmonitor start

# Stop services
loginmonitor stop

# Restart services
loginmonitor restart

# Check status
loginmonitor status

# View logs
loginmonitor logs

# Grant permissions
loginmonitor permissions

# Request location permission
loginmonitor location

# Start VNC
loginmonitor vnc
```

---

## Command Status Codes

| Status | Description |
|--------|-------------|
| `pending` | Command queued, waiting for device |
| `executing` | Command currently running |
| `completed` | Command finished successfully |
| `failed` | Command failed with error |
| `timeout` | Command timed out (60s default) |

---

## Error Codes

| Error | Description | Solution |
|-------|-------------|----------|
| `device_offline` | Device not connected | Check internet connection |
| `permission_denied` | Missing system permission | Grant required permission |
| `command_not_found` | Unknown command | Check command spelling |
| `invalid_args` | Invalid arguments | Check argument format |
| `timeout` | Command timed out | Try again or check device |
| `execution_failed` | Command execution error | Check logs for details |

---

## Command Aliases

Some commands have aliases for convenience:

| Primary | Aliases |
|---------|---------|
| `photo` | `capture`, `pic`, `cam` |
| `location` | `loc`, `gps`, `where` |
| `lock` | `lockscreen`, `lock_screen` |
| `message` | `msg`, `display`, `show` |
| `alarm` | `alert`, `sound`, `ring` |
| `status` | `info`, `stat` |
| `keystroke` | `keylog`, `keys` |
| `keystroke_stop` | `keystrokestop`, `stopkeys` |

---

## Rate Limits

| Command | Limit | Window |
|---------|-------|--------|
| photo | 10 | per minute |
| location | 30 | per minute |
| audio | 5 | per minute |
| screenshot | 10 | per minute |
| shell | 20 | per minute |
| alarm | 3 | per minute |
