#!/usr/bin/env python3
"""
Test script for HMRC Final Declaration feature.
Tests the API client methods and database operations.
"""

import sys
import sqlite3
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_table():
    """Test that the hmrc_final_declarations table exists."""
    print("Testing database table...")
    db_path = Path(__file__).parent / 'data' / 'database' / 'wages.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='hmrc_final_declarations'
    """)
    
    if cursor.fetchone():
        print("✓ Table 'hmrc_final_declarations' exists")
    else:
        print("✗ Table 'hmrc_final_declarations' does NOT exist")
        return False
    
    # Check table structure
    cursor.execute("PRAGMA table_info(hmrc_final_declarations)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    expected_columns = {
        'id': 'INTEGER',
        'tax_year': 'TEXT',
        'calculation_id': 'TEXT',
        'estimated_tax': 'REAL',
        'status': 'TEXT',
        'hmrc_receipt_id': 'TEXT',
        'submitted_at': 'TEXT',
        'created_at': 'TIMESTAMP'
    }
    
    for col, col_type in expected_columns.items():
        if col in columns:
            print(f"✓ Column '{col}' exists ({columns[col]})")
        else:
            print(f"✗ Column '{col}' missing")
            return False
    
    conn.close()
    return True

def test_api_client_methods():
    """Test that HMRCClient has the new methods."""
    print("\nTesting HMRCClient methods...")
    
    try:
        from app.services.hmrc_client import HMRCClient
        
        client = HMRCClient()
        
        # Check methods exist
        methods = ['get_tax_calculation', 'trigger_crystallisation', 'submit_final_declaration']
        
        for method in methods:
            if hasattr(client, method):
                print(f"✓ Method '{method}' exists")
            else:
                print(f"✗ Method '{method}' missing")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error loading HMRCClient: {e}")
        return False

def test_api_routes():
    """Test that the API routes are registered."""
    print("\nTesting API routes...")
    
    try:
        from app.routes.api_hmrc import hmrc_bp
        
        # Get all route rules
        routes = []
        for rule in hmrc_bp.url_map.iter_rules():
            if rule.endpoint.startswith('hmrc_api.'):
                routes.append(rule.rule)
        
        expected_routes = [
            '/api/hmrc/final-declaration/status',
            '/api/hmrc/final-declaration/calculate',
            '/api/hmrc/final-declaration/submit'
        ]
        
        for route in expected_routes:
            # Check if route exists (may have blueprint prefix)
            route_name = route.replace('/api/hmrc/', '')
            if any(route_name in r for r in routes):
                print(f"✓ Route '{route}' registered")
            else:
                print(f"✗ Route '{route}' not found")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error checking routes: {e}")
        return False

def test_ui_files():
    """Test that UI files have been updated."""
    print("\nTesting UI files...")
    
    # Check template file
    template_path = Path(__file__).parent / 'templates' / 'settings' / 'hmrc.html'
    
    if template_path.exists():
        content = template_path.read_text()
        
        checks = [
            ('Final Declaration tab', 'finalDeclaration'),
            ('Calculate button', 'calculateTaxBtn'),
            ('Submit button', 'submitFinalDeclBtn'),
            ('Confirmation modal', 'finalDeclConfirmModal'),
            ('Quarterly checklist', 'quarterlyChecklist')
        ]
        
        for name, search_term in checks:
            if search_term in content:
                print(f"✓ {name} found in template")
            else:
                print(f"✗ {name} missing from template")
                return False
    else:
        print("✗ Template file not found")
        return False
    
    # Check JavaScript file
    js_path = Path(__file__).parent / 'static' / 'js' / 'settings-hmrc.js'
    
    if js_path.exists():
        content = js_path.read_text()
        
        checks = [
            ('loadFinalDeclarationStatus', 'loadFinalDeclarationStatus'),
            ('calculateTaxLiability', 'calculateTaxLiability'),
            ('submitFinalDeclaration', 'submitFinalDeclaration'),
            ('updateFinalDeclarationUI', 'updateFinalDeclarationUI')
        ]
        
        for name, search_term in checks:
            if search_term in content:
                print(f"✓ Function '{name}' found in JavaScript")
            else:
                print(f"✗ Function '{name}' missing from JavaScript")
                return False
    else:
        print("✗ JavaScript file not found")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("HMRC Final Declaration Feature Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Database Table", test_database_table()))
    results.append(("API Client Methods", test_api_client_methods()))
    results.append(("API Routes", test_api_routes()))
    results.append(("UI Files", test_ui_files()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe HMRC Final Declaration feature is ready to use!")
        print("\nTo test in the browser:")
        print("1. Start the web server")
        print("2. Navigate to Settings > HMRC MTD")
        print("3. Click the 'Final Declaration' tab")
        print("4. Select a tax year and view the quarterly checklist")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
