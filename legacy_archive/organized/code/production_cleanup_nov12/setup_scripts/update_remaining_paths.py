#!/usr/bin/env python3
"""
Update Remaining Old Paths
Find and update any remaining references to old directory structure.
"""

import os
import re
from pathlib import Path

def find_and_update_old_paths():
    """Find and update remaining old path references."""
    
    print("🔍 Scanning for remaining old path references...")
    
    # Define path mappings
    path_mappings = {
        r'PaySlips/': 'data/payslips/',
        r'RunSheets/': 'data/runsheets/', 
        r'Uploads/': 'data/uploads/',
        r'(?<!data/)temp/': 'data/temp/',
        r'(?<!data/)backup/': 'data/backups/',
        r'(?<!data/)output/': 'data/output/',
        r'(?<!data/)reports/': 'data/reports/',
    }
    
    # Files to check (excluding certain directories)
    exclude_dirs = {'.git', '__pycache__', 'node_modules', 'legacy_archive', 'data'}
    exclude_files = {'update_remaining_paths.py', 'reorganize_structure.py', 'setup_file_structure.py'}
    
    files_to_check = []
    for root, dirs, files in os.walk('.'):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith(('.py', '.html', '.js', '.css', '.json', '.md')) and file not in exclude_files:
                files_to_check.append(Path(root) / file)
    
    updated_files = []
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply path mappings
            for old_pattern, new_path in path_mappings.items():
                content = re.sub(old_pattern, new_path, content)
            
            # Check if file was modified
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_files.append(file_path)
                print(f"   ✅ Updated: {file_path}")
        
        except Exception as e:
            print(f"   ⚠️  Error processing {file_path}: {e}")
    
    return updated_files

def verify_path_updates():
    """Verify that all critical paths have been updated."""
    
    print("\n🔍 Verifying critical path updates...")
    
    critical_files = [
        'app/routes/api_upload.py',
        'app/services/file_processor.py', 
        'app/services/periodic_sync.py',
        'scripts/import_run_sheets.py',
        'scripts/debug_job.py'
    ]
    
    old_patterns = [
        r'PaySlips/',
        r'RunSheets/',
        r'(?<!data/)Uploads/',
        r'(?<!data/)temp/',
        r'(?<!data/)backup/'
    ]
    
    issues_found = []
    
    for file_path in critical_files:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                for pattern in old_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        issues_found.append(f"{file_path}: Found '{pattern}' pattern")
                        
            except Exception as e:
                issues_found.append(f"{file_path}: Error reading file - {e}")
        else:
            issues_found.append(f"{file_path}: File not found")
    
    if issues_found:
        print("   ❌ Issues found:")
        for issue in issues_found:
            print(f"      • {issue}")
        return False
    else:
        print("   ✅ All critical files updated correctly")
        return True

def update_test_files():
    """Update test files to use new paths."""
    
    print("\n🧪 Updating test files...")
    
    test_file = Path('test_upload_system.py')
    if test_file.exists():
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Update test paths
        content = content.replace('PaySlips/Manual', 'data/payslips/Manual')
        content = content.replace('RunSheets/Manual', 'data/runsheets/Manual')
        content = content.replace('Uploads/Manual', 'data/uploads/Manual')
        
        with open(test_file, 'w') as f:
            f.write(content)
        
        print("   ✅ Updated test_upload_system.py")

def create_path_verification_script():
    """Create a script to verify paths are working."""
    
    verification_script = '''#!/usr/bin/env python3
"""
Path Verification Script
Verify that all new paths exist and are accessible.
"""

from pathlib import Path

def verify_data_structure():
    """Verify the new data directory structure."""
    
    required_paths = [
        'data/payslips/Manual',
        'data/payslips/Processing', 
        'data/payslips/Processed',
        'data/payslips/Failed',
        'data/payslips/Archive',
        'data/runsheets/Manual',
        'data/runsheets/Processing',
        'data/runsheets/Processed', 
        'data/runsheets/Failed',
        'data/runsheets/Archive',
        'data/uploads/Manual',
        'data/uploads/Temp',
        'data/uploads/Queue',
        'data/temp/downloads',
        'data/temp/processing',
        'data/temp/failed',
        'data/backups/daily',
        'data/backups/weekly',
        'data/backups/monthly'
    ]
    
    print("🔍 Verifying data directory structure...")
    
    all_good = True
    for path_str in required_paths:
        path = Path(path_str)
        if path.exists():
            print(f"   ✅ {path_str}")
        else:
            print(f"   ❌ {path_str} - MISSING")
            all_good = False
    
    if all_good:
        print("\\n🎉 All required directories exist!")
    else:
        print("\\n⚠️  Some directories are missing. Run reorganize_structure.py again.")
    
    return all_good

if __name__ == '__main__':
    verify_data_structure()
'''
    
    with open('verify_paths.py', 'w') as f:
        f.write(verification_script)
    
    print("   📄 Created verify_paths.py")

if __name__ == '__main__':
    print("🔧 Updating Remaining Old Paths")
    print("=" * 40)
    
    # Find and update old paths
    updated_files = find_and_update_old_paths()
    
    # Update test files
    update_test_files()
    
    # Verify critical files
    verification_passed = verify_path_updates()
    
    # Create verification script
    create_path_verification_script()
    
    print(f"\n📊 Summary:")
    print(f"   • Updated {len(updated_files)} files")
    print(f"   • Verification: {'✅ PASSED' if verification_passed else '❌ FAILED'}")
    
    if updated_files:
        print(f"\n📝 Updated files:")
        for file_path in updated_files:
            print(f"   • {file_path}")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Run: python3 verify_paths.py")
    print(f"   2. Test the application")
    print(f"   3. Check that file uploads work correctly")
    
    if not verification_passed:
        print(f"\n⚠️  Some issues found - please review the verification output above")
