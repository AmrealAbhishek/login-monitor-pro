# Mobile App Guide

Guide to the Login Monitor PRO Flutter mobile app.

---

## Installation

### Android
1. Download APK from releases
2. Enable "Install from unknown sources"
3. Install APK
4. Open app and create account

### Build from Source
```bash
cd login_monitor_app
flutter pub get
flutter build apk
# APK at: build/app/outputs/flutter-apk/app-release.apk
```

---

## Getting Started

### 1. Create Account

1. Open app
2. Tap "Sign Up"
3. Enter email and password
4. Verify email (check inbox)
5. Login with credentials

### 2. Pair Device

1. On Mac: Run `python3 setup.py`
2. Note the 6-digit pairing code
3. In app: Go to "Pair Device"
4. Enter the 6-digit code
5. Device appears in list

---

## App Screens

### Home Screen

Main dashboard with:
- Device selector (dropdown)
- Recent events list
- Quick stats
- Quick command buttons

### Events Screen

View all login/unlock/wake events:
- Filter by event type
- Search events
- Tap for details

### Event Detail Screen

Full event information:
- Photos gallery (swipe through)
- Map with location
- System info (battery, WiFi, IP)
- Face recognition results
- Audio playback

### Commands Screen

Send remote commands:

| Button | Action |
|--------|--------|
| 📷 Photo | Capture webcam photo |
| 📍 Location | Get GPS location |
| 🎙️ Audio | Record audio |
| 🔊 Alarm | Play alarm sound |
| 🔒 Lock | Lock screen |
| 💬 Message | Display message |
| 📊 Status | Get device status |
| 📸 Screenshot | Capture screen |

### Security Screen

View security alerts:
- Threat list with severity
- Failed login attempts
- Unknown face detections
- Tap to acknowledge

### Find My Mac

Locate your device:
- Map with current location
- Address display
- Accuracy indicator
- Google Maps link

### Geofence Screen

Manage geofenced areas:
- View geofences on map
- Create new geofence
- Set radius (meters)
- Configure entry/exit triggers

### Settings Screen

App preferences:
- Notification settings
- Auto-refresh interval
- Clear cache
- Logout

---

## Push Notifications

The app receives instant push notifications for:

| Event | Notification |
|-------|--------------|
| Login | "Login detected on MacBook-Pro" |
| Unlock | "Device unlocked" |
| Security Alert | "⚠️ Unusual login detected" |
| Failed Login | "🚨 3 failed login attempts" |
| Geofence Exit | "Device left Office area" |

### Enable Notifications

1. Allow notifications when prompted
2. Or: Settings → Notifications → Login Monitor → Allow

---

## Quick Actions

### From Event List
- Tap event → View details
- Long press → Quick actions (photo, lock)

### From Device Card
- Tap → Select device
- Tap status → View location

---

## Offline Mode

The app caches data for offline viewing:
- Recent events stored locally
- View events without internet
- Commands queue until online

---

## Theme

The app uses a cyberpunk-style dark theme:
- Dark background
- Cyan/neon accents
- Smooth animations
- Consistent with dashboard

---

## Troubleshooting

### No Push Notifications

1. Check notification permissions
2. Open app → Settings → Refresh Token
3. Check FCM token in Supabase

### Device Not Showing

1. Check Mac is online
2. Verify pairing code correct
3. Re-pair if needed

### Commands Not Working

1. Check Mac is online
2. Verify command_listener running
3. Check Supabase connection

### App Crashes

1. Clear app cache
2. Reinstall app
3. Check for updates

---

## Permissions

The app requires:

| Permission | Purpose |
|------------|---------|
| Internet | Connect to Supabase |
| Notifications | Push alerts |
| Location | Show device on map |

---

## Privacy

- All data encrypted in transit (HTTPS)
- Authentication required
- You only see your own devices
- No data shared with third parties
