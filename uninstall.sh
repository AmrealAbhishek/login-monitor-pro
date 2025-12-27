#!/bin/bash
#
# Login Monitor PRO - One-Line Uninstaller
# =========================================
# Uninstall: curl -fsSL https://your-domain.com/uninstall.sh | bash
# Or:        loginmonitor uninstall
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

echo -e "${YELLOW}This will completely remove Login Monitor PRO.${NC}"
read -p "Are you sure? [y/N]: " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}[1/4]${NC} Stopping services..."

# Unload LaunchAgents
launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.screen.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.commands.plist" 2>/dev/null || true

# Kill processes
pkill -f "screen_watcher.py" 2>/dev/null || true
pkill -f "command_listener.py" 2>/dev/null || true

echo -e "${GREEN}✓ Services stopped${NC}"

echo -e "${BLUE}[2/4]${NC} Removing LaunchAgents..."

rm -f "$LAUNCH_AGENTS_DIR/com.loginmonitor.screen.plist"
rm -f "$LAUNCH_AGENTS_DIR/com.loginmonitor.commands.plist"

echo -e "${GREEN}✓ LaunchAgents removed${NC}"

echo -e "${BLUE}[3/4]${NC} Removing files..."

# Backup option
if [[ -d "$INSTALL_DIR/events" ]] || [[ -d "$INSTALL_DIR/captured_images" ]]; then
    read -p "Keep captured photos and events? [y/N]: " KEEP_DATA
    if [[ "$KEEP_DATA" =~ ^[Yy]$ ]]; then
        BACKUP_DIR="$HOME/Desktop/LoginMonitor-Backup-$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp -r "$INSTALL_DIR/events" "$BACKUP_DIR/" 2>/dev/null || true
        cp -r "$INSTALL_DIR/captured_images" "$BACKUP_DIR/" 2>/dev/null || true
        cp -r "$INSTALL_DIR/captured_audio" "$BACKUP_DIR/" 2>/dev/null || true
        echo -e "${GREEN}✓ Data backed up to $BACKUP_DIR${NC}"
    fi
fi

rm -rf "$INSTALL_DIR"
rm -f "$CLI_PATH"

echo -e "${GREEN}✓ Files removed${NC}"

echo -e "${BLUE}[4/4]${NC} Cleaning up..."

rm -f /tmp/loginmonitor-*.log

echo -e "${GREEN}✓ Cleanup complete${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           UNINSTALL COMPLETE!                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Login Monitor PRO has been removed."
