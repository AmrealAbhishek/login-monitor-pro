#!/usr/bin/env python3
"""
Screen Recording Permission Helper for Login Monitor PRO

Run this script ONCE after installation to verify/grant screen recording permission.
This script must be run interactively from Terminal so that:
1. macOS can show the permission dialog if needed
2. Your Terminal app gets the Screen Recording permission

Usage:
    python3 request_screen_permission.py
"""

import os
import sys
import time
import subprocess
import tempfile
from pathlib import Path

def get_screenshot_size():
    """Take a test screenshot and return file size"""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name

    try:
        # Use screencapture
        result = subprocess.run(
            ["/usr/sbin/screencapture", "-x", temp_path],
            capture_output=True,
            timeout=10
        )

        if os.path.exists(temp_path):
            size = os.path.getsize(temp_path)
            os.unlink(temp_path)
            return size
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    return 0


def check_screen_recording_permission():
    """
    Check if screen recording permission is likely granted.

    macOS doesn't provide a direct API to check, so we use heuristics:
    - If screenshot captures actual content, file size is usually > 100KB
    - If only wallpaper is captured (no permission), file size is usually < 50KB
    - This varies by screen resolution and content
    """
    try:
        import Quartz
        from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID

        # Try to get window list - this requires screen recording permission
        window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

        if window_list is None:
            return False

        # Check if we can see window names (requires permission)
        for window in window_list:
            owner_name = window.get('kCGWindowOwnerName', '')
            window_name = window.get('kCGWindowName', '')
            # If we can see any non-system window names, permission is granted
            if owner_name and owner_name not in ['Window Server', 'SystemUIServer']:
                if window_name:  # Can see actual window titles
                    return True

        # Fallback: take a test screenshot and check size
        size = get_screenshot_size()
        return size > 100000  # 100KB threshold

    except Exception as e:
        # Fallback to screenshot test
        size = get_screenshot_size()
        return size > 100000


def get_terminal_app():
    """Detect which terminal app is running this script"""
    term_program = os.environ.get('TERM_PROGRAM', '')

    if 'WarpTerminal' in term_program:
        return 'Warp', '/Applications/Warp.app'
    elif 'Apple_Terminal' in term_program:
        return 'Terminal', '/System/Applications/Utilities/Terminal.app'
    elif 'iTerm' in term_program:
        return 'iTerm2', '/Applications/iTerm.app'
    elif 'vscode' in term_program.lower():
        return 'VS Code', '/Applications/Visual Studio Code.app'
    else:
        return 'Terminal', '/System/Applications/Utilities/Terminal.app'


def main():
    print("\n" + "="*60)
    print("LOGIN MONITOR PRO - Screen Recording Permission Setup")
    print("="*60 + "\n")

    term_name, term_path = get_terminal_app()
    print(f"[INFO] Detected terminal: {term_name}")

    print("\nChecking screen recording permission...")

    has_permission = check_screen_recording_permission()

    if has_permission:
        print("\n[SUCCESS] Screen Recording permission is GRANTED!")
        print("\nScreenshots will capture actual screen content.")

        # Take a test screenshot to verify
        print("\nTaking test screenshot...")
        test_dir = Path.home() / ".login-monitor" / "captured_images"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "test_screenshot.png"

        result = subprocess.run(
            ["/usr/sbin/screencapture", "-x", str(test_file)],
            capture_output=True,
            timeout=10
        )

        if test_file.exists():
            size = test_file.stat().st_size
            print(f"  Screenshot saved: {test_file}")
            print(f"  File size: {size:,} bytes")

            if size > 100000:
                print(f"\n[OK] Screenshot looks good (capturing actual content)")
            else:
                print(f"\n[WARNING] Screenshot may only contain wallpaper")
                print("Please check the file manually to verify.")

        return True

    # Permission not granted - guide user
    print("\n[WARNING] Screen Recording permission NOT detected!")
    print("\nWithout this permission, screenshots will only show your wallpaper,")
    print("not the actual windows and content on screen.")

    print("\n" + "-"*60)
    print("HOW TO FIX:")
    print("-"*60)
    print(f"""
1. Open System Settings
2. Go to: Privacy & Security > Screen Recording
3. Click the lock icon and authenticate
4. Click the '+' button to add an application
5. Add: {term_path}
6. Make sure the toggle is ON for {term_name}
7. RESTART your Terminal app
8. Run this script again to verify

NOTE: You need to grant permission to your TERMINAL app
      ({term_name}), not to Python directly.
""")

    # Try to open System Settings
    print("Opening System Settings...")
    subprocess.run([
        "open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
    ], capture_output=True)

    print("\n" + "-"*60)
    print("WAITING FOR PERMISSION...")
    print("-"*60)
    print("\nAfter granting permission and restarting Terminal,")
    print("this script will automatically detect the change.")
    print("\nPress Ctrl+C to exit.\n")

    # Wait and check periodically
    check_count = 0
    try:
        while True:
            check_count += 1
            time.sleep(5)

            print(f"Checking... (attempt {check_count})", end="")

            if check_screen_recording_permission():
                print(" GRANTED!")
                print("\n[SUCCESS] Screen Recording permission is now active!")

                # Restart command_listener to apply permission
                print("\nRestarting command_listener to apply new permission...")
                subprocess.run(["pkill", "-f", "command_listener.py"], capture_output=True)
                time.sleep(1)

                install_dir = Path.home() / ".login-monitor"
                subprocess.Popen(
                    ["python3", str(install_dir / "command_listener.py")],
                    cwd=str(install_dir),
                    stdout=open("/tmp/loginmonitor-commands.log", "a"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )

                print("[OK] command_listener restarted with Screen Recording permission")
                return True
            else:
                print(" not yet")

    except KeyboardInterrupt:
        print("\n\nExiting...")
        print("Run 'loginmonitor screen' or this script again after granting permission.")
        return False


if __name__ == "__main__":
    success = main()
    print("\n" + "="*60)
    if success:
        print("Screen Recording setup complete!")
        print("\nScreenshots should now work correctly.")
        print("Test with: 'loginmonitor test' or send Screenshot from Flutter app")
    else:
        print("Screen Recording setup incomplete.")
        print("Please follow the instructions above to grant permission.")
    print("="*60 + "\n")
    sys.exit(0 if success else 1)
