# Data Loss Prevention (DLP) Guide

Comprehensive guide to Login Monitor PRO's DLP capabilities.

---

## Overview

Data Loss Prevention (DLP) protects sensitive corporate data from unauthorized access, copying, or exfiltration. Login Monitor PRO provides multiple DLP layers:

```
┌─────────────────────────────────────────────────────────────┐
│                     DLP PROTECTION LAYERS                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │ Clipboard │  │    USB    │  │   File    │  │ Browser  │ │
│  │    DLP    │  │    DLP    │  │   DLP     │  │   DLP    │ │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘ │
│        │              │              │              │       │
│  ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐  ┌────┴─────┐ │
│  │ Shadow IT │  │ Keystroke │  │  Network  │  │   SIEM   │ │
│  │ Detection │  │  Monitor  │  │  Monitor  │  │  Export  │ │
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Clipboard DLP

Monitors copy/paste operations for sensitive data patterns.

### Detected Patterns

| Pattern | Example | Severity |
|---------|---------|----------|
| Credit Card | 4111-1111-1111-1111 | CRITICAL |
| SSN | 123-45-6789 | CRITICAL |
| AWS Key | AKIAIOSFODNN7EXAMPLE | CRITICAL |
| Private Key | -----BEGIN RSA PRIVATE KEY----- | CRITICAL |
| JWT Token | eyJhbGciOiJIUzI1NiIs... | HIGH |
| API Key | api_key_xxx... | HIGH |
| Password | password=secret123 | HIGH |
| Email | user@company.com | LOW |

### Configuration

```json
{
  "clipboard_dlp": {
    "enabled": true,
    "patterns": {
      "credit_card": {"enabled": true, "action": "alert"},
      "ssn": {"enabled": true, "action": "alert"},
      "private_key": {"enabled": true, "action": "block"},
      "api_key": {"enabled": true, "action": "alert"}
    },
    "alert_on_ai_paste": true,
    "monitored_apps": ["ChatGPT", "Claude", "Gemini"]
  }
}
```

### Actions

| Action | Description |
|--------|-------------|
| `log` | Log silently |
| `alert` | Log + send notification |
| `block` | Clear clipboard + alert |

### Dashboard View

**Location:** Dashboard → DLP → Clipboard

Shows:
- Time of copy
- User who copied
- Sensitive data type
- Source application
- Destination (if pasted to AI)
- Reveal button (for forensics)

---

## 2. USB DLP

Monitors USB device connections and file transfers.

### Monitored Events

| Event | Description | Risk |
|-------|-------------|------|
| USB Connected | External drive plugged in | Low |
| File Copied | File moved to USB | Medium-High |
| Sensitive File | Credentials/keys to USB | Critical |
| Mass Transfer | Many files to USB | High |

### Sensitive File Types

```python
SENSITIVE_EXTENSIONS = [
    # Keys & Certificates
    '.pem', '.key', '.p12', '.pfx', '.crt', '.cer',

    # Configuration
    '.env', '.env.local', '.env.production',

    # Databases
    '.sql', '.sqlite', '.db', '.mdb',

    # Data Files
    '.csv', '.xlsx', '.xls', '.json',

    # Documents
    '.doc', '.docx', '.pdf'
]

SENSITIVE_FILENAMES = [
    'id_rsa', 'id_ed25519', 'id_ecdsa',
    'credentials', 'secrets', 'passwords',
    '.netrc', '.npmrc', 'aws_credentials',
    'service-account.json', '.htpasswd'
]
```

### Configuration

```json
{
  "usb_dlp": {
    "enabled": true,
    "block_all_usb": false,
    "allowed_devices": ["SanDisk-Office-001"],
    "block_extensions": [".pem", ".key", ".env"],
    "alert_extensions": [".sql", ".csv", ".xlsx"],
    "max_file_size_mb": 100
  }
}
```

### Dashboard View

**Location:** Dashboard → DLP → USB & Devices

Shows:
- USB device name and vendor
- File transferred
- File size
- Action taken (allowed/blocked)
- User who transferred

---

## 3. File Access DLP

Real-time monitoring of file system operations.

### Monitored Operations

| Operation | Description |
|-----------|-------------|
| Create | New file created |
| Modify | File contents changed |
| Delete | File removed |
| Copy | File duplicated |
| Move | File relocated |

### Monitored Locations

```python
DEFAULT_PATHS = [
    "~/Documents",
    "~/Desktop",
    "~/Downloads",
    "/Volumes/*"  # External drives
]
```

### File Rules

Create rules in Dashboard → Admin → File Rules

| Rule Type | Example | Trigger |
|-----------|---------|---------|
| Extension | `*.pem` | Any .pem file |
| Filename | `*password*` | Files containing "password" |
| Path | `/Users/*/Documents/secrets/*` | Specific folder |
| Content | Contains "API_KEY" | File content match |

### Configuration

```json
{
  "file_rules": [
    {
      "name": "Secret Keys",
      "pattern": "*.pem|*.key|*private*",
      "action": "alert",
      "severity": "critical",
      "screenshot": true
    },
    {
      "name": "Password Files",
      "pattern": "*password*|*credential*",
      "action": "alert",
      "severity": "high"
    }
  ]
}
```

### Dashboard View

**Location:** Dashboard → DLP → File Transfers

Shows:
- Time of access
- User
- Action (create/modify/delete)
- File path
- Application that accessed
- Alert triggered (yes/no)

---

## 4. Shadow IT Detection

Detects unauthorized applications and services.

### Detected Categories

#### AI Tools (HIGH RISK)
| App/Service | Risk | Why It's Risky |
|-------------|------|----------------|
| ChatGPT | High | Data sent to external AI |
| Claude | High | Confidential info exposure |
| Gemini | High | Google data collection |
| Copilot | High | Code/data sent to Microsoft |
| Cursor | High | Code context shared |
| Perplexity | Medium | Search data exposure |

#### File Sharing (MEDIUM-HIGH)
| Service | Risk | Concern |
|---------|------|---------|
| Personal Dropbox | High | Uncontrolled data sync |
| Personal Google Drive | High | Data outside org |
| WeTransfer | High | Large file exfiltration |
| Mega | High | Encrypted, untrackable |
| iCloud | Medium | Personal cloud storage |

#### Remote Access (MEDIUM-HIGH)
| Tool | Risk | Concern |
|------|------|---------|
| TeamViewer | High | Unauthorized access |
| AnyDesk | High | Screen sharing |
| VNC | Medium | Remote control |
| RDP | Medium | Remote desktop |

#### Communication (MEDIUM)
| App | Risk | Concern |
|-----|------|---------|
| Personal Slack | Medium | Data in personal workspace |
| Telegram | Medium | Encrypted, untracked |
| Signal | Medium | Disappearing messages |
| WhatsApp | Medium | Personal messaging |
| Discord | Medium | Gaming/social platform |

### Configuration

```json
{
  "shadow_it": {
    "enabled": true,
    "block_ai_tools": true,
    "block_file_sharing": false,
    "alert_remote_access": true,
    "allowed_apps": ["Slack-Company", "Teams"],
    "blocked_apps": ["ChatGPT", "Personal Dropbox"]
  }
}
```

### Dashboard View

**Location:** Dashboard → DLP → Shadow IT

Shows:
- Last detected time
- User
- Risk level (Critical/High/Medium/Low)
- App category
- App name
- Detection count

---

## 5. Browser DLP

Controls and monitors web browsing.

### URL Rules

| Rule Type | Example | Action |
|-----------|---------|--------|
| Domain Block | `facebook.com` | Block access |
| Domain Alert | `dropbox.com` | Allow + alert |
| Category Block | `social_media` | Block category |
| Keyword Alert | `*password*` | Alert on URL keyword |

### URL Categories

```python
CATEGORIES = {
    "social_media": ["facebook.com", "twitter.com", "instagram.com"],
    "streaming": ["netflix.com", "youtube.com", "twitch.tv"],
    "gaming": ["steam.com", "epicgames.com"],
    "file_sharing": ["dropbox.com", "drive.google.com"],
    "ai_tools": ["chat.openai.com", "claude.ai", "gemini.google.com"],
    "job_sites": ["linkedin.com/jobs", "indeed.com"],
    "adult": ["explicit-site.com"]  # Blocked by default
}
```

### Configuration

```json
{
  "url_rules": [
    {
      "type": "domain_block",
      "pattern": "facebook.com",
      "action": "block"
    },
    {
      "type": "category_alert",
      "category": "file_sharing",
      "action": "alert"
    }
  ]
}
```

### Dashboard View

**Location:** Dashboard → Admin → URL Rules

- Create/edit URL rules
- View blocked attempts
- See browsing history

---

## 6. Keystroke Monitoring

Privacy-respecting keystroke analysis.

### What's Captured

| Data | Captured | Not Captured |
|------|----------|--------------|
| Keystroke count | ✓ | |
| Active window | ✓ | |
| Typing speed | ✓ | |
| Individual keys | | ✓ |
| Passwords | | ✓ |

### Use Cases

- Detect unusual typing patterns
- Identify idle vs active time
- Track application usage intensity
- Detect potential insider threat (unusual activity)

### Configuration

```json
{
  "keystroke_logging": {
    "enabled": true,
    "privacy_mode": true,
    "log_counts_only": true,
    "track_windows": true
  }
}
```

---

## 7. SIEM Integration

Export DLP events to security systems.

### Supported Systems

| SIEM | Protocol | Configuration |
|------|----------|---------------|
| Splunk | HEC | Token-based |
| Microsoft Sentinel | REST | Azure credentials |
| Elasticsearch | REST | API key |
| Slack | Webhook | Webhook URL |
| Teams | Webhook | Webhook URL |
| Custom | HTTP POST | Any endpoint |

### Event Format

```json
{
  "event_type": "dlp_clipboard",
  "severity": "HIGH",
  "timestamp": "2025-01-01T12:00:00Z",
  "device_id": "xxx",
  "hostname": "MacBook-Pro",
  "username": "john",
  "details": {
    "sensitive_type": "credit_card",
    "source_app": "Safari",
    "destination_app": "ChatGPT"
  }
}
```

### Configuration

```json
{
  "siem_integrations": [
    {
      "type": "slack",
      "name": "Security Alerts",
      "endpoint_url": "https://hooks.slack.com/...",
      "enabled": true
    },
    {
      "type": "splunk",
      "name": "Splunk SIEM",
      "endpoint_url": "https://splunk.company.com:8088",
      "auth_token": "xxx",
      "enabled": true
    }
  ]
}
```

---

## DLP Best Practices

### 1. Start with Monitoring
- Enable logging before blocking
- Understand normal behavior first
- Reduce false positives

### 2. Gradual Enforcement
```
Week 1-2: Log only
Week 3-4: Alert on violations
Week 5+: Block critical violations
```

### 3. User Communication
- Notify users of monitoring
- Explain DLP policies
- Provide approved alternatives

### 4. Regular Review
- Review alerts weekly
- Tune rules for accuracy
- Update shadow IT list

### 5. Incident Response
- Document DLP incidents
- Investigate high-severity alerts
- Follow up with users

---

## DLP Dashboard Quick Reference

| Tab | Purpose |
|-----|---------|
| USB & Devices | USB connections, file transfers |
| Clipboard | Sensitive data copied |
| Shadow IT | Unauthorized apps detected |
| File Transfers | File access events |
| Keystrokes | Keystroke logging sessions |
| SIEM/Webhooks | Integration configuration |

---

## Troubleshooting DLP

### Clipboard not detected
- Check AppKit availability
- Verify Accessibility permission
- Restart clipboard_dlp.py

### USB events missing
- Check watchdog installed: `pip3 install watchdog`
- Verify disk access permission
- Check /Volumes monitoring

### File events not logging
- Verify file_monitor.py running
- Check watched directories exist
- Review file rules configuration

### Shadow IT false positives
- Add app to allowed list
- Create exception rule
- Contact admin for policy update
