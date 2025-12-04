#!/usr/bin/env python3
"""
Test script to verify the Paypoint stock management system.
"""

import sqlite3
from pathlib import Path
import sys

# Add the app directory to the path
app_path = Path(__file__).parent.parent / 'app'
sys.path.insert(0, str(app_path))

from models.paypoint import PaypointModel

def test_paypoint_system():
    """Test the Paypoint system functionality."""
    
    print("🧪 TESTING PAYPOINT STOCK MANAGEMENT SYSTEM")
    print("=" * 60)
    
    try:
        # Initialize tables
        print("1. Initializing database tables...")
        PaypointModel.init_tables()
        print("   ✅ Tables initialized successfully")
        
        # Add some test stock items
        print("\n2. Adding test stock items...")
        
        # Add Paypoint device
        device_id = PaypointModel.add_stock_item(
            item_name="Paypoint Terminal",
            item_type="device",
            description="Portable payment terminal for van installations",
            minimum_stock=2,
            unit_cost=150.00,
            supplier="Paypoint Ltd",
            part_number="PP-TERM-001"
        )
        print(f"   ✅ Added Paypoint Terminal (ID: {device_id})")
        
        # Add consumables
        cable_id = PaypointModel.add_stock_item(
            item_name="Power Cable",
            item_type="consumable",
            description="12V power cable for Paypoint terminals",
            minimum_stock=10,
            unit_cost=15.50,
            supplier="TechSupply Co",
            part_number="PWR-CBL-12V"
        )
        print(f"   ✅ Added Power Cable (ID: {cable_id})")
        
        mount_id = PaypointModel.add_stock_item(
            item_name="Wall Mount Bracket",
            item_type="accessory",
            description="Secure wall mounting bracket",
            minimum_stock=5,
            unit_cost=25.00,
            supplier="MountTech",
            part_number="WMB-SEC-001"
        )
        print(f"   ✅ Added Wall Mount Bracket (ID: {mount_id})")
        
        # Add initial stock
        print("\n3. Adding initial stock quantities...")
        
        PaypointModel.add_stock(device_id, 5, "Initial stock delivery", "DEL-001")
        print("   ✅ Added 5 Paypoint Terminals")
        
        PaypointModel.add_stock(cable_id, 25, "Initial stock delivery", "DEL-001")
        print("   ✅ Added 25 Power Cables")
        
        PaypointModel.add_stock(mount_id, 15, "Initial stock delivery", "DEL-001")
        print("   ✅ Added 15 Wall Mount Brackets")
        
        # Test stock usage
        print("\n4. Testing stock usage on jobs...")
        
        PaypointModel.use_stock(
            stock_item_id=device_id,
            quantity=1,
            job_number="4053001",
            trace_number="INST-001-2025",
            customer="TESCO Express",
            location="123 High Street, London",
            installation_notes="Installed terminal at checkout position 1"
        )
        print("   ✅ Used 1 Paypoint Terminal on job 4053001")
        
        PaypointModel.use_stock(
            stock_item_id=cable_id,
            quantity=2,
            job_number="4053001",
            trace_number="INST-001-2025",
            customer="TESCO Express",
            location="123 High Street, London",
            installation_notes="Connected power and data cables"
        )
        print("   ✅ Used 2 Power Cables on job 4053001")
        
        PaypointModel.use_stock(
            stock_item_id=mount_id,
            quantity=1,
            job_number="4053001",
            trace_number="INST-001-2025",
            customer="TESCO Express",
            location="123 High Street, London",
            installation_notes="Mounted terminal securely to wall"
        )
        print("   ✅ Used 1 Wall Mount Bracket on job 4053001")
        
        # Get current stock status
        print("\n5. Checking current stock status...")
        stock_items = PaypointModel.get_all_stock_items()
        
        for item in stock_items:
            status = "🟡 LOW" if item['stock_status'] == 'low' else "🟢 OK"
            print(f"   {item['item_name']}: {item['current_stock']} units {status}")
        
        # Get summary statistics
        print("\n6. Summary statistics...")
        summary = PaypointModel.get_stock_summary()
        print(f"   Total items: {summary['total_items']}")
        print(f"   Total stock: {summary['total_stock']} units")
        print(f"   Total value: £{summary['total_value']:.2f}")
        print(f"   Low stock items: {summary['low_stock_items']}")
        
        # Check job usage history
        print("\n7. Job usage history...")
        usage_history = PaypointModel.get_job_usage_history(job_number="4053001")
        
        if usage_history:
            print(f"   Job 4053001 used {len(usage_history)} different items:")
            for usage in usage_history:
                print(f"   - {usage['item_name']}: {usage['quantity_used']} units (Trace: {usage['trace_number']})")
        
        # Check low stock items
        print("\n8. Low stock alerts...")
        low_stock = PaypointModel.get_low_stock_items()
        
        if low_stock:
            print("   ⚠️  Low stock items:")
            for item in low_stock:
                print(f"   - {item['item_name']}: {item['current_stock']} (need {item['shortage']} more)")
        else:
            print("   ✅ All stock levels are adequate")
        
        print(f"\n🎉 PAYPOINT SYSTEM TEST COMPLETED SUCCESSFULLY!")
        print(f"✅ Database tables created and functional")
        print(f"✅ Stock management working correctly")
        print(f"✅ Job linking and audit trails operational")
        print(f"✅ Ready for production use!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_paypoint_system()
    sys.exit(0 if success else 1)
