#!/usr/bin/env python3
"""
Location Permission Request Helper for Login Monitor PRO

Run this script ONCE after installation to grant location permission.
This script must be run interactively (not as a background service)
so that macOS can show the permission dialog.

IMPORTANT: Run this with the SAME Python that command_listener uses!

Usage:
    loginmonitor location
    OR
    python3 request_location_permission.py
"""

import sys
import os
import time
import platform
import json
from pathlib import Path


def get_config_python():
    """Get the Python path from config.json"""
    config_path = Path.home() / ".login-monitor" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                return config.get("python_path", "")
        except:
            pass
    return ""


def main():
    print("\n" + "="*60)
    print("LOGIN MONITOR PRO - Location Permission Setup")
    print("="*60 + "\n")

    if platform.system() != "Darwin":
        print("This script is only for macOS.")
        return False

    # Show which Python we're using
    current_python = sys.executable
    config_python = get_config_python()

    print(f"[INFO] Running with: {current_python}")

    if config_python and current_python != config_python:
        print(f"[WARNING] Config uses different Python: {config_python}")
        print(f"[TIP] For best results, run:")
        print(f"      {config_python} {__file__}")
        print("")

    # Check if CoreLocation is available
    try:
        import CoreLocation
        print("[OK] CoreLocation framework available")
    except ImportError:
        print("[ERROR] CoreLocation framework not installed!")
        print(f"Run: {current_python} -m pip install pyobjc-framework-CoreLocation")
        return False

    print("\nRequesting location permission...")
    print("A system dialog should appear asking for location access.")
    print("Please click 'Allow' when prompted.")
    print("\nNOTE: If no dialog appears, you may need to:")
    print("  1. Go to System Settings > Privacy & Security > Location Services")
    print("  2. Find 'Python' in the list and enable it")
    print("")

    try:
        # Create location manager
        manager = CoreLocation.CLLocationManager.alloc().init()

        # Check current authorization status
        status = manager.authorizationStatus()
        status_names = {
            0: "Not Determined",
            1: "Restricted",
            2: "Denied",
            3: "Authorized Always",
            4: "Authorized When In Use"
        }

        print(f"Current status: {status_names.get(status, 'Unknown')} ({status})")

        if status == 2:  # Denied
            print("\n[WARNING] Location access is DENIED!")
            print("\nTo fix this:")
            print("1. Open System Settings")
            print("2. Go to Privacy & Security > Location Services")
            print("3. Find 'Python' or 'Terminal' and enable it")
            print("4. Run this script again")
            return False

        if status == 0:  # Not determined - request permission
            print("\nRequesting authorization...")
            manager.requestWhenInUseAuthorization()

            # Wait for user response (up to 30 seconds)
            for i in range(30):
                time.sleep(1)
                new_status = manager.authorizationStatus()
                if new_status != 0:
                    status = new_status
                    print(f"\nNew status: {status_names.get(status, 'Unknown')} ({status})")
                    break
                print(f"Waiting for response... ({i+1}s)")

        if status >= 3:  # Authorized
            print("\n[SUCCESS] Location permission GRANTED!")

            # Try to get actual location
            print("\nTesting location acquisition...")
            manager.startUpdatingLocation()

            for i in range(15):
                time.sleep(1)
                location = manager.location()
                if location:
                    lat = location.coordinate().latitude
                    lon = location.coordinate().longitude
                    accuracy = location.horizontalAccuracy()

                    if accuracy > 0 and accuracy < 5000:
                        print(f"\n[SUCCESS] Location acquired!")
                        print(f"  Latitude:  {lat:.6f}")
                        print(f"  Longitude: {lon:.6f}")
                        print(f"  Accuracy:  {accuracy:.1f} meters")
                        print(f"  Maps: https://www.google.com/maps?q={lat},{lon}")
                        manager.stopUpdatingLocation()
                        return True
                print(f"Acquiring GPS... ({i+1}s)")

            manager.stopUpdatingLocation()
            print("\n[WARNING] Could not acquire location, but permission is granted.")
            print("Location should work when GPS signal is available.")
            return True
        else:
            print("\n[ERROR] Location permission not granted!")
            print("\nPlease manually enable in:")
            print("System Settings > Privacy & Security > Location Services")
            return False

    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "="*60)
    if success:
        print("Location setup complete! You can close this window.")
    else:
        print("Location setup failed. See instructions above.")
    print("="*60 + "\n")
    sys.exit(0 if success else 1)
