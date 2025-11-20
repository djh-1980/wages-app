#!/usr/bin/env python3
"""
Quick fix script for live site sync issues
Run this on your live site (tvs.daniel-hanson.co.uk)
"""

def fix_live_sync():
    """Fix the sync issues on live site"""
    try:
        from app.services.periodic_sync import periodic_sync_service
        from app.models.settings import SettingsModel
        
        print("🔧 Fixing live site sync issues...")
        
        # 1. Fix notification settings
        print("1. Fixing notification settings...")
        SettingsModel.set_setting('notify_on_error_only', 'false')
        print("   ✅ Set notify_on_error_only = false")
        
        # 2. Reset sync tracking flags
        print("2. Resetting sync tracking...")
        periodic_sync_service.runsheet_completed_today = False
        periodic_sync_service.payslip_completed_this_week = False
        periodic_sync_service.last_check_date = None
        periodic_sync_service.last_runsheet_date_processed = None
        periodic_sync_service.retry_count = 0
        periodic_sync_service.last_error = None
        print("   ✅ Reset all sync tracking flags")
        
        # 3. Restart sync service with new settings
        print("3. Restarting sync service...")
        periodic_sync_service.stop_periodic_sync()
        periodic_sync_service._load_config()  # Reload config
        periodic_sync_service.start_periodic_sync()
        print("   ✅ Sync service restarted")
        
        # 4. Check status
        print("4. Checking status...")
        status = periodic_sync_service.get_sync_status()
        print(f"   Service running: {status['is_running']}")
        print(f"   Current state: {status['current_state']}")
        print(f"   Runsheet completed today: {status['runsheet_completed_today']}")
        print(f"   Latest runsheet: {status['latest_runsheet_date']}")
        
        # 5. Force a sync attempt
        print("5. Testing sync...")
        periodic_sync_service.sync_latest(dry_run=True)
        print("   ✅ Dry run completed")
        
        print("\n🎉 Live site sync fixes applied successfully!")
        print("📧 You should now receive email notifications for successful syncs")
        print("🔄 Next sync will attempt to download new runsheets")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing sync: {e}")
        return False

if __name__ == "__main__":
    fix_live_sync()
