#!/bin/bash

echo "================================================================================"
echo "WAGES APP - WEB DASHBOARD"
echo "================================================================================"
echo ""

# Kill any existing processes on port 5001
PIDS=$(lsof -ti:5001 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "🔄 Stopping existing server on port 5001..."
    kill -9 $PIDS 2>/dev/null
    sleep 1
    echo "✅ Existing server stopped"
    echo ""
fi

echo "🌐 Starting web server..."
echo ""
echo "📊 Once started, open your browser to:"
echo "    http://localhost:5001"
echo ""
echo "⏹️  Press Ctrl+C to stop the server"
echo ""
echo "================================================================================"
echo ""

./venv/bin/python3 -m flask --app app run --host=0.0.0.0 --port=5001
