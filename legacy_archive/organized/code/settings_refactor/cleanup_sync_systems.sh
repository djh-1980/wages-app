#!/bin/bash
# Cleanup Script: Consolidate to Master Sync Only
# This script removes all redundant sync systems and keeps only sync_master.py

echo "🧹 CLEANING UP SYNC SYSTEMS"
echo "============================================================"

# 1. Update cron job to only use master sync
echo "📅 Updating cron job..."
(crontab -l 2>/dev/null | grep -v "sync" ; echo "# Master Sync Schedule") | crontab -
(crontab -l 2>/dev/null ; echo "0 20 * * * cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1") | crontab -
(crontab -l 2>/dev/null ; echo "0 21 * * * cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1") | crontab -
(crontab -l 2>/dev/null ; echo "0 9 * * 2 cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1") | crontab -

# 2. Stop and disable periodic sync service
echo "🛑 Stopping periodic sync service..."
sudo systemctl stop periodic-sync 2>/dev/null || echo "   Service not running"
sudo systemctl disable periodic-sync 2>/dev/null || echo "   Service not enabled"

# 3. Clean up old log files
echo "🗂️  Cleaning up old log files..."
cd /var/www/tvs-wages
rm -f logs/auto_sync.log
rm -f logs/periodic_sync.log
echo "   ✅ Removed old log files"

# 4. Archive old sync scripts (don't delete, just move)
echo "📦 Archiving old sync scripts..."
mkdir -p scripts/archive
mv scripts/production/download_payslips_gmail.py scripts/archive/ 2>/dev/null || echo "   Already archived"
mv scripts/production/import_*.py scripts/archive/ 2>/dev/null || echo "   Already archived"
echo "   ✅ Old scripts archived"

# 5. Create unified log if it doesn't exist
echo "📝 Setting up unified log..."
touch logs/sync.log
chmod 664 logs/sync.log
echo "   ✅ Unified log ready"

echo ""
echo "✅ CLEANUP COMPLETE!"
echo "============================================================"
echo "📊 Current Setup:"
echo "   • Sync System: sync_master.py ONLY"
echo "   • Log File: logs/sync.log ONLY"
echo "   • Schedule: 8PM, 9PM daily + Tuesday 9AM"
echo "   • Web Interface: Reads from unified log"
echo ""
echo "🚀 Your sync system is now clean and unified!"
