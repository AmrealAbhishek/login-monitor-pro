#!/usr/bin/env python3
"""
Location Permission Request Helper for Login Monitor PRO

Run this script ONCE after installation to grant location permission.
This script must be run interactively (not as a background service)
so that macOS can show the permission dialog.

Usage:
    python3 request_location_permission.py
"""

import sys
import time
import platform

def main():
    print("\n" + "="*60)
    print("LOGIN MONITOR PRO - Location Permission Setup")
    print("="*60 + "\n")

    if platform.system() != "Darwin":
        print("This script is only for macOS.")
        return False

    # Check if CoreLocation is available
    try:
        import CoreLocation
        print("[OK] CoreLocation framework available")
    except ImportError:
        print("[ERROR] CoreLocation framework not installed!")
        print("Run: pip3 install pyobjc-framework-CoreLocation")
        return False

    print("\nRequesting location permission...")
    print("A system dialog should appear asking for location access.")
    print("Please click 'Allow' when prompted.\n")

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
