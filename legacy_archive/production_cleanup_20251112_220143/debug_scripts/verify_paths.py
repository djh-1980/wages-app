#!/usr/bin/env python3
"""
Path Verification Script
Verify that all new paths exist and are accessible.
"""

from pathlib import Path

def verify_data_structure():
    """Verify the new data directory structure."""
    
    required_paths = [
        'data/payslips/Manual',
        'data/payslips/Processing', 
        'data/payslips/Processed',
        'data/payslips/Failed',
        'data/payslips/Archive',
        'data/runsheets/Manual',
        'data/runsheets/Processing',
        'data/runsheets/Processed', 
        'data/runsheets/Failed',
        'data/runsheets/Archive',
        'data/uploads/Manual',
        'data/uploads/Temp',
        'data/uploads/Queue',
        'data/temp/downloads',
        'data/temp/processing',
        'data/temp/failed',
        'data/backups/daily',
        'data/backups/weekly',
        'data/backups/monthly'
    ]
    
    print("🔍 Verifying data directory structure...")
    
    all_good = True
    for path_str in required_paths:
        path = Path(path_str)
        if path.exists():
            print(f"   ✅ {path_str}")
        else:
            print(f"   ❌ {path_str} - MISSING")
            all_good = False
    
    if all_good:
        print("\n🎉 All required directories exist!")
    else:
        print("\n⚠️  Some directories are missing. Run reorganize_structure.py again.")
    
    return all_good

if __name__ == '__main__':
    verify_data_structure()
