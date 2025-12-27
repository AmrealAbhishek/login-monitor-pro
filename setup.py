#!/usr/bin/env python3
"""
Login Monitor Setup - Easy setup for family members.
Just run this script and follow the prompts!
"""

import os
import sys
import json
import platform
import subprocess
import getpass
from pathlib import Path

def is_frozen():
    """Check if running as PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """Get base directory for data files"""
    if is_frozen():
        return Path.home() / ".login-monitor"
    return Path(__file__).parent


SCRIPT_DIR = get_base_dir()
CONFIG_FILE = SCRIPT_DIR / "config.json"


def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def print_banner():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║               LOGIN MONITOR SETUP                         ║
    ║                                                           ║
    ║   This tool will notify you when someone logs into       ║
    ║   your computer. You'll get an email with a photo!       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)


def check_dependencies():
    """Check and install required dependencies"""
    print("\n[1/4] Checking dependencies...")

    try:
        import cv2
        print("   ✓ OpenCV is installed")
    except ImportError:
        print("   Installing OpenCV (camera support)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "opencv-python", "-q"])
        print("   ✓ OpenCV installed")


def get_email_config():
    """Get email configuration from user"""
    print("\n[2/4] Email Configuration")
    print("=" * 50)

    print("""
Where should login alerts be sent?

You have two options:
  1. Use Gmail (easiest)
  2. Use custom email server
""")

    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")

    config = {"notification_email": "", "smtp": {}}

    if choice == '1':
        # Gmail setup
        print("\n--- Gmail Setup ---")
        print("""
To use Gmail, you need an "App Password" (not your regular password).

How to get an App Password:
  1. Go to: https://myaccount.google.com/apppasswords
  2. Sign in to your Google account
  3. Select "Mail" and your device
  4. Click "Generate"
  5. Copy the 16-character password
""")

        email = input("Your Gmail address: ").strip()
        print("\nEnter your App Password (16 characters, you can include spaces):")
        password = getpass.getpass("App Password: ").strip()

        print(f"\nWhere should alerts be sent?")
        notify = input(f"Notification email [{email}]: ").strip()
        if not notify:
            notify = email

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
        # Custom SMTP
        print("\n--- Custom SMTP Setup ---")

        server = input("SMTP server (e.g., smtp.example.com): ").strip()
        port = input("SMTP port [587]: ").strip() or "587"
        email = input("Your email address: ").strip()
        password = getpass.getpass("Email password: ").strip()

        use_ssl = input("Use SSL? (y/n) [n]: ").strip().lower() == 'y'
        use_tls = input("Use TLS? (y/n) [y]: ").strip().lower() != 'n'

        notify = input(f"Send alerts to [{email}]: ").strip() or email

        config["notification_email"] = notify
        config["smtp"] = {
            "server": server,
            "port": int(port),
            "sender_email": email,
            "password": password,
            "use_ssl": use_ssl,
            "use_tls": use_tls
        }

    # Ensure directory exists
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    # Save config
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)

    print(f"\n   ✓ Configuration saved!")
    return config


def get_telegram_config(config):
    """Get Telegram configuration from user"""
    print("\n[3/5] Telegram Configuration (Optional)")
    print("=" * 50)

    print("""
Do you want to receive instant Telegram notifications?
This gives you real-time alerts with photos on your phone!

To set up Telegram:
  1. Open Telegram and search for @BotFather
  2. Send /newbot and follow instructions
  3. Copy the bot token (looks like: 123456:ABC-DEF...)
  4. Start a chat with your bot and send any message
  5. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
  6. Find your chat_id in the response
""")

    setup_telegram = input("Set up Telegram? (y/n) [y]: ").strip().lower()

    if setup_telegram == 'n':
        config["telegram"] = {"enabled": False}
        print("   Skipping Telegram setup")
        return config

    print("\n--- Telegram Setup ---")
    bot_token = input("Bot Token: ").strip()
    chat_id = input("Chat ID: ").strip()

    config["telegram"] = {
        "enabled": True,
        "bot_token": bot_token,
        "chat_id": chat_id
    }

    # Save updated config
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    print("   ✓ Telegram configured!")
    return config


def test_email(config):
    """Send a test email"""
    print("\n[3/4] Testing Email...")

    try:
        # Import the main module to use its email function
        sys.path.insert(0, str(SCRIPT_DIR))
        from login_monitor import send_email_for_event, get_system_info, check_internet

        if not check_internet():
            print("   ⚠ No internet connection. Skipping test.")
            return False

        # Create a test event
        sys_info = get_system_info()
        test_event = {
            'id': 'TEST',
            'event_type': 'Test',
            'timestamp': sys_info['time'],
            'hostname': sys_info['hostname'],
            'user': sys_info['user'],
            'os': sys_info['os'],
            'os_version': sys_info['os_version'],
            'local_ip': sys_info['local_ip'],
            'public_ip': sys_info['public_ip'],
            'image_path': None,
            'send_attempts': 0
        }

        success, error = send_email_for_event(config, test_event)

        if success:
            print(f"   ✓ Test email sent to {config['notification_email']}")
            print("     Check your inbox!")
            return True
        else:
            print(f"   ✗ Failed to send email: {error}")
            print("     Please check your email settings.")
            return False

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def install_system_hooks():
    """Install login/wake detection based on OS"""
    print("\n[4/4] Installing System Hooks...")

    system = platform.system()
    python_path = sys.executable
    script_path = SCRIPT_DIR / "login_monitor.py"

    if system == "Darwin":  # macOS
        install_macos(python_path, script_path)
    elif system == "Linux":
        install_linux(python_path, script_path)
    elif system == "Windows":
        install_windows(python_path, script_path)
    else:
        print(f"   ⚠ Unsupported OS: {system}")
        return False

    return True


def install_macos(python_path, script_path):
    """Install on macOS"""
    launch_agent_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agent_dir.mkdir(parents=True, exist_ok=True)

    # Login detection
    login_plist = launch_agent_dir / "com.loginmonitor.plist"
    login_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
        <string>Login</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor.error.log</string>
</dict>
</plist>
"""
    with open(login_plist, 'w') as f:
        f.write(login_content)

    # Load agents
    subprocess.run(["launchctl", "unload", str(login_plist)], capture_output=True)
    subprocess.run(["launchctl", "load", str(login_plist)], capture_output=True)

    # Wake detection
    wake_plist = launch_agent_dir / "com.loginmonitor.wake.plist"
    wake_watcher = SCRIPT_DIR / "wake_watcher.py"

    wake_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.wake</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{wake_watcher}</string>
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

    # Retry service (checks for pending events periodically)
    retry_plist = launch_agent_dir / "com.loginmonitor.retry.plist"
    retry_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.retry</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
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

    print("   ✓ macOS LaunchAgents installed")
    print("     - Login detection: Active")
    print("     - Wake detection: Active")
    print("     - Retry pending: Every 5 minutes")


def install_linux(python_path, script_path):
    """Install on Linux"""
    systemd_user_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_user_dir.mkdir(parents=True, exist_ok=True)

    # Login service
    login_service = systemd_user_dir / "login-monitor.service"
    login_content = f"""[Unit]
Description=Login Monitor

[Service]
Type=oneshot
ExecStart={python_path} {script_path} Login
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
"""

    with open(login_service, 'w') as f:
        f.write(login_content)

    # Retry timer
    retry_timer = systemd_user_dir / "login-monitor-retry.timer"
    retry_timer_content = """[Unit]
Description=Login Monitor Retry Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
"""

    retry_service = systemd_user_dir / "login-monitor-retry.service"
    retry_service_content = f"""[Unit]
Description=Login Monitor Retry

[Service]
Type=oneshot
ExecStart={python_path} {script_path} --retry
"""

    with open(retry_timer, 'w') as f:
        f.write(retry_timer_content)

    with open(retry_service, 'w') as f:
        f.write(retry_service_content)

    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "login-monitor.service"], capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "login-monitor-retry.timer"], capture_output=True)

    print("   ✓ Linux systemd services installed")
    print("     - Login detection: Active")
    print("     - Retry pending: Every 5 minutes")
    print("\n   Note: For wake detection, you may need to run:")
    print("     sudo systemctl enable login-monitor-wake.service")


def install_windows(python_path, script_path):
    """Install on Windows"""
    ps_script = SCRIPT_DIR / "install_windows.ps1"
    ps_content = f"""
$pythonPath = "{python_path}"
$scriptPath = "{script_path}"

# Login task
$loginAction = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`" Login"
$loginTrigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "LoginMonitor-Login" -Action $loginAction -Trigger $loginTrigger -Force

# Wake task
$wakeXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="System"&gt;&lt;Select Path="System"&gt;*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
    </EventTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>$pythonPath</Command>
      <Arguments>"$scriptPath" Wake</Arguments>
    </Exec>
  </Actions>
</Task>
"@
Register-ScheduledTask -TaskName "LoginMonitor-Wake" -Xml $wakeXml -Force

# Retry task (every 5 minutes)
$retryAction = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`" --retry"
$retryTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "LoginMonitor-Retry" -Action $retryAction -Trigger $retryTrigger -Force

Write-Host "Tasks installed successfully!"
"""

    with open(ps_script, 'w') as f:
        f.write(ps_content)

    print("   Installing Windows scheduled tasks...")

    result = subprocess.run([
        "powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print("   ✓ Windows scheduled tasks installed")
        print("     - Login detection: Active")
        print("     - Wake detection: Active")
        print("     - Retry pending: Every 5 minutes")
    else:
        print("   ⚠ Could not install automatically.")
        print(f"     Run PowerShell as Admin and execute: {ps_script}")


def print_success():
    """Print success message"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║                  SETUP COMPLETE!                          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝

    Your computer is now protected! You will receive an email
    notification with a photo whenever:

      • Someone logs in
      • Someone wakes the computer from sleep
      • The computer restarts

    If there's no internet, events are saved and sent later
    automatically (checked every 5 minutes).

    USEFUL COMMANDS:
    ────────────────
    Check event status:
      python3 {script_path} --status

    Manually retry pending:
      python3 {script_path} --retry

    Test the monitor:
      python3 {script_path} Test

    IMPORTANT - Camera Permission:
    ──────────────────────────────
    If on macOS, you may need to allow camera access.
    Run the test command above and click "Allow" when prompted.

    """.format(script_path=SCRIPT_DIR / "login_monitor.py"))


def main():
    clear_screen()
    print_banner()

    input("Press Enter to start setup...")

    # Step 1: Check dependencies (skip if frozen)
    if not is_frozen():
        check_dependencies()

    # Step 2: Email configuration
    config = get_email_config()

    # Step 3: Telegram configuration
    config = get_telegram_config(config)

    # Step 4: Test email
    test = input("\nWould you like to send a test email? (y/n) [y]: ").strip().lower()
    if test != 'n':
        test_email(config)

    # Step 5: Install system hooks (skip if frozen - use install script instead)
    if not is_frozen():
        install = input("\nInstall automatic login/wake detection? (y/n) [y]: ").strip().lower()
        if install != 'n':
            install_system_hooks()
    else:
        print("\n[5/5] Installation")
        print("=" * 50)
        print("Configuration complete!")
        print("\nTo start the services, run:")
        print("  /Applications/LoginMonitorPRO.app/Contents/MacOS/screen_watcher &")
        print("  /Applications/LoginMonitorPRO.app/Contents/MacOS/telegram_bot &")
        print("\nOr use the install_binary.sh script to set up auto-start.")

    # Done!
    print_success()


if __name__ == "__main__":
    main()
