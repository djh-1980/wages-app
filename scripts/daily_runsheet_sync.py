#!/usr/bin/env python3
"""
Daily run sheet sync - downloads yesterday and today's run sheets.
Designed to run automatically via cron/launchd.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.download_runsheets_gmail import GmailRunSheetDownloader


def get_recent_date():
    """Get date for yesterday (run sheets sent evening before)."""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime('%Y/%m/%d')


def create_notification(count: int, date: str):
    """Create a notification file for the web app."""
    notification_file = Path('data/new_runsheets.json')
    notification_file.parent.mkdir(exist_ok=True)
    
    import json
    notification = {
        'count': count,
        'date': date,
        'timestamp': datetime.now().isoformat(),
        'read': False
    }
    
    with open(notification_file, 'w') as f:
        json.dump(notification, f)
    
    print(f"✅ Notification created: {count} new run sheets")


def main():
    """Run daily sync - downloads both run sheets and payslips."""
    print("=" * 70)
    print("DAILY AUTO-SYNC - RUN SHEETS & PAYSLIPS")
    print("=" * 70)
    print()
    
    # Get yesterday's date (run sheets sent evening before)
    search_date = get_recent_date()
    print(f"📅 Searching from: {search_date}")
    print()
    
    # Download, organize, and import
    downloader = GmailRunSheetDownloader()
    
    # Track downloads before running
    initial_runsheets = set(Path('RunSheets').rglob('*.pdf'))
    initial_payslips = set(Path('PaySlips').rglob('*.pdf')) if Path('PaySlips').exists() else set()
    
    # Run the download for both run sheets and payslips
    downloader.download_all(after_date=search_date)
    
    # Check how many new files were added
    final_runsheets = set(Path('RunSheets').rglob('*.pdf'))
    final_payslips = set(Path('PaySlips').rglob('*.pdf')) if Path('PaySlips').exists() else set()
    
    new_runsheets = final_runsheets - initial_runsheets
    new_payslips = final_payslips - initial_payslips
    
    total_new = len(new_runsheets) + len(new_payslips)
    
    if total_new > 0:
        create_notification(total_new, search_date)
        print(f"\n📊 Summary: {len(new_runsheets)} run sheets, {len(new_payslips)} payslips")
    
    print()
    print("=" * 70)
    print("SYNC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
