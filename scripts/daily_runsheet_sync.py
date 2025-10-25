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
    """Run daily sync."""
    print("=" * 70)
    print("DAILY RUN SHEET SYNC")
    print("=" * 70)
    print()
    
    # Get yesterday's date (run sheets sent evening before)
    search_date = get_recent_date()
    print(f"📅 Searching for run sheets from: {search_date}")
    print()
    
    # Download, organize, and import
    downloader = GmailRunSheetDownloader()
    
    # Track downloads before running
    initial_files = set(Path('RunSheets').rglob('*.pdf'))
    
    # Run the download
    downloader.download_all_run_sheets(
        after_date=search_date,
        organize=True,
        auto_import=True
    )
    
    # Check how many new files were added
    final_files = set(Path('RunSheets').rglob('*.pdf'))
    new_files = final_files - initial_files
    
    if new_files:
        create_notification(len(new_files), search_date)
    
    print()
    print("=" * 70)
    print("SYNC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
