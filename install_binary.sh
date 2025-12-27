#!/bin/bash
# Login Monitor PRO - Binary Installation Script
# This script installs the compiled app bundle and sets up LaunchAgents

set -e

APP_NAME="LoginMonitorPRO.app"
DIST_DIR="$(dirname "$0")/dist"
INSTALL_DIR="/Applications"
DATA_DIR="$HOME/.login-monitor"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "=============================================="
echo "  Login Monitor PRO - Installation"
echo "=============================================="
echo ""

# Check if app bundle exists
if [ ! -d "$DIST_DIR/$APP_NAME" ]; then
    echo "ERROR: $APP_NAME not found in $DIST_DIR"
    echo "Please run 'pyinstaller login_monitor.spec' first."
    exit 1
fi

# 1. Stop existing services if running
echo "[1/6] Stopping existing services..."
launchctl unload "$LAUNCH_AGENTS/com.loginmonitor.screen.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS/com.loginmonitor.telegram.plist" 2>/dev/null || true
pkill -f "LoginMonitorPRO" 2>/dev/null || true
echo "      Done."

# 2. Copy app bundle to Applications
echo "[2/6] Installing app to $INSTALL_DIR..."
rm -rf "$INSTALL_DIR/$APP_NAME"
cp -R "$DIST_DIR/$APP_NAME" "$INSTALL_DIR/"
echo "      Installed: $INSTALL_DIR/$APP_NAME"

# 3. Create data directories
echo "[3/6] Creating data directories..."
mkdir -p "$DATA_DIR"/{events,captured_images,captured_audio,known_faces,activity_logs,activity_screenshots}
echo "      Created: $DATA_DIR"

# 4. Copy config if exists and not already present in data dir
if [ -f "$(dirname "$0")/config.json" ] && [ ! -f "$DATA_DIR/config.json" ]; then
    echo "[4/6] Copying configuration..."
    cp "$(dirname "$0")/config.json" "$DATA_DIR/"
    chmod 600 "$DATA_DIR/config.json"
    echo "      Copied: config.json"
else
    echo "[4/6] Configuration already exists or not found, skipping..."
fi

# 5. Install LaunchAgents
echo "[5/6] Installing LaunchAgents..."
mkdir -p "$LAUNCH_AGENTS"

# Screen Watcher LaunchAgent
cat > "$LAUNCH_AGENTS/com.loginmonitor.screen.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.screen</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/LoginMonitorPRO.app/Contents/MacOS/screen_watcher</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-screen.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-screen.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLIST

# Telegram Bot LaunchAgent
cat > "$LAUNCH_AGENTS/com.loginmonitor.telegram.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.telegram</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/LoginMonitorPRO.app/Contents/MacOS/telegram_bot</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-telegram.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-telegram.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLIST

echo "      Created LaunchAgents"

# 6. Load services
echo "[6/6] Starting services..."
launchctl load "$LAUNCH_AGENTS/com.loginmonitor.screen.plist"
launchctl load "$LAUNCH_AGENTS/com.loginmonitor.telegram.plist"
echo "      Services started"

echo ""
echo "=============================================="
echo "  Installation Complete!"
echo "=============================================="
echo ""
echo "App installed to: $INSTALL_DIR/$APP_NAME"
echo "Data directory:   $DATA_DIR"
echo ""
echo "Services running:"
echo "  - Screen Watcher (com.loginmonitor.screen)"
echo "  - Telegram Bot (com.loginmonitor.telegram)"
echo ""
echo "View logs:"
echo "  tail -f /tmp/loginmonitor-screen.log"
echo "  tail -f /tmp/loginmonitor-telegram.log"
echo ""
echo "=============================================="
echo "  IMPORTANT: Grant Permissions!"
echo "=============================================="
echo ""
echo "Go to System Settings > Privacy & Security and allow:"
echo "  - Camera: LoginMonitorPRO"
echo "  - Location Services: LoginMonitorPRO"
echo "  - Microphone: LoginMonitorPRO (for audio recording)"
echo "  - Accessibility: LoginMonitorPRO (for activity monitoring)"
echo "  - Screen Recording: LoginMonitorPRO (for screenshots)"
echo ""
