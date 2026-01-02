#!/bin/bash
# OpenReLife Electron Launcher
# Starts both the Python backend and Electron frontend

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$DIR/.."
LOG_DIR="$DIR/../logs"
mkdir -p "$LOG_DIR"

BACKEND_LOG="$LOG_DIR/openrelife-backend.log"
BACKEND_PID_FILE="$LOG_DIR/backend.pid"

# Function to check if backend is running
is_backend_running() {
    if lsof -i :8082 -sTCP:LISTEN > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Function to stop backend
stop_backend() {
    echo "🛑 Stopping backend..."
    
    # Kill Python processes
    ps aux | grep -i "[p]ython.*openrelife" | awk '{print $2}' | while read pid; do
        kill -9 $pid 2>/dev/null
    done
    
    # Kill uv processes
    ps aux | grep -i "[u]v run.*openrelife" | awk '{print $2}' | while read pid; do
        kill -9 $pid 2>/dev/null
    done
    
    rm -f "$BACKEND_PID_FILE"
    sleep 1
    echo "✅ Backend stopped"
}

# Function to start backend
start_backend() {
    if is_backend_running; then
        echo "✅ Backend already running"
        return 0
    fi
    
    echo "🚀 Starting OpenReLife backend..."
    cd "$BACKEND_DIR"
    nohup uv run python -m openrelife.app > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$BACKEND_PID_FILE"
    
    echo "⏳ Waiting for backend to start..."
    for i in {1..10}; do
        sleep 1
        if is_backend_running; then
            echo "✅ Backend started successfully"
            return 0
        fi
    done
    
    echo "❌ Failed to start backend. Check $BACKEND_LOG"
    cat "$BACKEND_LOG" | tail -20
    return 1
}

# Handle commands
case "$1" in
    stop)
        stop_backend
        echo "💡 To stop Electron app, use Cmd+Q"
        exit 0
        ;;
    *)
        # Default: start
        ;;
esac

# Start backend
#if ! start_backend; then
#    exit 1
#fi

# Start Electron
echo ""
echo "🎯 Starting Electron app..."
echo ""
cd "$DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start Electron
npm start
