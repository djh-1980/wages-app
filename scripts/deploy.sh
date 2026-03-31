#!/bin/bash
# TVS Wages - Production Deployment Script
# Usage: ./deploy.sh

set -e  # Exit on error

echo "=========================================="
echo "TVS Wages - Production Deployment"
echo "=========================================="
echo ""

# Navigate to project directory
cd /opt/tvstcms

# Stash any local changes
echo "📦 Stashing local changes..."
git stash

# Pull latest changes from git
echo "⬇️  Pulling latest changes from git..."
git pull origin main

# Activate virtual environment and install/update dependencies
echo "📚 Updating dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Restart the web service
echo "🔄 Restarting web service..."
sudo systemctl restart tvs-wages

# Check service status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "Service status:"
sudo systemctl status tvs-wages --no-pager -l

echo ""
echo "Recent sync logs:"
tail -20 logs/auto_sync.log

echo ""
echo "=========================================="
echo "Deployment finished successfully!"
echo "=========================================="
