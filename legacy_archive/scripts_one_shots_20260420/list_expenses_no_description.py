#!/usr/bin/env python3
"""
List all expenses that don't have a description.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection

def list_no_description():
    """List all expenses without descriptions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find expenses with NULL or empty description
        cursor.execute("""
            SELECT 
                e.id,
                e.date,
                e.description,
                e.amount,
                c.name as category,
                e.tax_year
            FROM expenses e
            LEFT JOIN expense_categories c ON e.category_id = c.id
            WHERE e.description IS NULL OR e.description = '' OR TRIM(e.description) = ''
            ORDER BY e.date DESC
        """)
        
        expenses = cursor.fetchall()
        
        if not expenses:
            print("✓ All expenses have descriptions!")
            return
        
        print(f"Found {len(expenses)} expense(s) without descriptions:\n")
        print("=" * 80)
        
        total_amount = 0
        
        for exp in expenses:
            print(f"ID: {exp['id']}")
            print(f"Date: {exp['date']}")
            print(f"Amount: £{exp['amount']:.2f}")
            print(f"Category: {exp['category']}")
            print(f"Tax Year: {exp['tax_year']}")
            print(f"Description: {exp['description'] if exp['description'] else '(empty)'}")
            print("-" * 80)
            total_amount += exp['amount']
        
        print()
        print("=" * 80)
        print(f"Total: {len(expenses)} expenses without descriptions")
        print(f"Total Amount: £{total_amount:.2f}")
        print("=" * 80)
        print()
        print("💡 Tip: Add descriptions to help identify these expenses later")
        print("📝 You can edit them in the Expenses page")

if __name__ == '__main__':
    try:
        list_no_description()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
