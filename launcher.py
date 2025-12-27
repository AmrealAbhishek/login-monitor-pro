#!/usr/bin/env python3
"""
Login Monitor PRO - Launcher
Automatically shows setup wizard if not configured, then starts services.
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path


def is_frozen():
    """Check if running as PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False)


def get_executable_dir():
    """Get directory containing executables"""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_config_path():
    """Get config file path"""
    return Path.home() / ".login-monitor" / "config.json"


def config_exists():
    """Check if valid config exists"""
    config_path = get_config_path()
    if not config_path.exists():
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)
        # Check if Telegram is configured (required)
        telegram = config.get('telegram', {})
        if telegram.get('bot_token') and telegram.get('chat_id'):
            return True
        return False
    except:
        return False


def show_welcome_notification():
    """Show macOS notification"""
    try:
        subprocess.run([
            'osascript', '-e',
            'display notification "Starting Login Monitor PRO..." with title "Login Monitor PRO" sound name "default"'
        ], capture_output=True)
    except:
        pass


def run_setup():
    """Run the setup wizard"""
    exe_dir = get_executable_dir()
    setup_path = exe_dir / "Setup"

    if not setup_path.exists():
        # Try script version
        setup_path = exe_dir / "setup_gui.py"
        if setup_path.exists():
            subprocess.run([sys.executable, str(setup_path)])
        else:
            print("Setup not found!")
            return False
    else:
        subprocess.run([str(setup_path)])

    return config_exists()


def install_launch_agents():
    """Install LaunchAgents for auto-start"""
    exe_dir = get_executable_dir()
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    # Screen Watcher LaunchAgent
    screen_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.screen</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_dir}/screen_watcher</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-screen.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-screen.log</string>
</dict>
</plist>"""

    # Command Listener LaunchAgent (replaces Telegram Bot)
    command_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.commands</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_dir}/command_listener</string>
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
</plist>"""

    # Write plists
    screen_plist_path = launch_agents_dir / "com.loginmonitor.screen.plist"
    command_plist_path = launch_agents_dir / "com.loginmonitor.commands.plist"

    with open(screen_plist_path, 'w') as f:
        f.write(screen_plist)
    with open(command_plist_path, 'w') as f:
        f.write(command_plist)

    # Load the agents
    subprocess.run(['launchctl', 'unload', str(screen_plist_path)], capture_output=True)
    subprocess.run(['launchctl', 'unload', str(command_plist_path)], capture_output=True)
    subprocess.run(['launchctl', 'load', str(screen_plist_path)], capture_output=True)
    subprocess.run(['launchctl', 'load', str(command_plist_path)], capture_output=True)

    return True


def show_completion_dialog():
    """Show completion dialog with next steps"""
    script = '''
    display dialog "Login Monitor PRO is now running!

Services Started:
• Screen Watcher (monitors login/unlock)
• Command Listener (for mobile app)

The app will start automatically on boot.

IMPORTANT: Grant these permissions in System Settings:
• Privacy & Security → Location Services
• Privacy & Security → Camera
• Privacy & Security → Microphone" with title "Login Monitor PRO" buttons {"Open Privacy Settings", "Done"} default button "Done" with icon note

    set response to button returned of result
    if response is "Open Privacy Settings" then
        do shell script "open 'x-apple.systempreferences:com.apple.preference.security?Privacy'"
    end if
    '''
    subprocess.run(['osascript', '-e', script], capture_output=True)


def main():
    print("=" * 50)
    print("LOGIN MONITOR PRO - LAUNCHER")
    print("=" * 50)

    # Check if already configured
    if not config_exists():
        print("No configuration found. Starting setup wizard...")
        show_welcome_notification()

        if not run_setup():
            print("Setup cancelled or failed.")
            # Show error dialog
            subprocess.run([
                'osascript', '-e',
                'display alert "Setup Required" message "Login Monitor PRO requires configuration to run. Please run the app again to complete setup." as warning'
            ])
            sys.exit(1)

        print("Configuration saved!")
    else:
        print("Configuration found.")

    # Install LaunchAgents for auto-start
    print("Installing auto-start services...")
    install_launch_agents()

    # Show completion
    print("Services started!")
    show_completion_dialog()

    print("=" * 50)
    print("Login Monitor PRO is now running in background!")
    print("=" * 50)


if __name__ == "__main__":
    main()
