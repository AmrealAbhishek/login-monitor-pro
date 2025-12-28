#!/usr/bin/env python3
"""
FCM Push Notification Sender using Firebase HTTP v1 API
Sends instant push notifications to Android devices
"""

import json
import time
import requests
from pathlib import Path

# Google Auth
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("[FCM] google-auth not installed. Run: pip3 install google-auth")

# Configuration
SERVICE_ACCOUNT_FILE = Path(__file__).parent / "firebase-service-account.json"
PROJECT_ID = "cyvigil-monitor"
FCM_URL = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

# Supabase config - loaded from config.json
import json
_config_path = Path(__file__).parent / "config.json"
if _config_path.exists():
    with open(_config_path) as f:
        _config = json.load(f)
    SUPABASE_URL = _config.get('supabase', {}).get('url', '')
    SUPABASE_KEY = _config.get('supabase', {}).get('service_key', _config.get('supabase', {}).get('anon_key', ''))
else:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""

# Cache for access token
_access_token = None
_token_expiry = 0


def get_access_token():
    """Get OAuth 2.0 access token for FCM API"""
    global _access_token, _token_expiry

    if not GOOGLE_AUTH_AVAILABLE:
        print("[FCM] google-auth library not available")
        return None

    # Return cached token if still valid
    if _access_token and time.time() < _token_expiry - 60:
        return _access_token

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        credentials.refresh(Request())

        _access_token = credentials.token
        _token_expiry = time.time() + 3600  # Token valid for 1 hour

        print("[FCM] Access token obtained")
        return _access_token
    except Exception as e:
        print(f"[FCM] Error getting access token: {e}")
        return None


def get_fcm_tokens_for_device(device_id: str) -> list:
    """Get FCM tokens for all users who own this device"""
    try:
        # Get device owner's user_id
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/devices",
            params={"id": f"eq.{device_id}", "select": "user_id"},
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )

        if response.status_code != 200:
            print(f"[FCM] Error getting device: {response.text}")
            return []

        devices = response.json()
        if not devices:
            print(f"[FCM] Device not found: {device_id}")
            return []

        user_id = devices[0].get("user_id")
        if not user_id:
            return []

        # Get FCM tokens for this user
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/fcm_tokens",
            params={"user_id": f"eq.{user_id}", "select": "token"},
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )

        if response.status_code != 200:
            print(f"[FCM] Error getting tokens: {response.text}")
            return []

        tokens = [t["token"] for t in response.json()]
        print(f"[FCM] Found {len(tokens)} FCM token(s) for device owner")
        return tokens

    except Exception as e:
        print(f"[FCM] Error getting tokens: {e}")
        return []


def get_notification_content(event_type: str, username: str = None, hostname: str = None) -> dict:
    """Generate notification title and body based on event type"""
    device = hostname or "Your Mac"
    user = username or "Someone"

    titles = {
        "Login": "🔐 Mac Login Detected",
        "Unlock": "🔓 Mac Unlocked",
        "Wake": "💡 Mac Woke Up",
        "Intruder": "🚨 INTRUDER ALERT!",
        "Lock": "🔒 Mac Locked",
        "Sleep": "😴 Mac Sleeping",
    }

    bodies = {
        "Login": f"{user} logged into {device}",
        "Unlock": f"{device} was unlocked by {user}",
        "Wake": f"{device} woke from sleep",
        "Intruder": f"Failed login attempt detected on {device}!",
        "Lock": f"{device} was locked",
        "Sleep": f"{device} went to sleep",
    }

    return {
        "title": titles.get(event_type, "📱 Security Event"),
        "body": bodies.get(event_type, f"New event on {device}")
    }


def send_fcm_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    """Send FCM notification to a single device token"""
    access_token = get_access_token()
    if not access_token:
        return False

    message = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body
            },
            "android": {
                "priority": "high",
                "notification": {
                    "channel_id": "cyvigil_fcm",
                    "sound": "alert_sound",
                    "default_vibrate_timings": True,
                    "notification_priority": "PRIORITY_HIGH"
                }
            }
        }
    }

    if data:
        message["message"]["data"] = {k: str(v) for k, v in data.items()}

    try:
        response = requests.post(
            FCM_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=message
        )

        if response.status_code == 200:
            print(f"[FCM] ✅ Notification sent successfully")
            return True
        else:
            print(f"[FCM] ❌ Failed to send: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"[FCM] Error sending notification: {e}")
        return False


def send_event_notification(device_id: str, event_type: str, username: str = None, hostname: str = None, event_id: str = None):
    """Send FCM notifications to all device owners for an event"""
    tokens = get_fcm_tokens_for_device(device_id)

    if not tokens:
        print(f"[FCM] No FCM tokens found for device {device_id}")
        return 0

    content = get_notification_content(event_type, username, hostname)

    data = {
        "event_type": event_type,
        "device_id": device_id,
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
    }
    if event_id:
        data["event_id"] = event_id

    sent_count = 0
    for token in tokens:
        if send_fcm_notification(token, content["title"], content["body"], data):
            sent_count += 1

    print(f"[FCM] Sent {sent_count}/{len(tokens)} notifications for {event_type} event")
    return sent_count


def send_broadcast_notification(title: str, body: str, data: dict = None) -> bool:
    """Send FCM notification to ALL users via topic 'all_users'"""
    access_token = get_access_token()
    if not access_token:
        return False

    message = {
        "message": {
            "topic": "all_users",
            "notification": {
                "title": title,
                "body": body
            },
            "android": {
                "priority": "high",
                "notification": {
                    "channel_id": "cyvigil_fcm",
                    "sound": "alert_sound",
                    "default_vibrate_timings": True,
                    "notification_priority": "PRIORITY_HIGH"
                }
            }
        }
    }

    if data:
        message["message"]["data"] = {k: str(v) for k, v in data.items()}

    try:
        response = requests.post(
            FCM_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=message
        )

        if response.status_code == 200:
            print(f"[FCM] ✅ Broadcast sent to all users")
            return True
        else:
            print(f"[FCM] ❌ Broadcast failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"[FCM] Error sending broadcast: {e}")
        return False


# Test function
if __name__ == "__main__":
    print("Testing FCM notification...")

    # Check if google-auth is installed
    if not GOOGLE_AUTH_AVAILABLE:
        print("Installing google-auth...")
        import subprocess
        subprocess.run(["pip3", "install", "google-auth", "google-auth-httplib2"])
        print("Please run this script again after installation.")
    else:
        # Test getting access token
        token = get_access_token()
        if token:
            print(f"✅ Access token obtained: {token[:20]}...")
        else:
            print("❌ Failed to get access token")
