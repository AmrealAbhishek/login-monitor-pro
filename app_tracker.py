#!/usr/bin/env python3
"""
App Tracker for Login Monitor PRO
Tracks application usage on macOS using NSWorkspace notifications.
"""

import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

SYNC_INTERVAL_SECONDS = 300  # Sync to Supabase every 5 minutes
IDLE_THRESHOLD_SECONDS = 300  # 5 minutes = idle

# App productivity categories (default mappings)
PRODUCTIVE_APPS = {
    "com.apple.dt.Xcode": "productive",
    "com.microsoft.VSCode": "productive",
    "com.visualstudio.code.oss": "productive",
    "com.jetbrains.intellij": "productive",
    "com.jetbrains.pycharm": "productive",
    "com.apple.Terminal": "productive",
    "com.googlecode.iterm2": "productive",
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
    "notion.id": "productive",
    "com.linear": "productive",
    "com.github.GitHubClient": "productive",
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
}

COMMUNICATION_APPS = {
    "com.tinyspeck.slackmacgap": "communication",
    "com.microsoft.teams": "communication",
    "us.zoom.xos": "communication",
    "com.google.GoogleDrive": "communication",
    "com.apple.mail": "communication",
    "com.microsoft.Outlook": "communication",
    "com.apple.MobileSMS": "communication",
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


class AppSession:
    """Represents an app usage session"""
    def __init__(self, app_name: str, bundle_id: str, launched_at: datetime):
        self.app_name = app_name
        self.bundle_id = bundle_id
        self.launched_at = launched_at
        self.terminated_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> int:
        end_time = self.terminated_at or datetime.now()
        return int((end_time - self.launched_at).total_seconds())

    def to_dict(self) -> Dict:
        return {
            "app_name": self.app_name,
            "bundle_id": self.bundle_id,
            "launched_at": self.launched_at.isoformat(),
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "duration_seconds": self.duration_seconds
        }


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
                        # Extract nanoseconds value
                        try:
                            ns = int(line.split('=')[1].strip())
                            return ns // 1_000_000_000  # Convert to seconds
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


class ProductivityTracker:
    """Tracks and calculates productivity scores"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_productivity_table()

    def _init_productivity_table(self):
        """Initialize productivity scores table"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS productivity_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    productive_seconds INTEGER DEFAULT 0,
                    unproductive_seconds INTEGER DEFAULT 0,
                    neutral_seconds INTEGER DEFAULT 0,
                    communication_seconds INTEGER DEFAULT 0,
                    idle_seconds INTEGER DEFAULT 0,
                    total_active_seconds INTEGER DEFAULT 0,
                    productivity_score REAL,
                    login_count INTEGER DEFAULT 0,
                    first_login TEXT,
                    last_activity TEXT,
                    top_apps TEXT,
                    synced INTEGER DEFAULT 0
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            log(f"Error creating productivity table: {e}")

    def get_app_category(self, bundle_id: str) -> str:
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

    def update_daily_stats(self, bundle_id: str, duration_seconds: int, is_idle: bool = False):
        """Update daily productivity statistics"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            category = self.get_app_category(bundle_id) if not is_idle else "idle"

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Check if today's record exists
            cursor.execute('SELECT id FROM productivity_daily WHERE date = ?', (today,))
            row = cursor.fetchone()

            if row:
                # Update existing record
                if category == "productive":
                    cursor.execute('UPDATE productivity_daily SET productive_seconds = productive_seconds + ? WHERE date = ?',
                                 (duration_seconds, today))
                elif category == "unproductive":
                    cursor.execute('UPDATE productivity_daily SET unproductive_seconds = unproductive_seconds + ? WHERE date = ?',
                                 (duration_seconds, today))
                elif category == "communication":
                    cursor.execute('UPDATE productivity_daily SET communication_seconds = communication_seconds + ? WHERE date = ?',
                                 (duration_seconds, today))
                elif category == "idle":
                    cursor.execute('UPDATE productivity_daily SET idle_seconds = idle_seconds + ? WHERE date = ?',
                                 (duration_seconds, today))
                else:
                    cursor.execute('UPDATE productivity_daily SET neutral_seconds = neutral_seconds + ? WHERE date = ?',
                                 (duration_seconds, today))

                # Update total active time (non-idle)
                if not is_idle:
                    cursor.execute('UPDATE productivity_daily SET total_active_seconds = total_active_seconds + ? WHERE date = ?',
                                 (duration_seconds, today))

                # Update last activity
                cursor.execute('UPDATE productivity_daily SET last_activity = ? WHERE date = ?',
                             (datetime.now().isoformat(), today))

            else:
                # Create new record for today
                cursor.execute('''
                    INSERT INTO productivity_daily (date, productive_seconds, unproductive_seconds, neutral_seconds,
                                                   communication_seconds, idle_seconds, total_active_seconds,
                                                   first_login, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    today,
                    duration_seconds if category == "productive" else 0,
                    duration_seconds if category == "unproductive" else 0,
                    duration_seconds if category == "neutral" else 0,
                    duration_seconds if category == "communication" else 0,
                    duration_seconds if category == "idle" else 0,
                    duration_seconds if not is_idle else 0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            log(f"Error updating daily stats: {e}")

    def calculate_productivity_score(self, date: str = None) -> Dict:
        """Calculate productivity score for a given date"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT productive_seconds, unproductive_seconds, neutral_seconds,
                       communication_seconds, idle_seconds, total_active_seconds,
                       first_login, last_activity
                FROM productivity_daily WHERE date = ?
            ''', (date,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return {"date": date, "score": None, "message": "No data for this date"}

            productive, unproductive, neutral, communication, idle, total_active, first_login, last_activity = row

            # Calculate score: weighted average
            # Productive: +1.0, Communication: +0.5, Neutral: 0, Unproductive: -1.0
            if total_active == 0:
                score = 0
            else:
                weighted = (productive * 1.0) + (communication * 0.5) + (neutral * 0) + (unproductive * -0.5)
                # Normalize to 0-100 scale
                max_possible = total_active * 1.0
                min_possible = total_active * -0.5
                if max_possible - min_possible == 0:
                    score = 50
                else:
                    score = ((weighted - min_possible) / (max_possible - min_possible)) * 100

            score = round(max(0, min(100, score)), 2)

            # Update score in database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute('UPDATE productivity_daily SET productivity_score = ? WHERE date = ?', (score, date))
            conn.commit()
            conn.close()

            return {
                "date": date,
                "score": score,
                "productive_seconds": productive,
                "unproductive_seconds": unproductive,
                "neutral_seconds": neutral,
                "communication_seconds": communication,
                "idle_seconds": idle,
                "total_active_seconds": total_active,
                "first_login": first_login,
                "last_activity": last_activity,
                "breakdown": {
                    "productive": self._format_duration(productive),
                    "unproductive": self._format_duration(unproductive),
                    "neutral": self._format_duration(neutral),
                    "communication": self._format_duration(communication),
                    "idle": self._format_duration(idle),
                    "total_active": self._format_duration(total_active)
                }
            }

        except Exception as e:
            log(f"Error calculating productivity score: {e}")
            return {"error": str(e)}

    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def get_weekly_summary(self) -> Dict:
        """Get productivity summary for the last 7 days"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            cursor.execute('''
                SELECT date, productivity_score, productive_seconds, unproductive_seconds, total_active_seconds
                FROM productivity_daily
                WHERE date >= ?
                ORDER BY date DESC
            ''', (since_date,))

            rows = cursor.fetchall()
            conn.close()

            days = []
            total_score = 0
            valid_days = 0

            for row in rows:
                date, score, productive, unproductive, total = row
                days.append({
                    "date": date,
                    "score": score,
                    "productive_hours": round(productive / 3600, 1) if productive else 0,
                    "unproductive_hours": round(unproductive / 3600, 1) if unproductive else 0,
                    "total_hours": round(total / 3600, 1) if total else 0
                })
                if score is not None:
                    total_score += score
                    valid_days += 1

            avg_score = round(total_score / valid_days, 2) if valid_days > 0 else None

            return {
                "period": "last_7_days",
                "average_score": avg_score,
                "days": days,
                "total_days_tracked": len(days),
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            log(f"Error getting weekly summary: {e}")
            return {"error": str(e)}

    def sync_to_supabase(self, device_id: str, client):
        """Sync productivity data to Supabase"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT date, productivity_score, productive_seconds, unproductive_seconds,
                       neutral_seconds, idle_seconds, total_active_seconds, login_count,
                       first_login, last_activity
                FROM productivity_daily
                WHERE synced = 0
            ''')

            rows = cursor.fetchall()

            synced_dates = []
            for row in rows:
                date, score, productive, unproductive, neutral, idle, total, logins, first, last = row

                try:
                    # Upsert to productivity_scores table
                    client._request(
                        "POST",
                        "/rest/v1/productivity_scores",
                        {
                            "device_id": device_id,
                            "date": date,
                            "productivity_score": score,
                            "productive_seconds": productive,
                            "unproductive_seconds": unproductive,
                            "neutral_seconds": neutral,
                            "idle_seconds": idle,
                            "total_active_seconds": total,
                            "login_count": logins,
                            "first_login": first,
                            "last_activity": last
                        },
                        use_service_key=True,
                        headers={"Prefer": "resolution=merge-duplicates"}
                    )
                    synced_dates.append(date)
                except Exception as e:
                    log(f"Error syncing date {date}: {e}")

            if synced_dates:
                placeholders = ",".join("?" * len(synced_dates))
                cursor.execute(f'UPDATE productivity_daily SET synced = 1 WHERE date IN ({placeholders})', synced_dates)
                conn.commit()
                log(f"Synced {len(synced_dates)} days of productivity data")

            conn.close()

        except Exception as e:
            log(f"Error in productivity sync: {e}")


class AppTracker:
    """Tracks application usage"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.db_path = self.base_dir / "app_usage.db"
        self.active_apps: Dict[str, AppSession] = {}
        self.last_sync_time = datetime.now()
        self._init_database()

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

    def _init_database(self):
        """Initialize local SQLite database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                bundle_id TEXT,
                launched_at TEXT NOT NULL,
                terminated_at TEXT,
                duration_seconds INTEGER,
                synced INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()
        log("Database initialized")

    def get_running_apps(self) -> List[Dict]:
        """Get list of currently running applications"""
        apps = []

        try:
            # Use AppleScript to get running apps
            script = '''
            tell application "System Events"
                set appList to {}
                repeat with p in (every process whose background only is false)
                    set appName to name of p
                    set bundleId to bundle identifier of p
                    set end of appList to appName & "|||" & bundleId
                end repeat
                return appList
            end tell
            '''

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                app_strings = result.stdout.strip().split(", ")
                for app_str in app_strings:
                    parts = app_str.split("|||")
                    if len(parts) >= 2:
                        apps.append({
                            "app_name": parts[0].strip(),
                            "bundle_id": parts[1].strip() if parts[1] != "missing value" else ""
                        })

        except subprocess.TimeoutExpired:
            log("Timeout getting running apps")
        except Exception as e:
            log(f"Error getting running apps: {e}")

        return apps

    def track_app_changes(self):
        """Track app launches and terminations"""
        current_apps = self.get_running_apps()
        current_bundles = {app["bundle_id"]: app for app in current_apps if app.get("bundle_id")}

        # Check for new apps
        for bundle_id, app_info in current_bundles.items():
            if bundle_id and bundle_id not in self.active_apps:
                session = AppSession(
                    app_name=app_info["app_name"],
                    bundle_id=bundle_id,
                    launched_at=datetime.now()
                )
                self.active_apps[bundle_id] = session
                log(f"App launched: {app_info['app_name']}")

                # Check for suspicious apps
                self._check_suspicious_app(app_info)

        # Check for terminated apps
        terminated = []
        for bundle_id, session in self.active_apps.items():
            if bundle_id not in current_bundles:
                session.terminated_at = datetime.now()
                terminated.append(bundle_id)
                self._save_session(session)
                log(f"App terminated: {session.app_name} (duration: {session.duration_seconds}s)")

        # Remove terminated apps from active tracking
        for bundle_id in terminated:
            del self.active_apps[bundle_id]

    def _check_suspicious_app(self, app_info: Dict):
        """Check if an app launch is suspicious"""
        suspicious_apps = [
            "Terminal",
            "iTerm",
            "Remote Desktop",
            "TeamViewer",
            "AnyDesk",
            "VNC Viewer",
            "Screen Sharing"
        ]

        # Check current hour
        current_hour = datetime.now().hour
        is_unusual_time = current_hour < 6 or current_hour > 23

        app_name = app_info.get("app_name", "")

        if app_name in suspicious_apps and is_unusual_time:
            log(f"SUSPICIOUS: {app_name} opened at unusual time!")
            self._trigger_suspicious_alert(app_info)

    def _trigger_suspicious_alert(self, app_info: Dict):
        """Trigger alert for suspicious app usage"""
        try:
            from supabase_client import SupabaseClient

            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if supabase_config.get("url") and supabase_config.get("device_id"):
                client = SupabaseClient(
                    url=supabase_config["url"],
                    anon_key=supabase_config.get("anon_key", ""),
                    service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
                )

                event_data = {
                    "event_type": "SuspiciousApp",
                    "activity": {
                        "app_name": app_info.get("app_name"),
                        "bundle_id": app_info.get("bundle_id"),
                        "hour": datetime.now().hour,
                        "reason": "Unusual time of use"
                    },
                    "timestamp": datetime.now().isoformat()
                }

                client.send_event(
                    device_id=supabase_config["device_id"],
                    event_data=event_data
                )

        except Exception as e:
            log(f"Error triggering suspicious alert: {e}")

    def _save_session(self, session: AppSession):
        """Save a completed session to local database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO app_sessions (app_name, bundle_id, launched_at, terminated_at, duration_seconds)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session.app_name,
                session.bundle_id,
                session.launched_at.isoformat(),
                session.terminated_at.isoformat() if session.terminated_at else None,
                session.duration_seconds
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            log(f"Error saving session: {e}")

    def sync_to_supabase(self):
        """Sync unsynced sessions to Supabase"""
        try:
            from supabase_client import SupabaseClient

            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if not supabase_config.get("url") or not supabase_config.get("device_id"):
                return

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM app_sessions WHERE synced = 0 LIMIT 50')
            rows = cursor.fetchall()

            if not rows:
                conn.close()
                return

            client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config.get("anon_key", ""),
                service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
            )

            synced_ids = []

            for row in rows:
                session_id, app_name, bundle_id, launched_at, terminated_at, duration, _ = row

                try:
                    # Insert into Supabase app_usage table
                    client._request(
                        "POST",
                        "/rest/v1/app_usage",
                        {
                            "device_id": supabase_config["device_id"],
                            "app_name": app_name,
                            "bundle_id": bundle_id,
                            "launched_at": launched_at,
                            "terminated_at": terminated_at,
                            "duration_seconds": duration
                        },
                        use_service_key=True
                    )
                    synced_ids.append(session_id)

                except Exception as e:
                    log(f"Error syncing session {session_id}: {e}")

            # Mark as synced
            if synced_ids:
                cursor.execute(
                    f'UPDATE app_sessions SET synced = 1 WHERE id IN ({",".join("?" * len(synced_ids))})',
                    synced_ids
                )
                conn.commit()
                log(f"Synced {len(synced_ids)} app sessions to Supabase")

            conn.close()

        except Exception as e:
            log(f"Error in sync: {e}")

    def get_usage_summary(self, hours: int = 24) -> Dict:
        """Get app usage summary for the last N hours"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            since_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor.execute('''
                SELECT app_name, SUM(duration_seconds) as total_duration, COUNT(*) as sessions
                FROM app_sessions
                WHERE launched_at >= ?
                GROUP BY app_name
                ORDER BY total_duration DESC
                LIMIT 20
            ''', (since_time,))

            rows = cursor.fetchall()
            conn.close()

            apps = []
            for row in rows:
                app_name, total_duration, sessions = row
                apps.append({
                    "app_name": app_name,
                    "total_duration_seconds": total_duration,
                    "total_duration_formatted": self._format_duration(total_duration),
                    "session_count": sessions
                })

            return {
                "period_hours": hours,
                "apps": apps,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            log(f"Error getting usage summary: {e}")
            return {"error": str(e)}

    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def run(self):
        """Main tracking loop"""
        log("=" * 60)
        log("APP TRACKER STARTED")
        log("=" * 60)

        # Initial app scan
        current_apps = self.get_running_apps()
        log(f"Initial scan: {len(current_apps)} apps running")

        for app in current_apps:
            if app.get("bundle_id"):
                session = AppSession(
                    app_name=app["app_name"],
                    bundle_id=app["bundle_id"],
                    launched_at=datetime.now()
                )
                self.active_apps[app["bundle_id"]] = session

        check_interval = 10  # Check every 10 seconds

        while True:
            try:
                self.track_app_changes()

                # Sync to Supabase periodically
                if (datetime.now() - self.last_sync_time).total_seconds() >= SYNC_INTERVAL_SECONDS:
                    self.sync_to_supabase()
                    self.last_sync_time = datetime.now()

                time.sleep(check_interval)

            except KeyboardInterrupt:
                log("App tracker stopped by user")

                # Save active sessions on exit
                for session in self.active_apps.values():
                    session.terminated_at = datetime.now()
                    self._save_session(session)

                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(check_interval)


def main():
    tracker = AppTracker()
    tracker.run()


if __name__ == "__main__":
    main()
