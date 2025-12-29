#!/usr/bin/env python3
"""
CyVigil USB DLP Monitor
========================
Monitors USB device connections and file operations.
Detects and optionally blocks sensitive file transfers to USB drives.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import threading
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Try to import watchdog for file monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    print("Warning: watchdog not installed. File monitoring disabled.")
    print("Install with: pip3 install watchdog")

import requests

# Configuration
CONFIG_PATH = Path.home() / ".login-monitor" / "config.json"
LOG_PATH = "/tmp/loginmonitor-usb-dlp.log"

# Sensitive file patterns
SENSITIVE_EXTENSIONS = {
    '.pem', '.key', '.p12', '.pfx', '.cer', '.crt',  # Certificates/Keys
    '.env', '.env.local', '.env.production',          # Environment files
    '.sql', '.sqlite', '.db', '.mdb',                 # Databases
    '.csv', '.xlsx', '.xls',                          # Spreadsheets (may contain PII)
    '.doc', '.docx', '.pdf',                          # Documents
    '.pst', '.ost',                                    # Email archives
    '.kdbx', '.keychain',                              # Password databases
    '.wallet', '.dat',                                 # Crypto wallets
}

SENSITIVE_FILENAMES = {
    'id_rsa', 'id_ed25519', 'id_ecdsa',               # SSH keys
    'credentials', 'secrets', 'passwords',
    '.htpasswd', '.netrc', 'pgpass',
    'serviceAccountKey', 'firebase-adminsdk',
    'aws_credentials', 'gcloud_credentials',
}

# Known USB volume mount points on macOS
USB_MOUNT_PATHS = ['/Volumes']


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


class USBDevice:
    """Represents a USB device."""
    def __init__(self, name: str, vendor: str = "", serial: str = "",
                 device_type: str = "unknown", mount_point: str = ""):
        self.name = name
        self.vendor = vendor
        self.serial = serial
        self.device_type = device_type
        self.mount_point = mount_point
        self.connected_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "serial": self.serial,
            "device_type": self.device_type,
            "mount_point": self.mount_point,
            "connected_at": self.connected_at.isoformat()
        }


class USBDLPMonitor:
    """Main USB DLP monitoring class."""

    def __init__(self):
        self.config = self._load_config()
        self.device_id = self.config.get("device_id", "")
        self.supabase_url = self.config.get("supabase_url", "")
        self.supabase_key = self.config.get("supabase_key", "")

        self.connected_devices: Dict[str, USBDevice] = {}
        self.monitored_volumes: Set[str] = set()
        self.file_observers: Dict[str, Observer] = {}

        # DLP settings
        self.block_all_usb = self.config.get("dlp", {}).get("block_all_usb", False)
        self.block_storage = self.config.get("dlp", {}).get("block_usb_storage", False)
        self.alert_on_sensitive = self.config.get("dlp", {}).get("alert_sensitive_files", True)
        self.log_all_transfers = self.config.get("dlp", {}).get("log_all_transfers", True)

        log(f"USB DLP Monitor initialized. Device: {self.device_id[:8]}...")

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading config: {e}")
        return {}

    def _get_file_hash(self, filepath: str, block_size: int = 65536) -> str:
        """Calculate SHA256 hash of a file."""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    sha256.update(block)
            return sha256.hexdigest()
        except Exception:
            return ""

    def _is_sensitive_file(self, filepath: str) -> tuple:
        """Check if file is sensitive. Returns (is_sensitive, reason)."""
        path = Path(filepath)
        filename = path.name.lower()
        extension = path.suffix.lower()

        # Check extension
        if extension in SENSITIVE_EXTENSIONS:
            return True, f"sensitive_extension:{extension}"

        # Check filename
        for sensitive_name in SENSITIVE_FILENAMES:
            if sensitive_name.lower() in filename:
                return True, f"sensitive_filename:{sensitive_name}"

        # Check file content for secrets (first 4KB)
        try:
            with open(filepath, 'rb') as f:
                content = f.read(4096).decode('utf-8', errors='ignore')

            # Check for common secret patterns
            patterns = [
                (r'-----BEGIN.*PRIVATE KEY-----', 'private_key'),
                (r'AKIA[0-9A-Z]{16}', 'aws_key'),
                (r'api[_-]?key.*[=:]\s*["\']?[a-zA-Z0-9_\-]{20,}', 'api_key'),
                (r'password\s*[=:]\s*["\']?[^\s"\']{6,}', 'password'),
            ]

            for pattern, secret_type in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True, f"content:{secret_type}"

        except Exception:
            pass

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

    def get_usb_devices(self) -> List[USBDevice]:
        """Get list of connected USB devices using system_profiler."""
        devices = []

        try:
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-json"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                usb_data = data.get("SPUSBDataType", [])

                def parse_usb_items(items, parent_name=""):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("_name", "Unknown")
                            vendor = item.get("manufacturer", "")
                            serial = item.get("serial_num", "")

                            # Determine device type
                            device_type = "other"
                            media = item.get("Media", [])
                            if media:
                                device_type = "storage"
                            elif "keyboard" in name.lower():
                                device_type = "keyboard"
                            elif "mouse" in name.lower() or "trackpad" in name.lower():
                                device_type = "mouse"
                            elif "hub" in name.lower():
                                device_type = "hub"

                            # Get mount point for storage devices
                            mount_point = ""
                            if media:
                                for m in media:
                                    volumes = m.get("volumes", [])
                                    for vol in volumes:
                                        mount_point = vol.get("mount_point", "")
                                        break

                            device = USBDevice(
                                name=name,
                                vendor=vendor,
                                serial=serial,
                                device_type=device_type,
                                mount_point=mount_point
                            )
                            devices.append(device)

                            # Recurse into nested items
                            if "_items" in item:
                                parse_usb_items(item["_items"], name)

                parse_usb_items(usb_data)

        except Exception as e:
            log(f"Error getting USB devices: {e}")

        return devices

    def get_mounted_volumes(self) -> List[str]:
        """Get list of mounted external volumes."""
        volumes = []

        try:
            result = subprocess.run(
                ["diskutil", "list", "-plist", "external"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                # Parse plist output
                import plistlib
                data = plistlib.loads(result.stdout.encode())

                for disk in data.get("AllDisksAndPartitions", []):
                    for partition in disk.get("Partitions", []):
                        mount_point = partition.get("MountPoint", "")
                        if mount_point and mount_point.startswith("/Volumes/"):
                            volumes.append(mount_point)

        except Exception as e:
            # Fallback: list /Volumes
            try:
                for item in os.listdir("/Volumes"):
                    path = f"/Volumes/{item}"
                    # Skip system volumes
                    if item not in ["Macintosh HD", "Macintosh HD - Data", "Recovery"]:
                        if os.path.ismount(path):
                            volumes.append(path)
            except Exception:
                pass

        return volumes

    def log_usb_event(self, event_type: str, device: USBDevice,
                      file_path: str = "", file_name: str = "",
                      file_size: int = 0, file_hash: str = "",
                      action_taken: str = "logged"):
        """Log USB event to Supabase."""

        event_data = {
            "device_id": self.device_id,
            "event_type": event_type,
            "usb_name": device.name,
            "usb_vendor": device.vendor,
            "usb_serial": device.serial,
            "usb_type": device.device_type,
            "file_path": file_path,
            "file_name": file_name,
            "file_size": file_size,
            "file_hash": file_hash,
            "action_taken": action_taken
        }

        self._send_to_supabase("usb_events", event_data)
        log(f"USB Event: {event_type} - {device.name} - {file_name or 'N/A'}")

    def handle_device_connected(self, device: USBDevice):
        """Handle USB device connection."""
        key = f"{device.name}_{device.serial}"

        if key in self.connected_devices:
            return  # Already tracked

        self.connected_devices[key] = device
        log(f"USB Connected: {device.name} ({device.device_type})")

        # Log event
        self.log_usb_event("connected", device)

        # Check if storage device should be blocked
        if device.device_type == "storage":
            if self.block_all_usb or self.block_storage:
                self._create_security_alert(
                    "usb_blocked",
                    "high",
                    f"USB Storage Blocked: {device.name}",
                    f"USB storage device '{device.name}' was blocked by DLP policy. "
                    f"Vendor: {device.vendor}, Serial: {device.serial}"
                )
                self.log_usb_event("blocked", device, action_taken="blocked")

                # Try to eject the device
                if device.mount_point:
                    try:
                        subprocess.run(
                            ["diskutil", "eject", device.mount_point],
                            capture_output=True, timeout=10
                        )
                        log(f"Ejected blocked device: {device.mount_point}")
                    except Exception as e:
                        log(f"Failed to eject: {e}")
            else:
                # Start monitoring file operations on this volume
                if device.mount_point and HAS_WATCHDOG:
                    self._start_volume_monitoring(device)

    def handle_device_disconnected(self, device: USBDevice):
        """Handle USB device disconnection."""
        key = f"{device.name}_{device.serial}"

        if key in self.connected_devices:
            del self.connected_devices[key]
            log(f"USB Disconnected: {device.name}")
            self.log_usb_event("disconnected", device)

            # Stop monitoring if applicable
            if device.mount_point in self.file_observers:
                self.file_observers[device.mount_point].stop()
                del self.file_observers[device.mount_point]

    def _start_volume_monitoring(self, device: USBDevice):
        """Start monitoring file operations on a USB volume."""
        if not HAS_WATCHDOG or not device.mount_point:
            return

        if device.mount_point in self.file_observers:
            return  # Already monitoring

        class USBFileHandler(FileSystemEventHandler):
            def __init__(handler_self, monitor, usb_device):
                handler_self.monitor = monitor
                handler_self.device = usb_device

            def on_created(handler_self, event):
                if not event.is_directory:
                    handler_self.monitor._handle_file_operation(
                        "file_copied", handler_self.device, event.src_path
                    )

            def on_modified(handler_self, event):
                if not event.is_directory:
                    handler_self.monitor._handle_file_operation(
                        "file_modified", handler_self.device, event.src_path
                    )

            def on_moved(handler_self, event):
                if not event.is_directory:
                    handler_self.monitor._handle_file_operation(
                        "file_moved", handler_self.device, event.dest_path
                    )

        try:
            observer = Observer()
            handler = USBFileHandler(self, device)
            observer.schedule(handler, device.mount_point, recursive=True)
            observer.start()
            self.file_observers[device.mount_point] = observer
            log(f"Started monitoring: {device.mount_point}")
        except Exception as e:
            log(f"Failed to monitor {device.mount_point}: {e}")

    def _handle_file_operation(self, operation: str, device: USBDevice, filepath: str):
        """Handle a file operation on USB drive."""
        try:
            path = Path(filepath)
            if not path.exists():
                return

            filename = path.name
            filesize = path.stat().st_size if path.is_file() else 0

            # Skip small/system files
            if filesize < 100 or filename.startswith('.'):
                return

            # Check if sensitive
            is_sensitive, reason = self._is_sensitive_file(filepath)

            # Calculate hash for important files
            file_hash = ""
            if is_sensitive or filesize > 1024 * 1024:  # > 1MB or sensitive
                file_hash = self._get_file_hash(filepath)

            # Determine action
            action = "logged"
            if is_sensitive:
                if self.alert_on_sensitive:
                    self._create_security_alert(
                        "sensitive_file_usb",
                        "high",
                        f"Sensitive File Copied to USB: {filename}",
                        f"File '{filename}' ({reason}) was copied to USB drive '{device.name}'. "
                        f"Size: {filesize} bytes. Hash: {file_hash[:16]}..."
                    )
                    action = "alerted"

            # Log the transfer
            if self.log_all_transfers or is_sensitive:
                self.log_usb_event(
                    operation, device,
                    file_path=str(filepath),
                    file_name=filename,
                    file_size=filesize,
                    file_hash=file_hash,
                    action_taken=action
                )

        except Exception as e:
            log(f"Error handling file operation: {e}")

    def scan_existing_volumes(self):
        """Scan for already-mounted USB volumes."""
        volumes = self.get_mounted_volumes()
        devices = self.get_usb_devices()

        # Map volumes to devices
        for volume in volumes:
            # Find matching device
            matching_device = None
            for device in devices:
                if device.mount_point == volume:
                    matching_device = device
                    break

            if not matching_device:
                # Create placeholder device for unknown volume
                volume_name = os.path.basename(volume)
                matching_device = USBDevice(
                    name=volume_name,
                    device_type="storage",
                    mount_point=volume
                )

            self.handle_device_connected(matching_device)

    def run(self):
        """Main monitoring loop."""
        log("USB DLP Monitor starting...")

        # Initial scan
        self.scan_existing_volumes()

        # Track current volumes for change detection
        current_volumes = set(self.get_mounted_volumes())

        try:
            while True:
                # Check for volume changes
                new_volumes = set(self.get_mounted_volumes())

                # Detect new volumes
                added = new_volumes - current_volumes
                for volume in added:
                    volume_name = os.path.basename(volume)
                    device = USBDevice(
                        name=volume_name,
                        device_type="storage",
                        mount_point=volume
                    )
                    self.handle_device_connected(device)

                # Detect removed volumes
                removed = current_volumes - new_volumes
                for volume in removed:
                    volume_name = os.path.basename(volume)
                    # Find and remove from connected devices
                    for key, device in list(self.connected_devices.items()):
                        if device.mount_point == volume:
                            self.handle_device_disconnected(device)
                            break

                current_volumes = new_volumes

                # Sleep before next check
                time.sleep(2)

        except KeyboardInterrupt:
            log("USB DLP Monitor stopping...")
        finally:
            # Stop all observers
            for observer in self.file_observers.values():
                observer.stop()
                observer.join()


def main():
    """Entry point."""
    monitor = USBDLPMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
