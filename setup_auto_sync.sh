#!/bin/bash
# Setup automatic sync using cron

echo "🤖 Setting up automated sync..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Backup current crontab
echo "📋 Backing up current crontab..."
crontab -l > crontab_backup.txt 2>/dev/null || echo "No existing crontab found"

# Create optimized cron entries based on Gmail patterns
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📅 Choose your automation schedule:"
echo "1. Daily at 7 PM (recommended for end-of-day processing)"
echo "2. Weekdays at 6 PM (business days only)"
echo "3. Tuesday 9 AM + Daily 7 PM (payslip + runsheet optimized)"
echo "4. Multiple daily checks (handles late arrivals)"
echo "5. Custom schedule"
echo ""
read -p "Enter choice (1-5): " choice

case $choice in
    1)
        CRON_ENTRY="0 19 * * * cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        SCHEDULE_DESC="Daily at 7:00 PM"
        ;;
    2)
        CRON_ENTRY="0 18 * * 1-5 cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        SCHEDULE_DESC="Weekdays at 6:00 PM"
        ;;
    3)
        CRON_ENTRY1="0 9 * * 2 cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        CRON_ENTRY2="0 19 * * * cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        SCHEDULE_DESC="Tuesday 9 AM + Daily 7 PM"
        ;;
    4)
        # Multiple daily checks for late arrivals
        CRON_ENTRY1="0 18 * * 1-5 cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        CRON_ENTRY2="0 21 * * 1-5 cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        CRON_ENTRY3="0 9 * * 2 cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        SCHEDULE_DESC="Multiple checks: Weekdays 6PM & 9PM + Tuesday 9AM"
        ;;
    5)
        read -p "Enter cron schedule (e.g., '0 18 * * 1-5'): " custom_time
        CRON_ENTRY="$custom_time cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        SCHEDULE_DESC="Custom: $custom_time"
        ;;
    *)
        CRON_ENTRY="0 19 * * * cd $SCRIPT_DIR && python3 scripts/sync_master.py >> logs/auto_sync.log 2>&1"
        SCHEDULE_DESC="Daily at 7:00 PM (default)"
        ;;
esac

echo "📅 Adding cron job(s): $SCHEDULE_DESC"

# Add to crontab (remove existing sync entries first)
if [ "$choice" = "3" ]; then
    (crontab -l 2>/dev/null | grep -v "sync_master.py" | grep -v "download_runsheets_gmail.py" | grep -v "extract_payslips.py"; echo "$CRON_ENTRY1"; echo "$CRON_ENTRY2") | crontab -
elif [ "$choice" = "4" ]; then
    (crontab -l 2>/dev/null | grep -v "sync_master.py" | grep -v "download_runsheets_gmail.py" | grep -v "extract_payslips.py"; echo "$CRON_ENTRY1"; echo "$CRON_ENTRY2"; echo "$CRON_ENTRY3") | crontab -
else
    (crontab -l 2>/dev/null | grep -v "sync_master.py" | grep -v "download_runsheets_gmail.py" | grep -v "extract_payslips.py"; echo "$CRON_ENTRY") | crontab -
fi

echo "✅ Automated sync setup complete!"
echo ""
echo "📊 Summary:"
echo "   • Daily sync at 7:00 PM"
echo "   • Logs saved to: logs/auto_sync.log"
echo "   • Backup saved to: crontab_backup.txt"
echo ""
echo "🔧 Management commands:"
echo "   View logs: tail -f logs/auto_sync.log"
echo "   Edit cron: crontab -e"
echo "   List cron: crontab -l"
echo "   Remove cron: crontab -r"
echo ""
echo "🧪 Test run:"
echo "   cd $SCRIPT_DIR && python3 scripts/sync_master.py"
