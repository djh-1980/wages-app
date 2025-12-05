#!/usr/bin/env python3
"""
Seed expense categories if they don't exist.
Run this on the live server to ensure categories are populated.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection

def seed_categories():
    """Seed expense categories if they don't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if categories exist
        cursor.execute("SELECT COUNT(*) as count FROM expense_categories")
        count = cursor.fetchone()['count']
        
        if count > 0:
            print(f"✓ Found {count} existing expense categories")
            return
        
        print("Seeding expense categories...")
        
        # Insert default HMRC expense categories
        cursor.execute("""
            INSERT INTO expense_categories (name, hmrc_box, hmrc_box_number, description) VALUES
            ('Vehicle Costs', 'Vehicle costs', 20, 'Van loan, insurance, tax, MOT, repairs, tyres'),
            ('Fuel', 'Vehicle costs', 20, 'Fuel and oil for business vehicle'),
            ('Travel Costs', 'Travel costs', 21, 'Parking, tolls, public transport'),
            ('Home Office', 'Premises costs', 22, 'Home office allowance (£6/week simplified or actual costs)'),
            ('Premises Costs', 'Premises costs', 22, 'Rent, rates, power, insurance (if applicable)'),
            ('Admin Costs', 'Admin costs', 23, 'Phone, internet, stationery, postage'),
            ('Advertising', 'Advertising', 24, 'Marketing and advertising costs'),
            ('Interest', 'Interest', 25, 'Bank and loan interest'),
            ('Financial Charges', 'Financial charges', 26, 'Bank charges, card fees'),
            ('Professional Fees', 'Professional fees', 27, 'Accountant, legal, subscriptions'),
            ('Depreciation', 'Depreciation', 28, 'Equipment depreciation'),
            ('Other Expenses', 'Other expenses', 29, 'Tools, clothing, training, software')
        """)
        
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) as count FROM expense_categories")
        count = cursor.fetchone()['count']
        print(f"✓ Successfully seeded {count} expense categories")
        
        # List categories
        cursor.execute("SELECT name, hmrc_box FROM expense_categories ORDER BY hmrc_box_number")
        categories = cursor.fetchall()
        print("\nCategories:")
        for cat in categories:
            print(f"  - {cat['name']} ({cat['hmrc_box']})")

if __name__ == '__main__':
    try:
        seed_categories()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
