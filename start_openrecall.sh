#!/bin/bash
# OpenRecall Background Launcher
# Starts the app and global hotkey listener in background (no visible terminal)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"

APP_LOG="$LOG_DIR/openrecall.log"
HOTKEY_LOG="$LOG_DIR/hotkey.log"
PID_FILE="$LOG_DIR/openrecall.pid"

# Function to check if already running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to stop running instance
stop() {
    if [ -f "$PID_FILE" ]; then
        echo "🛑 Stopping OpenRecall..."
        PID=$(cat "$PID_FILE")
        
        # Kill child processes
        pkill -P $PID 2>/dev/null
        kill $PID 2>/dev/null
        
        rm -f "$PID_FILE"
        echo "✅ OpenRecall stopped"
    else
        echo "ℹ️  OpenRecall is not running"
    fi
}

# Function to show status
status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "✅ OpenRecall is running (PID: $PID)"
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

# Start everything in background
(
    # Start OpenRecall server
    cd "$DIR"
    uv run -m openrecall.app > "$APP_LOG" 2>&1 &
    APP_PID=$!
    
    # Wait for server to start
    sleep 3
    
    # Check if server started successfully
    if ! kill -0 $APP_PID 2>/dev/null; then
        echo "❌ Failed to start OpenRecall server. Check $APP_LOG"
        exit 1
    fi
    
    # Start hotkey listener
    uv run "$DIR/launch_openrecall.py" > "$HOTKEY_LOG" 2>&1 &
    HOTKEY_PID=$!
    
    # Wait a moment to check if hotkey listener started
    sleep 1
    if ! kill -0 $HOTKEY_PID 2>/dev/null; then
        echo "❌ Failed to start hotkey listener. Check $HOTKEY_LOG"
        kill $APP_PID 2>/dev/null
        exit 1
    fi
    
    # Save main PID
    echo $$ > "$PID_FILE"
    
    # Wait for processes
    wait $APP_PID $HOTKEY_PID
    
    # Cleanup
    rm -f "$PID_FILE"
    
) &

# Detach from terminal
disown

# Wait a moment to check if started successfully
sleep 2

if is_running; then
    echo ""
    echo "✅ OpenRecall started successfully!"
    echo ""
    echo "⌨️  Press Cmd+Shift+Space to open OpenRecall"
    echo "⎋  Press ESC to close the window"
    echo ""
    echo "📝 Logs: $LOG_DIR"
    echo "🛑 To stop: $0 stop"
    echo ""
else
    echo ""
    echo "❌ Failed to start OpenRecall"
    echo "📝 Check logs in: $LOG_DIR"
    echo ""
    exit 1
fi
