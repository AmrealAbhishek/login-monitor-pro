#!/bin/bash
# Create Professional DMG for Login Monitor PRO

set -e

APP_NAME="LoginMonitorPRO"
DMG_NAME="${APP_NAME}.dmg"
DIST_DIR="$(dirname "$0")/dist"
TMP_DMG="${DIST_DIR}/tmp_${DMG_NAME}"
FINAL_DMG="${DIST_DIR}/${DMG_NAME}"
VOLUME_NAME="Login Monitor PRO"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"

echo "Creating professional DMG..."

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Run pyinstaller first."
    exit 1
fi

# Remove old DMGs
rm -f "$TMP_DMG" "$FINAL_DMG"

# Create temporary directory for DMG contents
TMP_DIR="${DIST_DIR}/dmg_contents"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# Copy app
cp -R "$APP_PATH" "$TMP_DIR/"

# Create Applications symlink
ln -s /Applications "$TMP_DIR/Applications"

# Create background directory
mkdir -p "$TMP_DIR/.background"

# Create background image with instructions
cat > /tmp/create_bg.py << 'PYTHON'
import subprocess

# Create a simple HTML file for background
html = '''
<!DOCTYPE html>
<html>
<head>
<style>
body {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    margin: 0;
    text-align: center;
}
h1 { font-size: 28px; margin-bottom: 10px; }
p { font-size: 16px; opacity: 0.8; margin: 5px 0; }
.arrow { font-size: 60px; margin: 20px 0; }
.step {
    background: rgba(255,255,255,0.1);
    padding: 15px 25px;
    border-radius: 10px;
    margin: 10px;
}
</style>
</head>
<body>
<h1>Login Monitor PRO</h1>
<p>Anti-Theft Security for your Mac</p>
<div class="arrow">⬇️</div>
<div class="step">1. Drag app to Applications</div>
<div class="step">2. Double-click Setup to configure</div>
</body>
</html>
'''

# Save HTML
with open('/tmp/dmg_bg.html', 'w') as f:
    f.write(html)

print("Background HTML created")
PYTHON

python3 /tmp/create_bg.py

# Create a simple PNG background using sips (macOS built-in)
# First create a solid color image, then we'll use it
cat > /tmp/create_bg_image.py << 'PYTHON'
import subprocess
import os

# Create a gradient background image using Core Graphics via Python
script = '''
import Quartz
import CoreFoundation

width, height = 540, 380

# Create color space and context
colorSpace = Quartz.CGColorSpaceCreateDeviceRGB()
context = Quartz.CGBitmapContextCreate(
    None, width, height, 8, 0, colorSpace,
    Quartz.kCGImageAlphaPremultipliedLast
)

# Draw gradient background
colors = [
    (0.1, 0.1, 0.18, 1.0),  # Dark blue
    (0.06, 0.2, 0.38, 1.0)   # Lighter blue
]

gradientColors = CoreFoundation.CFArrayCreate(
    None,
    [Quartz.CGColorCreate(colorSpace, c) for c in colors],
    2,
    None
)

gradient = Quartz.CGGradientCreateWithColors(colorSpace, gradientColors, [0.0, 1.0])

Quartz.CGContextDrawLinearGradient(
    context, gradient,
    Quartz.CGPointMake(0, height),
    Quartz.CGPointMake(width, 0),
    0
)

# Add text
Quartz.CGContextSetRGBFillColor(context, 1, 1, 1, 1)

# Save image
image = Quartz.CGBitmapContextCreateImage(context)
url = CoreFoundation.CFURLCreateWithFileSystemPath(
    None, "/tmp/dmg_background.png",
    CoreFoundation.kCFURLPOSIXPathStyle, False
)
dest = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
Quartz.CGImageDestinationAddImage(dest, image, None)
Quartz.CGImageDestinationFinalize(dest)

print("Background image created")
'''

exec(script)
PYTHON

python3 /tmp/create_bg_image.py 2>/dev/null || echo "Using fallback background"

# Copy background if created
if [ -f "/tmp/dmg_background.png" ]; then
    cp /tmp/dmg_background.png "$TMP_DIR/.background/background.png"
fi

# Calculate size needed (app size + 50MB buffer)
APP_SIZE=$(du -sm "$APP_PATH" | cut -f1)
DMG_SIZE=$((APP_SIZE + 50))

echo "Creating DMG (${DMG_SIZE}MB)..."

# Create temporary DMG
hdiutil create -srcfolder "$TMP_DIR" -volname "$VOLUME_NAME" -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" -format UDRW -size ${DMG_SIZE}m "$TMP_DMG"

# Mount it
DEVICE=$(hdiutil attach -readwrite -noverify "$TMP_DMG" | grep "Apple_HFS" | awk '{print $1}')
MOUNT_POINT="/Volumes/$VOLUME_NAME"

echo "Configuring DMG appearance..."

# Wait for mount
sleep 2

# Set up DMG appearance using AppleScript
osascript << EOF
tell application "Finder"
    tell disk "$VOLUME_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set bounds of container window to {400, 100, 940, 520}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 100

        -- Position icons
        set position of item "${APP_NAME}.app" of container window to {135, 180}
        set position of item "Applications" of container window to {405, 180}

        -- Try to set background
        try
            set background picture of viewOptions to file ".background:background.png"
        end try

        close
        open
        update without registering applications
        delay 2
    end tell
end tell
EOF

# Sync and unmount
sync
hdiutil detach "$DEVICE" -quiet

# Convert to compressed read-only DMG
echo "Compressing DMG..."
hdiutil convert "$TMP_DMG" -format UDZO -imagekey zlib-level=9 -o "$FINAL_DMG"

# Cleanup
rm -f "$TMP_DMG"
rm -rf "$TMP_DIR"

echo ""
echo "========================================"
echo "  DMG Created Successfully!"
echo "========================================"
echo ""
echo "Location: $FINAL_DMG"
echo "Size: $(du -h "$FINAL_DMG" | cut -f1)"
echo ""
