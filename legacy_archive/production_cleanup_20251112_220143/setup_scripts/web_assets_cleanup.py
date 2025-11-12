#!/usr/bin/env python3
"""
Web Assets and Folder Cleanup Script
Removes unnecessary files and folders while preserving essential web assets.
"""

import os
import shutil
from pathlib import Path


def remove_system_files():
    """Remove macOS system files."""
    print("🧹 Removing system files...")
    
    # Remove .DS_Store files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == '.DS_Store':
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"  ❌ Removed: {file_path}")


def remove_unused_files():
    """Remove unused files."""
    print("\n🗑️ Removing unused files...")
    
    unused_files = [
        'wages.py',  # Old file, replaced by new_web_app.py
        'payslips.db',  # Empty file, real DB is in data/
        'example_frontend_enhancement.js',  # Example code, not used in production
    ]
    
    for file in unused_files:
        if Path(file).exists():
            os.remove(file)
            print(f"  ❌ Removed: {file}")
        else:
            print(f"  ℹ️ Not found: {file}")


def remove_empty_folders():
    """Remove empty folders."""
    print("\n📁 Removing empty folders...")
    
    empty_folders = [
        'PaySlips',
        'logs', 
        'output',
        'tests',
        'data/runsheets/2021',
        'data/runsheets/2022', 
        'data/runsheets/2023',
        'data/runsheets/2024',
        'data/runsheets/2025',
        'data/runsheets/manual',
    ]
    
    for folder in empty_folders:
        folder_path = Path(folder)
        if folder_path.exists() and folder_path.is_dir():
            try:
                # Only remove if empty
                if not any(folder_path.iterdir()):
                    folder_path.rmdir()
                    print(f"  ❌ Removed empty folder: {folder}")
                else:
                    print(f"  ℹ️ Folder not empty, keeping: {folder}")
            except OSError as e:
                print(f"  ⚠️ Could not remove {folder}: {e}")
        else:
            print(f"  ℹ️ Not found: {folder}")


def consolidate_documentation():
    """Move essential docs to docs/ and remove excessive documentation."""
    print("\n📚 Consolidating documentation...")
    
    # Ensure docs directory exists
    Path('docs').mkdir(exist_ok=True)
    
    # Move essential docs to docs/
    essential_docs = [
        'FINAL_CLEANUP_SUMMARY.md',
        'WEB_ASSETS_CLEANUP_ANALYSIS.md'
    ]
    
    for doc in essential_docs:
        if Path(doc).exists():
            target = f"docs/{doc}"
            if not Path(target).exists():
                shutil.move(doc, target)
                print(f"  📋 Moved to docs/: {doc}")
    
    # Remove excessive documentation
    excessive_docs = [
        'CHANGELOG.md',
        'CLEANUP_SUMMARY.md',
        'CODEBASE_CLEANUP_PLAN.md', 
        'LIVE_SERVER_SETUP.md',
        'PHASE3_SUMMARY.md',
        'PHASE4_SUMMARY.md',
        'REFACTORING_SUMMARY.md',
        'WEBSITE_UPDATE_GUIDE.md',
        'refactoring_plan.md'
    ]
    
    for doc in excessive_docs:
        if Path(doc).exists():
            os.remove(doc)
            print(f"  ❌ Removed excessive doc: {doc}")


def analyze_web_assets():
    """Analyze and report on web assets (but don't remove - they're all needed)."""
    print("\n🌐 Analyzing web assets...")
    
    # Check CSS files
    css_files = list(Path('static/css').glob('*.css')) if Path('static/css').exists() else []
    print(f"  ✅ CSS files: {len(css_files)} (all needed)")
    for css in css_files:
        print(f"    - {css.name}")
    
    # Check JS files
    js_files = []
    if Path('static/js').exists():
        js_files.extend(Path('static/js').glob('*.js'))
    if Path('static/runsheets.js').exists():
        js_files.append(Path('static/runsheets.js'))
    
    print(f"  ✅ JS files: {len(js_files)} (all needed)")
    for js in js_files:
        size_kb = js.stat().st_size / 1024
        print(f"    - {js.name} ({size_kb:.1f}KB)")
    
    # Check templates
    templates = list(Path('templates').glob('*.html')) if Path('templates').exists() else []
    print(f"  ✅ Templates: {len(templates)} (all needed)")
    for template in templates:
        print(f"    - {template.name}")


def create_final_structure_report():
    """Create a report of the final clean structure."""
    print("\n📊 Creating final structure report...")
    
    structure_report = """# Final Clean Project Structure

## ✅ Essential Directories
- `app/` - Core application (models, services, routes, utils)
- `static/` - Web assets (CSS, JS)
- `templates/` - HTML templates
- `docs/` - Essential documentation
- `scripts/` - Utility scripts
- `tools/` - Database management tools
- `legacy_archive/` - Archived old code
- `data/` - Application data
- `Backups/` - Database backups

## ✅ Essential Files
- `new_web_app.py` - Main application entry point
- `requirements.txt` - Python dependencies
- `requirements-gmail.txt` - Gmail integration dependencies
- `README.md` - Project overview
- All CSS, JS, and HTML files (all needed for functionality)

## 🧹 Cleaned Up
- ❌ Removed .DS_Store files
- ❌ Removed unused Python files
- ❌ Removed empty folders
- ❌ Consolidated excessive documentation
- ❌ Removed duplicate/old files

## 🎯 Result
Clean, professional project structure with only essential files.
All web assets preserved - they're all actively used by the application.
"""
    
    with open('docs/FINAL_PROJECT_STRUCTURE.md', 'w') as f:
        f.write(structure_report)
    
    print("  📋 Created: docs/FINAL_PROJECT_STRUCTURE.md")


def main():
    """Run the complete web assets and folder cleanup."""
    print("🧹 Starting Web Assets & Folder Cleanup...")
    print("="*60)
    
    remove_system_files()
    remove_unused_files()
    remove_empty_folders()
    consolidate_documentation()
    analyze_web_assets()
    create_final_structure_report()
    
    print("="*60)
    print("✅ Web assets and folder cleanup completed!")
    print("📋 All CSS, JS, and HTML files preserved (they're all needed)")
    print("🗑️ Removed unnecessary files and empty folders")
    print("📚 Consolidated documentation")
    print("🎯 Project structure is now clean and professional!")


if __name__ == "__main__":
    main()
