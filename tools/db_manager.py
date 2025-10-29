#!/usr/bin/env python3
"""Database management utilities."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.data_service import DataService
from app.database import init_database

def main():
    init_database()
    
    if len(sys.argv) < 2:
        print("Usage: python3 db_manager.py [backup|validate|optimize|sync]")
        return
    
    command = sys.argv[1]
    
    if command == "backup":
        result = DataService.create_intelligent_backup('manual')
        print(f"✅ Backup created: {result['backup_name']}")
    
    elif command == "validate":
        result = DataService.validate_data_integrity()
        print(f"Health: {result['overall_health']}")
        if result['issues_found']:
            print("Issues:", result['issues_found'])
    
    elif command == "optimize":
        result = DataService.optimize_database()
        print(f"✅ Optimized, saved {result['space_saved_mb']} MB")
    
    elif command == "sync":
        result = DataService.perform_intelligent_sync()
        print(f"✅ Sync completed in {result['total_time']:.2f}s")
    
    else:
        print("Unknown command:", command)

if __name__ == "__main__":
    main()
