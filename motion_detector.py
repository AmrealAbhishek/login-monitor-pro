#!/usr/bin/env python3
"""
Motion Detector for Login Monitor PRO
Detects physical movement of the Mac using lid events and location changes.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

CHECK_INTERVAL_SECONDS = 60
LOCATION_CHANGE_THRESHOLD_METERS = 100  # Movement threshold


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [MotionDetector] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-motion.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters"""
    import math
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


class MotionDetector:
    """Detects physical movement of the Mac"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.last_location: Optional[Dict] = None
        self.last_lid_state: Optional[bool] = None  # True = open, False = closed
        self.armed = True
        self.last_movement_time: Optional[datetime] = None

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

    def _save_config(self):
        """Save configuration to file"""
        try:
            config_file = self.base_dir / "config.json"
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            log(f"Error saving config: {e}")

    def arm(self, enabled: bool = True):
        """Arm or disarm motion detection"""
        self.armed = enabled
        self.config["motion_armed"] = enabled
        self._save_config()
        log(f"Motion detection {'armed' if enabled else 'disarmed'}")

    def get_lid_state(self) -> Optional[bool]:
        """Get current lid state (True = open, False = closed)"""
        try:
            # Check if running on a MacBook (has lid)
            result = subprocess.run(
                ["ioreg", "-r", "-k", "AppleClamshellState", "-d", "4"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                output = result.stdout
                if "AppleClamshellState" in output:
                    # True in output means lid is closed
                    is_closed = "Yes" in output.split("AppleClamshellState")[1].split("\n")[0]
                    return not is_closed  # Return True if open

            # Desktop Mac (no lid)
            return None

        except Exception as e:
            log(f"Error getting lid state: {e}")
            return None

    def get_current_location(self) -> Optional[Dict]:
        """Get current location"""
        try:
            from pro_monitor import SystemInfo
            return SystemInfo.get_location()
        except Exception as e:
            log(f"Error getting location: {e}")
            return None

    def check_for_movement(self) -> List[Dict]:
        """Check for various types of movement"""
        movements = []

        if not self.armed:
            return movements

        # Check lid state change
        current_lid_state = self.get_lid_state()
        if current_lid_state is not None:
            if self.last_lid_state is not None and current_lid_state != self.last_lid_state:
                movement_type = "LidOpened" if current_lid_state else "LidClosed"
                log(f"Movement detected: {movement_type}")

                movements.append({
                    "event_type": "Movement",
                    "motion_data": {
                        "trigger": "lid",
                        "detail": movement_type,
                        "magnitude": 1.0
                    },
                    "timestamp": datetime.now().isoformat()
                })

            self.last_lid_state = current_lid_state

        # Check location change
        current_location = self.get_current_location()
        if current_location and current_location.get("latitude") and current_location.get("longitude"):
            if self.last_location and self.last_location.get("latitude"):
                distance = haversine_distance(
                    self.last_location["latitude"],
                    self.last_location["longitude"],
                    current_location["latitude"],
                    current_location["longitude"]
                )

                if distance >= LOCATION_CHANGE_THRESHOLD_METERS:
                    log(f"Movement detected: Location changed by {distance:.0f}m")

                    # Only alert if enough time has passed since last movement
                    if not self.last_movement_time or \
                       (datetime.now() - self.last_movement_time).total_seconds() > 300:

                        movements.append({
                            "event_type": "Movement",
                            "motion_data": {
                                "trigger": "location",
                                "detail": f"Moved {distance:.0f}m",
                                "magnitude": distance,
                                "from_location": self.last_location,
                                "to_location": current_location
                            },
                            "location": current_location,
                            "timestamp": datetime.now().isoformat()
                        })

                        self.last_movement_time = datetime.now()

            self.last_location = current_location

        return movements

    def check_power_events(self) -> List[Dict]:
        """Check for power-related events that indicate movement"""
        events = []

        try:
            # Check if AC power was just connected/disconnected (indicates movement)
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                output = result.stdout
                # Parse battery info
                is_charging = "AC Power" in output or "charging" in output.lower()

                # Store for next check
                power_state_file = self.base_dir / ".power_state"

                if power_state_file.exists():
                    with open(power_state_file) as f:
                        last_state = f.read().strip() == "charging"

                    if last_state != is_charging:
                        event_type = "PowerConnected" if is_charging else "PowerDisconnected"
                        log(f"Power event: {event_type}")

                        events.append({
                            "event_type": "Movement",
                            "motion_data": {
                                "trigger": "power",
                                "detail": event_type,
                                "magnitude": 0.5
                            },
                            "timestamp": datetime.now().isoformat()
                        })

                with open(power_state_file, 'w') as f:
                    f.write("charging" if is_charging else "battery")

        except Exception as e:
            log(f"Error checking power events: {e}")

        return events

    def trigger_alert(self, movement_data: Dict) -> bool:
        """Trigger movement alert"""
        try:
            from supabase_client import SupabaseClient
            from pro_monitor import Capture

            trigger = movement_data.get("motion_data", {}).get("trigger", "unknown")
            log(f"MOVEMENT ALERT: {trigger}")

            # Capture photo if movement detected
            photos = []
            try:
                photo_paths = Capture.capture_photos(count=1, delay=0)
                if photo_paths:
                    photos = photo_paths
            except Exception as e:
                log(f"Failed to capture photo: {e}")

            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if supabase_config.get("url") and supabase_config.get("device_id"):
                client = SupabaseClient(
                    url=supabase_config["url"],
                    anon_key=supabase_config.get("anon_key", ""),
                    service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
                )

                result = client.send_event(
                    device_id=supabase_config["device_id"],
                    event_data=movement_data,
                    photos=photos
                )

                if result.get("success"):
                    log(f"Movement alert sent! Event ID: {result.get('event_id')}")
                    return True

            return False

        except Exception as e:
            log(f"Error triggering alert: {e}")
            return False

    def run(self):
        """Main monitoring loop"""
        log("=" * 60)
        log("MOTION DETECTOR STARTED")
        log(f"Armed: {self.armed}")
        log(f"Location threshold: {LOCATION_CHANGE_THRESHOLD_METERS}m")
        log("=" * 60)

        # Initialize lid state
        self.last_lid_state = self.get_lid_state()
        if self.last_lid_state is not None:
            log(f"Initial lid state: {'Open' if self.last_lid_state else 'Closed'}")

        # Initialize location
        self.last_location = self.get_current_location()
        if self.last_location:
            log(f"Initial location: ({self.last_location.get('latitude')}, {self.last_location.get('longitude')})")

        while True:
            try:
                if self.armed:
                    movements = self.check_for_movement()
                    power_events = self.check_power_events()

                    for movement in movements + power_events:
                        self.trigger_alert(movement)

                time.sleep(CHECK_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                log("Motion detector stopped by user")
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    detector = MotionDetector()
    detector.run()


if __name__ == "__main__":
    main()
