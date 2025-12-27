# Login Monitor PRO

**Anti-Theft & Security Monitoring for macOS**

Login Monitor PRO automatically captures photos and sends notifications whenever someone logs in, unlocks, or wakes your Mac. Perfect for security monitoring and stolen device recovery.

---

## Features

### Core Features
- **Auto Photo Capture** - Takes photos on login, unlock, and wake events
- **Email Notifications** - Sends alerts with captured photos
- **Telegram Notifications** - Instant alerts on your phone
- **GPS Location Tracking** - Pinpoint device location using CoreLocation + IP fallback
- **Offline Event Queue** - Stores events when offline, sends when internet available
- **Multiple Photos** - Captures 3 photos with delay to catch movement

### Anti-Theft Features (via Telegram)
- `/photo` - Take photo immediately
- `/location` - Get current GPS coordinates
- `/alarm` - Play loud alarm sound
- `/lock` - Lock the screen instantly
- `/message` - Display custom message on screen

### Status Commands (via Telegram)
- `/status` - Full device status report
- `/battery` - Battery level and charging status
- `/wifi` - Connected WiFi network details
- `/ip` - Local and public IP addresses

---

## Quick Installation

### One-Click Install

1. **Download** the Login Monitor PRO package
2. **Open Terminal** and navigate to the downloaded folder
3. **Run the installer:**

```bash
bash install.sh
```

Or with execute permission:
```bash
chmod +x install.sh
./install.sh
```

4. **Follow the prompts** to configure:
   - Your notification email
   - SMTP settings (Gmail recommended)
   - Telegram bot (optional but recommended)

5. **Allow permissions** when prompted:
   - Camera access
   - Location access

That's it! Login Monitor PRO is now protecting your Mac.

---

## Detailed Installation Guide

### Prerequisites

- macOS 10.15 (Catalina) or later
- Internet connection for notifications
- Email account for sending notifications (Gmail recommended)

### Step 1: Download

Download and extract Login Monitor PRO to any folder.

### Step 2: Run Installer

Open Terminal and run:

```bash
cd /path/to/login-monitor
chmod +x install.sh
./install.sh
```

### Step 3: Email Configuration

#### Using Gmail (Recommended)

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Sign in to your Google account
3. Select "Mail" and your device
4. Click "Generate"
5. Copy the 16-character password
6. Use this password during installation (NOT your regular Gmail password)

#### Using Custom SMTP

You can use any SMTP server:
- Server: Your SMTP host (e.g., smtp.your-provider.com)
- Port: Usually 465 (SSL) or 587 (TLS)
- Email: Your sender email
- Password: Your email password

### Step 4: Telegram Setup (Optional)

Setting up Telegram enables instant notifications and remote control.

#### Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Choose a name for your bot (e.g., "My Mac Monitor")
4. Choose a username (e.g., "my_mac_monitor_bot")
5. Copy the **bot token** you receive

#### Get Your Chat ID

1. Start a chat with your new bot
2. Send any message to it
3. Open this URL in your browser (replace YOUR_TOKEN):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
4. Find `"chat":{"id":XXXXXXXX}` - this number is your **chat_id**

#### Enter During Installation

When prompted, enter:
- Bot Token: The token from BotFather
- Chat ID: Your chat ID number

### Step 5: Grant Permissions

When you first login/unlock after installation:

1. **Camera Permission**
   - A popup will ask for camera access
   - Click "OK" to allow
   - If denied: System Preferences > Privacy & Security > Camera > Allow Terminal/Python

2. **Location Permission**
   - A popup may ask for location access
   - Click "Allow" for accurate GPS tracking
   - If denied: System Preferences > Privacy & Security > Location Services

---

## Usage

### Automatic Monitoring

Once installed, Login Monitor PRO runs automatically:

- **On Login** - When you log into your Mac
- **On Unlock** - When you unlock the screen
- **On Wake** - When Mac wakes from sleep

Each event captures photos and sends notifications.

### Telegram Commands

Send these commands to your Telegram bot:

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/photo` | Take photo now |
| `/location` | Get GPS location |
| `/status` | Full device status |
| `/battery` | Battery level |
| `/wifi` | WiFi network info |
| `/ip` | IP addresses |
| `/alarm [sec]` | Play alarm (default 30s) |
| `/lock` | Lock screen |
| `/message [text]` | Show popup on screen |
| `/audio [sec]` | Record audio (default 10s) |

### View Logs

```bash
# Screen watcher log
tail -f /tmp/loginmonitor-screen.log

# Telegram bot log
tail -f /tmp/loginmonitor-telegram.log

# Event history
ls -la ~/.login-monitor/events/
```

### Check Service Status

```bash
launchctl list | grep loginmonitor
```

---

## Uninstallation

To completely remove Login Monitor PRO:

```bash
cd ~/.login-monitor
./uninstall.sh
```

Or manually:

```bash
# Stop services
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.screen.plist
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.telegram.plist

# Remove files
rm -rf ~/.login-monitor
rm ~/Library/LaunchAgents/com.loginmonitor.*.plist
```

---

## Troubleshooting

### Camera not working

1. Check camera permission:
   - System Preferences > Privacy & Security > Camera
   - Ensure Terminal or Python has access

2. Test camera manually:
   ```bash
   /opt/homebrew/bin/imagesnap /tmp/test.jpg
   ```

### Not receiving emails

1. Check SMTP configuration in `~/.login-monitor/config.json`
2. For Gmail, ensure you're using an App Password
3. Check email spam folder
4. View logs for errors:
   ```bash
   tail -50 /tmp/loginmonitor-screen.log
   ```

### Telegram bot not responding

1. Ensure bot token and chat_id are correct
2. Make sure you started a chat with the bot
3. Check Telegram service status:
   ```bash
   launchctl list | grep telegram
   ```
4. Restart Telegram service:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.loginmonitor.telegram.plist
   launchctl load ~/Library/LaunchAgents/com.loginmonitor.telegram.plist
   ```

### Location not accurate

- Grant Location Services permission
- For better accuracy, allow "Precise Location"
- Falls back to IP-based location if GPS unavailable

### Events not triggering

1. Check screen watcher status:
   ```bash
   launchctl list | grep screen
   ```
2. Restart screen watcher:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.loginmonitor.screen.plist
   launchctl load ~/Library/LaunchAgents/com.loginmonitor.screen.plist
   ```

---

## Configuration

Configuration is stored in `~/.login-monitor/config.json`:

```json
{
    "notification_email": "your@email.com",
    "smtp": {
        "server": "smtp.gmail.com",
        "port": 465,
        "sender_email": "your@gmail.com",
        "password": "your-app-password",
        "use_ssl": true
    },
    "telegram": {
        "enabled": true,
        "bot_token": "YOUR_BOT_TOKEN",
        "chat_id": "YOUR_CHAT_ID"
    },
    "features": {
        "multi_photo": true,
        "photo_count": 3,
        "photo_delay": 2,
        "audio_recording": false,
        "audio_duration": 10
    },
    "cooldown_seconds": 10
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `notification_email` | Email to receive alerts | Required |
| `cooldown_seconds` | Minimum seconds between triggers | 10 |
| `features.multi_photo` | Capture multiple photos | true |
| `features.photo_count` | Number of photos to capture | 3 |
| `features.photo_delay` | Seconds between photos | 2 |
| `features.audio_recording` | Record audio on events | false |
| `features.audio_duration` | Audio recording length (seconds) | 10 |

---

## File Locations

| Path | Description |
|------|-------------|
| `~/.login-monitor/` | Main installation directory |
| `~/.login-monitor/config.json` | Configuration file |
| `~/.login-monitor/captures/` | Captured photos |
| `~/.login-monitor/events/` | Event JSON logs |
| `~/.login-monitor/audio/` | Audio recordings |
| `/tmp/loginmonitor-*.log` | Runtime logs |

---

## Security Notes

- Configuration contains sensitive data (passwords, tokens)
- Config file permissions are set to 600 (owner only)
- Photos are stored locally - consider disk encryption
- Telegram commands only work from your chat_id
- Consider running on encrypted volumes

---

## Support

For issues or feature requests, please open an issue on GitHub.

---

## License

This project is provided as-is for personal security use. Use responsibly and in accordance with local laws regarding surveillance and monitoring.
