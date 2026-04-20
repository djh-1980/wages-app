#!/usr/bin/env python3
"""
List all expenses that don't have notes.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection

def list_no_notes():
    """List all expenses without notes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if notes column exists
        cursor.execute("PRAGMA table_info(expenses)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        if 'notes' not in columns:
            print("⚠️  The expenses table doesn't have a 'notes' column")
            print("📝 Notes are tracked in the description field")
            return
        
        # Find expenses with NULL or empty notes
        cursor.execute("""
            SELECT 
                e.id,
                e.date,
                e.description,
                e.amount,
                c.name as category,
                e.tax_year,
                e.notes
            FROM expenses e
            LEFT JOIN expense_categories c ON e.category_id = c.id
            WHERE e.notes IS NULL OR e.notes = '' OR TRIM(e.notes) = ''
            ORDER BY e.date DESC
        """)
        
        expenses = cursor.fetchall()
        
        if not expenses:
            print("✓ All expenses have notes!")
            return
        
        print(f"Found {len(expenses)} expense(s) without notes:\n")
        print("=" * 100)
        
        total_amount = 0
        
        for exp in expenses:
            print(f"ID: {exp['id']}")
            print(f"Date: {exp['date']}")
            print(f"Amount: £{exp['amount']:.2f}")
            print(f"Category: {exp['category']}")
            print(f"Description: {exp['description'][:60]}..." if len(exp['description']) > 60 else f"Description: {exp['description']}")
            print(f"Tax Year: {exp['tax_year']}")
            print(f"Notes: (empty)")
            print("-" * 100)
            total_amount += exp['amount']
        
        print()
        print("=" * 100)
        print(f"Total: {len(expenses)} expenses without notes")
        print(f"Total Amount: £{total_amount:.2f}")
        print("=" * 100)
        print()
        print("💡 Notes are optional but helpful for:")
        print("   - Adding context to expenses")
        print("   - Explaining unusual amounts")
        print("   - Linking to receipts or invoices")
        print("   - Reminders for tax time")

if __name__ == '__main__':
    try:
        list_no_notes()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
