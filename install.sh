#!/bin/bash
#
# CyVigil - Enterprise Security Monitor
# =====================================
# One-Line Install: curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/install.sh | bash
#
# Features:
# - Screen lock/unlock detection with photo capture
# - Remote commands (screenshot, location, audio, lock, etc.)
# - Productivity tracking (app usage, idle time)
# - Browser activity monitoring
# - File access monitoring
# - Suspicious activity detection
# - Remote Desktop (VNC) support
#

set -e

VERSION="2.2.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================
# DEFAULT SUPABASE CREDENTIALS
# ============================================
DEFAULT_SUPABASE_URL="https://uldaniwnnwuiyyfygsxa.supabase.co"
DEFAULT_SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NDY4NjEsImV4cCI6MjA4MjQyMjg2MX0._9OU-el7-1I7aS_VLLdhjjexOFQdg0TQ7LI3KI6a2a4"
DEFAULT_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Njg0Njg2MSwiZXhwIjoyMDgyNDIyODYxfQ.TEcxmXe628_DJILYNOtFVXDMFDku4xL7v9IDCNkI0zo"
DEFAULT_VNC_PASSWORD="vnc123"
# ============================================

# Paths
INSTALL_DIR="$HOME/.login-monitor"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
CLI_PATH="$HOME/.local/bin/loginmonitor"
GITHUB_RAW="https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main"

# Parse command line arguments
ORG_ID=""
INSTALL_TOKEN=""
SILENT_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --org-id=*) ORG_ID="${1#*=}"; shift ;;
        --token=*) INSTALL_TOKEN="${1#*=}"; shift ;;
        --org-id) ORG_ID="$2"; shift 2 ;;
        --token) INSTALL_TOKEN="$2"; shift 2 ;;
        --silent) SILENT_MODE=true; shift ;;
        *) shift ;;
    esac
done

# Enterprise mode check
if [[ -n "$ORG_ID" && -n "$INSTALL_TOKEN" ]]; then
    ENTERPRISE_MODE=true
else
    ENTERPRISE_MODE=false
fi

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║      ██████╗██╗   ██╗██╗   ██╗██╗ ██████╗ ██╗██╗            ║"
echo "║     ██╔════╝╚██╗ ██╔╝██║   ██║██║██╔════╝ ██║██║            ║"
echo "║     ██║      ╚████╔╝ ██║   ██║██║██║  ███╗██║██║            ║"
echo "║     ██║       ╚██╔╝  ╚██╗ ██╔╝██║██║   ██║██║██║            ║"
echo "║     ╚██████╗   ██║    ╚████╔╝ ██║╚██████╔╝██║███████╗       ║"
echo "║      ╚═════╝   ╚═╝     ╚═══╝  ╚═╝ ╚═════╝ ╚═╝╚══════╝       ║"
echo "║                                                              ║"
echo "║           Enterprise Security Monitor v${VERSION}               ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: This installer is for macOS only.${NC}"
    exit 1
fi

echo -e "${BLUE}[1/8]${NC} Checking system requirements..."

# Check/Install Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    [[ -f "/opt/homebrew/bin/brew" ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
fi
echo -e "${GREEN}✓${NC} Homebrew"

# Check Python
if ! command -v python3 &> /dev/null; then
    brew install python3
fi
echo -e "${GREEN}✓${NC} Python $(python3 --version | cut -d' ' -f2)"

echo -e "${BLUE}[2/8]${NC} Installing dependencies..."

# Install imagesnap (for camera)
if ! command -v imagesnap &> /dev/null && ! [[ -f /opt/homebrew/bin/imagesnap ]]; then
    echo "  Installing imagesnap..."
    brew install imagesnap 2>/dev/null || true
fi
echo -e "${GREEN}✓${NC} imagesnap (camera capture)"

# Install cloudflared (for VNC tunneling)
if ! command -v cloudflared &> /dev/null && ! [[ -f /opt/homebrew/bin/cloudflared ]]; then
    echo "  Installing cloudflared..."
    brew install cloudflared 2>/dev/null || true
fi
echo -e "${GREEN}✓${NC} cloudflared (VNC tunneling)"

# Find best Python
PYTHON_CMD=""
for PY in "/Library/Developer/CommandLineTools/usr/bin/python3" "/usr/bin/python3" "/opt/homebrew/bin/python3"; do
    if [ -x "$PY" ]; then
        PYTHON_CMD="$PY"
        break
    fi
done
[ -z "$PYTHON_CMD" ] && PYTHON_CMD=$(which python3)
echo -e "${CYAN}Using Python: $PYTHON_CMD${NC}"

# Install Python packages
echo "  Installing Python packages..."
$PYTHON_CMD -m pip install --user --quiet pyobjc-framework-Quartz pyobjc-framework-CoreLocation pyobjc-framework-CoreWLAN pyobjc-framework-Cocoa supabase websockify watchdog 2>/dev/null || true
echo -e "${GREEN}✓${NC} Python packages"

echo -e "${BLUE}[3/8]${NC} Creating directories..."

mkdir -p "$INSTALL_DIR"/{captured_images,captured_audio,activity_logs,known_faces,events}
mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$HOME/.local/bin"
echo -e "${GREEN}✓${NC} Directories created"

echo -e "${BLUE}[4/8]${NC} Downloading scripts..."

# Core monitoring scripts
PYTHON_FILES=(
    "screen_watcher.py"
    "pro_monitor.py"
    "command_listener.py"
    "supabase_client.py"
    "app_tracker.py"
    "browser_monitor.py"
    "file_monitor.py"
    "suspicious_detector.py"
    "check_permissions.py"
    "request_location_permission.py"
    # DLP Enterprise Features
    "usb_dlp.py"
    "clipboard_dlp.py"
    "keystroke_logger.py"
    "shadow_it_detector.py"
    "ocr_search.py"
    "siem_export.py"
)

for file in "${PYTHON_FILES[@]}"; do
    echo "  Downloading $file..."
    curl -fsSL "$GITHUB_RAW/$file" -o "$INSTALL_DIR/$file" 2>/dev/null || {
        echo -e "${YELLOW}Warning: Could not download $file${NC}"
    }
done
chmod +x "$INSTALL_DIR"/*.py 2>/dev/null || true
echo -e "${GREEN}✓${NC} Scripts installed to $INSTALL_DIR"

echo -e "${BLUE}[5/8]${NC} Configuring Supabase..."

if [[ "$ENTERPRISE_MODE" == "true" ]]; then
    SUPABASE_URL="$DEFAULT_SUPABASE_URL"
    SUPABASE_KEY="$DEFAULT_SUPABASE_KEY"
    SERVICE_KEY="$DEFAULT_SERVICE_KEY"
    echo -e "${GREEN}✓${NC} Enterprise mode - Organization: $ORG_ID"
elif [[ "$SILENT_MODE" == "true" ]]; then
    SUPABASE_URL="$DEFAULT_SUPABASE_URL"
    SUPABASE_KEY="$DEFAULT_SUPABASE_KEY"
    SERVICE_KEY="$DEFAULT_SERVICE_KEY"
else
    echo ""
    echo -e "  ${CYAN}1)${NC} Use CyVigil Cloud ${GREEN}(Recommended)${NC}"
    echo -e "  ${CYAN}2)${NC} Use custom Supabase project"
    echo ""
    read -p "  Choice [1/2]: " SETUP_CHOICE < /dev/tty

    if [[ "$SETUP_CHOICE" == "2" ]]; then
        read -p "  Supabase URL: " SUPABASE_URL < /dev/tty
        read -p "  Anon Key: " SUPABASE_KEY < /dev/tty
        read -p "  Service Key: " SERVICE_KEY < /dev/tty
    else
        SUPABASE_URL="$DEFAULT_SUPABASE_URL"
        SUPABASE_KEY="$DEFAULT_SUPABASE_KEY"
        SERVICE_KEY="$DEFAULT_SERVICE_KEY"
    fi
fi
echo -e "${GREEN}✓${NC} Supabase configured"

# Generate device ID and pairing code
DEVICE_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
HOSTNAME=$(hostname)
OS_VERSION=$(sw_vers -productVersion)
PAIRING_CODE=$(printf "%06d" $((RANDOM % 1000000)))
PAIRING_EXPIRY=$(($(date +%s) + 300))

# Register device
echo -e "${BLUE}[6/8]${NC} Registering device..."

DEVICE_DATA="{\"id\":\"$DEVICE_ID\",\"hostname\":\"$HOSTNAME\",\"os_version\":\"macOS $OS_VERSION\",\"device_code\":\"$PAIRING_CODE\",\"is_active\":true"
[[ "$ENTERPRISE_MODE" == "true" ]] && DEVICE_DATA="$DEVICE_DATA,\"org_id\":\"$ORG_ID\""
DEVICE_DATA="$DEVICE_DATA}"

curl -s -X POST "${SUPABASE_URL}/rest/v1/devices" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d "$DEVICE_DATA" >/dev/null 2>&1 || true
echo -e "${GREEN}✓${NC} Device registered: $DEVICE_ID"

# Create config file
ORG_CONFIG=""
[[ "$ENTERPRISE_MODE" == "true" ]] && ORG_CONFIG="\"org_id\": \"$ORG_ID\","

cat > "$INSTALL_DIR/config.json" << EOF
{
  "version": "$VERSION",
  "supabase": {
    "url": "$SUPABASE_URL",
    "anon_key": "$SUPABASE_KEY",
    "service_key": "$SERVICE_KEY",
    "device_id": "$DEVICE_ID",
    $ORG_CONFIG
    "enterprise_mode": $ENTERPRISE_MODE
  },
  "pairing": {
    "code": "$PAIRING_CODE",
    "expires_at": $PAIRING_EXPIRY
  },
  "vnc": {
    "password": "$DEFAULT_VNC_PASSWORD",
    "enabled": false
  },
  "features": {
    "screenshots": true,
    "photos": true,
    "audio": true,
    "location": true,
    "productivity": true,
    "browser_monitoring": true,
    "file_monitoring": true,
    "threat_detection": true
  },
  "dlp": {
    "usb_monitoring": true,
    "clipboard_monitoring": true,
    "shadow_it_detection": true,
    "ocr_enabled": true,
    "keystroke_logging": false,
    "log_full_keystrokes": false,
    "block_usb_storage": false,
    "alert_sensitive_files": true,
    "alert_clipboard_sensitive": true,
    "monitor_ai_paste": true
  },
  "siem_integrations": [],
  "python_path": "$PYTHON_CMD",
  "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
chmod 600 "$INSTALL_DIR/config.json"

echo -e "${BLUE}[7/8]${NC} Setting up services..."

# ========================================
# LaunchAgent: Screen Watcher (login/unlock detection)
# ========================================
cat > "$LAUNCH_AGENTS_DIR/com.loginmonitor.screen.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.screen</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/screen_watcher.py</string>
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
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓${NC} Screen Watcher"

# ========================================
# LaunchAgent: Command Listener (remote commands)
# ========================================
cat > "$LAUNCH_AGENTS_DIR/com.loginmonitor.commands.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.commands</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/command_listener.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-commands.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-commands.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓${NC} Command Listener"

# ========================================
# LaunchAgent: App Tracker (productivity)
# ========================================
cat > "$LAUNCH_AGENTS_DIR/com.loginmonitor.apptracker.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.apptracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/app_tracker.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-apptracker.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-apptracker.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓${NC} App Tracker (Productivity)"

# ========================================
# LaunchAgent: Browser Monitor
# ========================================
cat > "$LAUNCH_AGENTS_DIR/com.loginmonitor.browser.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.browser</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/browser_monitor.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-browser.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-browser.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓${NC} Browser Monitor"

# ========================================
# LaunchAgent: USB DLP Monitor
# ========================================
cat > "$LAUNCH_AGENTS_DIR/com.loginmonitor.usb.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.usb</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/usb_dlp.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-usb.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-usb.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓${NC} USB DLP Monitor"

# ========================================
# LaunchAgent: Clipboard DLP Monitor
# ========================================
cat > "$LAUNCH_AGENTS_DIR/com.loginmonitor.clipboard.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.clipboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/clipboard_dlp.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-clipboard.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-clipboard.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓${NC} Clipboard DLP Monitor"

# ========================================
# LaunchAgent: Shadow IT Detector
# ========================================
cat > "$LAUNCH_AGENTS_DIR/com.loginmonitor.shadowit.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loginmonitor.shadowit</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/shadow_it_detector.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loginmonitor-shadowit.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loginmonitor-shadowit.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓${NC} Shadow IT Detector"

# ========================================
# Create LoginMonitorCommands.app (for Screen Recording permission)
# ========================================
APP_DIR="$INSTALL_DIR/LoginMonitorCommands.app"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

cat > "$APP_DIR/Contents/MacOS/LoginMonitorCommands" << 'APPEOF'
#!/bin/bash
cd ~/.login-monitor
PYTHON_PATH=$(python3 -c "import json; print(json.load(open('config.json')).get('python_path', '/usr/bin/python3'))" 2>/dev/null || echo "python3")
exec "$PYTHON_PATH" command_listener.py >> /tmp/loginmonitor-commands.log 2>&1
APPEOF
chmod +x "$APP_DIR/Contents/MacOS/LoginMonitorCommands"

cat > "$APP_DIR/Contents/Info.plist" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>LoginMonitorCommands</string>
    <key>CFBundleIdentifier</key>
    <string>com.cyvigil.commands</string>
    <key>CFBundleName</key>
    <string>CyVigil Commands</string>
    <key>CFBundleVersion</key>
    <string>2.1.0</string>
    <key>LSBackgroundOnly</key>
    <true/>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLISTEOF
echo -e "${GREEN}✓${NC} CyVigil Commands App"

# Load services
echo "  Loading services..."
for agent in screen apptracker browser usb clipboard shadowit; do
    launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.$agent.plist" 2>/dev/null || true
done

for agent in screen apptracker browser usb clipboard shadowit; do
    launchctl load "$LAUNCH_AGENTS_DIR/com.loginmonitor.$agent.plist" 2>/dev/null || true
done

# Start command_listener from Terminal (inherits Screen Recording permission)
pkill -f "command_listener.py" 2>/dev/null || true
cd "$INSTALL_DIR" && nohup "$PYTHON_CMD" command_listener.py >> /tmp/loginmonitor-commands.log 2>&1 &

echo -e "${GREEN}✓${NC} All services started"

echo -e "${BLUE}[8/8]${NC} Installing CLI..."

# ========================================
# CLI Script
# ========================================
cat > "$CLI_PATH" << 'CLIFEOF'
#!/bin/bash
INSTALL_DIR="$HOME/.login-monitor"
LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

get_python() {
    python3 -c "import json; print(json.load(open('$INSTALL_DIR/config.json')).get('python_path', '/usr/bin/python3'))" 2>/dev/null || echo "python3"
}

case "$1" in
    start)
        echo -e "${CYAN}Starting CyVigil services...${NC}"
        for agent in screen apptracker browser usb clipboard shadowit; do
            launchctl load "$LAUNCHAGENT_DIR/com.loginmonitor.$agent.plist" 2>/dev/null || true
        done
        pkill -f "command_listener.py" 2>/dev/null || true
        cd "$INSTALL_DIR" && nohup "$(get_python)" command_listener.py >> /tmp/loginmonitor-commands.log 2>&1 &
        sleep 2
        loginmonitor status
        ;;
    stop)
        echo -e "${CYAN}Stopping CyVigil services...${NC}"
        for agent in screen apptracker browser usb clipboard shadowit; do
            launchctl unload "$LAUNCHAGENT_DIR/com.loginmonitor.$agent.plist" 2>/dev/null || true
        done
        pkill -f "screen_watcher.py" 2>/dev/null || true
        pkill -f "command_listener.py" 2>/dev/null || true
        pkill -f "app_tracker.py" 2>/dev/null || true
        pkill -f "browser_monitor.py" 2>/dev/null || true
        pkill -f "usb_dlp.py" 2>/dev/null || true
        pkill -f "clipboard_dlp.py" 2>/dev/null || true
        pkill -f "shadow_it_detector.py" 2>/dev/null || true
        pkill -f "websockify" 2>/dev/null || true
        pkill -f "cloudflared.*tunnel" 2>/dev/null || true
        echo -e "${GREEN}✓ All services stopped${NC}"
        ;;
    restart)
        loginmonitor stop
        sleep 1
        loginmonitor start
        ;;
    status)
        echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║       CyVigil Service Status             ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${BOLD}Core Services:${NC}"
        for svc in "screen_watcher.py:Screen Watcher" "command_listener.py:Command Listener" "app_tracker.py:App Tracker" "browser_monitor.py:Browser Monitor"; do
            proc="${svc%%:*}"
            name="${svc#*:}"
            if pgrep -f "$proc" > /dev/null; then
                printf "  %-20s ${GREEN}● Running${NC}\n" "$name"
            else
                printf "  %-20s ${RED}○ Stopped${NC}\n" "$name"
            fi
        done
        echo ""
        echo -e "${BOLD}DLP Services:${NC}"
        for svc in "usb_dlp.py:USB Monitor" "clipboard_dlp.py:Clipboard DLP" "shadow_it_detector.py:Shadow IT"; do
            proc="${svc%%:*}"
            name="${svc#*:}"
            if pgrep -f "$proc" > /dev/null; then
                printf "  %-20s ${GREEN}● Running${NC}\n" "$name"
            else
                printf "  %-20s ${RED}○ Stopped${NC}\n" "$name"
            fi
        done
        echo ""
        # VNC status
        if netstat -an 2>/dev/null | grep -q "\.5900"; then
            echo -e "  VNC (Screen Share)   ${GREEN}● Enabled${NC}"
        else
            echo -e "  VNC (Screen Share)   ${YELLOW}○ Not enabled${NC}"
        fi
        ;;
    logs)
        echo -e "${CYAN}Tailing all logs (Ctrl+C to exit)...${NC}"
        tail -f /tmp/loginmonitor-*.log 2>/dev/null
        ;;
    pair)
        CODE=$(printf "%06d" $((RANDOM % 1000000)))
        EXPIRY=$(($(date +%s) + 300))
        $(get_python) << PEOF
import json, os, urllib.request
config_path = os.path.expanduser("~/.login-monitor/config.json")
with open(config_path, 'r') as f:
    config = json.load(f)
config['pairing'] = {'code': '$CODE', 'expires_at': $EXPIRY}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
try:
    req = urllib.request.Request(
        f"{config['supabase']['url']}/rest/v1/devices?id=eq.{config['supabase']['device_id']}",
        data=json.dumps({'device_code': '$CODE'}).encode(),
        method='PATCH'
    )
    req.add_header('apikey', config['supabase']['anon_key'])
    req.add_header('Authorization', f"Bearer {config['supabase']['anon_key']}")
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req)
except: pass
PEOF
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  PAIRING CODE:  ${YELLOW}${BOLD}$CODE${NC}${GREEN}                      ║${NC}"
        echo -e "${GREEN}║  Valid for 5 minutes                       ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
        echo ""
        ;;
    test)
        echo -e "${CYAN}Triggering test event...${NC}"
        $(get_python) "$INSTALL_DIR/pro_monitor.py" Test
        ;;
    location)
        echo -e "${CYAN}Setting up location permission...${NC}"
        $(get_python) "$INSTALL_DIR/request_location_permission.py"
        ;;
    screen)
        echo -e "${CYAN}Screen Recording Setup${NC}"
        echo ""
        PYTHON_PATH=$(get_python)
        echo -e "${YELLOW}Add this Python to Screen Recording:${NC}"
        echo -e "  ${GREEN}$PYTHON_PATH${NC}"
        echo ""
        echo "Steps:"
        echo "  1. System Settings → Privacy & Security → Screen Recording"
        echo "  2. Click '+' → Press Cmd+Shift+G"
        echo "  3. Paste the path above → Click Open"
        echo "  4. Toggle ON"
        echo ""
        open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
        echo -e "${YELLOW}After adding, run: loginmonitor restart${NC}"
        ;;
    vnc)
        echo -e "${CYAN}Remote Desktop (VNC) Setup${NC}"
        echo ""
        if netstat -an 2>/dev/null | grep -q "\.5900"; then
            echo -e "${GREEN}✓ Screen Sharing is enabled${NC}"
        else
            echo -e "${YELLOW}Screen Sharing is not enabled${NC}"
            echo ""
            echo "Opening System Settings..."
            open "x-apple.systempreferences:com.apple.preferences.sharing?Services_ScreenSharing"
            echo ""
            echo -e "${YELLOW}Steps:${NC}"
            echo "  1. Turn ON 'Screen Sharing'"
            echo "  2. Click 'Computer Settings...'"
            echo "  3. Check 'VNC viewers may control screen with password'"
            echo "  4. Set password: vnc123 (or your choice)"
            echo ""
            read -p "Press Enter after enabling..." < /dev/tty
        fi
        if netstat -an 2>/dev/null | grep -q "\.5900"; then
            echo -e "${GREEN}✓ Screen Sharing ready${NC}"
            echo ""
            echo -e "Dashboard: ${CYAN}https://web-dashboard-inky.vercel.app/remote${NC}"
            echo ""
            echo -e "${YELLOW}Login:${NC}"
            echo "  Username: $(whoami)"
            echo "  Password: Mac password OR VNC password"
        fi
        ;;
    permissions|perms|check)
        if [ -f "$INSTALL_DIR/check_permissions.py" ]; then
            $(get_python) "$INSTALL_DIR/check_permissions.py"
        else
            echo -e "${CYAN}Permission Check${NC}"
            echo ""
            netstat -an 2>/dev/null | grep -q "\.5900" && echo -e "  ${GREEN}✓${NC} VNC: Enabled" || echo -e "  ${RED}✗${NC} VNC: Run 'loginmonitor vnc'"
            echo -e "  ${YELLOW}?${NC} Screen Recording: Run 'loginmonitor screen'"
            echo -e "  ${YELLOW}?${NC} Location: Run 'loginmonitor location'"
        fi
        ;;
    uninstall)
        echo -e "${CYAN}Uninstalling CyVigil...${NC}"
        curl -fsSL "https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/uninstall.sh" | bash
        ;;
    update)
        echo -e "${CYAN}Updating CyVigil...${NC}"
        loginmonitor stop
        curl -fsSL "https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/install.sh" | bash --silent
        ;;
    version|-v|--version)
        VERSION=$(python3 -c "import json; print(json.load(open('$INSTALL_DIR/config.json')).get('version', '2.1.0'))" 2>/dev/null || echo "2.1.0")
        echo "CyVigil v$VERSION"
        ;;
    *)
        echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║       CyVigil CLI v2.2.0                 ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
        echo ""
        echo "Usage: loginmonitor <command>"
        echo ""
        echo -e "${BOLD}Services:${NC}"
        echo "  start        Start all monitoring services"
        echo "  stop         Stop all services"
        echo "  restart      Restart all services"
        echo "  status       Show service status (incl. DLP)"
        echo "  logs         View live logs"
        echo ""
        echo -e "${BOLD}Setup:${NC}"
        echo "  pair         Generate new pairing code"
        echo "  location     Setup GPS location permission"
        echo "  screen       Setup screen recording permission"
        echo "  vnc          Setup remote desktop (VNC)"
        echo "  permissions  Check all permissions"
        echo ""
        echo -e "${BOLD}DLP Features:${NC}"
        echo "  USB monitoring, Clipboard DLP, Shadow IT detection"
        echo "  Keystroke logging, OCR search, SIEM integration"
        echo ""
        echo -e "${BOLD}Other:${NC}"
        echo "  test         Trigger test event"
        echo "  update       Update to latest version"
        echo "  uninstall    Remove CyVigil"
        echo "  version      Show version"
        echo ""
        echo -e "Dashboard: ${CYAN}https://web-dashboard-inky.vercel.app${NC}"
        echo -e "DLP Page:  ${CYAN}https://web-dashboard-inky.vercel.app/dlp${NC}"
        echo ""
        ;;
esac
CLIFEOF

chmod +x "$CLI_PATH"

# Add to PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc 2>/dev/null || true
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi

echo -e "${GREEN}✓${NC} CLI installed: loginmonitor"

# ========================================
# Final Summary
# ========================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              INSTALLATION COMPLETE!                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  IMPORTANT: Complete these steps for full functionality      ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}1. GPS Location:${NC}"
echo -e "   ${GREEN}loginmonitor location${NC} → Click 'Allow' when prompted"
echo ""
echo -e "${YELLOW}2. Screenshots:${NC}"
echo -e "   ${GREEN}loginmonitor screen${NC} → Follow the steps shown"
echo ""
echo -e "${YELLOW}3. Remote Desktop (Optional):${NC}"
echo -e "   ${GREEN}loginmonitor vnc${NC} → Enable Screen Sharing"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo "  loginmonitor status      - Check service status"
echo "  loginmonitor permissions - Check all permissions"
echo "  loginmonitor logs        - View live logs"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║   PAIRING CODE:  ${YELLOW}${BOLD}$PAIRING_CODE${NC}${GREEN}                                    ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║   Enter this code in the mobile app to connect                ║${NC}"
echo -e "${GREEN}║   Code expires in 5 minutes                                   ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Dashboard: ${CYAN}https://web-dashboard-inky.vercel.app${NC}"
echo ""
echo -e "${GREEN}CyVigil is now protecting your Mac!${NC}"
echo ""
