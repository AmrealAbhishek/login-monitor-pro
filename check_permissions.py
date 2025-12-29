#!/usr/bin/env python3
"""
Login Monitor PRO - Permission Checker
Shows status of all required permissions and how to enable them.
"""

import subprocess
import os
import sys

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'

def check_screen_sharing():
    """Check if Screen Sharing (VNC) is enabled."""
    result = subprocess.run(["netstat", "-an"], capture_output=True, text=True)
    return ".5900" in result.stdout

def check_screen_recording():
    """Check if Screen Recording permission is granted (approximation)."""
    # Try to take a screenshot - if it fails or returns tiny image, no permission
    try:
        from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
        windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
        # If we can get window info, we likely have permission
        return len(windows) > 0
    except:
        return False

def check_location():
    """Check if Location Services might be available."""
    try:
        from CoreLocation import CLLocationManager
        manager = CLLocationManager.alloc().init()
        status = CLLocationManager.authorizationStatus()
        # 3 = authorized, 4 = authorized always
        return status in [3, 4]
    except:
        return False

def check_camera():
    """Check if camera access might be available."""
    # Check if imagesnap works
    result = subprocess.run(
        ["/opt/homebrew/bin/imagesnap", "-l"],
        capture_output=True, text=True, timeout=5
    )
    return "Video Devices" in result.stdout or "FaceTime" in result.stdout

def check_full_disk_access():
    """Check for Full Disk Access (needed for some operations)."""
    # Try to read a protected file
    test_paths = [
        os.path.expanduser("~/Library/Safari/History.db"),
        os.path.expanduser("~/Library/Mail"),
    ]
    for path in test_paths:
        if os.path.exists(path):
            try:
                os.listdir(path) if os.path.isdir(path) else open(path, 'rb').close()
                return True
            except PermissionError:
                return False
    return True  # Assume OK if test files don't exist

def print_status(name, enabled, how_to_enable):
    """Print permission status."""
    if enabled:
        print(f"  {GREEN}✓{NC} {name}: {GREEN}Enabled{NC}")
    else:
        print(f"  {RED}✗{NC} {name}: {RED}Not Enabled{NC}")
        print(f"    {YELLOW}→ {how_to_enable}{NC}")
    return enabled

def main():
    print(f"\n{CYAN}{'='*60}{NC}")
    print(f"{CYAN}  LOGIN MONITOR PRO - PERMISSION CHECK{NC}")
    print(f"{CYAN}{'='*60}{NC}\n")

    all_ok = True

    # 1. Screen Sharing (VNC)
    print(f"{CYAN}Remote Desktop (VNC):{NC}")
    if not print_status(
        "Screen Sharing",
        check_screen_sharing(),
        "System Settings → General → Sharing → Screen Sharing ON"
    ):
        all_ok = False
        print(f"    {CYAN}Run: loginmonitor vnc{NC}")
    print()

    # 2. Screen Recording
    print(f"{CYAN}Screenshots:{NC}")
    if not print_status(
        "Screen Recording",
        check_screen_recording(),
        "System Settings → Privacy & Security → Screen Recording → Add Python"
    ):
        all_ok = False
        print(f"    {CYAN}Run: loginmonitor screen{NC}")
    print()

    # 3. Location
    print(f"{CYAN}GPS Location:{NC}")
    if not print_status(
        "Location Services",
        check_location(),
        "System Settings → Privacy & Security → Location Services → Python ON"
    ):
        all_ok = False
        print(f"    {CYAN}Run: loginmonitor location{NC}")
    print()

    # 4. Camera
    print(f"{CYAN}Camera (Photo Capture):{NC}")
    try:
        cam_ok = check_camera()
    except:
        cam_ok = False
    if not print_status(
        "Camera Access",
        cam_ok,
        "Permission requested automatically on first use"
    ):
        print(f"    {CYAN}Or: System Settings → Privacy & Security → Camera{NC}")
    print()

    # Summary
    print(f"{CYAN}{'='*60}{NC}")
    if all_ok:
        print(f"{GREEN}All permissions are configured correctly!{NC}")
    else:
        print(f"{YELLOW}Some permissions need to be enabled.{NC}")
        print(f"{YELLOW}Follow the instructions above for each missing permission.{NC}")
    print(f"{CYAN}{'='*60}{NC}\n")

    # Quick commands
    print(f"{CYAN}Quick Commands:{NC}")
    print(f"  loginmonitor vnc       - Setup Remote Desktop")
    print(f"  loginmonitor screen    - Setup Screen Recording")
    print(f"  loginmonitor location  - Setup GPS Location")
    print(f"  loginmonitor status    - Check service status")
    print()

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
