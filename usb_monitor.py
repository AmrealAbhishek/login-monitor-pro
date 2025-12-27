#!/usr/bin/env python3
"""
USB Monitor for Login Monitor PRO
Monitors USB device connections and alerts on unknown devices.
"""

import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set

CHECK_INTERVAL_SECONDS = 10


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [USBMonitor] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-usb.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


class USBDevice:
    """Represents a USB device"""
    def __init__(self, vendor_id: str, product_id: str, name: str, serial: str = ""):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.name = name
        self.serial = serial

    @property
    def unique_id(self) -> str:
        return f"{self.vendor_id}:{self.product_id}"

    def to_dict(self) -> Dict:
        return {
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "name": self.name,
            "serial": self.serial
        }

    def __eq__(self, other):
        if isinstance(other, USBDevice):
            return self.unique_id == other.unique_id
        return False

    def __hash__(self):
        return hash(self.unique_id)


class USBMonitor:
    """Monitors USB device connections"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.known_devices: Set[str] = set()
        self.previous_devices: Dict[str, USBDevice] = {}
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
        """Load USB device whitelist from config"""
        whitelist = self.config.get("usb_whitelist", [])
        for device in whitelist:
            device_id = f"{device.get('vendor_id', '')}:{device.get('product_id', '')}"
            self.known_devices.add(device_id)
        log(f"Loaded {len(self.known_devices)} whitelisted USB devices")

    def add_to_whitelist(self, device: USBDevice):
        """Add a device to the whitelist"""
        if "usb_whitelist" not in self.config:
            self.config["usb_whitelist"] = []

        # Check if already exists
        for existing in self.config["usb_whitelist"]:
            if existing.get("vendor_id") == device.vendor_id and \
               existing.get("product_id") == device.product_id:
                return

        self.config["usb_whitelist"].append({
            "vendor_id": device.vendor_id,
            "product_id": device.product_id,
            "name": device.name
        })
        self.known_devices.add(device.unique_id)
        self._save_config()
        log(f"Added to whitelist: {device.name}")

    def get_connected_devices(self) -> Dict[str, USBDevice]:
        """Get currently connected USB devices"""
        devices = {}

        try:
            # Use system_profiler to get USB device info
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-xml"],
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0:
                devices = self._parse_usb_xml(result.stdout)
        except subprocess.TimeoutExpired:
            log("Timeout getting USB devices")
        except Exception as e:
            log(f"Error getting USB devices: {e}")

        return devices

    def _parse_usb_xml(self, xml_data: bytes) -> Dict[str, USBDevice]:
        """Parse system_profiler XML output"""
        devices = {}

        try:
            import plistlib
            plist = plistlib.loads(xml_data)

            def extract_devices(items):
                for item in items:
                    if isinstance(item, dict):
                        # Check if this is a USB device entry
                        if "vendor_id" in item or "_name" in item:
                            vendor_id = item.get("vendor_id", "0x0000")
                            product_id = item.get("product_id", "0x0000")
                            name = item.get("_name", "Unknown Device")
                            serial = item.get("serial_num", "")

                            # Skip internal hubs and built-in devices
                            if "hub" in name.lower() or not vendor_id:
                                pass
                            else:
                                device = USBDevice(vendor_id, product_id, name, serial)
                                devices[device.unique_id] = device

                        # Check for nested items
                        if "_items" in item:
                            extract_devices(item["_items"])

            if plist and len(plist) > 0:
                if "_items" in plist[0]:
                    extract_devices(plist[0]["_items"])

        except Exception as e:
            log(f"Error parsing USB XML: {e}")

        return devices

    def check_for_new_devices(self) -> List[Dict]:
        """Check for newly connected unknown devices"""
        new_unknown_devices = []
        current_devices = self.get_connected_devices()

        for device_id, device in current_devices.items():
            # Check if device was just connected (not in previous scan)
            if device_id not in self.previous_devices:
                # Check if it's unknown
                if device_id not in self.known_devices:
                    log(f"NEW UNKNOWN DEVICE: {device.name} ({device_id})")
                    new_unknown_devices.append({
                        "vendor_id": device.vendor_id,
                        "product_id": device.product_id,
                        "name": device.name,
                        "serial": device.serial,
                        "is_known": False,
                        "connected_at": datetime.now().isoformat()
                    })
                else:
                    log(f"Known device connected: {device.name}")

        # Check for disconnected devices
        for device_id, device in self.previous_devices.items():
            if device_id not in current_devices:
                log(f"Device disconnected: {device.name}")

        self.previous_devices = current_devices
        return new_unknown_devices

    def trigger_alert(self, usb_data: Dict) -> bool:
        """Trigger USB device alert"""
        try:
            from supabase_client import SupabaseClient
            from pro_monitor import Capture

            log("UNKNOWN USB DEVICE! Capturing photo and sending alert...")

            # Capture photo
            photos = []
            try:
                photo_paths = Capture.capture_photos(count=1, delay=0)
                if photo_paths:
                    photos = photo_paths
            except Exception as e:
                log(f"Failed to capture photo: {e}")

            # Send event
            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if supabase_config.get("url") and supabase_config.get("device_id"):
                client = SupabaseClient(
                    url=supabase_config["url"],
                    anon_key=supabase_config.get("anon_key", ""),
                    service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
                )

                event_data = {
                    "event_type": "UnknownUSB",
                    "usb_device": usb_data,
                    "timestamp": datetime.now().isoformat()
                }

                result = client.send_event(
                    device_id=supabase_config["device_id"],
                    event_data=event_data,
                    photos=photos
                )

                if result.get("success"):
                    log(f"USB alert sent! Event ID: {result.get('event_id')}")
                    return True

            return False

        except Exception as e:
            log(f"Error triggering alert: {e}")
            return False

    def list_devices(self) -> List[Dict]:
        """List all currently connected USB devices"""
        devices = self.get_connected_devices()
        return [
            {
                **device.to_dict(),
                "is_known": device.unique_id in self.known_devices
            }
            for device in devices.values()
        ]

    def run(self):
        """Main monitoring loop"""
        log("=" * 60)
        log("USB MONITOR STARTED")
        log(f"Whitelisted devices: {len(self.known_devices)}")
        log("=" * 60)

        # Initial scan
        self.previous_devices = self.get_connected_devices()
        log(f"Initial scan: {len(self.previous_devices)} devices connected")

        while True:
            try:
                new_devices = self.check_for_new_devices()

                for device_data in new_devices:
                    self.trigger_alert(device_data)

                time.sleep(CHECK_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                log("USB monitor stopped by user")
                break
            except Exception as e:
                log(f"Error in main loop: {e}")
                time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    monitor = USBMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
