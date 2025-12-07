#!/usr/bin/env python3
"""
Setup recurring templates for ANNUAL home office and server costs.
Run this to create yearly recurring expenses instead of monthly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection

def setup_annual_templates():
    """Create ANNUAL recurring templates for home office and server costs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Delete existing monthly templates if they exist
        cursor.execute("""
            DELETE FROM recurring_templates 
            WHERE name IN ('Home Office - Household Costs', 'Server Electricity - 24/7 Operation')
        """)
        
        # Get Home Office category ID
        cursor.execute("SELECT id FROM expense_categories WHERE name = 'Home Office'")
        home_office_cat = cursor.fetchone()
        
        # Get Premises Costs category ID  
        cursor.execute("SELECT id FROM expense_categories WHERE name = 'Premises Costs'")
        premises_cat = cursor.fetchone()
        
        if not home_office_cat or not premises_cat:
            print("❌ Error: Required expense categories not found")
            return
        
        home_office_id = home_office_cat['id']
        premises_id = premises_cat['id']
        
        print("Creating ANNUAL recurring templates...\n")
        
        # Template 1: Home Office Allowance (ANNUAL)
        cursor.execute("""
            INSERT INTO recurring_templates 
            (name, category_id, expected_amount, frequency, merchant_pattern, 
             day_of_month, is_active, tolerance_amount, auto_import)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Home Office - Annual Household Costs',
            home_office_id,
            486.00,  # £486 per year (£40.50 × 12)
            'annually',
            'HOME OFFICE ANNUAL',
            6,  # April 6th (start of tax year)
            1,  # Active
            50.00,  # £50 tolerance
            0  # Don't auto-import (manual entry)
        ))
        
        print("✓ Created: Home Office - Annual Household Costs")
        print("  Amount: £486.00/year")
        print("  Category: Home Office")
        print("  Date: April 6th (start of tax year)")
        print()
        
        # Template 2: Server Electricity (ANNUAL)
        cursor.execute("""
            INSERT INTO recurring_templates 
            (name, category_id, expected_amount, frequency, merchant_pattern, 
             day_of_month, is_active, tolerance_amount, auto_import)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Server Electricity - Annual 24/7 Operation',
            premises_id,
            438.00,  # £438 per year (£36.50 × 12)
            'annually',
            'SERVER ELECTRIC ANNUAL',
            6,  # April 6th (start of tax year)
            1,  # Active
            50.00,  # £50 tolerance
            0  # Don't auto-import (manual entry)
        ))
        
        print("✓ Created: Server Electricity - Annual 24/7 Operation")
        print("  Amount: £438.00/year")
        print("  Category: Premises Costs")
        print("  Date: April 6th (start of tax year)")
        print()
        
        conn.commit()
        
        print("=" * 60)
        print("✅ Successfully created 2 ANNUAL recurring templates!")
        print("=" * 60)
        print()
        print("📊 Annual Total: £924.00")
        print("💰 Tax Saving: £184.80/year (at 20% tax rate)")
        print()
        print("📝 Next Steps:")
        print("1. Add ONE expense on April 6th each year:")
        print("   - Home Office: £486.00")
        print("   - Server Electricity: £438.00")
        print()
        print("2. Or add now for current tax year (2025/2026):")
        print("   - Date: 06/04/2025")
        print("   - Total: £924.00")
        print()
        print("💡 Benefits of Annual Entry:")
        print("   ✓ Only 2 entries per year instead of 24")
        print("   ✓ Easier to track")
        print("   ✓ Same tax deduction")
        print("   ✓ Less admin work")
        print()
        print("📖 See docs/HOME_OFFICE_SERVER_CALCULATION.md for details")

if __name__ == '__main__':
    try:
        setup_annual_templates()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
