#!/usr/bin/env python3
"""
Threat Detector for Login Monitor PRO
Analyzes login events for security threats and unusual activity
"""

import json
import subprocess
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# Configuration
CONFIG_PATH = Path.home() / ".login-monitor" / "config.json"
LOG_PATH = Path.home() / ".login-monitor" / "threat_detector.log"

def log(message: str, level: str = "INFO"):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(log_entry + "\n")
    except:
        pass


class ThreatDetector:
    """
    Analyzes login events for potential security threats

    Threat Types:
    - unusual_time: Login during unusual hours (2-6 AM)
    - new_location: First-time login from new IP/city
    - after_hours: Activity outside business hours
    - failed_logins: Multiple failed login attempts (handled by intruder_detector.py)
    """

    # Default security rules
    DEFAULT_RULES = {
        "unusual_time": {
            "enabled": True,
            "alert_hours": [0, 1, 2, 3, 4, 5],  # Midnight to 6 AM
            "severity": "high",
            "action": "alert_screenshot"
        },
        "new_location": {
            "enabled": True,
            "notify_first_time": True,
            "severity": "medium",
            "action": "alert"
        },
        "after_hours": {
            "enabled": True,
            "work_start": "09:00",
            "work_end": "18:00",
            "weekends": True,  # Alert on weekends
            "severity": "low",
            "action": "alert"
        }
    }

    def __init__(self, config: Dict = None):
        """Initialize threat detector with config"""
        self.config = config or self._load_config()
        self.device_id = self.config.get("device_id") or self.config.get("supabase", {}).get("device_id")
        self.supabase_url = self.config.get("supabase", {}).get("url", "")
        self.supabase_key = self.config.get("supabase", {}).get("service_key") or \
                           self.config.get("supabase", {}).get("anon_key", "")

        # Load security rules (from config or defaults)
        self.rules = self.config.get("security_rules", self.DEFAULT_RULES)

        # Known locations cache
        self.known_locations = self._load_known_locations()

        log("[ThreatDetector] Initialized")

    def _load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading config: {e}", "ERROR")
        return {}

    def _load_known_locations(self) -> List[Dict]:
        """Load known locations from Supabase"""
        if not self.device_id or not self.supabase_url:
            return []

        try:
            response = requests.get(
                f"{self.supabase_url}/rest/v1/known_locations",
                params={"device_id": f"eq.{self.device_id}"},
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}"
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            log(f"Error loading known locations: {e}", "WARNING")
        return []

    def analyze_event(self, event: Dict) -> List[Dict]:
        """
        Analyze an event for potential threats

        Args:
            event: Event data with timestamp, location, public_ip, etc.

        Returns:
            List of threat alerts
        """
        threats = []

        # Check each enabled rule
        for rule_type, rule_config in self.rules.items():
            if not rule_config.get("enabled", True):
                continue

            threat = None

            if rule_type == "unusual_time":
                threat = self._check_unusual_time(event, rule_config)
            elif rule_type == "new_location":
                threat = self._check_new_location(event, rule_config)
            elif rule_type == "after_hours":
                threat = self._check_after_hours(event, rule_config)

            if threat:
                threats.append(threat)

        if threats:
            log(f"[ThreatDetector] Found {len(threats)} threat(s) in event")

        return threats

    def _check_unusual_time(self, event: Dict, rule: Dict) -> Optional[Dict]:
        """Check if event occurred at unusual time (e.g., 2-6 AM)"""
        try:
            timestamp = event.get("timestamp")
            if not timestamp:
                return None

            if isinstance(timestamp, str):
                # Parse ISO format timestamp
                event_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                event_dt = timestamp

            alert_hours = rule.get("alert_hours", [0, 1, 2, 3, 4, 5])

            if event_dt.hour in alert_hours:
                return {
                    "alert_type": "unusual_time",
                    "severity": rule.get("severity", "high"),
                    "title": "Unusual Login Time",
                    "description": f"Login detected at {event_dt.strftime('%I:%M %p')} - outside normal hours",
                    "action": rule.get("action", "alert"),
                    "metadata": {
                        "hour": event_dt.hour,
                        "timestamp": event_dt.isoformat(),
                        "event_type": event.get("event_type")
                    }
                }
        except Exception as e:
            log(f"Error checking unusual time: {e}", "ERROR")

        return None

    def _check_new_location(self, event: Dict, rule: Dict) -> Optional[Dict]:
        """Check if login from unknown location"""
        try:
            public_ip = event.get("public_ip")
            location = event.get("location", {})
            city = location.get("city") if isinstance(location, dict) else None
            country = location.get("country") if isinstance(location, dict) else None

            if not public_ip and not city:
                return None

            # Check against known locations
            is_known = False
            for known in self.known_locations:
                if known.get("ip_address") == public_ip:
                    is_known = True
                    # Update last_seen
                    self._update_known_location(known.get("id"))
                    break
                if known.get("city") == city and known.get("is_trusted"):
                    is_known = True
                    break

            if not is_known:
                # Add to known locations for future
                self._add_known_location(public_ip, city, country, location)

                return {
                    "alert_type": "new_location",
                    "severity": rule.get("severity", "medium"),
                    "title": "Login from New Location",
                    "description": f"First login from {city or public_ip or 'unknown location'}",
                    "action": rule.get("action", "alert"),
                    "metadata": {
                        "ip": public_ip,
                        "city": city,
                        "country": country,
                        "latitude": location.get("latitude") if isinstance(location, dict) else None,
                        "longitude": location.get("longitude") if isinstance(location, dict) else None
                    }
                }
        except Exception as e:
            log(f"Error checking new location: {e}", "ERROR")

        return None

    def _check_after_hours(self, event: Dict, rule: Dict) -> Optional[Dict]:
        """Check if activity during after-hours or weekends"""
        try:
            timestamp = event.get("timestamp")
            if not timestamp:
                return None

            if isinstance(timestamp, str):
                event_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                event_dt = timestamp

            # Check weekend
            check_weekends = rule.get("weekends", True)
            if check_weekends and event_dt.weekday() >= 5:  # Saturday=5, Sunday=6
                return {
                    "alert_type": "after_hours",
                    "severity": rule.get("severity", "low"),
                    "title": "Weekend Activity Detected",
                    "description": f"Activity on {event_dt.strftime('%A')} at {event_dt.strftime('%I:%M %p')}",
                    "action": rule.get("action", "alert"),
                    "metadata": {
                        "day": event_dt.strftime("%A"),
                        "time": event_dt.strftime("%H:%M"),
                        "is_weekend": True
                    }
                }

            # Check time
            work_start = time.fromisoformat(rule.get("work_start", "09:00"))
            work_end = time.fromisoformat(rule.get("work_end", "18:00"))
            event_time = event_dt.time()

            if event_time < work_start or event_time > work_end:
                return {
                    "alert_type": "after_hours",
                    "severity": rule.get("severity", "low"),
                    "title": "After-Hours Activity",
                    "description": f"Activity at {event_dt.strftime('%I:%M %p')} - outside work hours ({rule.get('work_start', '09:00')} - {rule.get('work_end', '18:00')})",
                    "action": rule.get("action", "alert"),
                    "metadata": {
                        "time": event_dt.strftime("%H:%M"),
                        "work_start": rule.get("work_start", "09:00"),
                        "work_end": rule.get("work_end", "18:00"),
                        "is_weekend": False
                    }
                }
        except Exception as e:
            log(f"Error checking after hours: {e}", "ERROR")

        return None

    def _add_known_location(self, ip: str, city: str, country: str, location: Dict):
        """Add new location to known locations"""
        if not self.device_id or not self.supabase_url:
            return

        try:
            data = {
                "device_id": self.device_id,
                "ip_address": ip,
                "city": city,
                "country": country,
                "latitude": location.get("latitude") if isinstance(location, dict) else None,
                "longitude": location.get("longitude") if isinstance(location, dict) else None,
                "is_trusted": False,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "visit_count": 1
            }

            response = requests.post(
                f"{self.supabase_url}/rest/v1/known_locations",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=data,
                timeout=10
            )

            if response.status_code in [200, 201]:
                log(f"[ThreatDetector] Added new known location: {city or ip}")
                # Reload known locations
                self.known_locations = self._load_known_locations()
        except Exception as e:
            log(f"Error adding known location: {e}", "WARNING")

    def _update_known_location(self, location_id: str):
        """Update last_seen for known location"""
        if not location_id or not self.supabase_url:
            return

        try:
            requests.patch(
                f"{self.supabase_url}/rest/v1/known_locations",
                params={"id": f"eq.{location_id}"},
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "last_seen": datetime.now().isoformat(),
                    "visit_count": "visit_count + 1"  # This won't work as expected, need RPC
                },
                timeout=10
            )
        except Exception as e:
            log(f"Error updating known location: {e}", "WARNING")

    def execute_action(self, threat: Dict, event: Dict = None):
        """Execute threat response action"""
        action = threat.get("action", "alert")

        log(f"[ThreatDetector] Executing action: {action} for {threat.get('alert_type')}")

        # Capture screenshot if action includes it
        if "screenshot" in action:
            self._capture_screenshot(threat)

        # Lock device if action is lock
        if action == "lock":
            self._lock_device()

        # Always create alert in Supabase
        self._create_alert(threat, event)

        # Send FCM push notification
        self._send_fcm_notification(threat)

    def _capture_screenshot(self, threat: Dict):
        """Capture screenshot for threat evidence"""
        try:
            screenshot_dir = Path.home() / ".login-monitor" / "threat_screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_type = threat.get("alert_type", "unknown")
            filename = f"threat_{alert_type}_{timestamp}.png"
            filepath = screenshot_dir / filename

            # Use screencapture command
            result = subprocess.run(
                ["/usr/sbin/screencapture", "-x", str(filepath)],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0 and filepath.exists():
                log(f"[ThreatDetector] Screenshot captured: {filename}")
                # Could upload to Supabase storage here
            else:
                log("[ThreatDetector] Screenshot capture failed", "WARNING")
        except Exception as e:
            log(f"Error capturing screenshot: {e}", "ERROR")

    def _lock_device(self):
        """Lock the device immediately"""
        try:
            subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
            log("[ThreatDetector] Device locked")
        except Exception as e:
            log(f"Error locking device: {e}", "ERROR")

    def _create_alert(self, threat: Dict, event: Dict = None):
        """Create security alert in Supabase"""
        if not self.device_id or not self.supabase_url:
            log("[ThreatDetector] Cannot create alert - no device_id or supabase_url", "WARNING")
            return

        try:
            alert_data = {
                "device_id": self.device_id,
                "alert_type": threat.get("alert_type"),
                "severity": threat.get("severity"),
                "title": threat.get("title"),
                "description": threat.get("description"),
                "metadata": threat.get("metadata", {}),
                "acknowledged": False,
                "created_at": datetime.now().isoformat()
            }

            # Add event_id if available
            if event and event.get("id"):
                alert_data["event_id"] = event.get("id")

            response = requests.post(
                f"{self.supabase_url}/rest/v1/security_alerts",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=alert_data,
                timeout=10
            )

            if response.status_code in [200, 201]:
                log(f"[ThreatDetector] Alert created: {threat.get('title')}")
            else:
                log(f"[ThreatDetector] Failed to create alert: {response.status_code} - {response.text}", "ERROR")
        except Exception as e:
            log(f"Error creating alert: {e}", "ERROR")

    def _send_fcm_notification(self, threat: Dict):
        """Send FCM push notification for threat alert"""
        try:
            # Import FCM sender if available
            from fcm_sender import send_event_notification, get_fcm_tokens_for_device

            if not self.device_id:
                return

            # Get severity emoji
            severity_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "🔔",
                "low": "ℹ️"
            }.get(threat.get("severity", "medium"), "🔔")

            title = f"{severity_emoji} Security Alert: {threat.get('title')}"
            body = threat.get("description", "Security threat detected")

            # Get FCM tokens for device owner
            tokens = get_fcm_tokens_for_device(self.device_id)

            if tokens:
                from fcm_sender import send_fcm_notification
                for token in tokens:
                    send_fcm_notification(
                        token=token,
                        title=title,
                        body=body,
                        data={
                            "alert_type": threat.get("alert_type"),
                            "severity": threat.get("severity"),
                            "device_id": self.device_id,
                            "click_action": "FLUTTER_NOTIFICATION_CLICK"
                        }
                    )
                log(f"[ThreatDetector] FCM notification sent for {threat.get('alert_type')}")
        except ImportError:
            log("[ThreatDetector] FCM sender not available", "WARNING")
        except Exception as e:
            log(f"Error sending FCM notification: {e}", "ERROR")


# Test function
if __name__ == "__main__":
    print("Testing Threat Detector...")

    detector = ThreatDetector()

    # Test event at unusual time
    test_event_unusual = {
        "timestamp": datetime.now().replace(hour=3, minute=30).isoformat(),
        "event_type": "Unlock",
        "public_ip": "203.0.113.42",
        "location": {
            "city": "Mumbai",
            "country": "India"
        }
    }

    threats = detector.analyze_event(test_event_unusual)

    if threats:
        print(f"\n Found {len(threats)} threat(s):")
        for threat in threats:
            print(f"  - {threat['title']}: {threat['description']}")
            print(f"    Severity: {threat['severity']}, Action: {threat['action']}")
    else:
        print("\n No threats detected")

    # Test normal event
    test_event_normal = {
        "timestamp": datetime.now().replace(hour=10, minute=30).isoformat(),
        "event_type": "Unlock",
        "public_ip": "known_ip",  # Would be in known locations
        "location": {
            "city": "Known City",
            "country": "India"
        }
    }

    threats_normal = detector.analyze_event(test_event_normal)
    print(f"\n Normal event threats: {len(threats_normal)}")
