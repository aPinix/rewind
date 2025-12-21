#!/bin/bash
# OpenReLife Quick Install & Setup

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "╔════════════════════════════════════════════════╗"
echo "║      🚀 OpenReLife Installation & Setup       ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
cd "$SCRIPT_DIR"
uv pip install pynput

echo ""
echo "✅ Dependencies installed"

# Make scripts executable
echo ""
echo "🔧 Setting up scripts..."
chmod +x "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR"/*.py

echo ""
echo "🎨 Creating macOS app..."
"$SCRIPT_DIR/create_app.sh"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║          ✨ Installation Complete! ✨          ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "🎯 Quick Start:"
echo ""
echo "   Option 1: Launch from app"
echo "   • Open Spotlight (Cmd+Space)"
echo "   • Type 'OpenReLife' and press Enter"
echo ""
echo "   Option 2: Launch from terminal"
echo "   • cd $SCRIPT_DIR"
echo "   • ./start_openrelife.sh"
echo ""
echo "⌨️  Usage:"
echo "   • Cmd+Shift+Space: Open OpenReLife"
echo "   • ESC: Close window"
echo ""
echo "🛑 Management:"
echo "   • Stop:    ./start_openrelife.sh stop"
echo "   • Status:  ./start_openrelife.sh status"
echo "   • Restart: ./start_openrelife.sh restart"
echo ""
echo "⚠️  Important: Grant Accessibility Permissions"
echo "   System Settings > Privacy & Security > Accessibility"
echo "   Add 'Google Chrome' or 'Python' when prompted"
echo ""
echo "📖 Read HOTKEY_SETUP.md for more info"
echo ""
