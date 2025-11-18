#!/usr/bin/env python3
"""
Send a test sync notification email using tonight's actual data.
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.periodic_sync import periodic_sync_service
from app.services.sync_helpers import get_latest_runsheet_date, get_latest_payslip_week
from app.models.settings import SettingsModel
from datetime import datetime

def send_test_notification():
    """Send test notification with tonight's data."""
    
    # Get notification email from settings
    notification_email = SettingsModel.get_setting('notification_email')
    if not notification_email:
        notification_email = SettingsModel.get_setting('userEmail')
    
    if not notification_email:
        print("❌ Error: No notification email configured!")
        print("Please set notification_email in Settings → Data & Sync → Configure")
        return False
    
    print(f"📧 Sending test notification to: {notification_email}")
    
    # Create test summary with tonight's actual data
    test_summary = {
        'runsheets_downloaded': 1,
        'runsheets_imported': 15,
        'payslips_downloaded': 0,
        'payslips_imported': 0,
        'jobs_synced': 0,
        'errors': [],
        'duration_seconds': 12,
        'latest_runsheet_date': get_latest_runsheet_date() or '18/11/2025',
        'latest_payslip_week': get_latest_payslip_week() or 'Week 33, 2025'
    }
    
    print(f"\n📊 Test Summary:")
    print(f"  Runsheets Downloaded: {test_summary['runsheets_downloaded']}")
    print(f"  Jobs Imported: {test_summary['runsheets_imported']}")
    print(f"  Latest Runsheet: {test_summary['latest_runsheet_date']}")
    print(f"  Latest Payslip: {test_summary['latest_payslip_week']}")
    print(f"  Duration: {test_summary['duration_seconds']} seconds")
    
    # Send notification
    try:
        periodic_sync_service._send_sync_notification(test_summary)
        print(f"\n✅ Test notification sent successfully to {notification_email}!")
        print(f"📁 Email backup saved to: logs/sync_notifications/")
        return True
    except Exception as e:
        print(f"\n❌ Failed to send notification: {e}")
        return False

if __name__ == '__main__':
    send_test_notification()
