#!/usr/bin/env python3
"""
Comprehensive fix script for payslip and runsheet import issues.
Addresses authentication, performance, and customer format problems.
"""

import os
import sys
import subprocess
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
import json

class ImportSystemFixer:
    def __init__(self):
        self.base_path = Path.cwd()
        self.issues_found = []
        self.fixes_applied = []
        
    def check_gmail_auth(self):
        """Check and fix Gmail authentication issues."""
        print("🔐 Checking Gmail authentication...")
        
        token_path = self.base_path / 'token.json'
        credentials_path = self.base_path / 'credentials.json'
        
        issues = []
        
        if not credentials_path.exists():
            issues.append("Missing credentials.json file")
            print("  ❌ credentials.json not found")
        else:
            print("  ✅ credentials.json found")
            
        if token_path.exists():
            try:
                with open(token_path, 'r') as f:
                    token_data = json.load(f)
                    
                # Check if token is expired
                if 'expiry' in token_data:
                    expiry = datetime.fromisoformat(token_data['expiry'].replace('Z', '+00:00'))
                    if expiry < datetime.now().astimezone():
                        issues.append("Gmail token expired")
                        print("  ⚠️  Token expired, will need refresh")
                        # Delete expired token
                        token_path.unlink()
                        print("  🗑️  Deleted expired token")
                        self.fixes_applied.append("Deleted expired Gmail token")
                    else:
                        print("  ✅ Token valid")
                        
            except Exception as e:
                issues.append(f"Invalid token file: {e}")
                print(f"  ❌ Token file corrupted: {e}")
                token_path.unlink()
                print("  🗑️  Deleted corrupted token")
                self.fixes_applied.append("Deleted corrupted Gmail token")
        else:
            print("  ℹ️  No token file (will authenticate on first run)")
            
        self.issues_found.extend(issues)
        return len(issues) == 0
    
    def check_database_performance(self):
        """Check database performance and optimize if needed."""
        print("🗄️  Checking database performance...")
        
        db_path = self.base_path / 'data' / 'payslips.db'
        if not db_path.exists():
            print("  ℹ️  Database doesn't exist yet")
            return True
            
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check table sizes
            cursor.execute("SELECT COUNT(*) FROM payslips")
            payslip_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs")
            runsheet_count = cursor.fetchone()[0]
            
            print(f"  📊 Database stats: {payslip_count} payslips, {runsheet_count} runsheet jobs")
            
            # Check for missing indexes
            cursor.execute("PRAGMA index_list(payslips)")
            payslip_indexes = cursor.fetchall()
            
            cursor.execute("PRAGMA index_list(run_sheet_jobs)")
            runsheet_indexes = cursor.fetchall()
            
            # Add performance indexes if missing
            indexes_to_add = []
            
            # Check if we have date indexes
            has_payslip_date_index = any('pay_date' in str(idx) for idx in payslip_indexes)
            has_runsheet_date_index = any('date' in str(idx) for idx in runsheet_indexes)
            
            if not has_payslip_date_index:
                indexes_to_add.append("CREATE INDEX IF NOT EXISTS idx_payslips_date ON payslips(pay_date)")
                
            if not has_runsheet_date_index:
                indexes_to_add.append("CREATE INDEX IF NOT EXISTS idx_runsheet_date ON run_sheet_jobs(date)")
                
            # Add source file index for duplicate checking
            indexes_to_add.append("CREATE INDEX IF NOT EXISTS idx_runsheet_source ON run_sheet_jobs(source_file)")
            
            for index_sql in indexes_to_add:
                cursor.execute(index_sql)
                print(f"  ✅ Added performance index")
                
            if indexes_to_add:
                conn.commit()
                self.fixes_applied.append(f"Added {len(indexes_to_add)} database indexes")
                
            # Analyze tables for better query planning
            cursor.execute("ANALYZE")
            conn.commit()
            conn.close()
            
            print("  ✅ Database optimized")
            return True
            
        except Exception as e:
            print(f"  ❌ Database check failed: {e}")
            self.issues_found.append(f"Database performance issue: {e}")
            return False
    
    def check_file_processing_performance(self):
        """Check for file processing performance issues."""
        print("📁 Checking file processing setup...")
        
        runsheets_path = self.base_path / 'RunSheets'
        payslips_path = self.base_path / 'PaySlips'
        
        issues = []
        
        if runsheets_path.exists():
            # Count files
            pdf_files = list(runsheets_path.rglob('*.pdf'))
            csv_files = list(runsheets_path.rglob('*.csv'))
            
            total_files = len(pdf_files) + len(csv_files)
            print(f"  📊 Found {total_files} runsheet files ({len(pdf_files)} PDFs, {len(csv_files)} CSVs)")
            
            if total_files > 1000:
                print("  ⚠️  Large number of files detected - parallel processing recommended")
                issues.append("Large file count may cause timeouts")
                
            # Check for very old files that might not need processing
            cutoff_date = datetime.now() - timedelta(days=365)
            old_files = [f for f in pdf_files if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_date]
            
            if len(old_files) > 100:
                print(f"  ℹ️  {len(old_files)} files older than 1 year - consider archiving")
                
        else:
            print("  ℹ️  RunSheets directory doesn't exist yet")
            
        if payslips_path.exists():
            payslip_files = list(payslips_path.rglob('*.pdf'))
            print(f"  📊 Found {len(payslip_files)} payslip files")
        else:
            print("  ℹ️  PaySlips directory doesn't exist yet")
            
        self.issues_found.extend(issues)
        return len(issues) == 0
    
    def check_ssl_issues(self):
        """Check for SSL/TLS configuration issues."""
        print("🔒 Checking SSL configuration...")
        
        try:
            import ssl
            import urllib3
            
            # Check SSL version
            ssl_version = ssl.OPENSSL_VERSION
            print(f"  📋 SSL Version: {ssl_version}")
            
            if 'LibreSSL' in ssl_version:
                print("  ⚠️  Using LibreSSL - may cause urllib3 warnings")
                self.issues_found.append("LibreSSL compatibility warnings")
                
                # Suggest fix
                print("  💡 Consider upgrading to OpenSSL 1.1.1+ or suppress warnings")
                
            return True
            
        except Exception as e:
            print(f"  ❌ SSL check failed: {e}")
            return False
    
    def create_optimized_sync_script(self):
        """Create an optimized sync script with better error handling."""
        print("🛠️  Creating optimized sync script...")
        
        script_content = '''#!/usr/bin/env python3
"""
Optimized sync script with improved error handling and performance.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import argparse

def run_with_timeout(cmd, timeout_minutes=10, description="Command"):
    """Run command with timeout and better error handling."""
    print(f"🔄 Running {description}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60
        )
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True, result.stdout
        else:
            print(f"❌ {description} failed with code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after {timeout_minutes} minutes")
        return False, f"Timeout after {timeout_minutes} minutes"
    except Exception as e:
        print(f"💥 {description} crashed: {e}")
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description='Optimized payslip and runsheet sync')
    parser.add_argument('--recent', type=int, default=7, help='Only process files from last N days')
    parser.add_argument('--payslips-only', action='store_true', help='Only sync payslips')
    parser.add_argument('--runsheets-only', action='store_true', help='Only sync runsheets')
    parser.add_argument('--skip-gmail', action='store_true', help='Skip Gmail download, only process local files')
    
    args = parser.parse_args()
    
    print("🚀 Starting optimized sync process...")
    print(f"📅 Processing files from last {args.recent} days")
    
    success_count = 0
    total_operations = 0
    
    if not args.runsheets_only:
        total_operations += 1
        if not args.skip_gmail:
            # Download payslips from Gmail
            success, output = run_with_timeout([
                sys.executable, 'scripts/download_runsheets_gmail.py', 
                '--payslips', '--recent'
            ], timeout_minutes=5, description="Gmail payslip download")
            
            if success:
                success_count += 1
        
        # Process payslips
        success, output = run_with_timeout([
            sys.executable, 'scripts/extract_payslips.py', '--recent', str(args.recent)
        ], timeout_minutes=10, description="Payslip extraction")
        
        if success:
            success_count += 1
    
    if not args.payslips_only:
        total_operations += 1
        if not args.skip_gmail:
            # Download runsheets from Gmail
            success, output = run_with_timeout([
                sys.executable, 'scripts/download_runsheets_gmail.py', 
                '--runsheets', '--recent'
            ], timeout_minutes=5, description="Gmail runsheet download")
            
            if success:
                success_count += 1
        
        # Process runsheets with parallel processing
        success, output = run_with_timeout([
            sys.executable, 'scripts/import_run_sheets.py', 
            '--recent', str(args.recent), '--workers', '2'
        ], timeout_minutes=15, description="Runsheet import")
        
        if success:
            success_count += 1
    
    print(f"\\n📊 Sync completed: {success_count}/{total_operations} operations successful")
    
    if success_count == total_operations:
        print("🎉 All operations completed successfully!")
        return 0
    else:
        print("⚠️  Some operations failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
        
        script_path = self.base_path / 'optimized_sync.py'
        with open(script_path, 'w') as f:
            f.write(script_content)
            
        # Make executable
        script_path.chmod(0o755)
        
        print(f"  ✅ Created optimized sync script: {script_path}")
        self.fixes_applied.append("Created optimized sync script")
        
    def create_customer_format_test(self):
        """Create a test script to identify customer format issues."""
        print("🧪 Creating customer format test script...")
        
        test_script = '''#!/usr/bin/env python3
"""
Test script to identify customer-specific format issues in payslips.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.extract_payslips import PayslipExtractor
import re

def test_customer_formats():
    """Test different customer name formats."""
    
    # Test patterns
    test_lines = [
        "Daniel Hanson: 2609338 | TESCO | Store 1234 | TECH EXCHANGE - ND 1700",
        "Hanson, Daniel: 2609339 | ASDA | Store 5678 | REPAIR WITH PARTS - 4HR",
        "D. Hanson: 2609340 | SAINSBURY | Store 9012 | COLLECTION - AP",
        "HANSON, DANIEL: 2609341 | MORRISONS | Store 3456 | DELIVERY - 8HR",
        "Daniel Hanson: TESCO | Store 1234 | TECH EXCHANGE - ND 1700",  # No job number
    ]
    
    extractor = PayslipExtractor()
    
    print("🧪 Testing customer format detection...")
    print("=" * 60)
    
    for i, line in enumerate(test_lines, 1):
        print(f"\\nTest {i}: {line}")
        
        # Test the parsing
        test_text = f"Some header text\\n{line}\\nSome footer text"
        jobs = extractor.parse_job_items(test_text)
        
        if jobs:
            job = jobs[0]
            print(f"  ✅ Parsed successfully:")
            print(f"     Job Number: {job.get('job_number', 'None')}")
            print(f"     Client: {job.get('client', 'None')}")
            print(f"     Location: {job.get('location', 'None')}")
            print(f"     Job Type: {job.get('job_type', 'None')}")
        else:
            print(f"  ❌ Failed to parse")
    
    print("\\n" + "=" * 60)
    print("Test completed. Check results above for parsing issues.")

if __name__ == "__main__":
    test_customer_formats()
'''
        
        test_path = self.base_path / 'test_customer_formats.py'
        with open(test_path, 'w') as f:
            f.write(test_script)
            
        test_path.chmod(0o755)
        
        print(f"  ✅ Created customer format test: {test_path}")
        self.fixes_applied.append("Created customer format test script")
    
    def run_comprehensive_fix(self):
        """Run all fixes and optimizations."""
        print("🔧 COMPREHENSIVE IMPORT SYSTEM FIX")
        print("=" * 50)
        
        # Run all checks
        self.check_gmail_auth()
        self.check_database_performance()
        self.check_file_processing_performance()
        self.check_ssl_issues()
        
        # Create optimization tools
        self.create_optimized_sync_script()
        self.create_customer_format_test()
        
        # Summary
        print("\n" + "=" * 50)
        print("🏁 FIX SUMMARY")
        print("=" * 50)
        
        if self.issues_found:
            print("⚠️  Issues found:")
            for issue in self.issues_found:
                print(f"   • {issue}")
        else:
            print("✅ No critical issues found")
            
        if self.fixes_applied:
            print("\\n🛠️  Fixes applied:")
            for fix in self.fixes_applied:
                print(f"   • {fix}")
        
        print("\\n📋 NEXT STEPS:")
        print("1. Test Gmail authentication: python scripts/download_runsheets_gmail.py --help")
        print("2. Run customer format test: python scripts/test_customer_formats.py")
        print("3. Use optimized sync: python scripts/optimized_sync.py --recent 7")
        print("4. For large imports: python scripts/import_run_sheets.py --recent 30 --workers 2")
        
        return len(self.issues_found) == 0

def main():
    fixer = ImportSystemFixer()
    success = fixer.run_comprehensive_fix()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
