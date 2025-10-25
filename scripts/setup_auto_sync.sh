#!/bin/bash
# Setup automatic daily run sheet sync on macOS

echo "=========================================="
echo "Setting up automatic daily run sheet sync"
echo "=========================================="
echo ""

# Get the project directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
PLIST_FILE="$HOME/Library/LaunchAgents/com.wages-app.runsheet-sync.plist"

echo "Project directory: $PROJECT_DIR"
echo "LaunchAgent file: $PLIST_FILE"
echo ""

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Create the plist file
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wages-app.runsheet-sync</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>$PROJECT_DIR/scripts/daily_runsheet_sync.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>20</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/runsheet_sync.log</string>
    
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/runsheet_sync_error.log</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Make the sync script executable
chmod +x "$PROJECT_DIR/scripts/daily_runsheet_sync.py"

# Unload if already loaded (ignore errors)
launchctl unload "$PLIST_FILE" 2>/dev/null

# Load the new configuration
launchctl load "$PLIST_FILE"

echo "✅ Setup complete!"
echo ""
echo "The sync will run automatically every day at 8:00 PM"
echo ""
echo "To check status:"
echo "  launchctl list | grep wages-app"
echo ""
echo "To view logs:"
echo "  tail -f $PROJECT_DIR/logs/runsheet_sync.log"
echo ""
echo "To test now:"
echo "  python3 $PROJECT_DIR/scripts/daily_runsheet_sync.py"
echo ""
echo "To disable:"
echo "  launchctl unload $PLIST_FILE"
echo ""
