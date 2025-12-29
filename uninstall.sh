#!/bin/bash
#
# CyVigil - Enterprise Security Monitor
# =====================================
# Uninstall: curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/uninstall.sh | bash
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

INSTALL_DIR="$HOME/.login-monitor"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
CLI_PATH="$HOME/.local/bin/loginmonitor"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║           CyVigil - UNINSTALLER                              ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BLUE}[1/6]${NC} Stopping all services..."

# Kill all monitoring processes
PROCESSES=(
    "screen_watcher.py"
    "command_listener.py"
    "pro_monitor.py"
    "app_tracker.py"
    "browser_monitor.py"
    "file_monitor.py"
    "suspicious_detector.py"
    "LoginMonitorCommands"
)

for proc in "${PROCESSES[@]}"; do
    pkill -9 -f "$proc" 2>/dev/null && echo "  Stopped $proc" || true
done

# Stop VNC tunnel processes
pkill -9 -f "websockify.*5900" 2>/dev/null && echo "  Stopped websockify" || true
pkill -9 -f "websockify.*6080" 2>/dev/null || true
pkill -9 -f "cloudflared.*tunnel" 2>/dev/null && echo "  Stopped cloudflared tunnel" || true

echo -e "${GREEN}✓${NC} All processes stopped"

echo -e "${BLUE}[2/6]${NC} Unloading LaunchAgents..."

# All LaunchAgent labels
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
    launchctl unload "$LAUNCH_AGENTS_DIR/${agent}.plist" 2>/dev/null && echo "  Unloaded $agent" || true
done

echo -e "${GREEN}✓${NC} LaunchAgents unloaded"

echo -e "${BLUE}[3/6]${NC} Removing from Login Items..."

# Remove from Login Items
osascript << 'OSEOF' 2>/dev/null || true
tell application "System Events"
    try
        delete login item "LoginMonitorCommands"
    end try
    try
        delete login item "CyVigil Commands"
    end try
end tell
OSEOF

echo -e "${GREEN}✓${NC} Login Items cleaned"

echo -e "${BLUE}[4/6]${NC} Removing LaunchAgent files..."

# Remove all LaunchAgent plist files
for agent in "${LAUNCH_AGENTS[@]}"; do
    rm -f "$LAUNCH_AGENTS_DIR/${agent}.plist" 2>/dev/null
done

# Remove any other login monitor plists (wildcard)
rm -f "$LAUNCH_AGENTS_DIR/com.loginmonitor."*.plist 2>/dev/null || true
rm -f "$LAUNCH_AGENTS_DIR/com.cyvigil."*.plist 2>/dev/null || true

echo -e "${GREEN}✓${NC} LaunchAgent files removed"

echo -e "${BLUE}[5/6]${NC} Removing installation directory..."

# Remove installation directory and all data
if [ -d "$INSTALL_DIR" ]; then
    # Count files for info
    FILE_COUNT=$(find "$INSTALL_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "  Removing $INSTALL_DIR ($FILE_COUNT files)..."
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓${NC} Installation directory removed"
else
    echo -e "${YELLOW}  Installation directory not found (already removed?)${NC}"
fi

# Remove CLI command
if [ -f "$CLI_PATH" ]; then
    rm -f "$CLI_PATH"
    echo -e "${GREEN}✓${NC} CLI command removed"
fi

echo -e "${BLUE}[6/6]${NC} Cleaning up temporary files..."

# Remove log files
rm -f /tmp/loginmonitor-*.log 2>/dev/null
rm -f /tmp/vnc_tunnel_*.txt 2>/dev/null
rm -f /tmp/cyvigil-*.log 2>/dev/null

echo -e "${GREEN}✓${NC} Temporary files cleaned"

# ========================================
# Final Summary
# ========================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              UNINSTALL COMPLETE!                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "CyVigil has been completely removed from this Mac."
echo ""

# Check if Screen Sharing is still enabled
if netstat -an 2>/dev/null | grep -q "\.5900"; then
    echo -e "${YELLOW}Note: Screen Sharing (VNC) is still enabled.${NC}"
    echo "To disable: System Settings → General → Sharing → Screen Sharing OFF"
    echo ""
fi

echo -e "${CYAN}Data Removed:${NC}"
echo "  • All captured screenshots and photos"
echo "  • Activity logs and browser history"
echo "  • Productivity tracking data"
echo "  • Configuration and credentials"
echo "  • CLI command (loginmonitor)"
echo ""

# Optional: Remove from Supabase
if [ -f "/tmp/cyvigil_device_id.txt" ]; then
    echo -e "${YELLOW}Note: Device may still appear in dashboard until deactivated.${NC}"
    echo ""
fi

echo -e "${CYAN}To reinstall:${NC}"
echo "  curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/install.sh | bash"
echo ""
echo -e "${GREEN}Thank you for using CyVigil!${NC}"
echo ""
