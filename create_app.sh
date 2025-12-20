#!/bin/bash
# Create macOS app bundle for OpenRecall

APP_NAME="OpenRecall"
BUNDLE_DIR="$HOME/Applications/$APP_NAME.app"
CONTENTS_DIR="$BUNDLE_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🎨 Creating OpenRecall.app..."

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
    <string>OpenRecall</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.openrecall.app</string>
    <key>CFBundleName</key>
    <string>OpenRecall</string>
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
cat > "$MACOS_DIR/OpenRecall" << EOF
#!/bin/bash
APP_DIR="$SCRIPT_DIR"

# Check if already running
if [ -f "\$APP_DIR/logs/openrecall.pid" ]; then
    PID=\$(cat "\$APP_DIR/logs/openrecall.pid")
    if ps -p \$PID > /dev/null 2>&1; then
        # Already running, show notification
        osascript -e 'display notification "OpenRecall is already running. Press Cmd+Shift+Space to open." with title "OpenRecall"'
        exit 0
    fi
fi

# Start in background
cd "\$APP_DIR"
./start_openrecall.sh start

# Show notification
osascript -e 'display notification "Press Cmd+Shift+Space to open, ESC to close" with title "OpenRecall Started"'
EOF

chmod +x "$MACOS_DIR/OpenRecall"

# Create simple icon (using emoji as placeholder)
# You can replace this with a proper .icns file
echo "🔍" > "$RESOURCES_DIR/icon.txt"

echo ""
echo "✅ OpenRecall.app created successfully!"
echo ""
echo "📍 Location: $BUNDLE_DIR"
echo ""
echo "🚀 To use:"
echo "   1. Open the app from Applications or Spotlight"
echo "   2. Press Cmd+Shift+Space to open OpenRecall"
echo "   3. Press ESC to close the window"
echo ""
echo "🛑 To stop the app:"
echo "   cd $SCRIPT_DIR && ./start_openrecall.sh stop"
echo ""
echo "⚠️  Important:"
echo "   Grant Accessibility permissions in:"
echo "   System Settings > Privacy & Security > Accessibility"
echo "   Add 'OpenRecall' when prompted"
echo ""
