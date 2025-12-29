#!/bin/bash
#
# CyVigil Permission Setup
# ========================
# Guides users through all required macOS permissions
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Get the terminal app name
TERMINAL_APP="$TERM_PROGRAM"
case "$TERMINAL_APP" in
    "WarpTerminal") TERMINAL_NAME="Warp" ;;
    "Apple_Terminal") TERMINAL_NAME="Terminal" ;;
    "iTerm.app") TERMINAL_NAME="iTerm" ;;
    "vscode") TERMINAL_NAME="Visual Studio Code" ;;
    *) TERMINAL_NAME="Terminal" ;;
esac

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CyVigil Permission Setup                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "Your terminal: ${BOLD}$TERMINAL_NAME${NC}"
echo ""

# Function to wait for user
wait_for_user() {
    echo ""
    echo -e "${YELLOW}Press ENTER when done...${NC}"
    read -r < /dev/tty
}

# ============================================
# 1. FULL DISK ACCESS
# ============================================
echo -e "${BOLD}${BLUE}[1/6] Full Disk Access${NC}"
echo -e "Required for: USB monitoring, Browser history, File monitoring"
echo ""
echo -e "${YELLOW}Steps:${NC}"
echo -e "  1. Click ${BOLD}+${NC} button"
echo -e "  2. Navigate to: /Applications → ${BOLD}$TERMINAL_NAME${NC}"
echo -e "  3. Enable the checkbox for ${BOLD}$TERMINAL_NAME${NC}"
echo ""
echo -e "${CYAN}Opening Full Disk Access settings...${NC}"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
wait_for_user

# ============================================
# 2. SCREEN RECORDING
# ============================================
echo -e "${BOLD}${BLUE}[2/6] Screen Recording${NC}"
echo -e "Required for: Screenshots, Screen capture"
echo ""
echo -e "${YELLOW}Steps:${NC}"
echo -e "  1. Click ${BOLD}+${NC} button"
echo -e "  2. Navigate to: /Applications → ${BOLD}$TERMINAL_NAME${NC}"
echo -e "  3. Enable the checkbox for ${BOLD}$TERMINAL_NAME${NC}"
echo ""
echo -e "${CYAN}Opening Screen Recording settings...${NC}"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"

# Trigger permission prompt
echo -e "${YELLOW}Triggering permission prompt...${NC}"
screencapture -x /tmp/cyvigil_test_screenshot.png 2>/dev/null && rm -f /tmp/cyvigil_test_screenshot.png
wait_for_user

# ============================================
# 3. AUTOMATION
# ============================================
echo -e "${BOLD}${BLUE}[3/6] Automation${NC}"
echo -e "Required for: Shadow IT detection (browser URLs, running apps)"
echo ""
echo -e "${YELLOW}Steps:${NC}"
echo -e "  1. Find ${BOLD}$TERMINAL_NAME${NC} in the list"
echo -e "  2. Enable these checkboxes:"
echo -e "     ${GREEN}✓${NC} Safari"
echo -e "     ${GREEN}✓${NC} Google Chrome"
echo -e "     ${GREEN}✓${NC} System Events"
echo ""
echo -e "${CYAN}Opening Automation settings...${NC}"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation"

# Trigger permission prompts
echo -e "${YELLOW}Triggering permission prompts...${NC}"
osascript -e 'tell application "System Events" to return name of first process' 2>/dev/null &
osascript -e 'tell application "Safari" to return name' 2>/dev/null &
osascript -e 'tell application "Google Chrome" to return name' 2>/dev/null &
wait
wait_for_user

# ============================================
# 4. ACCESSIBILITY
# ============================================
echo -e "${BOLD}${BLUE}[4/6] Accessibility${NC}"
echo -e "Required for: Keystroke logging (optional)"
echo ""
echo -e "${YELLOW}Steps:${NC}"
echo -e "  1. Click ${BOLD}+${NC} button"
echo -e "  2. Navigate to: /Applications → ${BOLD}$TERMINAL_NAME${NC}"
echo -e "  3. Enable the checkbox for ${BOLD}$TERMINAL_NAME${NC}"
echo ""
echo -e "${CYAN}Opening Accessibility settings...${NC}"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
wait_for_user

# ============================================
# 5. LOCATION SERVICES
# ============================================
echo -e "${BOLD}${BLUE}[5/6] Location Services${NC}"
echo -e "Required for: GPS location tracking"
echo ""
echo -e "${YELLOW}Steps:${NC}"
echo -e "  1. Enable ${BOLD}Location Services${NC} (top toggle)"
echo -e "  2. Scroll down and find ${BOLD}$TERMINAL_NAME${NC}"
echo -e "  3. Enable the checkbox"
echo ""
echo -e "${CYAN}Opening Location Services settings...${NC}"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_LocationServices"

# Trigger permission prompt
echo -e "${YELLOW}Triggering location prompt...${NC}"
python3 -c "
import CoreLocation
manager = CoreLocation.CLLocationManager.alloc().init()
manager.requestWhenInUseAuthorization()
" 2>/dev/null &
wait_for_user

# ============================================
# 6. CAMERA & MICROPHONE
# ============================================
echo -e "${BOLD}${BLUE}[6/6] Camera & Microphone${NC}"
echo -e "Required for: Photo capture, Audio recording"
echo ""
echo -e "${YELLOW}Steps:${NC}"
echo -e "  1. Find ${BOLD}$TERMINAL_NAME${NC} in Camera list - enable it"
echo -e "  2. Find ${BOLD}$TERMINAL_NAME${NC} in Microphone list - enable it"
echo ""
echo -e "${CYAN}Opening Camera settings...${NC}"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"

# Trigger camera permission
if command -v imagesnap &>/dev/null || [[ -f /opt/homebrew/bin/imagesnap ]]; then
    echo -e "${YELLOW}Triggering camera prompt...${NC}"
    /opt/homebrew/bin/imagesnap -q /tmp/cyvigil_test_photo.jpg 2>/dev/null && rm -f /tmp/cyvigil_test_photo.jpg
fi

echo ""
echo -e "${YELLOW}Now opening Microphone settings...${NC}"
sleep 2
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
wait_for_user

# ============================================
# VERIFICATION
# ============================================
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Verifying Permissions                           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test each permission
echo -e "${BOLD}Testing permissions...${NC}"
echo ""

# Screen Recording
if screencapture -x /tmp/cyvigil_verify.png 2>/dev/null; then
    SIZE=$(stat -f%z /tmp/cyvigil_verify.png 2>/dev/null || echo "0")
    if [[ "$SIZE" -gt 10000 ]]; then
        echo -e "  ${GREEN}✓${NC} Screen Recording: Working"
    else
        echo -e "  ${YELLOW}⚠${NC} Screen Recording: May only capture wallpaper"
    fi
    rm -f /tmp/cyvigil_verify.png
else
    echo -e "  ${RED}✗${NC} Screen Recording: Not enabled"
fi

# Automation (System Events)
if osascript -e 'tell application "System Events" to return name of first process' 2>/dev/null | grep -q "."; then
    echo -e "  ${GREEN}✓${NC} Automation (System Events): Working"
else
    echo -e "  ${RED}✗${NC} Automation (System Events): Not enabled"
fi

# Automation (Safari)
if osascript -e 'tell application "Safari" to return name' 2>/dev/null | grep -q "Safari"; then
    echo -e "  ${GREEN}✓${NC} Automation (Safari): Working"
else
    echo -e "  ${YELLOW}⚠${NC} Automation (Safari): Not enabled or Safari not running"
fi

# Location
LOCATION_STATUS=$(python3 -c "
import CoreLocation
manager = CoreLocation.CLLocationManager.alloc().init()
status = CoreLocation.CLLocationManager.authorizationStatus()
print(status)
" 2>/dev/null || echo "0")

if [[ "$LOCATION_STATUS" == "3" || "$LOCATION_STATUS" == "4" ]]; then
    echo -e "  ${GREEN}✓${NC} Location Services: Authorized"
elif [[ "$LOCATION_STATUS" == "0" ]]; then
    echo -e "  ${YELLOW}⚠${NC} Location Services: Not determined (run 'loginmonitor location')"
else
    echo -e "  ${RED}✗${NC} Location Services: Denied"
fi

# Camera
if [[ -f /opt/homebrew/bin/imagesnap ]]; then
    if /opt/homebrew/bin/imagesnap -q /tmp/cyvigil_cam_test.jpg 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Camera: Working"
        rm -f /tmp/cyvigil_cam_test.jpg
    else
        echo -e "  ${RED}✗${NC} Camera: Not enabled"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Camera: imagesnap not installed"
fi

# Full Disk Access (test by reading Safari history)
if sqlite3 "$HOME/Library/Safari/History.db" "SELECT 1 LIMIT 1" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Full Disk Access: Working"
else
    echo -e "  ${YELLOW}⚠${NC} Full Disk Access: Not enabled or Safari never used"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Permission Setup Complete!                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Run ${CYAN}loginmonitor permissions${NC} anytime to verify permissions."
echo ""
