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
echo -e "${BLUE}[1/5]${NC} Stopping services..."

# Kill all related processes
pkill -9 -f "screen_watcher.py" 2>/dev/null || true
pkill -9 -f "command_listener.py" 2>/dev/null || true
pkill -9 -f "pro_monitor.py" 2>/dev/null || true
pkill -9 -f "LoginMonitorCommands" 2>/dev/null || true

echo -e "${GREEN}✓ Processes stopped${NC}"

echo -e "${BLUE}[2/5]${NC} Unloading LaunchAgents..."

# Unload all LaunchAgents
launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.screen.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.commands.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.telegram.plist" 2>/dev/null || true

echo -e "${GREEN}✓ LaunchAgents unloaded${NC}"

echo -e "${BLUE}[3/5]${NC} Removing from Login Items..."

# Remove from Login Items (suppress errors - may fail without Automation permission)
osascript << 'OSEOF' 2>/dev/null || true
tell application "System Events"
    try
        delete login item "LoginMonitorCommands"
    end try
end tell
OSEOF

echo -e "${GREEN}✓ Login Items cleaned${NC}"

echo -e "${BLUE}[4/5]${NC} Removing files..."

# Remove LaunchAgent plist files
rm -f "$LAUNCH_AGENTS_DIR/com.loginmonitor.screen.plist"
rm -f "$LAUNCH_AGENTS_DIR/com.loginmonitor.commands.plist"
rm -f "$LAUNCH_AGENTS_DIR/com.loginmonitor.telegram.plist"

# Remove installation directory
rm -rf "$INSTALL_DIR"

# Remove CLI command
rm -f "$CLI_PATH"

echo -e "${GREEN}✓ Files removed${NC}"

echo -e "${BLUE}[5/5]${NC} Cleaning up..."

# Remove log files
rm -f /tmp/loginmonitor-*.log

echo -e "${GREEN}✓ Cleanup complete${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           UNINSTALL COMPLETE!                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Login Monitor PRO has been completely removed from this Mac."
echo ""
echo -e "${YELLOW}Note: To reinstall, run:${NC}"
echo "  curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/install.sh | bash"
echo ""
