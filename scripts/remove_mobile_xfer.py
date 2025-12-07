#!/usr/bin/env python3
"""
Remove Mobile Xfer transactions from expenses.
These are internal transfers, not actual business expenses.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection

def remove_mobile_xfer():
    """Remove all Mobile Xfer transactions from expenses."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find Mobile Xfer transactions
        cursor.execute("""
            SELECT id, date, description, amount
            FROM expenses
            WHERE description LIKE '%Mobile Xfer%' OR description LIKE '%Via Mobile Xfer%'
        """)
        
        transactions = cursor.fetchall()
        
        if not transactions:
            print("✓ No Mobile Xfer transactions found")
            return
        
        print(f"Found {len(transactions)} Mobile Xfer transaction(s):\n")
        
        for trans in transactions:
            print(f"  ID: {trans['id']}")
            print(f"  Date: {trans['date']}")
            print(f"  Description: {trans['description']}")
            print(f"  Amount: £{trans['amount']:.2f}")
            print()
        
        # Delete them
        cursor.execute("""
            DELETE FROM expenses
            WHERE description LIKE '%Mobile Xfer%' OR description LIKE '%Via Mobile Xfer%'
        """)
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        print("=" * 60)
        print(f"✅ Successfully deleted {deleted_count} Mobile Xfer transaction(s)")
        print("=" * 60)
        print()
        print("💡 These were internal transfers, not business expenses")
        print("📝 Your expense totals have been corrected")

if __name__ == '__main__':
    try:
        remove_mobile_xfer()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
