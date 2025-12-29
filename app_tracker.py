#!/usr/bin/env python3
"""
App Tracker for Login Monitor PRO
Tracks FOREGROUND application usage on macOS - measures actual active time.
"""

import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

SYNC_INTERVAL_SECONDS = 60  # Sync to Supabase every minute
IDLE_THRESHOLD_SECONDS = 300  # 5 minutes = idle
FOCUS_CHECK_INTERVAL = 5  # Check focus every 5 seconds

# App productivity categories (bundle ID -> category)
PRODUCTIVE_APPS = {
    "com.apple.dt.Xcode": "productive",
    "com.microsoft.VSCode": "productive",
    "com.visualstudio.code.oss": "productive",
    "com.todesktop.230313mzl4w4u92": "productive",  # Cursor
    "com.jetbrains.intellij": "productive",
    "com.jetbrains.pycharm": "productive",
    "com.apple.Terminal": "productive",
    "com.googlecode.iterm2": "productive",
    "dev.warp.Warp-Stable": "productive",  # Warp Terminal
    "com.figma.Desktop": "productive",
    "com.sketch": "productive",
    "com.adobe.Photoshop": "productive",
    "com.adobe.Illustrator": "productive",
    "com.microsoft.Excel": "productive",
    "com.microsoft.Word": "productive",
    "com.microsoft.Powerpoint": "productive",
    "com.apple.Numbers": "productive",
    "com.apple.Pages": "productive",
    "com.apple.Keynote": "productive",
    "com.apple.Notes": "productive",
    "notion.id": "productive",
    "com.linear": "productive",
    "com.github.GitHubClient": "productive",
    "com.apple.Safari": "productive",
    "com.google.Chrome": "productive",
}

UNPRODUCTIVE_APPS = {
    "com.spotify.client": "unproductive",
    "com.netflix.Netflix": "unproductive",
    "tv.twitch.TwitchClient": "unproductive",
    "com.google.youtube": "unproductive",
    "com.facebook.Facebook": "unproductive",
    "com.atebits.Tweetie2": "unproductive",  # Twitter
    "com.instagram.Instagram": "unproductive",
    "com.reddit.Reddit": "unproductive",
    "com.tiktok.TikTok": "unproductive",
    "com.valvesoftware.steam": "unproductive",
    "com.apple.AppStore": "unproductive",
    "org.videolan.vlc": "unproductive",
    "com.apple.TV": "unproductive",
    "com.apple.Music": "unproductive",
}

COMMUNICATION_APPS = {
    "com.tinyspeck.slackmacgap": "communication",
    "com.microsoft.teams": "communication",
    "us.zoom.xos": "communication",
    "com.google.GoogleDrive": "communication",
    "com.apple.mail": "communication",
    "com.microsoft.Outlook": "communication",
    "com.apple.MobileSMS": "communication",
    "net.whatsapp.WhatsApp": "communication",
    "Mattermost.Desktop": "communication",
    "com.hnc.Discord": "communication",
    "com.apple.FaceTime": "communication",
    "com.apple.mobilephone": "communication",
}

# Map bundle IDs to proper display names
APP_DISPLAY_NAMES = {
    "dev.warp.Warp-Stable": "Warp Terminal",
    "com.todesktop.230313mzl4w4u92": "Cursor",
    "com.apple.finder": "Finder",
    "com.apple.Terminal": "Terminal",
    "com.google.Chrome": "Google Chrome",
    "com.apple.Safari": "Safari",
    "com.apple.Notes": "Notes",
    "com.apple.mail": "Mail",
    "com.apple.Music": "Apple Music",
    "com.apple.TV": "Apple TV",
    "com.microsoft.VSCode": "VS Code",
    "com.visualstudio.code.oss": "VS Code",
    "com.tinyspeck.slackmacgap": "Slack",
    "net.whatsapp.WhatsApp": "WhatsApp",
    "Mattermost.Desktop": "Mattermost",
    "com.apple.mobilephone": "Phone",
    "org.videolan.vlc": "VLC",
    "com.apple.systempreferences": "System Settings",
    "com.apple.Preview": "Preview",
}


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [AppTracker] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-apps.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


def get_app_display_name(app_name: str, bundle_id: str) -> str:
    """Get proper display name for an app"""
    if bundle_id in APP_DISPLAY_NAMES:
        return APP_DISPLAY_NAMES[bundle_id]
    return app_name


def get_app_category(bundle_id: str) -> str:
    """Get productivity category for an app"""
    if not bundle_id:
        return "neutral"

    if bundle_id in PRODUCTIVE_APPS:
        return "productive"
    elif bundle_id in UNPRODUCTIVE_APPS:
        return "unproductive"
    elif bundle_id in COMMUNICATION_APPS:
        return "communication"
    else:
        return "neutral"


class IdleDetector:
    """Detects system idle time using macOS IOKit"""

    @staticmethod
    def get_idle_time() -> int:
        """Get system idle time in seconds using ioreg"""
        try:
            result = subprocess.run(
                ["ioreg", "-c", "IOHIDSystem", "-d", "4"],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'HIDIdleTime' in line:
                        try:
                            ns = int(line.split('=')[1].strip())
                            return ns // 1_000_000_000
                        except (IndexError, ValueError):
                            pass

            return 0

        except Exception as e:
            log(f"Error getting idle time: {e}")
            return 0

    @staticmethod
    def is_idle(threshold_seconds: int = IDLE_THRESHOLD_SECONDS) -> bool:
        """Check if system is idle"""
        return IdleDetector.get_idle_time() >= threshold_seconds


class ForegroundTracker:
    """Tracks foreground application usage"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.current_app: Optional[Dict] = None
        self.focus_start_time: Optional[datetime] = None
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Table for foreground app sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS foreground_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                bundle_id TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds INTEGER,
                category TEXT DEFAULT 'neutral',
                window_title TEXT,
                synced INTEGER DEFAULT 0
            )
        ''')

        # Table for daily aggregates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_productivity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                productive_seconds INTEGER DEFAULT 0,
                unproductive_seconds INTEGER DEFAULT 0,
                neutral_seconds INTEGER DEFAULT 0,
                communication_seconds INTEGER DEFAULT 0,
                idle_seconds INTEGER DEFAULT 0,
                first_activity TEXT,
                last_activity TEXT,
                productivity_score REAL,
                synced INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def get_foreground_app(self) -> Optional[Dict]:
        """Get the currently focused application"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                set bundleId to bundle identifier of frontApp
                try
                    set winTitle to name of front window of frontApp
                on error
                    set winTitle to ""
                end try
                return appName & "|||" & bundleId & "|||" & winTitle
            end tell
            '''

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                parts = result.stdout.strip().split("|||")
                if len(parts) >= 2:
                    app_name = parts[0].strip()
                    bundle_id = parts[1].strip() if parts[1] != "missing value" else ""
                    window_title = parts[2].strip() if len(parts) > 2 and parts[2] != "missing value" else ""

                    # Get proper display name
                    display_name = get_app_display_name(app_name, bundle_id)

                    return {
                        "app_name": display_name,
                        "bundle_id": bundle_id,
                        "window_title": window_title,
                        "category": get_app_category(bundle_id)
                    }

        except Exception as e:
            log(f"Error getting foreground app: {e}")

        return None

    def update_focus(self):
        """Update focus tracking - call this regularly"""
        now = datetime.now()
        is_idle = IdleDetector.is_idle()

        if is_idle:
            # User is idle - save current session and record idle time
            if self.current_app and self.focus_start_time:
                duration = int((now - self.focus_start_time).total_seconds())
                if duration > 0:
                    self._save_session(
                        self.current_app["app_name"],
                        self.current_app["bundle_id"],
                        self.current_app["category"],
                        self.current_app.get("window_title", ""),
                        self.focus_start_time,
                        now,
                        duration
                    )
                    self._update_daily_stats(self.current_app["category"], duration)

                self.current_app = None
                self.focus_start_time = None

            # Record idle time
            self._update_daily_stats("idle", FOCUS_CHECK_INTERVAL)
            return

        # Not idle - check foreground app
        foreground = self.get_foreground_app()

        if not foreground:
            return

        # Check if app changed
        app_changed = (
            self.current_app is None or
            foreground["bundle_id"] != self.current_app.get("bundle_id") or
            foreground["window_title"] != self.current_app.get("window_title", "")
        )

        if app_changed:
            # Save previous session
            if self.current_app and self.focus_start_time:
                duration = int((now - self.focus_start_time).total_seconds())
                if duration > 0:
                    self._save_session(
                        self.current_app["app_name"],
                        self.current_app["bundle_id"],
                        self.current_app["category"],
                        self.current_app.get("window_title", ""),
                        self.focus_start_time,
                        now,
                        duration
                    )
                    self._update_daily_stats(self.current_app["category"], duration)

            # Start new session
            self.current_app = foreground
            self.focus_start_time = now
            log(f"Focus: {foreground['app_name']} ({foreground['category']})")

    def _save_session(self, app_name: str, bundle_id: str, category: str,
                      window_title: str, start_time: datetime, end_time: datetime, duration: int):
        """Save a foreground session to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO foreground_sessions
                (app_name, bundle_id, start_time, end_time, duration_seconds, category, window_title)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                app_name,
                bundle_id,
                start_time.isoformat(),
                end_time.isoformat(),
                duration,
                category,
                window_title
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            log(f"Error saving session: {e}")

    def _update_daily_stats(self, category: str, duration_seconds: int):
        """Update daily productivity statistics"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            now = datetime.now().isoformat()

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Check if today's record exists
            cursor.execute('SELECT id FROM daily_productivity WHERE date = ?', (today,))
            row = cursor.fetchone()

            if row:
                # Update existing record
                column = f"{category}_seconds"
                cursor.execute(
                    f'UPDATE daily_productivity SET {column} = {column} + ?, last_activity = ?, synced = 0 WHERE date = ?',
                    (duration_seconds, now, today)
                )
            else:
                # Create new record
                cursor.execute('''
                    INSERT INTO daily_productivity
                    (date, productive_seconds, unproductive_seconds, neutral_seconds, communication_seconds, idle_seconds, first_activity, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    today,
                    duration_seconds if category == "productive" else 0,
                    duration_seconds if category == "unproductive" else 0,
                    duration_seconds if category == "neutral" else 0,
                    duration_seconds if category == "communication" else 0,
                    duration_seconds if category == "idle" else 0,
                    now,
                    now
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            log(f"Error updating daily stats: {e}")

    def calculate_productivity_score(self, date: str = None) -> float:
        """Calculate productivity score for a date (0-100)"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT productive_seconds, unproductive_seconds, neutral_seconds, communication_seconds
                FROM daily_productivity WHERE date = ?
            ''', (date,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return 0

            productive, unproductive, neutral, communication = row

            # Calculate total active time (excluding idle)
            total_active = productive + unproductive + neutral + communication

            if total_active == 0:
                return 0

            # Score calculation:
            # Productive: full weight
            # Communication: half weight (can be productive or not)
            # Neutral: zero weight
            # Unproductive: negative weight

            weighted_score = (
                (productive * 1.0) +
                (communication * 0.5) +
                (neutral * 0.0) +
                (unproductive * -0.5)
            )

            # Normalize to 0-100
            max_possible = total_active * 1.0
            min_possible = total_active * -0.5

            if max_possible == min_possible:
                return 50

            score = ((weighted_score - min_possible) / (max_possible - min_possible)) * 100
            return round(max(0, min(100, score)), 2)

        except Exception as e:
            log(f"Error calculating productivity score: {e}")
            return 0


class SupabaseSyncer:
    """Syncs data to Supabase"""

    def __init__(self, db_path: Path, config: dict):
        self.db_path = db_path
        self.config = config
        self.supabase_config = config.get("supabase", {})

    def sync_all(self):
        """Sync all unsynced data to Supabase"""
        if not self._is_configured():
            return

        self._sync_foreground_sessions()
        self._sync_daily_productivity()

    def _is_configured(self) -> bool:
        """Check if Supabase is configured"""
        return bool(
            self.supabase_config.get("url") and
            self.supabase_config.get("device_id")
        )

    def _sync_foreground_sessions(self):
        """Sync foreground sessions to app_usage table"""
        try:
            from supabase_client import SupabaseClient

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, app_name, bundle_id, start_time, end_time, duration_seconds, category, window_title
                FROM foreground_sessions
                WHERE synced = 0
                ORDER BY start_time ASC
                LIMIT 100
            ''')

            rows = cursor.fetchall()

            if not rows:
                conn.close()
                return

            client = SupabaseClient(
                url=self.supabase_config["url"],
                anon_key=self.supabase_config.get("anon_key", ""),
                service_key=self.supabase_config.get("service_key", self.supabase_config.get("anon_key", ""))
            )

            synced_ids = []
            device_id = self.supabase_config["device_id"]

            for row in rows:
                session_id, app_name, bundle_id, start_time, end_time, duration, category, window_title = row

                try:
                    client._request(
                        "POST",
                        "/rest/v1/app_usage",
                        {
                            "device_id": device_id,
                            "app_name": app_name,
                            "bundle_id": bundle_id,
                            "launched_at": start_time,
                            "terminated_at": end_time,
                            "duration_seconds": duration,
                            "category": category,
                            "window_title": window_title
                        },
                        use_service_key=True
                    )
                    synced_ids.append(session_id)

                except Exception as e:
                    log(f"Error syncing session {session_id}: {e}")

            if synced_ids:
                cursor.execute(
                    f'UPDATE foreground_sessions SET synced = 1 WHERE id IN ({",".join("?" * len(synced_ids))})',
                    synced_ids
                )
                conn.commit()
                log(f"Synced {len(synced_ids)} foreground sessions")

            conn.close()

        except Exception as e:
            log(f"Error in foreground sync: {e}")

    def _sync_daily_productivity(self):
        """Sync daily productivity to productivity_scores table"""
        try:
            from supabase_client import SupabaseClient

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT date, productive_seconds, unproductive_seconds, neutral_seconds,
                       communication_seconds, idle_seconds, first_activity, last_activity
                FROM daily_productivity
                WHERE synced = 0
            ''')

            rows = cursor.fetchall()

            if not rows:
                conn.close()
                return

            client = SupabaseClient(
                url=self.supabase_config["url"],
                anon_key=self.supabase_config.get("anon_key", ""),
                service_key=self.supabase_config.get("service_key", self.supabase_config.get("anon_key", ""))
            )

            device_id = self.supabase_config["device_id"]
            synced_dates = []

            for row in rows:
                date, productive, unproductive, neutral, communication, idle, first_activity, last_activity = row

                # Calculate score
                total_active = productive + unproductive + neutral + communication
                if total_active > 0:
                    weighted = (productive * 1.0) + (communication * 0.5) + (unproductive * -0.5)
                    max_p = total_active * 1.0
                    min_p = total_active * -0.5
                    score = ((weighted - min_p) / (max_p - min_p)) * 100 if max_p != min_p else 50
                    score = round(max(0, min(100, score)), 2)
                else:
                    score = 0

                # Extract just time from datetime for TIME columns
                first_time = None
                last_time = None
                if first_activity:
                    try:
                        first_time = first_activity.split('T')[1].split('.')[0] if 'T' in first_activity else first_activity
                    except:
                        first_time = None
                if last_activity:
                    try:
                        last_time = last_activity.split('T')[1].split('.')[0] if 'T' in last_activity else last_activity
                    except:
                        last_time = None

                try:
                    # Try to upsert to productivity_scores (use PATCH for existing, POST for new)
                    # First check if exists
                    try:
                        existing = client._request(
                            "GET",
                            f"/rest/v1/productivity_scores?device_id=eq.{device_id}&date=eq.{date}",
                            use_service_key=True
                        )
                        if existing and len(existing) > 0:
                            # Update existing
                            update_data = {
                                "productivity_score": score,
                                "productive_seconds": productive,
                                "unproductive_seconds": unproductive,
                                "idle_seconds": idle,
                            }
                            if first_time:
                                update_data["first_login"] = first_time
                            if last_time:
                                update_data["last_activity"] = last_time

                            client._request(
                                "PATCH",
                                f"/rest/v1/productivity_scores?device_id=eq.{device_id}&date=eq.{date}",
                                update_data,
                                use_service_key=True
                            )
                        else:
                            # Insert new
                            insert_data = {
                                "device_id": device_id,
                                "date": date,
                                "productivity_score": score,
                                "productive_seconds": productive,
                                "unproductive_seconds": unproductive,
                                "idle_seconds": idle,
                            }
                            if first_time:
                                insert_data["first_login"] = first_time
                            if last_time:
                                insert_data["last_activity"] = last_time

                            client._request(
                                "POST",
                                "/rest/v1/productivity_scores",
                                insert_data,
                                use_service_key=True
                            )
                    except Exception:
                        # If check fails, try insert
                        insert_data = {
                            "device_id": device_id,
                            "date": date,
                            "productivity_score": score,
                            "productive_seconds": productive,
                            "unproductive_seconds": unproductive,
                            "idle_seconds": idle,
                        }
                        if first_time:
                            insert_data["first_login"] = first_time
                        if last_time:
                            insert_data["last_activity"] = last_time

                        client._request(
                            "POST",
                            "/rest/v1/productivity_scores",
                            insert_data,
                            use_service_key=True
                        )
                    synced_dates.append(date)

                except Exception as e:
                    log(f"Error syncing date {date}: {e}")

            if synced_dates:
                cursor.execute(
                    f'UPDATE daily_productivity SET synced = 1 WHERE date IN ({",".join("?" * len(synced_dates))})',
                    synced_dates
                )
                conn.commit()
                log(f"Synced {len(synced_dates)} days of productivity data")

            conn.close()

        except Exception as e:
            log(f"Error in daily productivity sync: {e}")


class AppTracker:
    """Main application tracker"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.db_path = self.base_dir / "app_usage.db"
        self.foreground_tracker = ForegroundTracker(self.db_path)
        self.syncer = SupabaseSyncer(self.db_path, self.config)
        self.last_sync_time = datetime.now()

    def _load_config(self) -> dict:
        """Load configuration from file"""
        config_file = self.base_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception as e:
                log(f"Error loading config: {e}")
        return {}

    def run(self):
        """Main tracking loop"""
        log("=" * 60)
        log("APP TRACKER STARTED (Foreground Mode)")
        log("=" * 60)

        while True:
            try:
                # Update foreground tracking
                self.foreground_tracker.update_focus()

                # Sync to Supabase periodically
                if (datetime.now() - self.last_sync_time).total_seconds() >= SYNC_INTERVAL_SECONDS:
                    self.syncer.sync_all()
                    self.last_sync_time = datetime.now()

                time.sleep(FOCUS_CHECK_INTERVAL)

            except KeyboardInterrupt:
                log("App tracker stopped by user")
                # Final sync
                self.syncer.sync_all()
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(FOCUS_CHECK_INTERVAL)


def main():
    tracker = AppTracker()
    tracker.run()


if __name__ == "__main__":
    main()
