#!/bin/bash
#
# Login Monitor PRO - One-Line Installer
# ========================================
# Install: curl -fsSL https://your-domain.com/install.sh | bash
#
# Supabase + Flutter App
#

set -e

VERSION="2.0.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================
# DEFAULT SUPABASE CREDENTIALS (Your Project)
# ============================================
DEFAULT_SUPABASE_URL="https://uldaniwnnwuiyyfygsxa.supabase.co"
DEFAULT_SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NDY4NjEsImV4cCI6MjA4MjQyMjg2MX0._9OU-el7-1I7aS_VLLdhjjexOFQdg0TQ7LI3KI6a2a4"
# ============================================

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.login-monitor"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║           LOGIN MONITOR PRO - INSTALLER v${VERSION}            ║"
echo "║                                                            ║"
echo "║   Anti-Theft & Security Monitoring for macOS               ║"
echo "║   Supabase + Flutter Mobile App                            ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: This installer is for macOS only.${NC}"
    exit 1
fi

echo -e "${BLUE}[1/7]${NC} Checking system requirements..."

# Check Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    [[ -f "/opt/homebrew/bin/brew" ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
fi
echo -e "${GREEN}✓ Homebrew${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    brew install python3
fi
echo -e "${GREEN}✓ Python $(python3 --version | cut -d' ' -f2)${NC}"

echo -e "${BLUE}[2/7]${NC} Installing dependencies..."

# Install imagesnap
if ! command -v imagesnap &> /dev/null && ! [[ -f /opt/homebrew/bin/imagesnap ]]; then
    brew install imagesnap
fi
echo -e "${GREEN}✓ imagesnap${NC}"

# Python path
PYTHON_CMD="/Library/Developer/CommandLineTools/usr/bin/python3"
[[ ! -f "$PYTHON_CMD" ]] && PYTHON_CMD=$(which python3)

# Install Python packages
echo "Installing Python packages..."
$PYTHON_CMD -m pip install --user --quiet pyobjc-framework-Quartz pyobjc-framework-CoreLocation pyobjc-framework-CoreWLAN pyobjc-framework-Cocoa 2>/dev/null || true
echo -e "${GREEN}✓ Python packages${NC}"

echo -e "${BLUE}[3/7]${NC} Installing files..."

# Create directories
mkdir -p "$INSTALL_DIR"/{captures,events,audio,captured_images,captured_audio,activity_logs,known_faces}
mkdir -p "$LAUNCH_AGENTS_DIR"

# Copy Python files
cp "$SCRIPT_DIR"/*.py "$INSTALL_DIR/" 2>/dev/null || true
chmod +x "$INSTALL_DIR"/*.py
echo -e "${GREEN}✓ Files installed to $INSTALL_DIR${NC}"

echo -e "${BLUE}[4/7]${NC} Supabase Configuration..."
echo ""
echo -e "${CYAN}Choose setup option:${NC}"
echo ""
echo "  1) ${GREEN}Default${NC} - Use Login Monitor PRO cloud (Recommended)"
echo "  2) ${YELLOW}Custom${NC}  - Use your own Supabase project"
echo ""
read -p "Enter choice [1/2]: " SETUP_CHOICE < /dev/tty

if [[ "$SETUP_CHOICE" == "2" ]]; then
    echo ""
    echo -e "${YELLOW}Enter your Supabase credentials:${NC}"
    read -p "Supabase Project URL (https://xxx.supabase.co): " SUPABASE_URL < /dev/tty
    read -p "Supabase Anon Key: " SUPABASE_KEY < /dev/tty

    if [[ -z "$SUPABASE_URL" || -z "$SUPABASE_KEY" ]]; then
        echo -e "${RED}Error: Supabase URL and Key are required!${NC}"
        exit 1
    fi
else
    # Use default credentials
    SUPABASE_URL="$DEFAULT_SUPABASE_URL"
    SUPABASE_KEY="$DEFAULT_SUPABASE_KEY"
    echo -e "${GREEN}✓ Using Login Monitor PRO cloud${NC}"
fi

echo -e "${BLUE}[5/7]${NC} User Registration..."
echo ""
read -p "Enter your email address: " USER_EMAIL < /dev/tty

if [[ -z "$USER_EMAIL" ]]; then
    echo -e "${RED}Error: Email is required for pairing code delivery!${NC}"
    exit 1
fi

# Validate email format
if [[ ! "$USER_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo -e "${RED}Error: Invalid email format!${NC}"
    exit 1
fi

# Generate device ID
DEVICE_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
HOSTNAME=$(hostname)
OS_VERSION=$(sw_vers -productVersion)

# Generate 6-digit pairing code (valid for 5 minutes)
PAIRING_CODE=$(printf "%06d" $((RANDOM % 1000000)))
PAIRING_EXPIRY=$(($(date +%s) + 300))
PAIRING_EXPIRY_ISO=$(date -u -r $PAIRING_EXPIRY +"%Y-%m-%dT%H:%M:%SZ")

echo ""
echo "Registering device and sending pairing code..."

# Register device in Supabase and send email
REGISTER_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/devices" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d "{
        \"id\": \"${DEVICE_ID}\",
        \"hostname\": \"${HOSTNAME}\",
        \"os_version\": \"macOS ${OS_VERSION}\",
        \"pairing_code\": \"${PAIRING_CODE}\",
        \"pairing_expires_at\": \"${PAIRING_EXPIRY_ISO}\",
        \"user_email\": \"${USER_EMAIL}\",
        \"is_active\": true
    }" 2>/dev/null)

# Send pairing code via Supabase Edge Function
EMAIL_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/functions/v1/send-pairing-email" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"${USER_EMAIL}\",
        \"pairing_code\": \"${PAIRING_CODE}\",
        \"hostname\": \"${HOSTNAME}\",
        \"device_id\": \"${DEVICE_ID}\"
    }" 2>/dev/null)

# Check if email was sent successfully
if echo "$EMAIL_RESPONSE" | grep -q '"success":true'; then
    EMAIL_SENT=true
else
    EMAIL_SENT=false
fi

# Create config
cat > "$INSTALL_DIR/config.json" << EOF
{
  "supabase": {
    "url": "$SUPABASE_URL",
    "anon_key": "$SUPABASE_KEY",
    "device_id": "$DEVICE_ID"
  },
  "user": {
    "email": "$USER_EMAIL"
  },
  "pairing": {
    "code": "$PAIRING_CODE",
    "expires_at": $PAIRING_EXPIRY
  },
  "features": {
    "multi_photo": true,
    "photo_count": 3,
    "audio_recording": true,
    "face_recognition": false
  },
  "cooldown_seconds": 10,
  "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
chmod 600 "$INSTALL_DIR/config.json"

echo -e "${GREEN}✓ Configuration saved${NC}"
echo "  Device ID: $DEVICE_ID"
echo "  Email: $USER_EMAIL"

echo ""
if [[ "$EMAIL_SENT" == "true" ]]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║   ${CYAN}PAIRING CODE SENT TO YOUR EMAIL!${GREEN}                        ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║   Check: ${YELLOW}${USER_EMAIL}${GREEN}                        "
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║   Code valid for: 5 minutes                                ║${NC}"
    echo -e "${GREEN}║   Enter the code in the Flutter app to connect             ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                                                            ║${NC}"
    echo -e "${YELLOW}║   ${CYAN}PAIRING CODE:  ${GREEN}$PAIRING_CODE${YELLOW}                              ║${NC}"
    echo -e "${YELLOW}║                                                            ║${NC}"
    echo -e "${YELLOW}║   (Email delivery failed - use code above)                 ║${NC}"
    echo -e "${YELLOW}║   Valid for: 5 minutes                                     ║${NC}"
    echo -e "${YELLOW}║   Enter this code in the Flutter app to connect            ║${NC}"
    echo -e "${YELLOW}║                                                            ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
fi
echo ""

echo -e "${BLUE}[6/7]${NC} Setting up services..."

# Screen Watcher LaunchAgent
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

# Command Listener LaunchAgent
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

# Load services
launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.screen.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.loginmonitor.commands.plist" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS_DIR/com.loginmonitor.screen.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.loginmonitor.commands.plist"

echo -e "${GREEN}✓ Services started${NC}"

echo -e "${BLUE}[7/7]${NC} Creating CLI command..."

# Create CLI
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/loginmonitor" << 'CLIFEOF'
#!/bin/bash
INSTALL_DIR="$HOME/.login-monitor"
LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

case "$1" in
    start)
        echo "Starting Login Monitor..."
        launchctl load "$LAUNCHAGENT_DIR/com.loginmonitor.screen.plist" 2>/dev/null || true
        launchctl load "$LAUNCHAGENT_DIR/com.loginmonitor.commands.plist" 2>/dev/null || true
        sleep 2
        loginmonitor status
        ;;
    stop)
        echo "Stopping Login Monitor..."
        launchctl unload "$LAUNCHAGENT_DIR/com.loginmonitor.screen.plist" 2>/dev/null || true
        launchctl unload "$LAUNCHAGENT_DIR/com.loginmonitor.commands.plist" 2>/dev/null || true
        pkill -f "screen_watcher.py" 2>/dev/null || true
        pkill -f "command_listener.py" 2>/dev/null || true
        echo -e "${GREEN}Stopped.${NC}"
        ;;
    restart)
        loginmonitor stop
        sleep 1
        loginmonitor start
        ;;
    status)
        echo -e "${CYAN}Login Monitor PRO Status:${NC}"
        echo ""
        if pgrep -f "screen_watcher.py" > /dev/null; then
            echo -e "  Screen Watcher:    ${GREEN}Running${NC}"
        else
            echo -e "  Screen Watcher:    ${RED}Stopped${NC}"
        fi
        if pgrep -f "command_listener.py" > /dev/null; then
            echo -e "  Command Listener:  ${GREEN}Running${NC}"
        else
            echo -e "  Command Listener:  ${RED}Stopped${NC}"
        fi
        ;;
    logs)
        echo "Press Ctrl+C to exit..."
        tail -f /tmp/loginmonitor-screen.log /tmp/loginmonitor-commands.log 2>/dev/null
        ;;
    pair)
        # Generate new 6-digit pairing code and send via email
        CODE=$(printf "%06d" $((RANDOM % 1000000)))
        EXPIRY=$(($(date +%s) + 300))
        EXPIRY_ISO=$(date -u -r $EXPIRY +"%Y-%m-%dT%H:%M:%SZ")

        python3 << PEOF
import json
import os
import urllib.request
import urllib.error

config_path = os.path.expanduser("~/.login-monitor/config.json")
with open(config_path, 'r') as f:
    config = json.load(f)

# Update pairing code
config['pairing'] = {'code': '$CODE', 'expires_at': $EXPIRY}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

# Get Supabase credentials
supabase_url = config['supabase']['url']
supabase_key = config['supabase']['anon_key']
device_id = config['supabase']['device_id']
user_email = config.get('user', {}).get('email', '')

# Update device in Supabase
try:
    update_data = json.dumps({
        'pairing_code': '$CODE',
        'pairing_expires_at': '$EXPIRY_ISO'
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{supabase_url}/rest/v1/devices?id=eq.{device_id}",
        data=update_data,
        method='PATCH'
    )
    req.add_header('apikey', supabase_key)
    req.add_header('Authorization', f'Bearer {supabase_key}')
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req)
except Exception as e:
    pass

# Send email via Edge Function
email_sent = False
if user_email:
    try:
        email_data = json.dumps({
            'email': user_email,
            'pairing_code': '$CODE',
            'hostname': os.uname().nodename,
            'device_id': device_id
        }).encode('utf-8')

        req = urllib.request.Request(
            f"{supabase_url}/functions/v1/send-pairing-email",
            data=email_data,
            method='POST'
        )
        req.add_header('apikey', supabase_key)
        req.add_header('Authorization', f'Bearer {supabase_key}')
        req.add_header('Content-Type', 'application/json')
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        email_sent = result.get('success', False)
    except Exception as e:
        pass

print("")
if email_sent:
    print("\033[0;32m╔════════════════════════════════════════════════════╗\033[0m")
    print("\033[0;32m║                                                    ║\033[0m")
    print("\033[0;32m║   PAIRING CODE SENT TO YOUR EMAIL!                 ║\033[0m")
    print(f"\033[0;32m║   Check: {user_email[:40]:<40} ║\033[0m")
    print("\033[0;32m║                                                    ║\033[0m")
    print("\033[0;32m║   Valid for: 5 minutes                             ║\033[0m")
    print("\033[0;32m║                                                    ║\033[0m")
    print("\033[0;32m╚════════════════════════════════════════════════════╝\033[0m")
else:
    print("╔════════════════════════════════════════════════════╗")
    print("║                                                    ║")
    print("║   PAIRING CODE:  $CODE                         ║")
    print("║                                                    ║")
    print("║   Valid for: 5 minutes                             ║")
    print("║   Enter this code in the Flutter app               ║")
    print("║                                                    ║")
    print("╚════════════════════════════════════════════════════╝")
print("")
PEOF
        ;;
    test)
        echo "Triggering test event..."
        python3 "$INSTALL_DIR/pro_monitor.py" Test
        ;;
    uninstall)
        bash "$INSTALL_DIR/../login-monitor/uninstall.sh" 2>/dev/null || bash /Users/*/tool/login-monitor/uninstall.sh 2>/dev/null || echo "Run: bash /path/to/uninstall.sh"
        ;;
    version)
        echo "Login Monitor PRO v2.0.0"
        ;;
    *)
        echo -e "${CYAN}Login Monitor PRO CLI${NC}"
        echo ""
        echo "Usage: loginmonitor <command>"
        echo ""
        echo "Commands:"
        echo "  start      Start monitoring services"
        echo "  stop       Stop all services"
        echo "  restart    Restart services"
        echo "  status     Show service status"
        echo "  logs       View live logs"
        echo "  pair       Generate new 6-digit pairing code (sent to email)"
        echo "  test       Trigger test event"
        echo "  uninstall  Remove Login Monitor"
        echo "  version    Show version"
        echo ""
        ;;
esac
CLIFEOF

chmod +x "$HOME/.local/bin/loginmonitor"

# Add to PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc 2>/dev/null || true
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi

echo -e "${GREEN}✓ CLI command: loginmonitor${NC}"

# Final summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           INSTALLATION COMPLETE!                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo "  1. Check your email for the 6-digit pairing code"
echo "  2. Open the Flutter app on your phone"
echo "  3. Enter the pairing code to connect"
echo ""
echo -e "${CYAN}CLI Commands:${NC}"
echo "  loginmonitor status   - Check if running"
echo "  loginmonitor pair     - Generate new pairing code (sent to email)"
echo "  loginmonitor logs     - View logs"
echo "  loginmonitor stop     - Stop monitoring"
echo ""
echo -e "${YELLOW}Note: Grant Camera, Location & Screen Recording permissions${NC}"
echo -e "${YELLOW}      in System Settings > Privacy & Security${NC}"
echo ""
echo -e "${GREEN}Login Monitor PRO is now protecting your Mac!${NC}"
