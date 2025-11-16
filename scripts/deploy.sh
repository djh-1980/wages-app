#!/bin/bash
# Quick deployment script - Update server and clear Cloudflare cache

set -e  # Exit on error

echo "=========================================="
echo "TVS Wages - Quick Deploy"
echo "=========================================="
echo

# Step 1: Update server
echo "📦 Updating server..."
ssh -i ~/.ssh/tvs_wages_proxmox tvswages@192.168.1.202 << 'EOF'
cd /var/www/tvs-wages
echo "  - Pulling latest code from GitHub..."
git pull origin main
echo "  - Restarting application..."
sudo systemctl restart tvs-wages
echo "  ✓ Server updated!"
EOF

echo

# Step 2: Clear Cloudflare cache
echo "🔄 Clearing Cloudflare cache..."
echo "  Please manually purge cache in Cloudflare Dashboard:"
echo "  1. Go to: https://dash.cloudflare.com"
echo "  2. Select: daniel-hanson.co.uk"
echo "  3. Caching → Purge Everything"
echo
echo "  Or purge specific files:"
echo "  - https://tvs.daniel-hanson.co.uk/static/css/reports.css"
echo "  - https://tvs.daniel-hanson.co.uk/static/css/unified-styles.css"
echo "  - https://tvs.daniel-hanson.co.uk/static/js/weekly-summary.js"
echo

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "  1. Clear Cloudflare cache (see above)"
echo "  2. Hard refresh browser: Cmd+Shift+R"
echo "  3. Test at: http://tvs.daniel-hanson.co.uk"
echo
