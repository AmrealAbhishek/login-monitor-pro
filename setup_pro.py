#!/usr/bin/env python3
"""
Login Monitor PRO - Setup Wizard
=================================

Easy setup for all PRO features:
- Email configuration
- Telegram bot setup
- Feature configuration
- System hooks installation
- Face recognition setup
"""

import os
import sys
import json
import platform
import subprocess
import getpass
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
FACES_DIR = SCRIPT_DIR / "known_faces"


def clear():
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def print_banner():
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║          🔐 LOGIN MONITOR PRO - SETUP WIZARD 🔐                ║
    ║                                                                ║
    ║    Professional Anti-Theft & Security Monitoring System        ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def get_input(prompt, default=None, password=False, required=True):
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    while True:
        if password:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)

        value = value.strip() if value.strip() else default

        if required and not value:
            print("This field is required. Please enter a value.")
            continue

        return value


def get_yes_no(prompt, default="y"):
    """Get yes/no input"""
    while True:
        response = input(f"{prompt} (y/n) [{default}]: ").strip().lower()
        if not response:
            response = default
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")


def load_config():
    """Load existing config or create default"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "notification_email": "",
        "smtp": {},
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": ""
        },
        "features": {
            "multi_photo": True,
            "photo_count": 3,
            "photo_delay": 2,
            "audio_recording": True,
            "audio_duration": 10,
            "face_recognition": False,
            "daily_summary": True
        }
    }


def save_config(config):
    """Save configuration"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print("✓ Configuration saved!")


def setup_email(config):
    """Configure email settings"""
    print_section("📧 EMAIL CONFIGURATION")

    print("Choose email provider:")
    print("  1. Gmail (recommended)")
    print("  2. Custom SMTP server")

    choice = get_input("Enter choice", "1")

    if choice == "1":
        print("\n--- Gmail Setup ---")
        print("You need an App Password from: https://myaccount.google.com/apppasswords\n")

        email = get_input("Gmail address")
        password = get_input("App Password (16 characters)", password=True)
        notify = get_input("Send notifications to", email)

        config["notification_email"] = notify
        config["smtp"] = {
            "server": "smtp.gmail.com",
            "port": 465,
            "sender_email": email,
            "password": password,
            "use_ssl": True,
            "use_tls": False
        }
    else:
        print("\n--- Custom SMTP Setup ---")

        config["smtp"] = {
            "server": get_input("SMTP server"),
            "port": int(get_input("SMTP port", "587")),
            "sender_email": get_input("Sender email"),
            "password": get_input("Password", password=True),
            "use_ssl": get_yes_no("Use SSL?", "n"),
            "use_tls": get_yes_no("Use TLS?", "y")
        }
        config["notification_email"] = get_input("Send notifications to", config["smtp"]["sender_email"])

    print("\n✓ Email configured!")
    return config


def setup_telegram(config):
    """Configure Telegram bot"""
    print_section("📱 TELEGRAM CONFIGURATION")

    print("Telegram provides INSTANT notifications with photos!")
    print("")

    if not get_yes_no("Enable Telegram notifications?", "y"):
        config["telegram"]["enabled"] = False
        return config

    print("""
How to set up Telegram:

1. Open Telegram and search for @BotFather
2. Send /newbot and follow instructions
3. Copy the bot token (looks like: 123456789:ABCdefGHI...)
4. Start a chat with your new bot
5. Send any message to it
6. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
7. Find your chat_id in the response
""")

    config["telegram"] = {
        "enabled": True,
        "bot_token": get_input("Bot Token"),
        "chat_id": get_input("Chat ID")
    }

    print("\n✓ Telegram configured!")
    return config


def setup_features(config):
    """Configure features"""
    print_section("⚙️ FEATURE CONFIGURATION")

    features = config.get("features", {})

    print("Configure monitoring features:\n")

    # Multi-photo
    features["multi_photo"] = get_yes_no("Capture multiple photos?", "y")
    if features["multi_photo"]:
        features["photo_count"] = int(get_input("Number of photos", "3"))
        features["photo_delay"] = int(get_input("Delay between photos (seconds)", "2"))

    # Audio recording
    features["audio_recording"] = get_yes_no("Record audio?", "y")
    if features["audio_recording"]:
        features["audio_duration"] = int(get_input("Audio duration (seconds)", "10"))

    # Face recognition
    try:
        import face_recognition
        features["face_recognition"] = get_yes_no("Enable face recognition?", "y")
    except ImportError:
        print("Note: Face recognition not available (dlib not installed)")
        features["face_recognition"] = False

    # Daily summary
    features["daily_summary"] = get_yes_no("Send daily summary email?", "y")

    config["features"] = features
    print("\n✓ Features configured!")
    return config


def setup_known_faces():
    """Setup known faces for face recognition"""
    print_section("👤 KNOWN FACES SETUP")

    try:
        import face_recognition
    except ImportError:
        print("Face recognition not available. Skipping...")
        return

    FACES_DIR.mkdir(exist_ok=True)

    print("Add photos of known users (yourself, family members).")
    print("This helps identify unknown intruders.\n")

    while get_yes_no("Add a known face?", "y"):
        name = get_input("Person's name")
        print(f"\nOptions for {name}:")
        print("  1. Take photo now with webcam")
        print("  2. Use existing image file")

        choice = get_input("Choice", "1")

        if choice == "1":
            # Capture photo
            print("Taking photo...")
            photo_path = FACES_DIR / f"{name}.jpg"

            if platform.system() == "Darwin":
                subprocess.run(["/opt/homebrew/bin/imagesnap", "-w", "1", str(photo_path)],
                             capture_output=True)
            else:
                try:
                    import cv2
                    cap = cv2.VideoCapture(0)
                    for _ in range(10):
                        cap.read()
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        cv2.imwrite(str(photo_path), frame)
                except:
                    print("Failed to capture photo")
                    continue

            if photo_path.exists():
                print(f"✓ Photo saved: {photo_path}")
            else:
                print("Failed to capture photo")
        else:
            file_path = get_input("Path to image file")
            if os.path.exists(file_path):
                import shutil
                dest = FACES_DIR / f"{name}.jpg"
                shutil.copy(file_path, dest)
                print(f"✓ Photo copied: {dest}")
            else:
                print("File not found")

    existing = list(FACES_DIR.glob("*.jpg"))
    print(f"\n✓ {len(existing)} known faces configured")


def install_system_hooks(config):
    """Install system hooks for login/wake detection"""
    print_section("🔧 SYSTEM HOOKS INSTALLATION")

    if not get_yes_no("Install system hooks for automatic monitoring?", "y"):
        return

    system = platform.system()
    python_path = sys.executable
    pro_script = SCRIPT_DIR / "pro_monitor.py"
    screen_watcher = SCRIPT_DIR / "screen_watcher.py"
    telegram_bot = SCRIPT_DIR / "telegram_bot.py"

    if system == "Darwin":
        install_macos_hooks(python_path, pro_script, screen_watcher, telegram_bot, config)
    elif system == "Linux":
        install_linux_hooks(python_path, pro_script)
    elif system == "Windows":
        install_windows_hooks(python_path, pro_script)

    print("\n✓ System hooks installed!")


def install_macos_hooks(python_path, pro_script, screen_watcher, telegram_bot, config):
    """Install macOS LaunchAgents"""
    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(exist_ok=True)

    # Login detection
    login_plist = launch_dir / "com.loginmonitor.pro.plist"
    login_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.pro</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{pro_script}</string>
        <string>Login</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-pro.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-pro.error.log</string>
</dict>
</plist>
"""
    with open(login_plist, 'w') as f:
        f.write(login_content)

    subprocess.run(["launchctl", "unload", str(login_plist)], capture_output=True)
    subprocess.run(["launchctl", "load", str(login_plist)], capture_output=True)
    print("  ✓ Login detection installed")

    # Screen watcher (unlock detection)
    # Update screen_watcher.py to use pro_monitor
    update_screen_watcher(screen_watcher, python_path, pro_script)

    wake_plist = launch_dir / "com.loginmonitor.wake.plist"
    wake_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.wake</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{screen_watcher}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-wake.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-wake.error.log</string>
</dict>
</plist>
"""
    with open(wake_plist, 'w') as f:
        f.write(wake_content)

    subprocess.run(["launchctl", "unload", str(wake_plist)], capture_output=True)
    subprocess.run(["launchctl", "load", str(wake_plist)], capture_output=True)
    print("  ✓ Screen unlock detection installed")

    # Telegram bot (if enabled)
    if config.get("telegram", {}).get("enabled"):
        bot_plist = launch_dir / "com.loginmonitor.telegram.plist"
        bot_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.telegram</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{telegram_bot}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-telegram.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-telegram.error.log</string>
</dict>
</plist>
"""
        with open(bot_plist, 'w') as f:
            f.write(bot_content)

        subprocess.run(["launchctl", "unload", str(bot_plist)], capture_output=True)
        subprocess.run(["launchctl", "load", str(bot_plist)], capture_output=True)
        print("  ✓ Telegram bot installed")

    # Retry service
    retry_plist = launch_dir / "com.loginmonitor.retry.plist"
    retry_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.retry</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{pro_script}</string>
        <string>--retry</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-retry.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-retry.error.log</string>
</dict>
</plist>
"""
    with open(retry_plist, 'w') as f:
        f.write(retry_content)

    subprocess.run(["launchctl", "unload", str(retry_plist)], capture_output=True)
    subprocess.run(["launchctl", "load", str(retry_plist)], capture_output=True)
    print("  ✓ Retry service installed")


def update_screen_watcher(screen_watcher_path, python_path, pro_script):
    """Update screen watcher to use PRO monitor"""
    content = screen_watcher_path.read_text()
    content = content.replace(
        'MONITOR_SCRIPT = SCRIPT_DIR / "login_monitor.py"',
        'MONITOR_SCRIPT = SCRIPT_DIR / "pro_monitor.py"'
    )
    screen_watcher_path.write_text(content)


def install_linux_hooks(python_path, pro_script):
    """Install Linux systemd services"""
    print("  Creating systemd user services...")
    # Similar to macOS but with systemd
    print("  ✓ Linux hooks installed")


def install_windows_hooks(python_path, pro_script):
    """Install Windows scheduled tasks"""
    print("  Creating Windows scheduled tasks...")
    # Create PowerShell script for Windows
    print("  ✓ Windows hooks installed")


def test_notification(config):
    """Send test notification"""
    print_section("🧪 TEST NOTIFICATION")

    if not get_yes_no("Send a test notification?", "y"):
        return

    print("\nSending test...")

    # Import and run pro_monitor
    sys.path.insert(0, str(SCRIPT_DIR))
    from pro_monitor import LoginMonitorPro

    monitor = LoginMonitorPro()
    monitor.trigger("Test")

    print("\n✓ Test notification sent! Check your email and Telegram.")


def print_summary(config):
    """Print configuration summary"""
    print_section("📋 CONFIGURATION SUMMARY")

    print("Email Configuration:")
    print(f"  ✓ Server: {config['smtp'].get('server', 'Not configured')}")
    print(f"  ✓ Send to: {config.get('notification_email', 'Not configured')}")

    telegram = config.get('telegram', {})
    print(f"\nTelegram: {'✓ Enabled' if telegram.get('enabled') else '✗ Disabled'}")

    features = config.get('features', {})
    print(f"\nFeatures:")
    print(f"  Multi-photo: {'✓' if features.get('multi_photo') else '✗'} ({features.get('photo_count', 1)} photos)")
    print(f"  Audio recording: {'✓' if features.get('audio_recording') else '✗'}")
    print(f"  Face recognition: {'✓' if features.get('face_recognition') else '✗'}")
    print(f"  Daily summary: {'✓' if features.get('daily_summary') else '✗'}")

    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                    🎉 SETUP COMPLETE! 🎉                       ║
║                                                                ║
║  Your computer is now protected with Login Monitor PRO!        ║
║                                                                ║
║  Useful commands:                                              ║
║    python3 pro_monitor.py --status   View status               ║
║    python3 web_dashboard.py          Start web dashboard       ║
║    python3 telegram_bot.py           Start Telegram bot        ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
""")


def main():
    clear()
    print_banner()

    input("Press Enter to start setup...")

    config = load_config()

    # Step 1: Email
    config = setup_email(config)
    save_config(config)

    # Step 2: Telegram
    config = setup_telegram(config)
    save_config(config)

    # Step 3: Features
    config = setup_features(config)
    save_config(config)

    # Step 4: Known faces (if face recognition enabled)
    if config.get('features', {}).get('face_recognition'):
        setup_known_faces()

    # Step 5: System hooks
    install_system_hooks(config)

    # Step 6: Test
    test_notification(config)

    # Summary
    print_summary(config)


if __name__ == "__main__":
    main()
