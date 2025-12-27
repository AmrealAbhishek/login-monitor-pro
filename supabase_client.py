#!/usr/bin/env python3
"""
Supabase Client for Login Monitor PRO
Handles all communication with Supabase backend (REST API + Storage)
"""

import json
import os
import random
import string
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class SupabaseClient:
    """REST API client for Supabase"""

    def __init__(self, url: str, anon_key: str, service_key: str = None):
        self.url = url.rstrip('/')
        self.anon_key = anon_key
        self.service_key = service_key or anon_key
        self.device_id = None
        self.user_id = None

    def _headers(self, use_service_key: bool = False) -> Dict[str, str]:
        """Get headers for API requests"""
        key = self.service_key if use_service_key else self.anon_key
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def _request(self, method: str, endpoint: str, data: dict = None,
                 use_service_key: bool = False, content_type: str = None) -> dict:
        """Make HTTP request to Supabase"""
        url = f"{self.url}{endpoint}"
        headers = self._headers(use_service_key)

        if content_type:
            headers["Content-Type"] = content_type

        body = None
        if data:
            if content_type and "octet-stream" in content_type:
                body = data  # Binary data
            else:
                body = json.dumps(data).encode('utf-8')

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                if response_data:
                    return json.loads(response_data)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            print(f"[Supabase] HTTP Error {e.code}: {error_body}")
            raise
        except urllib.error.URLError as e:
            print(f"[Supabase] URL Error: {e.reason}")
            raise
        except Exception as e:
            print(f"[Supabase] Error: {e}")
            raise

    # =========================================================================
    # DEVICE MANAGEMENT
    # =========================================================================

    def generate_pairing_code(self) -> str:
        """Generate a 6-digit pairing code"""
        return ''.join(random.choices(string.digits, k=6))

    def register_device(self, hostname: str, os_version: str, mac_address: str = None) -> Dict:
        """Register this device with a pairing code"""
        code = self.generate_pairing_code()

        device_data = {
            "device_code": code,
            "hostname": hostname,
            "os_version": os_version,
            "mac_address": mac_address,
            "is_active": True,
            "last_seen": datetime.utcnow().isoformat()
        }

        try:
            result = self._request(
                "POST",
                "/rest/v1/devices",
                device_data,
                use_service_key=True
            )

            if result and len(result) > 0:
                self.device_id = result[0]["id"]
                return {"device_id": self.device_id, "pairing_code": code}

            return {"error": "Failed to register device"}
        except Exception as e:
            return {"error": str(e)}

    def check_device_paired(self, device_id: str) -> Dict:
        """Check if device has been paired with a user"""
        try:
            result = self._request(
                "GET",
                f"/rest/v1/devices?id=eq.{device_id}&select=user_id,hostname",
                use_service_key=True
            )

            if result and len(result) > 0:
                user_id = result[0].get("user_id")
                if user_id:
                    self.user_id = user_id
                    return {"paired": True, "user_id": user_id}
                return {"paired": False}

            return {"error": "Device not found"}
        except Exception as e:
            return {"error": str(e)}

    def update_device_status(self, device_id: str) -> bool:
        """Update device last_seen timestamp"""
        try:
            self._request(
                "PATCH",
                f"/rest/v1/devices?id=eq.{device_id}",
                {"last_seen": datetime.utcnow().isoformat()},
                use_service_key=True
            )
            return True
        except:
            return False

    # =========================================================================
    # EVENTS (Login/Unlock notifications)
    # =========================================================================

    def send_event(self, device_id: str, event_data: Dict, photos: List[str] = None) -> Dict:
        """Send a login/unlock event to Supabase"""
        try:
            # Upload photos first
            photo_urls = []
            if photos:
                for photo_path in photos:
                    url = self.upload_file(device_id, photo_path, "photos")
                    if url:
                        photo_urls.append(url)

            # Prepare event data
            event = {
                "device_id": device_id,
                "event_type": event_data.get("event_type", "Unknown"),
                "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
                "hostname": event_data.get("hostname"),
                "username": event_data.get("user"),
                "local_ip": event_data.get("local_ip"),
                "public_ip": event_data.get("public_ip"),
                "location": event_data.get("location", {}),
                "battery": event_data.get("battery", {}),
                "wifi": event_data.get("wifi", {}),
                "face_recognition": event_data.get("face_recognition", {}),
                "activity": event_data.get("activity", {}),
                "photos": photo_urls,
                "audio_url": event_data.get("audio_url"),
                "is_read": False
            }

            result = self._request(
                "POST",
                "/rest/v1/events",
                event,
                use_service_key=True
            )

            if result and len(result) > 0:
                return {"success": True, "event_id": result[0]["id"]}

            return {"success": False, "error": "No result returned"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # COMMANDS (Remote control)
    # =========================================================================

    def get_pending_commands(self, device_id: str) -> List[Dict]:
        """Get pending commands for this device"""
        try:
            result = self._request(
                "GET",
                f"/rest/v1/commands?device_id=eq.{device_id}&status=eq.pending&order=created_at.asc",
                use_service_key=True
            )
            return result if result else []
        except Exception as e:
            print(f"[Supabase] Error getting commands: {e}")
            return []

    def update_command_status(self, command_id: str, status: str,
                              result: Dict = None, result_url: str = None) -> bool:
        """Update command status after execution"""
        try:
            update_data = {
                "status": status,
                "executed_at": datetime.utcnow().isoformat()
            }
            if result:
                update_data["result"] = result
            if result_url:
                update_data["result_url"] = result_url

            self._request(
                "PATCH",
                f"/rest/v1/commands?id=eq.{command_id}",
                update_data,
                use_service_key=True
            )
            return True
        except Exception as e:
            print(f"[Supabase] Error updating command: {e}")
            return False

    # =========================================================================
    # STORAGE (Photos/Audio)
    # =========================================================================

    def upload_file(self, device_id: str, file_path: str, bucket: str = "photos") -> Optional[str]:
        """Upload file to Supabase Storage"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"[Supabase] File not found: {file_path}")
                return None

            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Determine content type
            ext = file_path.suffix.lower()
            content_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg'
            }
            content_type = content_types.get(ext, 'application/octet-stream')

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{device_id}/{timestamp}_{file_path.name}"

            # Upload to storage
            url = f"{self.url}/storage/v1/object/{bucket}/{filename}"
            headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": content_type
            }

            req = urllib.request.Request(url, data=file_data, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status in [200, 201]:
                    # Return public URL
                    return f"{self.url}/storage/v1/object/public/{bucket}/{filename}"

            return None
        except Exception as e:
            print(f"[Supabase] Upload error: {e}")
            return None

    def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> Optional[str]:
        """Get a signed URL for private file access"""
        try:
            result = self._request(
                "POST",
                f"/storage/v1/object/sign/{bucket}/{path}",
                {"expiresIn": expires_in},
                use_service_key=True
            )
            if result and "signedURL" in result:
                return f"{self.url}{result['signedURL']}"
            return None
        except Exception as e:
            print(f"[Supabase] Signed URL error: {e}")
            return None


class SupabaseNotifier:
    """Notification sender using Supabase (replaces TelegramNotifier)"""

    def __init__(self, url: str, anon_key: str, service_key: str, device_id: str):
        self.client = SupabaseClient(url, anon_key, service_key)
        self.device_id = device_id
        self.enabled = bool(url and anon_key and device_id)

    def send_event(self, event_data: Dict, photos: List[str] = None) -> bool:
        """Send complete event with photos"""
        if not self.enabled:
            print("[Supabase] Notifier not configured")
            return False

        result = self.client.send_event(self.device_id, event_data, photos)
        return result.get("success", False)

    def send_location(self, latitude: float, longitude: float) -> bool:
        """Send just location update"""
        if not self.enabled:
            return False

        event_data = {
            "event_type": "LocationUpdate",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        result = self.client.send_event(self.device_id, event_data)
        return result.get("success", False)

    def upload_photo(self, photo_path: str) -> Optional[str]:
        """Upload single photo and return URL"""
        if not self.enabled:
            return None
        return self.client.upload_file(self.device_id, photo_path, "photos")

    def upload_audio(self, audio_path: str) -> Optional[str]:
        """Upload audio file and return URL"""
        if not self.enabled:
            return None
        return self.client.upload_file(self.device_id, audio_path, "audio")


# Test the client
if __name__ == "__main__":
    import socket
    import platform

    # Test credentials
    URL = "https://uldaniwnnwuiyyfygsxa.supabase.co"
    ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NDY4NjEsImV4cCI6MjA4MjQyMjg2MX0._9OU-el7-1I7aS_VLLdhjjexOFQdg0TQ7LI3KI6a2a4"
    SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Njg0Njg2MSwiZXhwIjoyMDgyNDIyODYxfQ.TEcxmXe628_DJILYNOtFVXDMFDku4xL7v9IDCNkI0zo"

    print("Testing Supabase Client...")
    print("=" * 50)

    client = SupabaseClient(URL, ANON_KEY, SERVICE_KEY)

    # Test device registration
    print("\n1. Registering device...")
    result = client.register_device(
        hostname=socket.gethostname(),
        os_version=platform.platform()
    )
    print(f"   Result: {result}")

    if "device_id" in result:
        device_id = result["device_id"]
        pairing_code = result["pairing_code"]
        print(f"\n   PAIRING CODE: {pairing_code}")
        print(f"   Device ID: {device_id}")

        # Test sending event
        print("\n2. Sending test event...")
        test_event = {
            "event_type": "Test",
            "hostname": socket.gethostname(),
            "user": os.getenv("USER"),
            "local_ip": "192.168.1.100",
            "public_ip": "1.2.3.4",
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "city": "New York",
                "country": "USA"
            },
            "battery": {
                "percentage": 85,
                "charging": False
            }
        }

        event_result = client.send_event(device_id, test_event)
        print(f"   Result: {event_result}")

    print("\n" + "=" * 50)
    print("Test complete!")
