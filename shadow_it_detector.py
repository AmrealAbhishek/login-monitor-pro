#!/usr/bin/env python3
"""
CyVigil Shadow IT & AI Detector
================================
Detects unauthorized applications, AI tools, file sharing services,
and VPNs that bypass corporate security controls.
"""

import os
import sys
import json
import time
import subprocess
import re
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

import requests

# Configuration
CONFIG_PATH = Path.home() / ".login-monitor" / "config.json"
LOG_PATH = "/tmp/loginmonitor-shadow-it.log"

# Shadow IT Categories
SHADOW_IT_RULES = {
    # AI Chatbots (HIGH RISK - data leakage)
    'ai_chatbot': {
        'urls': [
            'chat.openai.com', 'chatgpt.com',
            'claude.ai', 'anthropic.com',
            'gemini.google.com', 'bard.google.com',
            'perplexity.ai',
            'poe.com',
            'character.ai',
            'you.com',
            'phind.com',
            'writesonic.com', 'jasper.ai',
            'copy.ai', 'rytr.me',
            'huggingface.co/chat',
        ],
        'apps': ['ChatGPT', 'Claude', 'Poe'],
        'risk_level': 'high',
        'default_action': 'monitor'
    },

    # AI Code Assistants (HIGH RISK - code exposure)
    'ai_code': {
        'urls': [
            'github.com/copilot',
            'copilot.github.com',
            'codeium.com',
            'tabnine.com',
            'replit.com',
            'cursor.sh',
        ],
        'apps': ['Copilot', 'Cursor', 'Replit'],
        'risk_level': 'high',
        'default_action': 'monitor'
    },

    # File Sharing (MEDIUM-HIGH RISK)
    'file_sharing': {
        'urls': [
            'dropbox.com',
            'drive.google.com',
            'onedrive.live.com',
            'wetransfer.com',
            'mega.nz', 'mega.io',
            'mediafire.com',
            'sendspace.com',
            'zippyshare.com',
            'box.com',
            'icloud.com/drive',
            'airdrop',
        ],
        'apps': ['Dropbox', 'Google Drive', 'OneDrive', 'WeTransfer'],
        'risk_level': 'medium',
        'default_action': 'monitor'
    },

    # Personal Email (MEDIUM RISK)
    'personal_email': {
        'urls': [
            'mail.google.com',
            'outlook.live.com',
            'mail.yahoo.com',
            'proton.me', 'protonmail.com',
            'tutanota.com',
            'mail.aol.com',
            'zoho.com/mail',
        ],
        'apps': [],
        'risk_level': 'medium',
        'default_action': 'monitor'
    },

    # Messaging Apps (MEDIUM RISK)
    'messaging': {
        'urls': [
            'web.telegram.org', 'telegram.org',
            'web.whatsapp.com',
            'discord.com', 'discordapp.com',
            'slack.com',
            'signal.org',
            'messenger.com',
            'teams.microsoft.com',
        ],
        'apps': ['Telegram', 'WhatsApp', 'Discord', 'Signal', 'Slack'],
        'risk_level': 'medium',
        'default_action': 'monitor'
    },

    # VPN Services (HIGH RISK - bypass security)
    'vpn': {
        'urls': [
            'nordvpn.com',
            'expressvpn.com',
            'surfshark.com',
            'privateinternetaccess.com',
            'cyberghostvpn.com',
            'protonvpn.com',
            'mullvad.net',
            'windscribe.com',
        ],
        'apps': ['NordVPN', 'ExpressVPN', 'Surfshark', 'ProtonVPN', 'Windscribe'],
        'risk_level': 'high',
        'default_action': 'blocked'
    },

    # Remote Access (HIGH RISK)
    'remote_access': {
        'urls': [
            'anydesk.com',
            'teamviewer.com',
            'remotedesktop.google.com',
            'parsec.app',
            'rustdesk.com',
        ],
        'apps': ['AnyDesk', 'TeamViewer', 'Parsec', 'RustDesk'],
        'risk_level': 'high',
        'default_action': 'blocked'
    },

    # Torrents (HIGH RISK)
    'torrent': {
        'urls': [
            'thepiratebay',
            '1337x.to',
            'rarbg',
            'torrentz',
            'yts.',
            'nyaa.si',
        ],
        'apps': ['uTorrent', 'BitTorrent', 'qBittorrent', 'Transmission', 'Vuze'],
        'risk_level': 'critical',
        'default_action': 'blocked'
    },

    # Social Media (LOW RISK - productivity)
    'social_media': {
        'urls': [
            'facebook.com',
            'twitter.com', 'x.com',
            'instagram.com',
            'tiktok.com',
            'linkedin.com',
            'reddit.com',
            'pinterest.com',
            'snapchat.com',
        ],
        'apps': ['Facebook', 'Twitter', 'Instagram', 'TikTok', 'Reddit'],
        'risk_level': 'low',
        'default_action': 'monitor'
    },

    # Streaming (LOW RISK - productivity)
    'streaming': {
        'urls': [
            'netflix.com',
            'youtube.com',
            'twitch.tv',
            'hulu.com',
            'disneyplus.com',
            'primevideo.com',
            'spotify.com',
            'soundcloud.com',
        ],
        'apps': ['Netflix', 'Spotify', 'YouTube', 'Twitch'],
        'risk_level': 'low',
        'default_action': 'monitor'
    },

    # Gaming (LOW RISK - productivity)
    'gaming': {
        'urls': [
            'steampowered.com', 'store.steampowered.com',
            'epicgames.com',
            'origin.com',
            'battle.net',
            'roblox.com',
        ],
        'apps': ['Steam', 'Epic Games', 'Origin', 'Battle.net', 'Roblox'],
        'risk_level': 'low',
        'default_action': 'monitor'
    },
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


class ShadowITDetector:
    """Detects and monitors Shadow IT usage."""

    def __init__(self):
        self.config = self._load_config()
        # Handle nested config structure
        supabase_config = self.config.get("supabase", {})
        self.device_id = supabase_config.get("device_id", self.config.get("device_id", ""))
        self.supabase_url = supabase_config.get("url", self.config.get("supabase_url", ""))
        self.supabase_key = supabase_config.get("anon_key", self.config.get("supabase_key", ""))

        # Get device context for admin visibility
        self.hostname = socket.gethostname()
        self.username = os.getenv("USER", "unknown")

        # Detection settings
        dlp_config = self.config.get("dlp", {})
        self.enabled = dlp_config.get("shadow_it_detection", True)
        self.alert_on_high_risk = dlp_config.get("alert_shadow_it_high", True)
        self.block_critical = dlp_config.get("block_critical_shadow_it", False)

        # Track detections to avoid spam
        self.recent_detections: Dict[str, datetime] = {}
        self.detection_cooldown = 300  # 5 minutes between same alerts

        # Running processes cache
        self.known_processes: Set[str] = set()

        log(f"Shadow IT Detector initialized. Device: {self.device_id[:8] if self.device_id else 'unknown'}...")

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading config: {e}")
        return {}

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

    def _should_alert(self, key: str) -> bool:
        """Check if we should alert for this detection (cooldown)."""
        now = datetime.now()
        if key in self.recent_detections:
            elapsed = (now - self.recent_detections[key]).total_seconds()
            if elapsed < self.detection_cooldown:
                return False

        self.recent_detections[key] = now
        return True

    def get_browser_urls(self) -> List[Tuple[str, str, str]]:
        """Get URLs from browser tabs. Returns [(browser, title, url), ...]"""
        urls = []

        # Safari
        try:
            script = '''
            tell application "Safari"
                set urlList to {}
                repeat with w in windows
                    repeat with t in tabs of w
                        set end of urlList to {name of t, URL of t}
                    end repeat
                end repeat
                return urlList
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # Parse AppleScript list output
                output = result.stdout.strip()
                # Simple parsing - this is fragile but works for basic cases
                for match in re.finditer(r'\{([^,]+), ([^}]+)\}', output):
                    title = match.group(1).strip()
                    url = match.group(2).strip()
                    urls.append(('Safari', title, url))
        except Exception:
            pass

        # Chrome
        try:
            script = '''
            tell application "Google Chrome"
                set urlList to {}
                repeat with w in windows
                    repeat with t in tabs of w
                        set end of urlList to {title of t, URL of t}
                    end repeat
                end repeat
                return urlList
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                output = result.stdout.strip()
                for match in re.finditer(r'\{([^,]+), ([^}]+)\}', output):
                    title = match.group(1).strip()
                    url = match.group(2).strip()
                    urls.append(('Chrome', title, url))
        except Exception:
            pass

        # Firefox (more complex, using window title)
        try:
            script = '''
            tell application "System Events"
                tell process "Firefox"
                    set windowTitles to {}
                    repeat with w in windows
                        set end of windowTitles to name of w
                    end repeat
                    return windowTitles
                end tell
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                for title in result.stdout.strip().split(','):
                    title = title.strip()
                    if title:
                        urls.append(('Firefox', title, ''))
        except Exception:
            pass

        return urls

    def get_running_apps(self) -> List[str]:
        """Get list of running applications."""
        apps = []

        # Try AppleScript first
        try:
            script = '''
            tell application "System Events"
                set appNames to name of every application process
                return appNames
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                apps = [app.strip() for app in result.stdout.split(',')]
                return apps
        except Exception:
            pass

        # Fallback: Use ps command (no permission needed)
        try:
            result = subprocess.run(
                ['ps', '-eo', 'comm'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    app = line.strip()
                    if app and not app.startswith('COMM'):
                        # Extract app name from path
                        app_name = app.split('/')[-1]
                        if app_name:
                            apps.append(app_name)
        except Exception:
            pass

        return list(set(apps))  # Remove duplicates

    def get_active_network_connections(self) -> List[Dict]:
        """Get active network connections to detect VPN/tunnel usage."""
        connections = []

        try:
            result = subprocess.run(
                ['netstat', '-an'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'ESTABLISHED' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            connections.append({
                                'protocol': parts[0],
                                'local': parts[3] if len(parts) > 3 else '',
                                'remote': parts[4] if len(parts) > 4 else '',
                            })
        except Exception:
            pass

        return connections

    def detect_shadow_it_via_network(self) -> List[Dict]:
        """Detect Shadow IT by checking network connections (no AppleScript needed)."""
        detections = []

        # Known Shadow IT domains to check
        shadow_domains = []
        for category, rules in SHADOW_IT_RULES.items():
            for url in rules['urls']:
                shadow_domains.append((url, category, rules['risk_level']))

        try:
            # Use lsof to get network connections with hostnames
            result = subprocess.run(
                ['lsof', '-i', '-n', '-P'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                connections = result.stdout.lower()

                for domain, category, risk_level in shadow_domains:
                    domain_lower = domain.lower().replace('.', '')
                    # Check if domain appears in connections (IP or process name)
                    if domain_lower in connections or domain.lower() in connections:
                        detections.append({
                            'app_name': domain,
                            'app_category': category,
                            'url_accessed': f'https://{domain}',
                            'risk_level': risk_level,
                            'matched_rule': domain,
                            'detection_method': 'network'
                        })
        except Exception:
            pass

        # Also check DNS cache for recently accessed domains
        try:
            result = subprocess.run(
                ['dscacheutil', '-cachedump', '-entries'],
                capture_output=True, text=True, timeout=5
            )
            # Note: This may not work on all macOS versions
        except Exception:
            pass

        # Check browser history files (SQLite) - works without permissions
        try:
            import sqlite3

            # Safari history
            safari_history = Path.home() / "Library/Safari/History.db"
            if safari_history.exists():
                conn = sqlite3.connect(f"file:{safari_history}?mode=ro", uri=True)
                cursor = conn.cursor()
                # Get URLs from last hour
                cursor.execute("""
                    SELECT url FROM history_items
                    WHERE visit_time > (strftime('%s', 'now') - 3600)
                """)
                for row in cursor.fetchall():
                    url = row[0].lower() if row[0] else ""
                    for domain, category, risk_level in shadow_domains:
                        if domain.lower() in url:
                            if not any(d['matched_rule'] == domain for d in detections):
                                detections.append({
                                    'app_name': domain.split('.')[0].title(),
                                    'app_category': category,
                                    'url_accessed': row[0],
                                    'risk_level': risk_level,
                                    'matched_rule': domain,
                                    'detection_method': 'browser_history'
                                })
                conn.close()

            # Chrome history
            chrome_history = Path.home() / "Library/Application Support/Google/Chrome/Default/History"
            if chrome_history.exists():
                # Chrome locks the file, so copy it first
                import shutil
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    shutil.copy2(chrome_history, tmp.name)
                    conn = sqlite3.connect(tmp.name)
                    cursor = conn.cursor()
                    # Get URLs from last hour
                    cursor.execute("""
                        SELECT url FROM urls
                        WHERE last_visit_time > (strftime('%s', 'now') - 3600) * 1000000 + 11644473600000000
                    """)
                    for row in cursor.fetchall():
                        url = row[0].lower() if row[0] else ""
                        for domain, category, risk_level in shadow_domains:
                            if domain.lower() in url:
                                if not any(d['matched_rule'] == domain for d in detections):
                                    detections.append({
                                        'app_name': domain.split('.')[0].title(),
                                        'app_category': category,
                                        'url_accessed': row[0],
                                        'risk_level': risk_level,
                                        'matched_rule': domain,
                                        'detection_method': 'browser_history'
                                    })
                    conn.close()
                    Path(tmp.name).unlink()
        except Exception as e:
            log(f"Browser history check error: {e}")

        return detections

    def detect_shadow_it_url(self, url: str, title: str, browser: str) -> Optional[Dict]:
        """Check if URL matches Shadow IT rules."""
        url_lower = url.lower() if url else ""
        title_lower = title.lower() if title else ""

        for category, rules in SHADOW_IT_RULES.items():
            for shadow_url in rules['urls']:
                if shadow_url.lower() in url_lower or shadow_url.lower() in title_lower:
                    return {
                        'app_name': title or shadow_url,
                        'app_bundle_id': browser,
                        'app_category': category,
                        'url_accessed': url or title,
                        'risk_level': rules['risk_level'],
                        'matched_rule': shadow_url
                    }

        return None

    def detect_shadow_it_app(self, app_name: str) -> Optional[Dict]:
        """Check if app matches Shadow IT rules."""
        app_lower = app_name.lower()

        for category, rules in SHADOW_IT_RULES.items():
            for shadow_app in rules.get('apps', []):
                if shadow_app.lower() in app_lower:
                    return {
                        'app_name': app_name,
                        'app_bundle_id': '',
                        'app_category': category,
                        'url_accessed': '',
                        'risk_level': rules['risk_level'],
                        'matched_rule': shadow_app
                    }

        return None

    def log_detection(self, detection: Dict):
        """Log Shadow IT detection to Supabase."""
        event_data = {
            "device_id": self.device_id,
            "hostname": self.hostname,
            "username": self.username,
            "app_name": detection['app_name'],
            "app_bundle_id": detection.get('app_bundle_id', ''),
            "app_category": detection['app_category'],
            "url_accessed": detection.get('url_accessed', ''),
            "is_approved": False,
            "risk_level": detection['risk_level'],
            "detection_count": 1
        }

        self._send_to_supabase("shadow_it_detections", event_data)
        log(f"Shadow IT: [{detection['risk_level'].upper()}] {detection['app_category']} - {detection['app_name']}")

    def scan(self):
        """Perform a full Shadow IT scan."""
        detections = []

        # Scan browser URLs (AppleScript method)
        urls = self.get_browser_urls()
        for browser, title, url in urls:
            detection = self.detect_shadow_it_url(url, title, browser)
            if detection:
                key = f"{detection['app_category']}:{detection['matched_rule']}"
                if self._should_alert(key):
                    detections.append(detection)
                    self.log_detection(detection)

                    # Alert on high/critical risk
                    if detection['risk_level'] in ('high', 'critical') and self.alert_on_high_risk:
                        self._create_security_alert(
                            f"shadow_it_{detection['app_category']}",
                            detection['risk_level'],
                            f"Shadow IT Detected: {detection['app_name']}",
                            f"Unauthorized {detection['app_category']} usage detected: {detection['app_name']}. "
                            f"URL: {detection.get('url_accessed', 'N/A')}. "
                            f"This may violate security policies."
                        )

        # Fallback: Network/History-based detection (no AppleScript needed)
        if not urls:
            network_detections = self.detect_shadow_it_via_network()
            for detection in network_detections:
                key = f"network:{detection['matched_rule']}"
                if self._should_alert(key):
                    detections.append(detection)
                    self.log_detection(detection)

                    if detection['risk_level'] in ('high', 'critical') and self.alert_on_high_risk:
                        self._create_security_alert(
                            f"shadow_it_{detection['app_category']}",
                            detection['risk_level'],
                            f"Shadow IT Detected: {detection['app_name']}",
                            f"Unauthorized {detection['app_category']} usage detected via {detection.get('detection_method', 'network')}. "
                            f"URL: {detection.get('url_accessed', 'N/A')}. "
                            f"This may violate security policies."
                        )

        # Scan running apps
        apps = self.get_running_apps()
        new_apps = set(apps) - self.known_processes
        self.known_processes = set(apps)

        for app in new_apps:
            detection = self.detect_shadow_it_app(app)
            if detection:
                key = f"app:{detection['matched_rule']}"
                if self._should_alert(key):
                    detections.append(detection)
                    self.log_detection(detection)

                    if detection['risk_level'] in ('high', 'critical') and self.alert_on_high_risk:
                        self._create_security_alert(
                            f"shadow_it_app_{detection['app_category']}",
                            detection['risk_level'],
                            f"Shadow IT App Launched: {detection['app_name']}",
                            f"Unauthorized {detection['app_category']} application detected: {detection['app_name']}. "
                            f"This may violate security policies."
                        )

        return detections

    def run(self):
        """Main monitoring loop."""
        log("Shadow IT Detector starting...")

        try:
            while True:
                if self.enabled:
                    self.scan()

                # Scan every 30 seconds
                time.sleep(30)

        except KeyboardInterrupt:
            log("Shadow IT Detector stopping...")


def main():
    """Entry point."""
    detector = ShadowITDetector()
    detector.run()


if __name__ == "__main__":
    main()
