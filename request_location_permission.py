#!/usr/bin/env python3
"""
Location Permission Helper for Login Monitor PRO

Run this script ONCE after installation to grant location permission.
This script must be run interactively from Terminal so that:
1. macOS can show the permission dialog
2. Your Terminal/Python gets Location Services permission

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
    print("\n" + "=" * 60)
    print("  LOGIN MONITOR PRO - Location Permission Setup")
    print("=" * 60 + "\n")

    if platform.system() != "Darwin":
        print("This script is only for macOS.")
        return False

    # Show which Python we're using
    current_python = sys.executable
    config_python = get_config_python()

    print(f"[INFO] Running with: {current_python}")

    if config_python and os.path.realpath(current_python) != os.path.realpath(config_python):
        print(f"[WARNING] Config uses different Python: {config_python}")
        print(f"[TIP] For best results, run:")
        print(f"      {config_python} {__file__}")
        print("")

    # Check if CoreLocation is available
    try:
        import objc
        from Foundation import NSObject, NSRunLoop, NSDate
        from CoreLocation import (
            CLLocationManager,
            kCLLocationAccuracyBest,
        )
        print("[OK] CoreLocation framework available")
    except ImportError as e:
        print(f"[ERROR] CoreLocation framework not installed!")
        print(f"        {e}")
        print(f"Run: {current_python} -m pip install pyobjc-framework-CoreLocation")
        return False

    # Check if Location Services is enabled system-wide
    if not CLLocationManager.locationServicesEnabled():
        print("\n[ERROR] Location Services is disabled system-wide!")
        print("To enable:")
        print("  1. Open System Settings")
        print("  2. Go to Privacy & Security > Location Services")
        print("  3. Toggle ON at the top")
        return False

    print("[OK] Location Services: Enabled")

    # Create delegate class for receiving callbacks
    class LocationDelegate(NSObject):
        def init(self):
            self = objc.super(LocationDelegate, self).init()
            if self is None:
                return None
            self.location = None
            self.error = None
            self.done = False
            self.auth_status = None
            return self

        def locationManager_didUpdateLocations_(self, manager, locations):
            if locations and len(locations) > 0:
                self.location = locations[-1]
                lat = self.location.coordinate().latitude
                lon = self.location.coordinate().longitude
                acc = self.location.horizontalAccuracy()
                print(f"\n[SUCCESS] GPS Location received!")
                print(f"  Latitude:  {lat:.6f}")
                print(f"  Longitude: {lon:.6f}")
                print(f"  Accuracy:  {acc:.1f} meters")
                print(f"  Maps: https://www.google.com/maps?q={lat},{lon}")
            self.done = True

        def locationManager_didFailWithError_(self, manager, error):
            self.error = error
            print(f"\n[ERROR] Location error: {error.localizedDescription()}")
            self.done = True

        def locationManagerDidChangeAuthorization_(self, manager):
            status = manager.authorizationStatus()
            self.auth_status = status
            status_names = {
                0: "Not Determined",
                1: "Restricted",
                2: "Denied",
                3: "Authorized Always",
                4: "Authorized When In Use"
            }
            print(f"[INFO] Authorization: {status_names.get(status, 'Unknown')}")

            if status in [3, 4]:  # Authorized
                print("[OK] Permission granted! Getting location...")
                manager.startUpdatingLocation()
            elif status == 2:  # Denied
                print("\n[ERROR] Location access was DENIED!")
                print("\nTo fix:")
                print("  1. Open System Settings > Privacy & Security > Location Services")
                print("  2. Scroll down and find 'Python' or 'Terminal'")
                print("  3. Toggle it ON")
                print("  4. Run this script again")
                self.done = True

    # Create manager and delegate
    manager = CLLocationManager.alloc().init()
    delegate = LocationDelegate.alloc().init()
    manager.setDelegate_(delegate)
    manager.setDesiredAccuracy_(kCLLocationAccuracyBest)

    status = manager.authorizationStatus()
    status_names = {0: "Not Determined", 1: "Restricted", 2: "Denied", 3: "Authorized Always", 4: "Authorized When In Use"}

    print(f"[INFO] Current status: {status_names.get(status, 'Unknown')}")

    if status == 0:  # Not Determined
        print("\n[INFO] Requesting location permission...")
        print("       A popup should appear - click 'Allow'!")
        print("")
        print("       If no popup appears, manually add Python:")
        print("       System Settings > Privacy & Security > Location Services")
        print("       Click '+' and add your Python or Terminal app")
        print("")

        # Request authorization - this triggers the popup
        manager.requestWhenInUseAuthorization()
        # Also try always authorization
        try:
            manager.requestAlwaysAuthorization()
        except:
            pass

    elif status in [3, 4]:  # Already authorized
        print("[OK] Already authorized! Testing location...")
        manager.startUpdatingLocation()

    elif status == 2:  # Denied
        print("\n[ERROR] Location access was previously DENIED!")
        print("\nTo fix:")
        print("  1. Open System Settings > Privacy & Security > Location Services")
        print("  2. Scroll down and find 'Python' or 'Terminal'")
        print("  3. Toggle it ON (or remove and re-add)")
        print("  4. Run this script again")
        return False

    elif status == 1:  # Restricted
        print("\n[ERROR] Location access is RESTRICTED (parental controls?)")
        return False

    # Run the event loop to receive callbacks
    print("\n[INFO] Waiting for location (max 30 seconds)...")

    timeout = 30
    start = time.time()

    while not delegate.done and (time.time() - start) < timeout:
        # Process events - this is CRITICAL for receiving callbacks
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.5)
        )

    if not delegate.done:
        print("\n[WARNING] Timeout waiting for location.")
        print("          This might mean permission wasn't granted.")
        print("\nManual steps:")
        print("  1. Open System Settings > Privacy & Security > Location Services")
        print("  2. Scroll down and find 'Terminal' or 'Python'")
        print("  3. Toggle it ON")
        print("  4. Run this script again")

    manager.stopUpdatingLocation()

    if delegate.location:
        print("\n[SUCCESS] Location permission is working!")
        print("          Login Monitor will now use GPS location.")
        return True

    return False


if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("Location setup complete! GPS tracking is now enabled.")
    else:
        print("Location setup incomplete. See instructions above.")
    print("=" * 60 + "\n")
    sys.exit(0 if success else 1)
