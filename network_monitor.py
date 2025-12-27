#!/usr/bin/env python3
"""
Network Monitor for Login Monitor PRO
Monitors WiFi network changes and alerts on unknown networks.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set

CHECK_INTERVAL_SECONDS = 30


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [NetworkMonitor] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-network.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


class NetworkMonitor:
    """Monitors WiFi network changes"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.known_networks: Set[str] = set()
        self.current_network: Optional[str] = None
        self.previous_network: Optional[str] = None
        self._load_whitelist()

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

    def _load_whitelist(self):
        """Load WiFi network whitelist from config"""
        whitelist = self.config.get("wifi_whitelist", [])
        for network in whitelist:
            if isinstance(network, str):
                self.known_networks.add(network)
            elif isinstance(network, dict):
                self.known_networks.add(network.get("ssid", ""))
        log(f"Loaded {len(self.known_networks)} whitelisted networks")

    def add_to_whitelist(self, ssid: str):
        """Add a network to the whitelist"""
        if "wifi_whitelist" not in self.config:
            self.config["wifi_whitelist"] = []

        if ssid not in self.config["wifi_whitelist"]:
            self.config["wifi_whitelist"].append(ssid)
            self.known_networks.add(ssid)
            self._save_config()
            log(f"Added to whitelist: {ssid}")

    def get_current_wifi(self) -> Optional[Dict]:
        """Get current WiFi network information"""
        try:
            # Get WiFi interface name
            result = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True,
                timeout=10
            )

            wifi_interface = "en0"  # Default
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if 'Wi-Fi' in line or 'AirPort' in line:
                        if i + 1 < len(lines) and 'Device:' in lines[i + 1]:
                            wifi_interface = lines[i + 1].split(':')[1].strip()
                            break

            # Get current WiFi info using airport command
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"

            if os.path.exists(airport_path):
                result = subprocess.run(
                    [airport_path, "-I"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    info = {}
                    for line in result.stdout.split('\n'):
                        if ':' in line:
                            parts = line.strip().split(':', 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                info[key] = value

                    ssid = info.get('SSID')
                    if ssid:
                        return {
                            "ssid": ssid,
                            "bssid": info.get('BSSID', ''),
                            "channel": info.get('channel', ''),
                            "security": info.get('link auth', ''),
                            "rssi": info.get('agrCtlRSSI', ''),
                            "noise": info.get('agrCtlNoise', '')
                        }

            # Fallback: use networksetup
            result = subprocess.run(
                ["networksetup", "-getairportnetwork", wifi_interface],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and "Current Wi-Fi Network:" in result.stdout:
                ssid = result.stdout.split("Current Wi-Fi Network:")[1].strip()
                return {"ssid": ssid}

        except subprocess.TimeoutExpired:
            log("Timeout getting WiFi info")
        except Exception as e:
            log(f"Error getting WiFi info: {e}")

        return None

    def check_network_change(self) -> Optional[Dict]:
        """Check if network has changed to an unknown network"""
        wifi_info = self.get_current_wifi()

        if not wifi_info:
            if self.current_network:
                log("Disconnected from WiFi")
                self.previous_network = self.current_network
                self.current_network = None
            return None

        new_ssid = wifi_info.get("ssid")

        # Check if network changed
        if new_ssid != self.current_network:
            self.previous_network = self.current_network
            self.current_network = new_ssid

            log(f"Network changed: {self.previous_network} -> {new_ssid}")

            # Check if new network is unknown
            if new_ssid not in self.known_networks:
                return {
                    "event_type": "UnknownNetwork",
                    "network_change": {
                        "previous_ssid": self.previous_network,
                        "new_ssid": new_ssid,
                        "is_known": False,
                        "wifi_info": wifi_info
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                log(f"Connected to known network: {new_ssid}")

        return None

    def trigger_alert(self, network_data: Dict) -> bool:
        """Trigger network change alert"""
        try:
            from supabase_client import SupabaseClient

            log("UNKNOWN NETWORK! Sending alert...")

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
                    event_data=network_data
                )

                if result.get("success"):
                    log(f"Network alert sent! Event ID: {result.get('event_id')}")
                    return True

            return False

        except Exception as e:
            log(f"Error triggering alert: {e}")
            return False

    def list_known_networks(self) -> List[str]:
        """List all whitelisted networks"""
        return list(self.known_networks)

    def run(self):
        """Main monitoring loop"""
        log("=" * 60)
        log("NETWORK MONITOR STARTED")
        log(f"Whitelisted networks: {len(self.known_networks)}")
        log("=" * 60)

        # Initial network check
        wifi_info = self.get_current_wifi()
        if wifi_info:
            self.current_network = wifi_info.get("ssid")
            log(f"Current network: {self.current_network}")

            # Auto-whitelist current network on first run
            if self.current_network and not self.known_networks:
                self.add_to_whitelist(self.current_network)

        while True:
            try:
                network_change = self.check_network_change()

                if network_change:
                    self.trigger_alert(network_change)

                time.sleep(CHECK_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                log("Network monitor stopped by user")
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    monitor = NetworkMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
