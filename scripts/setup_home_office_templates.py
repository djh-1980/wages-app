#!/usr/bin/env python3
"""
Setup recurring templates for home office and server costs.
Run this to automatically create the monthly recurring expenses.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection

def setup_templates():
    """Create recurring templates for home office and server costs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get Home Office category ID
        cursor.execute("SELECT id FROM expense_categories WHERE name = 'Home Office'")
        home_office_cat = cursor.fetchone()
        
        # Get Premises Costs category ID  
        cursor.execute("SELECT id FROM expense_categories WHERE name = 'Premises Costs'")
        premises_cat = cursor.fetchone()
        
        if not home_office_cat or not premises_cat:
            print("❌ Error: Required expense categories not found")
            print("   Make sure 'Home Office' and 'Premises Costs' categories exist")
            return
        
        home_office_id = home_office_cat['id']
        premises_id = premises_cat['id']
        
        print("Creating recurring templates...\n")
        
        # Template 1: Home Office Allowance (10% of household costs)
        cursor.execute("""
            INSERT INTO recurring_templates 
            (name, category_id, expected_amount, frequency, merchant_pattern, 
             day_of_month, is_active, tolerance_amount, auto_import)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Home Office - Household Costs',
            home_office_id,
            40.50,  # £40.50 per month
            'monthly',
            'HOME OFFICE',
            1,  # 1st of month
            1,  # Active
            5.00,  # £5 tolerance
            0  # Don't auto-import (manual entry)
        ))
        
        print("✓ Created: Home Office - Household Costs")
        print("  Amount: £40.50/month")
        print("  Category: Home Office")
        print("  Day: 1st of each month")
        print()
        
        # Template 2: Server Electricity (24/7 operation)
        cursor.execute("""
            INSERT INTO recurring_templates 
            (name, category_id, expected_amount, frequency, merchant_pattern, 
             day_of_month, is_active, tolerance_amount, auto_import)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Server Electricity - 24/7 Operation',
            premises_id,
            36.50,  # £36.50 per month
            'monthly',
            'SERVER ELECTRIC',
            1,  # 1st of month
            1,  # Active
            5.00,  # £5 tolerance
            0  # Don't auto-import (manual entry)
        ))
        
        print("✓ Created: Server Electricity - 24/7 Operation")
        print("  Amount: £36.50/month")
        print("  Category: Premises Costs")
        print("  Day: 1st of each month")
        print()
        
        conn.commit()
        
        print("=" * 60)
        print("✅ Successfully created 2 recurring templates!")
        print("=" * 60)
        print()
        print("📊 Monthly Total: £77.00")
        print("📅 Annual Total: £924.00")
        print("💰 Tax Saving: £184.80/year (at 20% tax rate)")
        print()
        print("📝 Next Steps:")
        print("1. Go to Expenses → Recurring Templates")
        print("2. Review the templates")
        print("3. Add your first monthly expenses manually")
        print("4. Adjust amounts if your costs differ")
        print()
        print("💡 Tip: Add these on the 1st of each month:")
        print("   - Home Office: £40.50")
        print("   - Server Electricity: £36.50")
        print()
        print("📖 See docs/HOME_OFFICE_SERVER_CALCULATION.md for details")

if __name__ == '__main__':
    try:
        setup_templates()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
