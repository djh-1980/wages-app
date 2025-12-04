#!/bin/bash

echo "================================================================================"
echo "WAGES APP - WEB DASHBOARD"
echo "================================================================================"
echo ""
echo "🌐 Starting web server..."
echo ""
echo "📊 Once started, open your browser to:"
echo "    http://localhost:5001"
echo ""
echo "⏹️  Press Ctrl+C to stop the server"
echo ""
echo "================================================================================"
echo ""

python3 -m flask --app app run --host=0.0.0.0 --port=5001
