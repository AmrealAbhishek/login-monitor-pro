#!/usr/bin/env python3
"""
CyVigil Clipboard DLP Monitor
==============================
Monitors clipboard for sensitive data patterns.
Detects when sensitive data is copied/pasted, especially to AI tools.
"""

import os
import sys
import json
import time
import hashlib
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Try to import AppKit for clipboard access
try:
    from AppKit import NSPasteboard, NSStringPboardType
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False
    print("Warning: PyObjC not available. Using pbpaste fallback.")

# Configuration
CONFIG_PATH = Path.home() / ".login-monitor" / "config.json"
LOG_PATH = "/tmp/loginmonitor-clipboard-dlp.log"

# Sensitive data patterns
SENSITIVE_PATTERNS = {
    'credit_card': {
        'pattern': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
        'severity': 'critical',
        'description': 'Credit card number'
    },
    'ssn': {
        'pattern': r'\b\d{3}-\d{2}-\d{4}\b',
        'severity': 'critical',
        'description': 'Social Security Number'
    },
    'aws_key': {
        'pattern': r'\bAKIA[0-9A-Z]{16}\b',
        'severity': 'critical',
        'description': 'AWS Access Key'
    },
    'aws_secret': {
        'pattern': r'\b[A-Za-z0-9/+=]{40}\b',
        'severity': 'high',
        'description': 'Possible AWS Secret Key'
    },
    'private_key': {
        'pattern': r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----',
        'severity': 'critical',
        'description': 'Private Key'
    },
    'api_key': {
        'pattern': r'\b(?:api[_-]?key|apikey|api_secret|secret_key|access_token)["\'\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?',
        'severity': 'high',
        'description': 'API Key or Token'
    },
    'jwt_token': {
        'pattern': r'\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b',
        'severity': 'high',
        'description': 'JWT Token'
    },
    'password': {
        'pattern': r'\b(?:password|passwd|pwd|secret)["\'\s:=]+["\']?([^\s"\']{8,})["\']?',
        'severity': 'high',
        'description': 'Password'
    },
    'email': {
        'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'severity': 'low',
        'description': 'Email Address'
    },
    'phone': {
        'pattern': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        'severity': 'low',
        'description': 'Phone Number'
    },
    'ip_address': {
        'pattern': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        'severity': 'low',
        'description': 'IP Address'
    },
    'github_token': {
        'pattern': r'\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})\b',
        'severity': 'critical',
        'description': 'GitHub Token'
    },
    'slack_token': {
        'pattern': r'\bxox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}\b',
        'severity': 'critical',
        'description': 'Slack Token'
    },
    'stripe_key': {
        'pattern': r'\b(sk_live_[a-zA-Z0-9]{24,}|pk_live_[a-zA-Z0-9]{24,})\b',
        'severity': 'critical',
        'description': 'Stripe API Key'
    },
    'database_url': {
        'pattern': r'\b(postgres|mysql|mongodb|redis)://[^\s]+\b',
        'severity': 'high',
        'description': 'Database Connection String'
    },
    'source_code': {
        'pattern': r'(?:def |class |function |const |let |var |import |from |require\()',
        'severity': 'medium',
        'description': 'Source Code'
    }
}

# AI Tools to monitor (clipboard paste destinations)
AI_TOOLS = {
    'ChatGPT': ['chat.openai.com', 'chatgpt.com'],
    'Claude': ['claude.ai', 'anthropic.com'],
    'Gemini': ['gemini.google.com', 'bard.google.com'],
    'Perplexity': ['perplexity.ai'],
    'GitHub Copilot': ['copilot.github.com'],
    'Bing Chat': ['bing.com/chat'],
    'Poe': ['poe.com'],
    'Character.AI': ['character.ai'],
}


def log(message: str):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(log_line + '\n')
    except Exception:
        pass


class ClipboardDLPMonitor:
    """Monitors clipboard for sensitive data."""

    def __init__(self):
        self.config = self._load_config()
        self.device_id = self.config.get("device_id", "")
        self.supabase_url = self.config.get("supabase_url", "")
        self.supabase_key = self.config.get("supabase_key", "")

        self.last_content_hash = ""
        self.last_content = ""

        # DLP settings
        dlp_config = self.config.get("dlp", {})
        self.monitor_clipboard = dlp_config.get("monitor_clipboard", True)
        self.alert_on_sensitive = dlp_config.get("alert_clipboard_sensitive", True)
        self.monitor_ai_paste = dlp_config.get("monitor_ai_paste", True)

        # Compile patterns
        self.compiled_patterns = {}
        for name, info in SENSITIVE_PATTERNS.items():
            try:
                self.compiled_patterns[name] = {
                    'regex': re.compile(info['pattern'], re.IGNORECASE | re.MULTILINE),
                    'severity': info['severity'],
                    'description': info['description']
                }
            except re.error as e:
                log(f"Invalid pattern for {name}: {e}")

        log(f"Clipboard DLP Monitor initialized. Device: {self.device_id[:8] if self.device_id else 'unknown'}...")

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading config: {e}")
        return {}

    def _get_clipboard_content(self) -> Tuple[str, str]:
        """Get current clipboard content. Returns (content, content_type)."""
        try:
            if HAS_APPKIT:
                pasteboard = NSPasteboard.generalPasteboard()
                content = pasteboard.stringForType_(NSStringPboardType)
                if content:
                    return str(content), 'text'
            else:
                # Fallback to pbpaste
                result = subprocess.run(
                    ['pbpaste'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout, 'text'
        except Exception as e:
            pass

        return "", ""

    def _get_content_hash(self, content: str) -> str:
        """Get hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_active_app(self) -> Tuple[str, str]:
        """Get the currently active application. Returns (app_name, window_title)."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                set windowTitle to ""
                try
                    tell process frontApp
                        set windowTitle to name of front window
                    end tell
                end try
                return frontApp & "|||" & windowTitle
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split('|||')
                app_name = parts[0] if parts else ""
                window_title = parts[1] if len(parts) > 1 else ""
                return app_name, window_title
        except Exception:
            pass

        return "", ""

    def _detect_sensitive_data(self, content: str) -> List[Dict]:
        """Detect sensitive data patterns in content."""
        detections = []

        for name, info in self.compiled_patterns.items():
            matches = info['regex'].findall(content)
            if matches:
                # Count matches
                match_count = len(matches) if isinstance(matches, list) else 1

                # For low severity, require multiple matches or long content
                if info['severity'] == 'low':
                    if match_count < 3 and len(content) < 100:
                        continue

                detections.append({
                    'type': name,
                    'severity': info['severity'],
                    'description': info['description'],
                    'match_count': match_count,
                    'sample': str(matches[0])[:50] if matches else ""
                })

        return detections

    def _is_ai_tool_active(self, app_name: str, window_title: str) -> Tuple[bool, str]:
        """Check if an AI tool is currently active."""
        app_lower = app_name.lower()
        title_lower = window_title.lower()

        # Check browser windows
        browsers = ['safari', 'chrome', 'firefox', 'edge', 'brave', 'arc']
        is_browser = any(b in app_lower for b in browsers)

        if is_browser:
            for ai_name, domains in AI_TOOLS.items():
                for domain in domains:
                    if domain.lower() in title_lower:
                        return True, ai_name

        # Check dedicated apps
        ai_app_names = ['chatgpt', 'claude', 'copilot']
        for ai_app in ai_app_names:
            if ai_app in app_lower:
                return True, ai_app.title()

        return False, ""

    def _send_to_supabase(self, table: str, data: dict) -> bool:
        """Send data to Supabase."""
        if not self.supabase_url or not self.supabase_key:
            return False

        try:
            response = requests.post(
                f"{self.supabase_url}/rest/v1/{table}",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=data,
                timeout=10
            )
            return response.status_code in (200, 201)
        except Exception as e:
            log(f"Supabase error: {e}")
            return False

    def _create_security_alert(self, alert_type: str, severity: str,
                                title: str, description: str):
        """Create a security alert."""
        alert_data = {
            "device_id": self.device_id,
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "description": description
        }
        self._send_to_supabase("security_alerts", alert_data)
        log(f"ALERT [{severity.upper()}]: {title}")

    def log_clipboard_event(self, content: str, content_type: str,
                            source_app: str, dest_app: str,
                            detections: List[Dict]):
        """Log clipboard event to Supabase."""

        # Create preview (first 500 chars, redacted)
        preview = content[:500]
        if len(content) > 500:
            preview += "... [truncated]"

        # Determine if sensitive and highest severity
        is_sensitive = len(detections) > 0
        sensitive_types = [d['type'] for d in detections]
        highest_severity = 'low'
        if detections:
            severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            highest_severity = max(detections, key=lambda d: severity_order.get(d['severity'], 0))['severity']

        event_data = {
            "device_id": self.device_id,
            "content_type": content_type,
            "content_preview": preview if not is_sensitive else f"[REDACTED - {', '.join(sensitive_types)}]",
            "content_hash": self._get_content_hash(content),
            "content_length": len(content),
            "source_app": source_app,
            "destination_app": dest_app,
            "sensitive_data_detected": is_sensitive,
            "sensitive_type": ', '.join(sensitive_types) if sensitive_types else None,
            "action_taken": "alerted" if is_sensitive else "logged"
        }

        self._send_to_supabase("clipboard_events", event_data)

        if is_sensitive:
            log(f"Clipboard: SENSITIVE [{highest_severity}] - {', '.join(sensitive_types)} - {source_app} → {dest_app}")
        else:
            log(f"Clipboard: {len(content)} chars - {source_app}")

    def check_clipboard(self):
        """Check clipboard for changes and analyze content."""
        content, content_type = self._get_clipboard_content()

        if not content:
            return

        # Check if content changed
        content_hash = self._get_content_hash(content)
        if content_hash == self.last_content_hash:
            return

        self.last_content_hash = content_hash
        self.last_content = content

        # Get active app (likely destination)
        dest_app, window_title = self._get_active_app()

        # Detect sensitive data
        detections = self._detect_sensitive_data(content)

        # Check if pasting to AI tool
        is_ai, ai_name = self._is_ai_tool_active(dest_app, window_title)

        if is_ai and self.monitor_ai_paste:
            # Special handling for AI tools
            if detections:
                # Critical: Sensitive data being pasted to AI
                self._create_security_alert(
                    "ai_data_paste",
                    "critical",
                    f"Sensitive Data Pasted to {ai_name}",
                    f"Detected {', '.join([d['type'] for d in detections])} being pasted to {ai_name}. "
                    f"Content length: {len(content)} chars. This may violate data protection policies."
                )
            elif len(content) > 500:
                # Warning: Large content to AI (possible code/data paste)
                if 'source_code' in [d['type'] for d in self._detect_sensitive_data(content)]:
                    self._create_security_alert(
                        "ai_code_paste",
                        "high",
                        f"Source Code Pasted to {ai_name}",
                        f"Detected source code ({len(content)} chars) being pasted to {ai_name}. "
                        f"This may expose proprietary code to third-party AI services."
                    )

            # Log AI paste event
            shadow_it_data = {
                "device_id": self.device_id,
                "app_name": ai_name,
                "app_category": "ai_chatbot",
                "url_accessed": window_title,
                "risk_level": "high" if detections else "medium",
                "data_sent_preview": content[:200] if not detections else "[REDACTED]",
                "detection_count": 1
            }
            self._send_to_supabase("shadow_it_detections", shadow_it_data)

        elif detections and self.alert_on_sensitive:
            # Alert on sensitive data in clipboard
            highest = max(detections, key=lambda d: {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}.get(d['severity'], 0))
            if highest['severity'] in ('high', 'critical'):
                self._create_security_alert(
                    "clipboard_sensitive",
                    highest['severity'],
                    f"Sensitive Data in Clipboard: {highest['description']}",
                    f"Detected {len(detections)} sensitive data type(s) in clipboard: "
                    f"{', '.join([d['description'] for d in detections])}. "
                    f"Active app: {dest_app}"
                )

        # Log the event
        self.log_clipboard_event(
            content=content,
            content_type=content_type,
            source_app="",  # Hard to determine source
            dest_app=dest_app,
            detections=detections
        )

    def run(self):
        """Main monitoring loop."""
        log("Clipboard DLP Monitor starting...")

        try:
            while True:
                if self.monitor_clipboard:
                    self.check_clipboard()

                # Check every 500ms for clipboard changes
                time.sleep(0.5)

        except KeyboardInterrupt:
            log("Clipboard DLP Monitor stopping...")


def main():
    """Entry point."""
    monitor = ClipboardDLPMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
