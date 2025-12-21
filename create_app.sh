#!/bin/bash
# Create macOS app bundle for OpenReLife

APP_NAME="OpenReLife"
BUNDLE_DIR="$HOME/Applications/$APP_NAME.app"
CONTENTS_DIR="$BUNDLE_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🎨 Creating OpenReLife.app..."

# Remove old app if exists
if [ -d "$BUNDLE_DIR" ]; then
    echo "🗑️  Removing old app..."
    rm -rf "$BUNDLE_DIR"
fi

# Create directory structure
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Create Info.plist
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>OpenReLife</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.openrelife.app</string>
    <key>CFBundleName</key>
    <string>OpenReLife</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <string>0</string>
    <key>LSBackgroundOnly</key>
    <string>0</string>
</dict>
</plist>
EOF

# Create launcher script (no visible terminal)
cat > "$MACOS_DIR/OpenReLife" << EOF
#!/bin/bash
APP_DIR="$SCRIPT_DIR"

# Check if already running
if [ -f "\$APP_DIR/logs/openrelife.pid" ]; then
    PID=\$(cat "\$APP_DIR/logs/openrelife.pid")
    if ps -p \$PID > /dev/null 2>&1; then
        # Already running, show notification
        osascript -e 'display notification "OpenReLife is already running. Press Cmd+Shift+Space to open." with title "OpenReLife"'
        exit 0
    fi
fi

# Start in background
cd "\$APP_DIR"
./start_openrelife.sh start

# Show notification
osascript -e 'display notification "Press Cmd+Shift+Space to open, ESC to close" with title "OpenReLife Started"'
EOF

chmod +x "$MACOS_DIR/OpenReLife"

# Create simple icon (using emoji as placeholder)
# You can replace this with a proper .icns file
echo "🔍" > "$RESOURCES_DIR/icon.txt"

echo ""
echo "✅ OpenReLife.app created successfully!"
echo ""
echo "📍 Location: $BUNDLE_DIR"
echo ""
echo "🚀 To use:"
echo "   1. Open the app from Applications or Spotlight"
echo "   2. Press Cmd+Shift+Space to open OpenReLife"
echo "   3. Press ESC to close the window"
echo ""
echo "🛑 To stop the app:"
echo "   cd $SCRIPT_DIR && ./start_openrelife.sh stop"
echo ""
echo "⚠️  Important:"
echo "   Grant Accessibility permissions in:"
echo "   System Settings > Privacy & Security > Accessibility"
echo "   Add 'OpenReLife' when prompted"
echo ""
