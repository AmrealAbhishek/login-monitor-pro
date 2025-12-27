#!/usr/bin/env python3
"""
Geofence Monitor for Login Monitor PRO
Monitors device location and triggers alerts when leaving/entering geofenced areas.
"""

import json
import math
import os
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

CHECK_INTERVAL_SECONDS = 300  # Check every 5 minutes


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [GeofenceMonitor] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-geofence.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula"""
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


class Geofence:
    """Represents a geofenced area"""
    def __init__(self, id: str, name: str, latitude: float, longitude: float, radius_meters: int = 500, is_active: bool = True):
        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.radius_meters = radius_meters
        self.is_active = is_active

    def contains(self, lat: float, lon: float) -> bool:
        """Check if a point is inside this geofence"""
        distance = haversine_distance(self.latitude, self.longitude, lat, lon)
        return distance <= self.radius_meters

    def distance_to(self, lat: float, lon: float) -> float:
        """Get distance from point to geofence center"""
        return haversine_distance(self.latitude, self.longitude, lat, lon)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_meters": self.radius_meters,
            "is_active": self.is_active
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Geofence':
        return Geofence(
            id=data.get("id", ""),
            name=data.get("name", ""),
            latitude=data.get("latitude", 0),
            longitude=data.get("longitude", 0),
            radius_meters=data.get("radius_meters", 500),
            is_active=data.get("is_active", True)
        )


class GeofenceMonitor:
    """Monitors device location relative to geofences"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.geofences: List[Geofence] = []
        self.inside_geofences: Dict[str, bool] = {}  # Track which geofences we're inside
        self.last_location: Optional[Dict] = None
        self._load_geofences()

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

    def _load_geofences(self):
        """Load geofences from config"""
        geofences_data = self.config.get("geofences", [])
        for gf_data in geofences_data:
            geofence = Geofence.from_dict(gf_data)
            if geofence.is_active:
                self.geofences.append(geofence)
                self.inside_geofences[geofence.id] = False
        log(f"Loaded {len(self.geofences)} geofences")

    def add_geofence(self, name: str, latitude: float, longitude: float, radius_meters: int = 500) -> Geofence:
        """Add a new geofence"""
        import uuid
        geofence_id = str(uuid.uuid4())

        geofence = Geofence(
            id=geofence_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters
        )

        if "geofences" not in self.config:
            self.config["geofences"] = []

        self.config["geofences"].append(geofence.to_dict())
        self.geofences.append(geofence)
        self.inside_geofences[geofence.id] = False
        self._save_config()

        log(f"Added geofence: {name} at ({latitude}, {longitude}) with {radius_meters}m radius")
        return geofence

    def remove_geofence(self, geofence_id: str):
        """Remove a geofence"""
        self.config["geofences"] = [
            gf for gf in self.config.get("geofences", [])
            if gf.get("id") != geofence_id
        ]
        self.geofences = [gf for gf in self.geofences if gf.id != geofence_id]
        if geofence_id in self.inside_geofences:
            del self.inside_geofences[geofence_id]
        self._save_config()
        log(f"Removed geofence: {geofence_id}")

    def get_current_location(self) -> Optional[Dict]:
        """Get current GPS location"""
        try:
            # Try CoreLocation first
            from pro_monitor import SystemInfo
            location = SystemInfo.get_location()
            if location and location.get("latitude") and location.get("longitude"):
                return location
        except Exception as e:
            log(f"CoreLocation failed: {e}")

        # Fallback to IP geolocation
        try:
            with urllib.request.urlopen("http://ip-api.com/json/", timeout=10) as r:
                data = json.loads(r.read().decode())
                return {
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                    "city": data.get("city"),
                    "region": data.get("regionName"),
                    "country": data.get("country"),
                    "source": "IP Geolocation"
                }
        except Exception as e:
            log(f"IP geolocation failed: {e}")

        return None

    def check_geofences(self) -> List[Dict]:
        """Check current location against all geofences"""
        events = []
        location = self.get_current_location()

        if not location or not location.get("latitude") or not location.get("longitude"):
            log("Unable to get current location")
            return events

        lat = location["latitude"]
        lon = location["longitude"]
        self.last_location = location

        for geofence in self.geofences:
            if not geofence.is_active:
                continue

            is_inside = geofence.contains(lat, lon)
            was_inside = self.inside_geofences.get(geofence.id, False)

            if is_inside and not was_inside:
                # Entered geofence
                log(f"ENTERED geofence: {geofence.name}")
                events.append({
                    "event_type": "GeofenceEnter",
                    "geofence_name": geofence.name,
                    "location": location,
                    "geofence": geofence.to_dict(),
                    "timestamp": datetime.now().isoformat()
                })
                self.inside_geofences[geofence.id] = True

            elif not is_inside and was_inside:
                # Exited geofence
                distance = geofence.distance_to(lat, lon)
                log(f"EXITED geofence: {geofence.name} (now {distance:.0f}m away)")
                events.append({
                    "event_type": "GeofenceExit",
                    "geofence_name": geofence.name,
                    "location": location,
                    "geofence": geofence.to_dict(),
                    "distance_meters": round(distance),
                    "timestamp": datetime.now().isoformat()
                })
                self.inside_geofences[geofence.id] = False

            elif is_inside:
                self.inside_geofences[geofence.id] = True

        return events

    def trigger_alert(self, event_data: Dict) -> bool:
        """Trigger geofence alert"""
        try:
            from supabase_client import SupabaseClient
            from pro_monitor import Capture

            event_type = event_data.get("event_type", "Geofence")
            geofence_name = event_data.get("geofence_name", "Unknown")

            log(f"GEOFENCE ALERT: {event_type} - {geofence_name}")

            # Capture photo on geofence exit (security concern)
            photos = []
            if event_type == "GeofenceExit":
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
                    event_data=event_data,
                    photos=photos
                )

                if result.get("success"):
                    log(f"Geofence alert sent! Event ID: {result.get('event_id')}")
                    return True

            return False

        except Exception as e:
            log(f"Error triggering alert: {e}")
            return False

    def list_geofences(self) -> List[Dict]:
        """List all configured geofences"""
        return [gf.to_dict() for gf in self.geofences]

    def run(self):
        """Main monitoring loop"""
        log("=" * 60)
        log("GEOFENCE MONITOR STARTED")
        log(f"Active geofences: {len(self.geofences)}")
        for gf in self.geofences:
            log(f"  - {gf.name}: ({gf.latitude}, {gf.longitude}) r={gf.radius_meters}m")
        log("=" * 60)

        # Initial location check
        location = self.get_current_location()
        if location:
            log(f"Current location: ({location.get('latitude')}, {location.get('longitude')})")

            # Initialize geofence states
            lat = location["latitude"]
            lon = location["longitude"]
            for geofence in self.geofences:
                is_inside = geofence.contains(lat, lon)
                self.inside_geofences[geofence.id] = is_inside
                if is_inside:
                    log(f"  Currently inside: {geofence.name}")

        while True:
            try:
                events = self.check_geofences()

                for event in events:
                    self.trigger_alert(event)

                time.sleep(CHECK_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                log("Geofence monitor stopped by user")
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    monitor = GeofenceMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
