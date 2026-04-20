#!/usr/bin/env python3
"""
Add home office and server expenses for current tax year (2025/2026).
This adds the annual expenses starting from April 6th, 2025.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.expense import ExpenseModel

def add_current_year_expenses():
    """Add home office and server expenses for 2025/2026 tax year."""
    
    # Tax year starts April 6th
    expense_date = "06/04/2025"
    
    print("Adding home office and server expenses for tax year 2025/2026...")
    print(f"Date: {expense_date}")
    print()
    
    # Get categories
    categories = ExpenseModel.get_categories()
    category_map = {cat['name']: cat['id'] for cat in categories}
    
    if 'Home Office' not in category_map:
        print("❌ Error: 'Home Office' category not found")
        return
    
    if 'Premises Costs' not in category_map:
        print("❌ Error: 'Premises Costs' category not found")
        return
    
    # Check if expenses already exist
    if ExpenseModel.transaction_exists(expense_date, "Annual household costs (10% business use)", 486.00):
        print("⚠️  Home Office expense already exists for this date")
    else:
        # Add Home Office expense
        ExpenseModel.add_expense(
            date=expense_date,
            category_id=category_map['Home Office'],
            amount=486.00,
            description="Annual household costs (10% business use)",
            vat_amount=0,
            receipt_file=None,
            is_recurring=True,
            recurring_frequency='annually'
        )
        print("✓ Added: Home Office - Annual Household Costs")
        print("  Amount: £486.00")
        print("  Category: Home Office")
        print("  Description: Annual household costs (10% business use)")
        print()
    
    if ExpenseModel.transaction_exists(expense_date, "Server electricity - 24/7 operation", 438.00):
        print("⚠️  Server Electricity expense already exists for this date")
    else:
        # Add Server Electricity expense
        ExpenseModel.add_expense(
            date=expense_date,
            category_id=category_map['Premises Costs'],
            amount=438.00,
            description="Server electricity - 24/7 operation",
            vat_amount=0,
            receipt_file=None,
            is_recurring=True,
            recurring_frequency='annually'
        )
        print("✓ Added: Server Electricity - Annual 24/7 Operation")
        print("  Amount: £438.00")
        print("  Category: Premises Costs")
        print("  Description: Server electricity - 24/7 operation")
        print()
    
    print("=" * 60)
    print("✅ Successfully added home office expenses!")
    print("=" * 60)
    print()
    print("📊 Total Added: £924.00")
    print("💰 Tax Saving: £184.80/year (at 20% tax rate)")
    print()
    print("📝 What's Next:")
    print("1. Go to Expenses page to view your entries")
    print("2. Remember to add these again on 06/04/2026")
    print("3. Adjust amounts if your costs change")
    print()
    print("💡 Tip: Set a calendar reminder for April 6th each year!")

if __name__ == '__main__':
    try:
        add_current_year_expenses()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
