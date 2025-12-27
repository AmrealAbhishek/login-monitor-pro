# Login Monitor PRO - Mobile App

Flutter companion app for Login Monitor PRO Mac monitoring.

## Setup Instructions

### 1. Install Flutter

```bash
# macOS
brew install flutter

# Or download from https://flutter.dev/docs/get-started/install
```

### 2. Create Flutter Project

Since this directory contains the Dart source files, you need to initialize Flutter:

```bash
cd login_monitor_app
flutter create . --project-name login_monitor_app --org com.loginmonitor
```

### 3. Install Dependencies

```bash
flutter pub get
```

### 4. Configure Google Maps (for location display)

1. Get a Google Maps API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Enable "Maps SDK for Android" and "Maps SDK for iOS"

**Android:** Add to `android/app/src/main/AndroidManifest.xml`:
```xml
<meta-data android:name="com.google.android.geo.API_KEY"
           android:value="YOUR_API_KEY"/>
```

**iOS:** Add to `ios/Runner/AppDelegate.swift`:
```swift
GMSServices.provideAPIKey("YOUR_API_KEY")
```

### 5. Run the App

```bash
# Debug mode
flutter run

# Build release APK
flutter build apk --release

# Build release App Bundle (for Play Store)
flutter build appbundle --release
```

## Features

- **Real-time Notifications**: Receive instant alerts when someone logs in/unlocks your Mac
- **Photo Capture**: View photos captured during login events
- **Location Tracking**: See the location where events occurred
- **Remote Commands**: Send commands to your Mac:
  - Take Photo
  - Get Location
  - Capture Screenshot
  - Record Audio
  - Sound Alarm
  - Lock Screen
  - Show Message
  - Get Device Status
- **Face Recognition**: Get alerts when unknown faces are detected
- **Audio Playback**: Listen to recorded audio from events

## Architecture

```
lib/
├── main.dart              # App entry point
├── models/
│   ├── device.dart        # Device model
│   ├── event.dart         # Event model
│   └── command.dart       # Command model
├── services/
│   └── supabase_service.dart  # Supabase API client
├── screens/
│   ├── splash_screen.dart
│   ├── login_screen.dart
│   ├── pairing_screen.dart
│   ├── home_screen.dart
│   ├── events_screen.dart
│   ├── event_detail_screen.dart
│   ├── commands_screen.dart
│   └── settings_screen.dart
└── widgets/
    ├── event_card.dart
    └── command_button.dart
```

## Supabase Configuration

The app is pre-configured with Supabase credentials in `lib/services/supabase_service.dart`.

If you need to change the Supabase project:
1. Update `supabaseUrl` and `supabaseAnonKey` in `supabase_service.dart`
2. Make sure the database schema matches (see `../supabase_schema.sql`)

## Pairing with Mac

1. Install Login Monitor PRO on your Mac
2. Run the app and complete the setup wizard
3. A 6-digit pairing code will be displayed
4. Open this mobile app and enter the pairing code
5. Done! You'll now receive notifications from your Mac

## Permissions Required

- **Internet**: For Supabase communication
- **Storage**: For caching photos
- **Notifications**: For push notifications (optional)
