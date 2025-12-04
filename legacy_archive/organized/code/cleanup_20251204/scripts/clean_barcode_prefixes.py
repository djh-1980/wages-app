#!/usr/bin/env python3
"""
Clean barcode prefixes from existing paypoint stock data.
Removes prefixes like C|, D|, etc. from serial_ptid and trace_stock fields.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection

def clean_barcode_prefixes():
    """Remove barcode prefixes from existing paypoint stock and returns records."""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        total_updates = 0
        
        # Clean paypoint_stock table
        print("🔍 Scanning paypoint_stock table for barcode prefixes...")
        cursor.execute("""
            SELECT id, serial_ptid, trace_stock 
            FROM paypoint_stock 
            WHERE serial_ptid LIKE '%|%' OR trace_stock LIKE '%|%'
        """)
        
        stock_records = cursor.fetchall()
        
        if stock_records:
            print(f"📋 Found {len(stock_records)} stock records with barcode prefixes:")
            total_updates += clean_stock_records(cursor, stock_records)
        else:
            print("✅ No stock records found with barcode prefixes.")
        
        print()
        
        # Clean paypoint_returns table
        print("🔍 Scanning paypoint_returns table for barcode prefixes...")
        cursor.execute("""
            SELECT id, return_serial_ptid, return_trace 
            FROM paypoint_returns 
            WHERE return_serial_ptid LIKE '%|%' OR return_trace LIKE '%|%'
        """)
        
        return_records = cursor.fetchall()
        
        if return_records:
            print(f"📋 Found {len(return_records)} return records with barcode prefixes:")
            total_updates += clean_return_records(cursor, return_records)
        else:
            print("✅ No return records found with barcode prefixes.")
        
        print()
        
        # Clean paypoint_deployments table
        print("🔍 Scanning paypoint_deployments table for barcode prefixes...")
        cursor.execute("""
            SELECT id, serial_ptid, trace_stock 
            FROM paypoint_deployments 
            WHERE serial_ptid LIKE '%|%' OR trace_stock LIKE '%|%'
        """)
        
        deployment_records = cursor.fetchall()
        
        if deployment_records:
            print(f"📋 Found {len(deployment_records)} deployment records with barcode prefixes:")
            total_updates += clean_deployment_records(cursor, deployment_records)
        else:
            print("✅ No deployment records found with barcode prefixes.")
        
        if total_updates > 0:
            conn.commit()
            print()
            print(f"✅ Successfully cleaned {total_updates} total records!")
            print("🔄 Barcode prefixes have been removed from the database.")
        else:
            print()
            print("ℹ️  No updates needed - all prefixes were already clean.")

def clean_stock_records(cursor, records):
    """Clean barcode prefixes from stock records."""
    updates_made = 0
    
    for record in records:
        record_id, serial_ptid, trace_stock = record
        
        # Clean serial_ptid
        clean_serial = clean_barcode_field(serial_ptid)
        
        # Clean trace_stock
        clean_trace = clean_barcode_field(trace_stock)
        
        # Check if any changes were made
        if clean_serial != serial_ptid or clean_trace != trace_stock:
            print(f"🔧 Stock Record ID {record_id}:")
            if clean_serial != serial_ptid:
                print(f"   Serial/TID: '{serial_ptid}' → '{clean_serial}'")
            if clean_trace != trace_stock:
                print(f"   Trace/Stock: '{trace_stock}' → '{clean_trace}'")
            
            # Update the record
            cursor.execute("""
                UPDATE paypoint_stock 
                SET serial_ptid = ?, trace_stock = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (clean_serial, clean_trace, record_id))
            
            updates_made += 1
            print()
    
    return updates_made

def clean_return_records(cursor, records):
    """Clean barcode prefixes from return records."""
    updates_made = 0
    
    for record in records:
        record_id, return_serial_ptid, return_trace = record
        
        # Clean return_serial_ptid
        clean_serial = clean_barcode_field(return_serial_ptid)
        
        # Clean return_trace
        clean_trace = clean_barcode_field(return_trace)
        
        # Check if any changes were made
        if clean_serial != return_serial_ptid or clean_trace != return_trace:
            print(f"🔧 Return Record ID {record_id}:")
            if clean_serial != return_serial_ptid:
                print(f"   Return Serial/TID: '{return_serial_ptid}' → '{clean_serial}'")
            if clean_trace != return_trace:
                print(f"   Return Trace: '{return_trace}' → '{clean_trace}'")
            
            # Update the record
            cursor.execute("""
                UPDATE paypoint_returns 
                SET return_serial_ptid = ?, return_trace = ?
                WHERE id = ?
            """, (clean_serial, clean_trace, record_id))
            
            updates_made += 1
            print()
    
    return updates_made

def clean_deployment_records(cursor, records):
    """Clean barcode prefixes from deployment records."""
    updates_made = 0
    
    for record in records:
        record_id, serial_ptid, trace_stock = record
        
        # Clean serial_ptid
        clean_serial = clean_barcode_field(serial_ptid)
        
        # Clean trace_stock
        clean_trace = clean_barcode_field(trace_stock)
        
        # Check if any changes were made
        if clean_serial != serial_ptid or clean_trace != trace_stock:
            print(f"🔧 Deployment Record ID {record_id}:")
            if clean_serial != serial_ptid:
                print(f"   Serial/TID: '{serial_ptid}' → '{clean_serial}'")
            if clean_trace != trace_stock:
                print(f"   Trace/Stock: '{trace_stock}' → '{clean_trace}'")
            
            # Update the record
            cursor.execute("""
                UPDATE paypoint_deployments 
                SET serial_ptid = ?, trace_stock = ?
                WHERE id = ?
            """, (clean_serial, clean_trace, record_id))
            
            updates_made += 1
            print()
    
    return updates_made

def clean_barcode_field(field_value):
    """Clean a single barcode field by removing prefixes."""
    if not field_value or '|' not in field_value:
        return field_value
    
    parts = field_value.split('|')
    if len(parts) == 2 and len(parts[0]) <= 2:
        return parts[1]  # Return part after the |
    
    return field_value  # Return original if not a simple prefix format

def main():
    print("=" * 60)
    print("🧹 PAYPOINT BARCODE PREFIX CLEANER")
    print("=" * 60)
    print()
    
    try:
        clean_barcode_prefixes()
        print()
        print("✅ Cleanup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
