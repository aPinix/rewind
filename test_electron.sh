#!/bin/bash
# Quick test script for Electron app

echo "🧪 Testing OpenRecall Electron App"
echo ""

# Check if backend is running
if ! lsof -i :8082 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "❌ Backend not running on port 8082"
    echo "Starting backend..."
    ./start_openrecall.sh start
    sleep 3
fi

if lsof -i :8082 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "✅ Backend is running"
else
    echo "❌ Failed to start backend"
    exit 1
fi

# Check if electron dependencies are installed
if [ ! -d "electron-app/node_modules" ]; then
    echo "📦 Installing Electron dependencies..."
    cd electron-app
    npm install
    cd ..
fi

echo ""
echo "✅ Ready to launch Electron!"
echo ""
echo "Starting in 2 seconds..."
sleep 2

cd electron-app
npm start
