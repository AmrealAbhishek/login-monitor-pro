#!/usr/bin/env python3
"""
Location Permission Helper for Login Monitor PRO
Run this once to grant location permission to Python.
"""

import time
import objc
from Foundation import NSObject, NSRunLoop, NSDate
from CoreLocation import (
    CLLocationManager,
    kCLLocationAccuracyBest,
    kCLAuthorizationStatusNotDetermined,
    kCLAuthorizationStatusAuthorizedAlways,
    kCLAuthorizationStatusDenied,
    kCLAuthorizationStatusRestricted
)

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
            print(f"\n✅ GPS Location received!")
            print(f"   Latitude:  {self.location.coordinate().latitude}")
            print(f"   Longitude: {self.location.coordinate().longitude}")
            print(f"   Accuracy:  {self.location.horizontalAccuracy()}m")
        self.done = True

    def locationManager_didFailWithError_(self, manager, error):
        self.error = error
        print(f"\n❌ Location error: {error.localizedDescription()}")
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
        print(f"📍 Authorization changed: {status_names.get(status, 'Unknown')}")

        if status in [3, 4]:  # Authorized
            print("   Starting location updates...")
            manager.startUpdatingLocation()
        elif status == 2:  # Denied
            print("\n❌ Location access denied!")
            print("   Please enable in: System Settings > Privacy & Security > Location Services")
            print("   Find 'Python' or 'Terminal' and toggle ON")
            self.done = True


def main():
    print("=" * 60)
    print("  LOGIN MONITOR PRO - Location Permission Setup")
    print("=" * 60)
    print()

    if not CLLocationManager.locationServicesEnabled():
        print("❌ Location Services is disabled system-wide!")
        print("   Enable in: System Settings > Privacy & Security > Location Services")
        return

    print("📍 Location Services: Enabled")

    # Create manager and delegate
    manager = CLLocationManager.alloc().init()
    delegate = LocationDelegate.alloc().init()
    manager.setDelegate_(delegate)
    manager.setDesiredAccuracy_(kCLLocationAccuracyBest)

    status = manager.authorizationStatus()

    if status == kCLAuthorizationStatusNotDetermined:
        print("📍 Requesting location permission...")
        print()
        print("⚠️  A popup should appear asking for location access.")
        print("   If no popup appears, manually add Python to Location Services:")
        print("   System Settings > Privacy & Security > Location Services")
        print("   Click '+' and add: /usr/bin/python3")
        print()

        # Request authorization - this should trigger a popup
        manager.requestWhenInUseAuthorization()
        # Also try always authorization
        manager.requestAlwaysAuthorization()

    elif status in [3, 4]:  # Already authorized
        print("✅ Location already authorized! Testing...")
        manager.startUpdatingLocation()

    elif status == 2:  # Denied
        print("❌ Location access was denied!")
        print("   To fix: System Settings > Privacy & Security > Location Services")
        print("   Find 'Python' or 'Terminal' and toggle ON")
        return

    elif status == 1:  # Restricted
        print("❌ Location access is restricted (parental controls?)")
        return

    # Run the event loop to receive callbacks
    print("\n⏳ Waiting for location (max 30 seconds)...")

    timeout = 30
    start = time.time()

    while not delegate.done and (time.time() - start) < timeout:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.5)
        )

    if not delegate.done:
        print("\n⏱️  Timeout waiting for location.")
        print("   This might mean permission wasn't granted.")
        print("\n   Manual steps:")
        print("   1. Open: System Settings > Privacy & Security > Location Services")
        print("   2. Scroll down and find 'Terminal' or 'Python'")
        print("   3. Toggle it ON")
        print("   4. Run this script again")

    manager.stopUpdatingLocation()

    if delegate.location:
        print("\n✅ Location permission is working!")
        print("   Login Monitor will now use GPS location.")

    print()


if __name__ == "__main__":
    main()
