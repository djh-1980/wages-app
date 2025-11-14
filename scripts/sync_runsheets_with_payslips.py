#!/usr/bin/env python3
"""
Sync runsheet data with payslip data.
Uses the existing RunsheetModel.update_job_pay_info() function.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.runsheet import RunsheetModel

def sync_runsheets_with_payslips():
    """
    Update runsheet jobs with pay information from payslips.
    Uses the existing model function that already works.
    """
    
    print("=" * 60)
    print("SYNCING RUNSHEETS WITH PAYSLIP DATA")
    print("=" * 60)
    print()
    
    try:
        # Use the existing function that already works
        RunsheetModel.update_job_pay_info()
        
        print()
        print("=" * 60)
        print("SYNC COMPLETE")
        print("=" * 60)
        print("Runsheet jobs updated with payslip data:")
        print("  - Pay amounts")
        print("  - Pay rates")
        print("  - Pay units")
        print("  - Week numbers")
        print("  - Tax years")
        print("=" * 60)
        
        return {'success': True}
        
    except Exception as e:
        print(f"Error syncing data: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    sync_runsheets_with_payslips()
