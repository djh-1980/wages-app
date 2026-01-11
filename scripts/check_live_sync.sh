#!/bin/bash
# Script to check and update live server sync files

SERVER="daniel@tvs.daniel-hanson.co.uk"
APP_DIR="/var/www/tvs-wages"

echo "=================================================="
echo "🔍 CHECKING LIVE SERVER SYNC STATUS"
echo "=================================================="
echo ""

echo "📍 Current local commit:"
git log --oneline -1
echo ""

echo "📍 Current live server commit:"
ssh $SERVER "cd $APP_DIR && git log --oneline -1"
echo ""

echo "📊 Live server git status:"
ssh $SERVER "cd $APP_DIR && git status"
echo ""

echo "=================================================="
echo "🔄 UPDATING LIVE SERVER"
echo "=================================================="
echo ""

echo "⬇️  Pulling latest changes..."
ssh $SERVER "cd $APP_DIR && git pull origin main"
echo ""

echo "✅ Verifying sync files exist:"
ssh $SERVER "ls -lh $APP_DIR/scripts/sync_master.py $APP_DIR/app/utils/sync_logger.py"
echo ""

echo "📅 Checking cron schedule:"
ssh $SERVER "crontab -l | grep sync_master"
echo ""

echo "=================================================="
echo "🧪 TESTING SYNC"
echo "=================================================="
echo ""

echo "Would you like to run a test sync? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🚀 Running test sync on live server..."
    ssh $SERVER "cd $APP_DIR && python3 scripts/sync_master.py"
    echo ""
    echo "📋 Recent sync log entries:"
    ssh $SERVER "tail -30 $APP_DIR/logs/sync.log"
fi

echo ""
echo "=================================================="
echo "✅ COMPLETE"
echo "=================================================="
