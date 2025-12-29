#!/usr/bin/env python3
"""
Browser Monitor for Login Monitor PRO
Tracks URL visits, browser history, and which app opened URLs.
Supports Chrome, Safari, Firefox, and Edge on macOS.
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient


def get_base_dir() -> Path:
    return Path.home() / ".login-monitor"


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [BrowserMonitor] {message}"
    print(log_msg, flush=True)
    try:
        log_file = Path("/tmp/loginmonitor-browser.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


@dataclass
class UrlRule:
    """URL monitoring rule"""
    id: str
    name: str
    rule_type: str  # domain_block, domain_alert, category_block, keyword_alert
    pattern: str
    category: Optional[str] = None
    severity: str = "medium"
    action: str = "alert"
    enabled: bool = True

    def matches(self, url: str, domain: str) -> bool:
        """Check if URL matches this rule"""
        patterns = [p.strip().lower() for p in self.pattern.split(',')]

        if self.rule_type in ['domain_block', 'domain_alert', 'domain_allow']:
            for pat in patterns:
                if domain and (domain == pat or domain.endswith('.' + pat)):
                    return True

        elif self.rule_type == 'keyword_alert':
            url_lower = url.lower()
            for pat in patterns:
                if pat in url_lower:
                    return True

        return False


@dataclass
class UrlVisit:
    """Represents a URL visit"""
    url: str
    domain: str
    title: Optional[str] = None
    browser: Optional[str] = None
    source_app: Optional[str] = None
    source_bundle_id: Optional[str] = None
    category: str = "neutral"
    duration_seconds: int = 0
    is_incognito: bool = False
    user_name: str = field(default_factory=lambda: os.getenv("USER", "unknown"))
    timestamp: datetime = field(default_factory=datetime.now)
    matched_rule: Optional[UrlRule] = None


# Default URL categories
URL_CATEGORIES = {
    # Productive
    'github.com': 'productive',
    'gitlab.com': 'productive',
    'stackoverflow.com': 'productive',
    'docs.google.com': 'productive',
    'notion.so': 'productive',
    'figma.com': 'productive',
    'trello.com': 'productive',
    'asana.com': 'productive',
    'jira.atlassian.com': 'productive',
    'confluence.atlassian.com': 'productive',
    'medium.com': 'productive',
    'dev.to': 'productive',

    # Communication (neutral - could be work or personal)
    'slack.com': 'communication',
    'teams.microsoft.com': 'communication',
    'zoom.us': 'communication',
    'meet.google.com': 'communication',
    'discord.com': 'communication',
    'mail.google.com': 'communication',
    'outlook.live.com': 'communication',

    # Social (unproductive)
    'facebook.com': 'social',
    'instagram.com': 'social',
    'twitter.com': 'social',
    'x.com': 'social',
    'tiktok.com': 'social',
    'snapchat.com': 'social',
    'linkedin.com': 'social',
    'reddit.com': 'social',

    # Entertainment (unproductive)
    'youtube.com': 'entertainment',
    'netflix.com': 'entertainment',
    'twitch.tv': 'entertainment',
    'hulu.com': 'entertainment',
    'primevideo.com': 'entertainment',
    'disneyplus.com': 'entertainment',
    'spotify.com': 'entertainment',

    # Shopping
    'amazon.com': 'shopping',
    'ebay.com': 'shopping',
    'flipkart.com': 'shopping',
    'etsy.com': 'shopping',

    # News
    'news.google.com': 'news',
    'cnn.com': 'news',
    'bbc.com': 'news',
    'nytimes.com': 'news',
    'reuters.com': 'news',
}


class BrowserHistoryReader:
    """Reads browser history from local databases"""

    def __init__(self):
        self.last_read_times: Dict[str, datetime] = {}

    def _copy_locked_db(self, db_path: Path) -> Optional[Path]:
        """Copy database to temp location (browser locks the file)"""
        if not db_path.exists():
            return None

        temp_path = Path(f"/tmp/browser_history_{db_path.name}_{int(time.time())}.db")
        try:
            shutil.copy2(db_path, temp_path)
            return temp_path
        except Exception as e:
            log(f"Error copying {db_path}: {e}")
            return None

    def get_chrome_history(self, since: datetime = None) -> List[Dict]:
        """Get Chrome browsing history"""
        history = []
        db_path = Path.home() / "Library/Application Support/Google/Chrome/Default/History"

        temp_db = self._copy_locked_db(db_path)
        if not temp_db:
            return history

        try:
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()

            # Chrome stores timestamps as microseconds since 1601-01-01
            # Convert to Unix timestamp
            if since:
                # Chrome epoch is 1601-01-01, Unix epoch is 1970-01-01
                # Difference is 11644473600 seconds
                chrome_time = int((since.timestamp() + 11644473600) * 1000000)
                query = '''
                    SELECT url, title, last_visit_time
                    FROM urls
                    WHERE last_visit_time > ?
                    ORDER BY last_visit_time DESC
                    LIMIT 100
                '''
                cursor.execute(query, (chrome_time,))
            else:
                query = '''
                    SELECT url, title, last_visit_time
                    FROM urls
                    ORDER BY last_visit_time DESC
                    LIMIT 50
                '''
                cursor.execute(query)

            for row in cursor.fetchall():
                url, title, chrome_time = row
                # Convert Chrome timestamp to Python datetime
                unix_time = (chrome_time / 1000000) - 11644473600
                visit_time = datetime.fromtimestamp(unix_time)

                history.append({
                    'url': url,
                    'title': title,
                    'timestamp': visit_time,
                    'browser': 'Chrome'
                })

            conn.close()
        except Exception as e:
            log(f"Error reading Chrome history: {e}")
        finally:
            if temp_db and temp_db.exists():
                temp_db.unlink()

        return history

    def get_safari_history(self, since: datetime = None) -> List[Dict]:
        """Get Safari browsing history"""
        history = []
        db_path = Path.home() / "Library/Safari/History.db"

        temp_db = self._copy_locked_db(db_path)
        if not temp_db:
            return history

        try:
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()

            # Safari stores timestamps as seconds since 2001-01-01 (Cocoa epoch)
            cocoa_epoch_offset = 978307200  # seconds between 1970 and 2001

            if since:
                safari_time = since.timestamp() - cocoa_epoch_offset
                query = '''
                    SELECT h.url, v.title, v.visit_time
                    FROM history_items h
                    JOIN history_visits v ON h.id = v.history_item
                    WHERE v.visit_time > ?
                    ORDER BY v.visit_time DESC
                    LIMIT 100
                '''
                cursor.execute(query, (safari_time,))
            else:
                query = '''
                    SELECT h.url, v.title, v.visit_time
                    FROM history_items h
                    JOIN history_visits v ON h.id = v.history_item
                    ORDER BY v.visit_time DESC
                    LIMIT 50
                '''
                cursor.execute(query)

            for row in cursor.fetchall():
                url, title, safari_time = row
                unix_time = safari_time + cocoa_epoch_offset
                visit_time = datetime.fromtimestamp(unix_time)

                history.append({
                    'url': url,
                    'title': title,
                    'timestamp': visit_time,
                    'browser': 'Safari'
                })

            conn.close()
        except Exception as e:
            log(f"Error reading Safari history: {e}")
        finally:
            if temp_db and temp_db.exists():
                temp_db.unlink()

        return history

    def get_firefox_history(self, since: datetime = None) -> List[Dict]:
        """Get Firefox browsing history"""
        history = []

        # Find Firefox profile
        profiles_dir = Path.home() / "Library/Application Support/Firefox/Profiles"
        if not profiles_dir.exists():
            return history

        # Find default profile
        for profile_dir in profiles_dir.iterdir():
            if profile_dir.is_dir() and 'default' in profile_dir.name.lower():
                db_path = profile_dir / "places.sqlite"
                if db_path.exists():
                    break
        else:
            return history

        temp_db = self._copy_locked_db(db_path)
        if not temp_db:
            return history

        try:
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()

            # Firefox stores timestamps as microseconds since Unix epoch
            if since:
                firefox_time = int(since.timestamp() * 1000000)
                query = '''
                    SELECT p.url, p.title, h.visit_date
                    FROM moz_places p
                    JOIN moz_historyvisits h ON p.id = h.place_id
                    WHERE h.visit_date > ?
                    ORDER BY h.visit_date DESC
                    LIMIT 100
                '''
                cursor.execute(query, (firefox_time,))
            else:
                query = '''
                    SELECT p.url, p.title, h.visit_date
                    FROM moz_places p
                    JOIN moz_historyvisits h ON p.id = h.place_id
                    ORDER BY h.visit_date DESC
                    LIMIT 50
                '''
                cursor.execute(query)

            for row in cursor.fetchall():
                url, title, firefox_time = row
                visit_time = datetime.fromtimestamp(firefox_time / 1000000)

                history.append({
                    'url': url,
                    'title': title,
                    'timestamp': visit_time,
                    'browser': 'Firefox'
                })

            conn.close()
        except Exception as e:
            log(f"Error reading Firefox history: {e}")
        finally:
            if temp_db and temp_db.exists():
                temp_db.unlink()

        return history

    def get_all_history(self, since: datetime = None) -> List[Dict]:
        """Get history from all browsers"""
        all_history = []
        all_history.extend(self.get_chrome_history(since))
        all_history.extend(self.get_safari_history(since))
        all_history.extend(self.get_firefox_history(since))

        # Sort by timestamp descending
        all_history.sort(key=lambda x: x['timestamp'], reverse=True)
        return all_history


class ActiveTabMonitor:
    """Monitors the active browser tab URL"""

    def __init__(self):
        self.last_url: Optional[str] = None
        self.last_change_time: Optional[datetime] = None

    def get_active_tab_url(self) -> Optional[Tuple[str, str, str]]:
        """Get URL from active browser tab. Returns (url, title, browser)"""

        # Try Chrome first
        try:
            script = '''
            tell application "System Events"
                if exists (process "Google Chrome") then
                    tell application "Google Chrome"
                        if (count of windows) > 0 then
                            set theURL to URL of active tab of front window
                            set theTitle to title of active tab of front window
                            return theURL & "|" & theTitle & "|Chrome"
                        end if
                    end tell
                end if
            end tell
            return ""
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 3:
                    return parts[0], parts[1], parts[2]
        except Exception:
            pass

        # Try Safari
        try:
            script = '''
            tell application "System Events"
                if exists (process "Safari") then
                    tell application "Safari"
                        if (count of windows) > 0 then
                            set theURL to URL of current tab of front window
                            set theTitle to name of current tab of front window
                            return theURL & "|" & theTitle & "|Safari"
                        end if
                    end tell
                end if
            end tell
            return ""
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 3:
                    return parts[0], parts[1], parts[2]
        except Exception:
            pass

        return None

    def get_frontmost_app(self) -> Tuple[Optional[str], Optional[str]]:
        """Get currently frontmost app"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                return name of frontApp & "|" & bundle identifier of frontApp
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split('|')
                return parts[0], parts[1] if len(parts) > 1 else None
        except Exception:
            pass
        return None, None


class BrowserMonitor:
    """Main browser monitoring class"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.running = False
        self.rules: List[UrlRule] = []
        self.client: Optional[SupabaseClient] = None
        self.device_id: Optional[str] = None
        self.history_reader = BrowserHistoryReader()
        self.active_tab_monitor = ActiveTabMonitor()
        self.url_categories: Dict[str, str] = URL_CATEGORIES.copy()
        self.visit_queue: List[UrlVisit] = []
        self.queue_lock = threading.Lock()
        self.seen_urls: Dict[str, datetime] = {}

        self._init_supabase()
        self._load_rules()
        self._load_categories()

    def _load_config(self) -> dict:
        config_file = self.base_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception as e:
                log(f"Error loading config: {e}")
        return {}

    def _init_supabase(self):
        supabase_config = self.config.get("supabase", {})
        if not supabase_config.get("url"):
            log("Supabase not configured")
            return

        try:
            self.client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config.get("anon_key", ""),
                service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
            )
            self.device_id = supabase_config.get("device_id")
            log(f"Supabase initialized, device: {self.device_id}")
        except Exception as e:
            log(f"Error initializing Supabase: {e}")

    def _load_rules(self):
        """Load URL rules from Supabase"""
        if not self.client:
            self._load_default_rules()
            return

        try:
            response = self.client._request(
                "GET",
                "/rest/v1/url_rules?enabled=eq.true&select=*",
                use_service_key=True
            )

            if response:
                self.rules = []
                for rule_data in response:
                    rule = UrlRule(
                        id=rule_data['id'],
                        name=rule_data['name'],
                        rule_type=rule_data['rule_type'],
                        pattern=rule_data['pattern'],
                        category=rule_data.get('category'),
                        severity=rule_data.get('severity', 'medium'),
                        action=rule_data.get('action', 'alert'),
                        enabled=rule_data.get('enabled', True)
                    )
                    self.rules.append(rule)
                log(f"Loaded {len(self.rules)} URL rules from Supabase")
            else:
                self._load_default_rules()

        except Exception as e:
            log(f"Error loading URL rules: {e}")
            self._load_default_rules()

    def _load_default_rules(self):
        """Load default URL rules"""
        self.rules = [
            UrlRule(
                id="default-1",
                name="Job Sites",
                rule_type="domain_alert",
                pattern="indeed.com,glassdoor.com,monster.com,linkedin.com/jobs",
                severity="medium",
                action="alert"
            ),
            UrlRule(
                id="default-2",
                name="Cloud Storage",
                rule_type="domain_alert",
                pattern="dropbox.com,mega.nz,wetransfer.com,sendspace.com",
                severity="high",
                action="alert_screenshot"
            ),
            UrlRule(
                id="default-3",
                name="Gambling",
                rule_type="keyword_alert",
                pattern="casino,poker,betting,gambling",
                severity="critical",
                action="alert_screenshot"
            ),
        ]
        log(f"Loaded {len(self.rules)} default URL rules")

    def _load_categories(self):
        """Load URL categories from Supabase"""
        if not self.client:
            return

        try:
            response = self.client._request(
                "GET",
                "/rest/v1/url_categories?select=domain,category",
                use_service_key=True
            )

            if response:
                for cat in response:
                    self.url_categories[cat['domain']] = cat['category']
                log(f"Loaded {len(response)} URL categories")

        except Exception as e:
            log(f"Error loading URL categories: {e}")

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ""

    def _get_category(self, domain: str) -> str:
        """Get category for a domain"""
        # Check exact match first
        if domain in self.url_categories:
            return self.url_categories[domain]

        # Check parent domains
        parts = domain.split('.')
        for i in range(len(parts) - 1):
            parent = '.'.join(parts[i:])
            if parent in self.url_categories:
                return self.url_categories[parent]

        return "neutral"

    def _capture_screenshot(self, reason: str) -> Optional[str]:
        """Capture screenshot and upload"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.base_dir / "captured_images" / f"url_alert_{timestamp}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                ["/usr/sbin/screencapture", "-x", str(screenshot_path)],
                timeout=10
            )

            if screenshot_path.exists() and self.client and self.device_id:
                url = self.client.upload_file(
                    bucket="screenshots",
                    file_path=str(screenshot_path),
                    device_id=self.device_id
                )
                log(f"Screenshot captured for: {reason}")
                return url

        except Exception as e:
            log(f"Error capturing screenshot: {e}")
        return None

    def process_url_visit(self, url: str, title: str = None, browser: str = None,
                          source_app: str = None, source_bundle_id: str = None):
        """Process a URL visit"""
        if not url or url.startswith('file://') or url.startswith('chrome://'):
            return

        domain = self._get_domain(url)
        if not domain:
            return

        # Debounce: skip if we just saw this URL
        now = datetime.now()
        url_key = f"{domain}:{url[:100]}"
        if url_key in self.seen_urls:
            if (now - self.seen_urls[url_key]).total_seconds() < 60:
                return
        self.seen_urls[url_key] = now

        # Clean old entries
        cutoff = now - timedelta(minutes=5)
        self.seen_urls = {k: v for k, v in self.seen_urls.items() if v > cutoff}

        category = self._get_category(domain)

        visit = UrlVisit(
            url=url,
            domain=domain,
            title=title,
            browser=browser,
            source_app=source_app,
            source_bundle_id=source_bundle_id,
            category=category,
            timestamp=now
        )

        # Check against rules
        for rule in self.rules:
            if rule.matches(url, domain):
                visit.matched_rule = rule
                log(f"ALERT: {rule.name} triggered by {domain}")
                self._handle_alert(visit, rule)
                break

        # Queue for sync
        with self.queue_lock:
            self.visit_queue.append(visit)

    def _handle_alert(self, visit: UrlVisit, rule: UrlRule):
        """Handle URL alert"""
        screenshot_url = None

        if rule.action == 'alert_screenshot':
            screenshot_url = self._capture_screenshot(f"{rule.name}: {visit.domain}")

        if self.client and self.device_id:
            try:
                alert_data = {
                    "device_id": self.device_id,
                    "alert_type": "url_alert",
                    "severity": rule.severity,
                    "title": f"{rule.name}: {visit.domain}",
                    "description": f"URL accessed: {visit.url}\nUser: {visit.user_name}\nBrowser: {visit.browser or 'Unknown'}\nCategory: {visit.category}",
                    "metadata": {
                        "url": visit.url,
                        "domain": visit.domain,
                        "browser": visit.browser,
                        "user_name": visit.user_name,
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "screenshot_url": screenshot_url
                    },
                    "acknowledged": False
                }

                self.client._request(
                    "POST",
                    "/rest/v1/security_alerts",
                    alert_data,
                    use_service_key=True
                )
                log(f"URL alert sent: {rule.name}")

                if rule.severity in ['critical', 'high']:
                    self._send_push_notification(visit, rule)

            except Exception as e:
                log(f"Error sending URL alert: {e}")

    def _send_push_notification(self, visit: UrlVisit, rule: UrlRule):
        """Send push notification for URL alert"""
        try:
            from fcm_sender import send_fcm_notification
            send_fcm_notification(
                device_id=self.device_id,
                title=f"URL Alert: {rule.name}",
                body=f"{visit.domain} accessed via {visit.browser or 'browser'}",
                data={
                    "type": "url_alert",
                    "severity": rule.severity,
                    "url": visit.url[:200]
                }
            )
        except Exception as e:
            log(f"Error sending push: {e}")

    def _sync_visits(self):
        """Sync queued visits to Supabase"""
        if not self.client or not self.device_id:
            return

        with self.queue_lock:
            if not self.visit_queue:
                return
            visits_to_sync = self.visit_queue[:100]
            self.visit_queue = self.visit_queue[100:]

        for visit in visits_to_sync:
            try:
                visit_data = {
                    "device_id": self.device_id,
                    "url": visit.url[:2000],
                    "domain": visit.domain,
                    "title": visit.title[:500] if visit.title else None,
                    "browser": visit.browser,
                    "source_app": visit.source_app,
                    "source_bundle_id": visit.source_bundle_id,
                    "category": visit.category,
                    "duration_seconds": visit.duration_seconds,
                    "user_name": visit.user_name,
                    "triggered_rule_id": visit.matched_rule.id if visit.matched_rule and not visit.matched_rule.id.startswith('default') else None
                }

                self.client._request(
                    "POST",
                    "/rest/v1/url_visits",
                    visit_data,
                    use_service_key=True
                )

            except Exception as e:
                log(f"Error syncing visit: {e}")

    def _poll_active_tab(self):
        """Poll active browser tab"""
        result = self.active_tab_monitor.get_active_tab_url()
        if result:
            url, title, browser = result
            self.process_url_visit(url, title, browser)

    def _poll_history(self):
        """Poll browser history for new entries"""
        since = datetime.now() - timedelta(minutes=5)
        history = self.history_reader.get_all_history(since)

        for entry in history:
            self.process_url_visit(
                url=entry['url'],
                title=entry.get('title'),
                browser=entry.get('browser')
            )

    def _monitor_loop(self):
        """Main monitoring loop"""
        poll_count = 0
        while self.running:
            try:
                # Poll active tab every 5 seconds
                self._poll_active_tab()

                # Poll history every 30 seconds
                if poll_count % 6 == 0:
                    self._poll_history()

                # Sync to Supabase every minute
                if poll_count % 12 == 0:
                    self._sync_visits()

                poll_count += 1
                time.sleep(5)

            except Exception as e:
                log(f"Error in monitor loop: {e}")
                time.sleep(5)

    def run(self):
        """Start browser monitoring"""
        log("=" * 60)
        log("BROWSER MONITOR STARTED")
        log(f"URL rules: {len(self.rules)}")
        log(f"URL categories: {len(self.url_categories)}")
        log("=" * 60)

        self.running = True
        self._monitor_loop()


def main():
    monitor = BrowserMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        log("Browser monitor stopped")
        monitor.running = False


if __name__ == "__main__":
    main()
