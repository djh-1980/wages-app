#!/bin/bash
# Universal setup script for automatic daily run sheet sync
# Works on macOS (launchd) and Linux (systemd)

set -e

echo "=========================================="
echo "Setting up automatic daily run sheet sync"
echo "=========================================="
echo ""

# Get the project directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
PYTHON_PATH=$(which python3)

echo "Project directory: $PROJECT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "Detected: macOS"
elif [[ -f /etc/debian_version ]]; then
    OS="debian"
    echo "Detected: Debian/Ubuntu Linux"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo ""

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Make the sync script executable
chmod +x "$PROJECT_DIR/scripts/daily_runsheet_sync.py"

if [ "$OS" == "macos" ]; then
    # ============================================
    # macOS Setup (launchd)
    # ============================================
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.wages-app.runsheet-sync.plist"
    
    echo "Creating LaunchAgent: $PLIST_FILE"
    
    # Create LaunchAgents directory
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
        <string>$PYTHON_PATH</string>
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
    
    # Unload if already loaded (ignore errors)
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    
    # Load the new configuration
    launchctl load "$PLIST_FILE"
    
    echo ""
    echo "✅ macOS LaunchAgent setup complete!"
    echo ""
    echo "The sync will run automatically every day at 8:00 PM"
    echo ""
    echo "Commands:"
    echo "  Check status:  launchctl list | grep wages-app"
    echo "  View logs:     tail -f $PROJECT_DIR/logs/runsheet_sync.log"
    echo "  Test now:      python3 $PROJECT_DIR/scripts/daily_runsheet_sync.py"
    echo "  Disable:       launchctl unload $PLIST_FILE"
    echo ""

elif [ "$OS" == "debian" ]; then
    # ============================================
    # Debian/Ubuntu Setup (systemd)
    # ============================================
    
    SERVICE_FILE="/etc/systemd/system/wages-app-runsheet-sync.service"
    TIMER_FILE="/etc/systemd/system/wages-app-runsheet-sync.timer"
    
    echo "Creating systemd service and timer"
    echo "This requires sudo privileges..."
    echo ""
    
    # Create the service file
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Wages App Run Sheet Sync
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PYTHON_PATH $PROJECT_DIR/scripts/daily_runsheet_sync.py
StandardOutput=append:$PROJECT_DIR/logs/runsheet_sync.log
StandardError=append:$PROJECT_DIR/logs/runsheet_sync_error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Create the timer file (runs daily at 8:00 PM)
    sudo tee "$TIMER_FILE" > /dev/null << EOF
[Unit]
Description=Wages App Run Sheet Sync Timer
Requires=wages-app-runsheet-sync.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 20:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start the timer
    sudo systemctl enable wages-app-runsheet-sync.timer
    sudo systemctl start wages-app-runsheet-sync.timer
    
    echo ""
    echo "✅ Debian/Ubuntu systemd setup complete!"
    echo ""
    echo "The sync will run automatically every day at 8:00 PM"
    echo ""
    echo "Commands:"
    echo "  Check status:  sudo systemctl status wages-app-runsheet-sync.timer"
    echo "  View logs:     tail -f $PROJECT_DIR/logs/runsheet_sync.log"
    echo "  Test now:      sudo systemctl start wages-app-runsheet-sync.service"
    echo "  Disable:       sudo systemctl disable wages-app-runsheet-sync.timer"
    echo "  Stop:          sudo systemctl stop wages-app-runsheet-sync.timer"
    echo ""
fi

echo "=========================================="
echo "Setup complete!"
echo "=========================================="
