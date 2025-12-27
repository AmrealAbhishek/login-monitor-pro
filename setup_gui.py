#!/usr/bin/env python3
"""
Login Monitor PRO - GUI Setup Wizard
Uses native macOS dialogs for a professional experience
Now uses Supabase for cloud notifications and Flutter app integration
"""

import os
import sys
import json
import subprocess
import socket
import platform
from pathlib import Path


def is_frozen():
    """Check if running as PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """Get base directory for data files"""
    if is_frozen():
        return Path.home() / ".login-monitor"
    return Path(__file__).parent


CONFIG_DIR = get_base_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"

# Supabase credentials (hardcoded for this build)
SUPABASE_URL = "https://uldaniwnnwuiyyfygsxa.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NDY4NjEsImV4cCI6MjA4MjQyMjg2MX0._9OU-el7-1I7aS_VLLdhjjexOFQdg0TQ7LI3KI6a2a4"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Njg0Njg2MSwiZXhwIjoyMDgyNDIyODYxfQ.TEcxmXe628_DJILYNOtFVXDMFDku4xL7v9IDCNkI0zo"


def run_applescript(script):
    """Run AppleScript and return result"""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True
        )
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        return str(e), False


def show_dialog(message, title="Login Monitor PRO", buttons=["OK"], default_button="OK", icon="note"):
    """Show a dialog with buttons"""
    buttons_str = ", ".join([f'"{b}"' for b in buttons])
    script = f'''
    display dialog "{message}" with title "{title}" buttons {{{buttons_str}}} default button "{default_button}" with icon {icon}
    '''
    result, success = run_applescript(script)
    if success and "button returned:" in result:
        return result.split("button returned:")[1].strip()
    return None


def show_input(message, title="Login Monitor PRO", default_value="", hidden=False):
    """Show input dialog"""
    hidden_str = "with hidden answer" if hidden else ""
    script = f'''
    display dialog "{message}" with title "{title}" default answer "{default_value}" {hidden_str}
    '''
    result, success = run_applescript(script)
    if success and "text returned:" in result:
        text = result.split("text returned:")[1]
        if ", button returned:" in text:
            text = text.split(", button returned:")[0]
        return text.strip()
    return None


def show_list(message, items, title="Login Monitor PRO"):
    """Show list selection dialog"""
    items_str = ", ".join([f'"{item}"' for item in items])
    script = f'''
    choose from list {{{items_str}}} with title "{title}" with prompt "{message}"
    '''
    result, success = run_applescript(script)
    if success and result and result != "false":
        return result.strip()
    return None


def show_notification(message, title="Login Monitor PRO"):
    """Show notification"""
    script = f'''
    display notification "{message}" with title "{title}"
    '''
    run_applescript(script)


def welcome_screen():
    """Show welcome screen"""
    message = """Welcome to Login Monitor PRO Setup!

This wizard will help you configure:
• Cloud notifications via mobile app
• Email alerts (optional)
• Anti-theft features

Your Mac will be paired with the
Login Monitor mobile app.

Click Continue to begin."""

    result = show_dialog(message, buttons=["Quit", "Continue"], default_button="Continue", icon="note")
    return result == "Continue"


def register_device():
    """Register device with Supabase and get pairing code"""
    import urllib.request
    import urllib.error
    import random
    import string
    from datetime import datetime

    # Generate 6-digit pairing code
    pairing_code = ''.join(random.choices(string.digits, k=6))

    # Device info
    hostname = socket.gethostname()
    os_version = platform.platform()

    # Prepare device data
    device_data = {
        "device_code": pairing_code,
        "hostname": hostname,
        "os_version": os_version,
        "is_active": True,
        "last_seen": datetime.utcnow().isoformat()
    }

    try:
        # Register with Supabase
        url = f"{SUPABASE_URL}/rest/v1/devices"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(device_data).encode(),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            if result and len(result) > 0:
                return {
                    "success": True,
                    "device_id": result[0]["id"],
                    "pairing_code": pairing_code
                }

        return {"success": False, "error": "No result returned"}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return {"success": False, "error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def setup_cloud():
    """Setup cloud connection (Supabase)"""
    message = """Setting up cloud connection...

This will register your Mac with our
secure cloud service. You'll receive a
pairing code to connect your mobile app."""

    show_dialog(message, buttons=["Continue"])

    # Register device
    result = register_device()

    if not result.get("success"):
        show_dialog(f"Failed to register device:\\n{result.get('error', 'Unknown error')}", icon="stop")
        return None

    device_id = result["device_id"]
    pairing_code = result["pairing_code"]

    # Show pairing code
    message = f"""Device Registered Successfully!

Your Pairing Code:

    {pairing_code}

To connect the mobile app:
1. Download 'Login Monitor' app
2. Create an account or log in
3. Tap 'Add Device'
4. Enter this code: {pairing_code}

The code is valid until the device is paired."""

    show_dialog(message, buttons=["Done"], icon="note")

    return {
        "url": SUPABASE_URL,
        "anon_key": SUPABASE_ANON_KEY,
        "service_key": SUPABASE_SERVICE_KEY,
        "device_id": device_id,
        "pairing_code": pairing_code
    }


def setup_email():
    """Configure email settings (optional)"""
    message = "Would you like to also receive email alerts?\\n\\n(You'll still get mobile app notifications)"

    result = show_dialog(message, buttons=["Skip", "Setup Email"], default_button="Skip")

    if result != "Setup Email":
        return {"enabled": False}

    # Gmail setup
    show_dialog("""To use Gmail, you need an App Password.

How to get one:
1. Go to myaccount.google.com/apppasswords
2. Sign in to your Google account
3. Select 'Mail' and your device
4. Click 'Generate'
5. Copy the 16-character password""", buttons=["Continue"])

    email = show_input("Enter your Gmail address:", default_value="@gmail.com")
    if not email:
        return {"enabled": False}

    password = show_input("Enter your Gmail App Password:", hidden=True)
    if not password:
        return {"enabled": False}

    notify_email = show_input("Where should alerts be sent?", default_value=email)
    if not notify_email:
        notify_email = email

    return {
        "enabled": True,
        "notification_email": notify_email,
        "smtp": {
            "server": "smtp.gmail.com",
            "port": 465,
            "sender_email": email,
            "password": password,
            "use_ssl": True,
            "use_tls": False
        }
    }


def setup_features():
    """Configure features"""
    features = {
        "multi_photo": True,
        "photo_count": 3,
        "photo_delay": 2,
        "audio_recording": False,
        "audio_duration": 10,
        "face_recognition": True,
        "daily_summary": False
    }

    message = "Would you like to customize advanced features?"
    result = show_dialog(message, buttons=["Use Defaults", "Customize"])

    if result == "Customize":
        # Photo count
        count = show_input("Number of photos to capture (1-5):", default_value="3")
        if count and count.isdigit():
            features["photo_count"] = min(5, max(1, int(count)))

        # Audio recording
        audio = show_dialog("Enable audio recording on events?", buttons=["No", "Yes"])
        features["audio_recording"] = (audio == "Yes")

        # Face recognition
        face = show_dialog("Enable face recognition?\\n(Alerts you when unknown faces are detected)", buttons=["No", "Yes"])
        features["face_recognition"] = (face == "Yes")

    return features


def save_config(config):
    """Save configuration to file"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (CONFIG_DIR / "events").mkdir(exist_ok=True)
        (CONFIG_DIR / "captured_images").mkdir(exist_ok=True)
        (CONFIG_DIR / "captured_audio").mkdir(exist_ok=True)
        (CONFIG_DIR / "known_faces").mkdir(exist_ok=True)

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
        return True
    except Exception as e:
        show_dialog(f"Error saving configuration: {e}", icon="stop")
        return False


def install_services():
    """Install and start monitoring services"""
    message = """Would you like to start Login Monitor now?

This will:
• Start monitoring for login/unlock events
• Start the command listener (for mobile app)
• Set up auto-start on login"""

    result = show_dialog(message, buttons=["Later", "Start Now"], default_button="Start Now")

    if result == "Start Now":
        # Determine app location
        if is_frozen():
            app_path = Path(sys.executable).parent.parent.parent
        else:
            app_path = Path("/Applications/LoginMonitorPRO.app")

        macos_path = app_path / "Contents" / "MacOS"

        if not macos_path.exists():
            show_dialog("App not found in expected location.\\nPlease drag the app to Applications first.", icon="stop")
            return False

        # Create LaunchAgents
        launch_agents = Path.home() / "Library" / "LaunchAgents"
        launch_agents.mkdir(parents=True, exist_ok=True)

        # Screen watcher plist
        screen_plist = launch_agents / "com.loginmonitor.screen.plist"
        screen_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.screen</string>
    <key>ProgramArguments</key>
    <array>
        <string>{macos_path}/screen_watcher</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-screen.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-screen.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>'''

        with open(screen_plist, 'w') as f:
            f.write(screen_content)

        # Command listener plist (replaces telegram_bot)
        command_plist = launch_agents / "com.loginmonitor.commands.plist"
        command_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.commands</string>
    <key>ProgramArguments</key>
    <array>
        <string>{macos_path}/command_listener</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-commands.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-commands.log</string>
</dict>
</plist>'''

        with open(command_plist, 'w') as f:
            f.write(command_content)

        # Unload old telegram service if exists
        old_telegram_plist = launch_agents / "com.loginmonitor.telegram.plist"
        if old_telegram_plist.exists():
            subprocess.run(['launchctl', 'unload', str(old_telegram_plist)], capture_output=True)
            old_telegram_plist.unlink()

        # Load services
        subprocess.run(['launchctl', 'unload', str(screen_plist)], capture_output=True)
        subprocess.run(['launchctl', 'unload', str(command_plist)], capture_output=True)
        subprocess.run(['launchctl', 'load', str(screen_plist)], capture_output=True)
        subprocess.run(['launchctl', 'load', str(command_plist)], capture_output=True)

        return True

    return False


def show_completion(services_started, pairing_code):
    """Show completion message"""
    if services_started:
        message = f"""Setup Complete!

Login Monitor PRO is now running.

Your Pairing Code: {pairing_code}

You will receive notifications when:
• Someone logs into your Mac
• Someone unlocks the screen
• The computer wakes from sleep

IMPORTANT: Grant permissions when prompted:
• Camera (for photos)
• Location (for tracking)
• Microphone (for audio)

Download the mobile app and enter your
pairing code to connect!"""
    else:
        message = f"""Setup Complete!

Your configuration has been saved.
Pairing Code: {pairing_code}

To start monitoring manually, run:
/Applications/LoginMonitorPRO.app

Download the mobile app and enter your
pairing code to connect!"""

    show_dialog(message, title="Setup Complete!", buttons=["Done"], icon="note")


def main():
    """Main setup wizard"""
    # Welcome
    if not welcome_screen():
        return

    # Cloud setup (Supabase)
    supabase_config = setup_cloud()
    if not supabase_config:
        show_dialog("Cloud setup is required for mobile app notifications.", icon="stop")
        return

    # Email setup (optional)
    email_config = setup_email()

    # Features setup
    features_config = setup_features()

    # Combine config
    config = {
        "supabase": supabase_config,
        "features": features_config
    }

    # Add email config if enabled
    if email_config.get("enabled"):
        config["notification_email"] = email_config.get("notification_email", "")
        config["smtp"] = email_config.get("smtp", {})

    # Keep telegram section empty for backwards compatibility
    config["telegram"] = {"enabled": False}

    # Save config
    if not save_config(config):
        return

    show_notification("Configuration saved successfully!")

    # Install services
    services_started = install_services()

    # Show completion
    show_completion(services_started, supabase_config.get("pairing_code", ""))


if __name__ == "__main__":
    main()
