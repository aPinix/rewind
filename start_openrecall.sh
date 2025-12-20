#!/bin/bash
# OpenRecall Background Launcher
# Starts the app and global hotkey listener in background (no visible terminal)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"

APP_LOG="$LOG_DIR/openrecall.log"
HOTKEY_LOG="$LOG_DIR/hotkey.log"
PID_FILE="$LOG_DIR/openrecall.pid"
APP_PID_FILE="$LOG_DIR/app.pid"
HOTKEY_PID_FILE="$LOG_DIR/hotkey.pid"

# Function to check if already running
is_running() {
    # Check if server is running on port 8082
    if lsof -i :8082 -sTCP:LISTEN > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Function to stop running instance
stop() {
    echo "🛑 Stopping OpenRecall..."
    
    # Kill all Python processes running openrecall
    ps aux | grep -i "[p]ython.*openrecall" | awk '{print $2}' | while read pid; do
        kill -9 $pid 2>/dev/null
    done
    
    # Also kill any uv processes
    ps aux | grep -i "[u]v run.*openrecall" | awk '{print $2}' | while read pid; do
        kill -9 $pid 2>/dev/null
    done
    
    rm -f "$PID_FILE" "$APP_PID_FILE" "$HOTKEY_PID_FILE"
    sleep 1
    echo "✅ OpenRecall stopped"
}

# Function to show status
status() {
    if is_running; then
        echo "✅ OpenRecall is running"
        echo "📝 Logs: $LOG_DIR"
        echo "⌨️  Hotkey: Cmd+Shift+Space to open"
        echo "⎋  ESC: Close window"
    else
        echo "❌ OpenRecall is not running"
    fi
}

# Handle commands
case "$1" in
    stop)
        stop
        exit 0
        ;;
    status)
        status
        exit 0
        ;;
    restart)
        stop
        sleep 2
        # Continue to start
        ;;
    start|"")
        # Continue to start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

# Check if already running
if is_running; then
    echo "⚠️  OpenRecall is already running!"
    status
    exit 1
fi

echo "🚀 Starting OpenRecall in background..."

# Start OpenRecall server
cd "$DIR"
nohup uv run -m openrecall.app > "$APP_LOG" 2>&1 &
APP_PID=$!
echo $APP_PID > "$APP_PID_FILE"

echo "⏳ Waiting for server to start..."
sleep 3

# Check if server started successfully
if ! ps -p $APP_PID > /dev/null 2>&1; then
    echo "❌ Failed to start OpenRecall server. Check $APP_LOG"
    cat "$APP_LOG" | tail -20
    exit 1
fi

# Start hotkey listener
nohup uv run "$DIR/launch_openrecall.py" > "$HOTKEY_LOG" 2>&1 &
HOTKEY_PID=$!
echo $HOTKEY_PID > "$HOTKEY_PID_FILE"

sleep 1

# Check if hotkey listener started
if ! ps -p $HOTKEY_PID > /dev/null 2>&1; then
    echo "❌ Failed to start hotkey listener. Check $HOTKEY_LOG"
    cat "$HOTKEY_LOG" | tail -20
    kill -9 $APP_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✅ OpenRecall started successfully!"
echo ""
echo "⌨️  Press Cmd+Shift+Space to open OpenRecall"
echo "⎋  Press ESC to close the window"
echo ""
echo "📝 Logs: $LOG_DIR"
echo "🛑 To stop: $0 stop"
echo ""
