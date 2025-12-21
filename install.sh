#!/bin/bash
# OpenReLife Quick Install & Setup

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "╔════════════════════════════════════════════════╗"
echo "║      🚀 OpenReLife Installation & Setup       ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# 1. UV Setup
echo "🔎 Checking uv..."
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "Please install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "✅ uv found"

# 2. Install Backend Dependencies
echo ""
echo "📦 Installing Backend Dependencies (via uv)..."
cd "$SCRIPT_DIR"
uv sync


# 3. Install Frontend Dependencies (Electron)
echo ""
echo "� Installing Electron Dependencies..."
cd "$SCRIPT_DIR/electron-app"
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "   node_modules exists, skipping npm install (run manually if needed)"
fi

# 4. Build Application
echo ""
echo "�️  Building macOS Application..."
# npm run build-mac executes: electron-builder --mac
npm run build-mac

# 5. Final Output
echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║          ✨ Build Complete! ✨                 ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "� App is ready at:"
echo "   $SCRIPT_DIR/electron-app/dist/mac-arm64/OpenReLife.app"
echo "   (or mac-x64 depending on your architecture)"
echo ""
echo "👉 To install:"
echo "   Drag the .app file to your Applications folder."
echo ""
echo "⚠️  Permissions:"
echo "   On first run, grant Accessibility & Screen Recording permissions"
echo "   in System Settings > Privacy & Security."
echo ""

