#!/usr/bin/env python3
"""
Fix client names in job_items table by extracting from description field.
"""

import sqlite3
import re
from pathlib import Path

def fix_client_names():
    """Update job_items with client names extracted from descriptions."""
    
    # Get database path
    db_path = Path(__file__).parent.parent / 'data' / 'database' / 'payslips.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all job items where client is NULL or empty
    cursor.execute("""
        SELECT id, description 
        FROM job_items 
        WHERE client IS NULL OR client = '' OR client = 'N/A'
    """)
    
    rows = cursor.fetchall()
    print(f"Found {len(rows)} job items with missing client names")
    
    updated_count = 0
    
    for row_id, description in rows:
        if not description:
            continue
        
        client_name = None
        
        # Try to extract client from description
        # Format: "Daniel Hanson: 4209480 | Xerox (UK) Technical***DO"
        fallback_match = re.search(r'Daniel Hanson:\s*\d+\s*\|\s*([^|*]+?)(?:\*\*\*|$)', description)
        if fallback_match:
            client_name = fallback_match.group(1).strip()
        
        if client_name:
            cursor.execute("""
                UPDATE job_items 
                SET client = ? 
                WHERE id = ?
            """, (client_name, row_id))
            updated_count += 1
            print(f"Updated job {row_id}: {client_name}")
    
    conn.commit()
    conn.close()
    
    print(f"\nUpdated {updated_count} job items with client names")

if __name__ == '__main__':
    fix_client_names()
