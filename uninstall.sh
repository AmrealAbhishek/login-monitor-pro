#!/bin/bash
#
# Login Monitor PRO - One-Line Uninstaller
# =========================================
# Uninstall: curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/uninstall.sh | bash
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/.login-monitor"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
CLI_PATH="$HOME/.local/bin/loginmonitor"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           LOGIN MONITOR PRO - UNINSTALLER                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BLUE}[1/6]${NC} Stopping all services..."

# Kill all related processes
echo "  Stopping monitoring processes..."
pkill -9 -f "screen_watcher.py" 2>/dev/null || true
pkill -9 -f "command_listener.py" 2>/dev/null || true
pkill -9 -f "pro_monitor.py" 2>/dev/null || true
pkill -9 -f "app_tracker.py" 2>/dev/null || true
pkill -9 -f "browser_monitor.py" 2>/dev/null || true
pkill -9 -f "file_monitor.py" 2>/dev/null || true
pkill -9 -f "suspicious_detector.py" 2>/dev/null || true
pkill -9 -f "LoginMonitorCommands" 2>/dev/null || true

# Stop VNC tunnel processes
echo "  Stopping VNC tunnel processes..."
pkill -9 -f "websockify.*5900" 2>/dev/null || true
pkill -9 -f "cloudflared.*tunnel" 2>/dev/null || true

echo -e "${GREEN}✓ All processes stopped${NC}"

echo -e "${BLUE}[2/6]${NC} Unloading LaunchAgents..."

# Unload all LaunchAgents
LAUNCH_AGENTS=(
    "com.loginmonitor.screen"
    "com.loginmonitor.commands"
    "com.loginmonitor.telegram"
    "com.loginmonitor.apptracker"
    "com.loginmonitor.browser"
    "com.loginmonitor.files"
    "com.loginmonitor.suspicious"
)

for agent in "${LAUNCH_AGENTS[@]}"; do
    launchctl unload "$LAUNCH_AGENTS_DIR/${agent}.plist" 2>/dev/null && \
        echo "  Unloaded $agent" || true
done

echo -e "${GREEN}✓ LaunchAgents unloaded${NC}"

echo -e "${BLUE}[3/6]${NC} Removing from Login Items..."

# Remove from Login Items (suppress errors - may fail without Automation permission)
osascript << 'OSEOF' 2>/dev/null || true
tell application "System Events"
    try
        delete login item "LoginMonitorCommands"
    end try
end tell
OSEOF

echo -e "${GREEN}✓ Login Items cleaned${NC}"

echo -e "${BLUE}[4/6]${NC} Removing LaunchAgent files..."

# Remove all LaunchAgent plist files
for agent in "${LAUNCH_AGENTS[@]}"; do
    rm -f "$LAUNCH_AGENTS_DIR/${agent}.plist"
done

# Also remove any legacy or wildcard matches
rm -f "$LAUNCH_AGENTS_DIR/com.loginmonitor."*.plist 2>/dev/null || true

echo -e "${GREEN}✓ LaunchAgent files removed${NC}"

echo -e "${BLUE}[5/6]${NC} Removing installation directory..."

# Remove installation directory and all data
if [ -d "$INSTALL_DIR" ]; then
    echo "  Removing $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓ Installation directory removed${NC}"
else
    echo -e "${YELLOW}  Installation directory not found (already removed?)${NC}"
fi

# Remove CLI command
if [ -f "$CLI_PATH" ]; then
    rm -f "$CLI_PATH"
    echo -e "${GREEN}✓ CLI command removed${NC}"
fi

echo -e "${BLUE}[6/6]${NC} Cleaning up temporary files..."

# Remove log files
rm -f /tmp/loginmonitor-*.log
rm -f /tmp/vnc_tunnel_*.txt 2>/dev/null || true

echo -e "${GREEN}✓ Cleanup complete${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           UNINSTALL COMPLETE!                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Login Monitor PRO has been completely removed from this Mac."
echo ""

# Check if Screen Sharing is still enabled and remind user
if netstat -an 2>/dev/null | grep -q "\.5900"; then
    echo -e "${YELLOW}Note: Screen Sharing (VNC) is still enabled on this Mac.${NC}"
    echo "If you want to disable it:"
    echo "  System Settings → General → Sharing → Screen Sharing OFF"
    echo ""
fi

echo -e "${CYAN}Data removed:${NC}"
echo "  • All captured screenshots and photos"
echo "  • All activity logs and events"
echo "  • Configuration and credentials"
echo "  • CLI command (loginmonitor)"
echo ""
echo -e "${YELLOW}To reinstall, run:${NC}"
echo "  curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/install.sh | bash"
echo ""
