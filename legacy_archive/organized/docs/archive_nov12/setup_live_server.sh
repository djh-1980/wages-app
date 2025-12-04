#!/bin/bash
# Setup script for live server - Run this on 192.168.1.202

echo "=========================================="
echo "Wages App - Live Server Setup"
echo "=========================================="
echo ""

# Pull latest code
echo "1. Pulling latest code..."
cd ~/wages-app
git pull origin main

# Check for Gmail credentials
echo ""
echo "2. Checking Gmail credentials..."
if [ -f "credentials.json" ]; then
    echo "   ✓ credentials.json found"
else
    echo "   ✗ credentials.json NOT found"
    echo "   Please copy it from your local machine:"
    echo "   scp credentials.json wagesapp@192.168.1.202:~/wages-app/"
fi

if [ -f "token.json" ]; then
    echo "   ✓ token.json found (Gmail authorized)"
else
    echo "   ✗ token.json NOT found"
    echo "   You need to authorize Gmail. Run:"
    echo "   python3 scripts/download_runsheets_gmail.py"
fi

# Setup cron job
echo ""
echo "3. Setting up auto-sync cron job..."
echo "   Current crontab:"
crontab -l 2>/dev/null | grep auto_sync.py || echo "   (no auto-sync job found)"

echo ""
echo "   To add auto-sync (daily at 6 AM), run:"
echo "   (crontab -l 2>/dev/null; echo '0 6 * * * cd /home/wagesapp/wages-app && /usr/bin/python3 scripts/auto_sync.py >> logs/auto_sync.log 2>&1') | crontab -"

# Test auto-sync
echo ""
echo "4. Test auto-sync script..."
read -p "   Run test now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 scripts/auto_sync.py
fi

# Restart web app
echo ""
echo "5. Restarting web app..."
mkdir -p logs
pkill -f web_app.py
sleep 2
nohup python3 web_app.py > logs/web_app.log 2>&1 &
echo "   ✓ Web app restarted"

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. If Gmail not authorized, copy credentials.json and token.json"
echo "2. Add cron job for auto-sync (see command above)"
echo "3. Test via web: http://192.168.1.202:5001/settings"
echo ""
