#!/bin/bash
# Fix production server configuration

echo "=== Fixing Production Server ==="

# 1. Update systemd service to use app factory
echo "Step 1: Updating systemd service configuration..."
sudo sed -i 's/new_web_app:app/"app:create_app()"/g' /etc/systemd/system/tvs-wages.service

# 2. Reload systemd
echo "Step 2: Reloading systemd daemon..."
sudo systemctl daemon-reload

# 3. Restart service
echo "Step 3: Restarting tvs-wages service..."
sudo systemctl restart tvs-wages

# 4. Wait a moment for service to start
sleep 2

# 5. Check status
echo "Step 4: Checking service status..."
sudo systemctl status tvs-wages --no-pager -l

# 6. Test local connection
echo ""
echo "Step 5: Testing local connection..."
curl -I http://localhost:5001

echo ""
echo "=== Done! ==="
echo "Check https://tvs.daniel-hanson.co.uk to verify site is working"
