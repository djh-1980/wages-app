#!/usr/bin/env python3
"""
Test script for the new hybrid upload system.
Run this to verify all components are working correctly.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from app.routes.api_upload import upload_bp
        print("✅ Upload blueprint imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import upload blueprint: {e}")
        return False
    
    try:
        from werkzeug.utils import secure_filename
        print("✅ Werkzeug utilities available")
    except ImportError as e:
        print(f"❌ Werkzeug not available: {e}")
        return False
    
    return True

def test_directories():
    """Test that required directories exist or can be created."""
    print("\n📁 Testing directory structure...")
    
    required_dirs = [
        Path('data/payslips/Manual'),
        Path('data/runsheets/Manual'),
        Path('data/uploads/Manual'),
        Path('logs'),
        Path('data')
    ]
    
    for directory in required_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Directory ready: {directory}")
        except Exception as e:
            print(f"❌ Failed to create directory {directory}: {e}")
            return False
    
    return True

def test_flask_app():
    """Test that the Flask app can be created with new blueprint."""
    print("\n🚀 Testing Flask app creation...")
    
    try:
        from app import create_app
        app = create_app('development')
        
        # Check if upload blueprint is registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        
        if 'upload_api' in blueprint_names:
            print("✅ Upload blueprint registered successfully")
        else:
            print("❌ Upload blueprint not found in registered blueprints")
            print(f"   Available blueprints: {blueprint_names}")
            return False
        
        # Test a few key routes
        with app.test_client() as client:
            # Test settings page (now contains file management)
            response = client.get('/settings')
            if response.status_code == 200:
                print("✅ Settings page (with integrated file management) accessible")
            else:
                print(f"❌ Settings page failed: {response.status_code}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        return False

def test_static_files():
    """Test that static files exist."""
    print("\n📄 Testing static files...")
    
    static_files = [
        Path('static/js/file-upload.js'),
        Path('static/css/file-upload.css'),
        Path('static/css/unified-styles.css')
    ]
    
    for file_path in static_files:
        if file_path.exists():
            print(f"✅ Static file exists: {file_path}")
        else:
            print(f"❌ Missing static file: {file_path}")
            return False
    
    return True

def test_templates():
    """Test that template files exist."""
    print("\n📋 Testing templates...")
    
    template_files = [
        Path('templates/files.html'),
        Path('templates/base.html')
    ]
    
    for file_path in template_files:
        if file_path.exists():
            print(f"✅ Template exists: {file_path}")
        else:
            print(f"❌ Missing template: {file_path}")
            return False
    
    return True

def main():
    """Run all tests."""
    print("🧪 Testing TVS Wages Hybrid Upload System")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_directories,
        test_static_files,
        test_templates,
        test_flask_app
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"\n❌ Test failed: {test.__name__}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The integrated settings system is ready to use.")
        print("\n🚀 Next steps:")
        print("1. Start your Flask app: python new_web_app.py")
        print("2. Navigate to http://localhost:5000/settings")
        print("3. Go to 'Data & Sync' tab and try uploading some PDF files!")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
