#!/bin/bash
#
# Login Monitor - Full Uninstall Script
# Completely removes all components from the system
#

echo "=========================================="
echo "  Login Monitor - Full Uninstall"
echo "=========================================="
echo ""

# Stop all services
echo "[1/5] Stopping services..."
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.retry.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.screen.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.telegram.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.wake.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.loginmonitor.dashboard.plist 2>/dev/null

# Stop stealth mode services if active
launchctl unload ~/Library/LaunchAgents/com.apple.systemhelper.core.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.apple.systemhelper.sync.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.apple.systemhelper.analytics.plist 2>/dev/null

echo "  Services stopped"

# Kill any running processes
echo "[2/5] Killing processes..."
pkill -f "login_monitor.py" 2>/dev/null
pkill -f "screen_watcher.py" 2>/dev/null
pkill -f "telegram_bot.py" 2>/dev/null
pkill -f "pro_monitor.py" 2>/dev/null
pkill -f "activity_monitor.py" 2>/dev/null
pkill -f "web_dashboard.py" 2>/dev/null
echo "  Processes killed"

# Remove LaunchAgent files
echo "[3/5] Removing LaunchAgents..."
rm -f ~/Library/LaunchAgents/com.loginmonitor.plist
rm -f ~/Library/LaunchAgents/com.loginmonitor.retry.plist
rm -f ~/Library/LaunchAgents/com.loginmonitor.screen.plist
rm -f ~/Library/LaunchAgents/com.loginmonitor.telegram.plist
rm -f ~/Library/LaunchAgents/com.loginmonitor.wake.plist
rm -f ~/Library/LaunchAgents/com.loginmonitor.dashboard.plist

# Remove stealth mode LaunchAgents
rm -f ~/Library/LaunchAgents/com.apple.systemhelper.core.plist
rm -f ~/Library/LaunchAgents/com.apple.systemhelper.sync.plist
rm -f ~/Library/LaunchAgents/com.apple.systemhelper.analytics.plist
echo "  LaunchAgents removed"

# Remove install directories
echo "[4/5] Removing install directories..."
rm -rf ~/.login-monitor
rm -rf ~/.system_helper
echo "  Install directories removed"

# Remove log files
echo "[5/5] Removing log files..."
rm -f /tmp/loginmonitor-*.log
rm -f /tmp/systemhelper-*.log
echo "  Log files removed"

echo ""
echo "=========================================="
echo "  Uninstall Complete!"
echo "=========================================="
echo ""
echo "Login Monitor has been fully removed from this system."
echo ""
echo "Note: Project source files remain at:"
echo "  /Users/cyvigilant/tool/login-monitor"
echo "  /Users/cyvigilant/tool/login-monitor 2"
echo "  /Users/cyvigilant/tool/login-monitor-pro.zip"
echo ""
echo "To remove source files too, run:"
echo "  rm -rf /Users/cyvigilant/tool/login-monitor"
echo "  rm -rf /Users/cyvigilant/tool/login-monitor\\ 2"
echo "  rm -f /Users/cyvigilant/tool/login-monitor-pro.zip"
echo ""
