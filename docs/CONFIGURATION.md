# Configuration Guide

Complete configuration options for Login Monitor PRO.

---

## Configuration File

Location: `~/.login-monitor/config.json`

---

## Core Configuration

```json
{
  "device_id": "uuid-of-device",
  "hostname": "MacBook-Pro",
  "os_version": "macOS 14.0",

  "supabase_url": "https://your-project.supabase.co",
  "supabase_key": "eyJ...",

  "notification_email": "admin@company.com"
}
```

---

## Feature Configuration

### Photo Capture

```json
{
  "features": {
    "multi_photo": true,
    "photo_count": 3,
    "photo_delay": 1.0,
    "photo_quality": "high"
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| multi_photo | bool | true | Enable multiple photos |
| photo_count | int | 3 | Photos per event (1-10) |
| photo_delay | float | 1.0 | Delay between photos (seconds) |
| photo_quality | string | "high" | Quality: low, medium, high |

### Audio Recording

```json
{
  "features": {
    "audio_recording": true,
    "audio_duration": 10,
    "audio_format": "wav"
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| audio_recording | bool | false | Enable audio capture |
| audio_duration | int | 10 | Recording length (seconds) |
| audio_format | string | "wav" | Format: wav |

### Face Recognition

```json
{
  "features": {
    "face_recognition": true,
    "known_faces_path": "~/.login-monitor/known_faces",
    "alert_unknown": true
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| face_recognition | bool | false | Enable face recognition |
| known_faces_path | string | ~/.login-monitor/known_faces | Path to known faces |
| alert_unknown | bool | true | Alert on unknown face |

---

## Email Configuration

```json
{
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_ssl": true,
    "from_email": "sender@gmail.com",
    "from_password": "app-password",
    "to_email": "recipient@company.com",
    "cc_emails": ["security@company.com"]
  }
}
```

| Option | Type | Description |
|--------|------|-------------|
| enabled | bool | Enable email notifications |
| smtp_server | string | SMTP server address |
| smtp_port | int | SMTP port (587 for TLS) |
| smtp_ssl | bool | Use TLS encryption |
| from_email | string | Sender email address |
| from_password | string | App password (not regular password) |
| to_email | string | Primary recipient |
| cc_emails | array | Additional recipients |

### Gmail Setup
1. Enable 2FA on Gmail account
2. Generate App Password: Google Account → Security → App Passwords
3. Use app password in config (not regular password)

---

## Telegram Configuration

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "123456789:ABC...",
    "chat_id": "987654321",
    "send_photos": true,
    "send_location": true
  }
}
```

| Option | Type | Description |
|--------|------|-------------|
| enabled | bool | Enable Telegram notifications |
| bot_token | string | Bot token from @BotFather |
| chat_id | string | Your chat ID |
| send_photos | bool | Send photos with events |
| send_location | bool | Send location with events |

### Get Chat ID
1. Message your bot
2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find your chat_id in the response

---

## Threat Detection Configuration

```json
{
  "threat_detection": {
    "enabled": true,
    "unusual_time": {
      "enabled": true,
      "alert_hours": [0, 1, 2, 3, 4, 5],
      "severity": "high"
    },
    "new_location": {
      "enabled": true,
      "severity": "medium"
    },
    "after_hours": {
      "enabled": true,
      "work_start": "09:00",
      "work_end": "18:00",
      "work_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
      "severity": "low"
    },
    "failed_login": {
      "enabled": true,
      "threshold": 3,
      "time_window_minutes": 5,
      "severity": "high"
    }
  }
}
```

---

## DLP Configuration

### Clipboard DLP

```json
{
  "clipboard_dlp": {
    "enabled": true,
    "patterns": {
      "credit_card": {"enabled": true, "action": "alert"},
      "ssn": {"enabled": true, "action": "alert"},
      "private_key": {"enabled": true, "action": "block"},
      "api_key": {"enabled": true, "action": "alert"},
      "jwt_token": {"enabled": true, "action": "alert"},
      "aws_key": {"enabled": true, "action": "block"},
      "password": {"enabled": true, "action": "alert"}
    },
    "monitor_ai_paste": true,
    "ai_apps": ["ChatGPT", "Claude", "Gemini"]
  }
}
```

### USB DLP

```json
{
  "usb_dlp": {
    "enabled": true,
    "block_all": false,
    "allowed_devices": ["SanDisk-Company-001"],
    "block_extensions": [".pem", ".key", ".env", ".sql"],
    "alert_extensions": [".csv", ".xlsx", ".doc"],
    "max_file_size_mb": 100,
    "log_all_transfers": true
  }
}
```

### Shadow IT

```json
{
  "shadow_it": {
    "enabled": true,
    "block_ai_tools": true,
    "ai_tools": ["ChatGPT", "Claude", "Gemini", "Copilot", "Cursor"],
    "block_file_sharing": false,
    "file_sharing": ["Dropbox", "Google Drive Personal", "WeTransfer"],
    "alert_remote_access": true,
    "remote_access": ["TeamViewer", "AnyDesk", "VNC"],
    "allowed_apps": ["Slack-Work", "Teams", "Zoom"]
  }
}
```

---

## Productivity Configuration

```json
{
  "productivity": {
    "enabled": true,
    "idle_threshold_seconds": 300,
    "sync_interval_seconds": 60,
    "categories": {
      "productive": [
        "Xcode", "VS Code", "Terminal", "iTerm",
        "Figma", "Sketch", "Adobe *",
        "Microsoft Word", "Excel", "PowerPoint",
        "Notion", "Linear", "Jira"
      ],
      "unproductive": [
        "Netflix", "YouTube", "Twitch",
        "Spotify", "Apple Music",
        "Facebook", "Twitter", "Instagram", "TikTok",
        "Reddit", "Steam"
      ],
      "communication": [
        "Slack", "Teams", "Zoom", "Discord",
        "Mail", "Messages", "WhatsApp"
      ]
    }
  }
}
```

---

## Geofencing Configuration

```json
{
  "geofences": [
    {
      "name": "Office",
      "latitude": 28.6139,
      "longitude": 77.2090,
      "radius_meters": 500,
      "trigger_on_exit": true,
      "trigger_on_enter": true,
      "action_on_exit": "lock"
    },
    {
      "name": "Home",
      "latitude": 28.5500,
      "longitude": 77.1000,
      "radius_meters": 200,
      "trigger_on_exit": false,
      "trigger_on_enter": true
    }
  ]
}
```

---

## SIEM Integration Configuration

```json
{
  "siem_integrations": [
    {
      "integration_type": "slack",
      "name": "Security Alerts",
      "endpoint_url": "https://hooks.slack.com/services/...",
      "enabled": true
    },
    {
      "integration_type": "splunk",
      "name": "Splunk SIEM",
      "endpoint_url": "https://splunk.company.com:8088/services/collector",
      "auth_token": "HEC-token-here",
      "enabled": true
    },
    {
      "integration_type": "sentinel",
      "name": "Azure Sentinel",
      "workspace_id": "workspace-id",
      "shared_key": "shared-key",
      "log_type": "CyVigil",
      "enabled": true
    },
    {
      "integration_type": "webhook",
      "name": "Custom Webhook",
      "endpoint_url": "https://api.company.com/security/events",
      "auth_type": "bearer",
      "auth_token": "api-token",
      "enabled": true
    }
  ]
}
```

---

## Reporting Configuration

```json
{
  "reports": {
    "daily_report": true,
    "weekly_report": true,
    "monthly_report": true,
    "send_time": "09:00",
    "recipients": ["admin@company.com", "security@company.com"],
    "include": {
      "events_summary": true,
      "security_alerts": true,
      "productivity_stats": true,
      "dlp_incidents": true,
      "app_usage": true
    }
  }
}
```

---

## Advanced Configuration

### Encryption

```json
{
  "encryption": {
    "encrypt_config": true,
    "encrypt_photos": false,
    "encrypt_audio": false,
    "key_path": "~/.login-monitor/.key"
  }
}
```

### Offline Mode

```json
{
  "offline": {
    "queue_events": true,
    "max_queue_size": 100,
    "retry_interval_seconds": 300
  }
}
```

### Logging

```json
{
  "logging": {
    "level": "INFO",
    "log_path": "/tmp/loginmonitor-*.log",
    "max_log_size_mb": 50,
    "log_rotation": true
  }
}
```

---

## Environment Variables

Override config with environment variables:

```bash
export LM_SUPABASE_URL="https://..."
export LM_SUPABASE_KEY="eyJ..."
export LM_EMAIL_PASSWORD="..."
export LM_TELEGRAM_TOKEN="..."
export LM_LOG_LEVEL="DEBUG"
```

---

## Configuration Best Practices

1. **Security**
   - Never commit config.json to git
   - Use environment variables for secrets
   - Enable config encryption

2. **Performance**
   - Reduce photo count for slow connections
   - Increase sync interval for battery life
   - Limit log file size

3. **Privacy**
   - Disable keystroke logging if not needed
   - Use productivity tracking responsibly
   - Inform employees of monitoring

4. **Reliability**
   - Enable offline queue
   - Configure multiple notification channels
   - Test configuration before deployment
