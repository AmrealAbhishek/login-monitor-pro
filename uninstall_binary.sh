#!/bin/bash
# Login Monitor PRO - Uninstall Script

set -e

APP_NAME="LoginMonitorPRO.app"
INSTALL_DIR="/Applications"
DATA_DIR="$HOME/.login-monitor"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "=============================================="
echo "  Login Monitor PRO - Uninstall"
echo "=============================================="
echo ""

# 1. Stop services
echo "[1/3] Stopping services..."
launchctl unload "$LAUNCH_AGENTS/com.loginmonitor.screen.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS/com.loginmonitor.telegram.plist" 2>/dev/null || true
pkill -f "LoginMonitorPRO" 2>/dev/null || true
echo "      Done."

# 2. Remove LaunchAgents
echo "[2/3] Removing LaunchAgents..."
rm -f "$LAUNCH_AGENTS/com.loginmonitor.screen.plist"
rm -f "$LAUNCH_AGENTS/com.loginmonitor.telegram.plist"
echo "      Done."

# 3. Remove app bundle
echo "[3/3] Removing application..."
rm -rf "$INSTALL_DIR/$APP_NAME"
echo "      Done."

echo ""
echo "=============================================="
echo "  Uninstall Complete!"
echo "=============================================="
echo ""
echo "Note: Data directory preserved at: $DATA_DIR"
echo "To remove all data, run: rm -rf $DATA_DIR"
echo ""
