#!/usr/bin/env python3
"""
Reorganize runsheet folders to use consistent MM-MonthName format.
Converts inconsistent folder names like "November" to "11-November".
Removes empty folders and consolidates duplicates.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

class RunsheetFolderReorganizer:
    def __init__(self):
        self.base_dir = Path('data/documents/runsheets')
        self.month_mapping = {
            'january': '01-January',
            'february': '02-February', 
            'march': '03-March',
            'april': '04-April',
            'may': '05-May',
            'june': '06-June',
            'july': '07-July',
            'august': '08-August',
            'september': '09-September',
            'october': '10-October',
            'november': '11-November',
            'december': '12-December'
        }
        self.changes_made = []
        self.errors = []
        
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def is_correct_format(self, folder_name):
        """Check if folder name follows MM-MonthName format"""
        if len(folder_name) < 3:
            return False
        if folder_name[2] != '-':
            return False
        try:
            month_num = int(folder_name[:2])
            return 1 <= month_num <= 12
        except ValueError:
            return False
    
    def get_correct_month_name(self, folder_name):
        """Convert folder name to correct MM-MonthName format"""
        folder_lower = folder_name.lower()
        
        # If already correct format, return as-is
        if self.is_correct_format(folder_name):
            return folder_name
            
        # Map month names to correct format
        if folder_lower in self.month_mapping:
            return self.month_mapping[folder_lower]
            
        return None
    
    def reorganize_year_folder(self, year_dir):
        """Reorganize all month folders within a year directory"""
        self.log(f"📁 Processing year: {year_dir.name}")
        
        if not year_dir.is_dir():
            return
            
        month_dirs = [d for d in year_dir.iterdir() if d.is_dir()]
        
        for month_dir in month_dirs:
            month_name = month_dir.name
            correct_name = self.get_correct_month_name(month_name)
            
            if correct_name is None:
                # Unknown folder - check if it has PDFs
                pdf_files = list(month_dir.glob('*.pdf'))
                if pdf_files:
                    self.log(f"⚠️  Unknown month folder with {len(pdf_files)} PDFs: {month_dir}")
                    self.errors.append(f"Unknown month folder: {month_dir}")
                else:
                    # Empty unknown folder - mark for removal
                    self.log(f"🗑️  Empty unknown folder: {month_dir.name}")
                    try:
                        month_dir.rmdir()
                        self.changes_made.append(f"Removed empty folder: {month_dir}")
                        self.log(f"✅ Removed: {month_dir.name}")
                    except Exception as e:
                        self.errors.append(f"Failed to remove {month_dir}: {e}")
                continue
                
            if correct_name == month_name:
                # Already correct format
                self.log(f"✅ Already correct: {month_name}")
                continue
                
            # Need to rename/merge
            target_dir = year_dir / correct_name
            
            if target_dir.exists():
                # Target already exists - need to merge
                self.log(f"🔄 Merging: {month_name} → {correct_name}")
                self.merge_folders(month_dir, target_dir)
            else:
                # Simple rename
                self.log(f"📝 Renaming: {month_name} → {correct_name}")
                try:
                    month_dir.rename(target_dir)
                    self.changes_made.append(f"Renamed: {month_name} → {correct_name}")
                    self.log(f"✅ Renamed successfully")
                except Exception as e:
                    self.errors.append(f"Failed to rename {month_dir} to {target_dir}: {e}")
                    self.log(f"❌ Failed: {e}")
    
    def merge_folders(self, source_dir, target_dir):
        """Merge source folder into target folder, handling duplicates"""
        try:
            pdf_files = list(source_dir.glob('*.pdf'))
            merged_count = 0
            duplicate_count = 0
            
            for pdf_file in pdf_files:
                target_file = target_dir / pdf_file.name
                
                if target_file.exists():
                    # Check if files are identical
                    if pdf_file.stat().st_size == target_file.stat().st_size:
                        # Same size - likely duplicate, remove source
                        pdf_file.unlink()
                        duplicate_count += 1
                        self.log(f"  🗑️  Removed duplicate: {pdf_file.name}")
                    else:
                        # Different sizes - rename with suffix
                        counter = 1
                        while target_file.exists():
                            name_parts = pdf_file.stem, counter, pdf_file.suffix
                            target_file = target_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                            counter += 1
                        
                        shutil.move(str(pdf_file), str(target_file))
                        merged_count += 1
                        self.log(f"  📄 Moved with new name: {target_file.name}")
                else:
                    # No conflict - move directly
                    shutil.move(str(pdf_file), str(target_file))
                    merged_count += 1
                    self.log(f"  📄 Moved: {pdf_file.name}")
            
            # Remove source directory if empty
            remaining_files = list(source_dir.iterdir())
            if not remaining_files:
                source_dir.rmdir()
                self.changes_made.append(f"Merged {source_dir.name} into {target_dir.name} ({merged_count} files, {duplicate_count} duplicates removed)")
                self.log(f"✅ Merge complete: {merged_count} files moved, {duplicate_count} duplicates removed")
            else:
                self.errors.append(f"Source folder not empty after merge: {source_dir} ({len(remaining_files)} items remain)")
                
        except Exception as e:
            self.errors.append(f"Failed to merge {source_dir} into {target_dir}: {e}")
            self.log(f"❌ Merge failed: {e}")
    
    def remove_empty_folders(self):
        """Remove any empty year or month folders"""
        self.log("🧹 Removing empty folders...")
        
        if not self.base_dir.exists():
            return
            
        # Check year directories
        year_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        for year_dir in year_dirs:
            if year_dir.name == 'manual':
                continue  # Skip manual folder
                
            # Check month directories within year
            month_dirs = [d for d in year_dir.iterdir() if d.is_dir()]
            empty_months = []
            
            for month_dir in month_dirs:
                pdf_files = list(month_dir.glob('*.pdf'))
                if not pdf_files:
                    empty_months.append(month_dir)
            
            # Remove empty month directories
            for empty_month in empty_months:
                try:
                    empty_month.rmdir()
                    self.changes_made.append(f"Removed empty month folder: {empty_month}")
                    self.log(f"🗑️  Removed empty: {empty_month.name}")
                except Exception as e:
                    self.errors.append(f"Failed to remove empty folder {empty_month}: {e}")
            
            # Check if year directory is now empty
            remaining_items = list(year_dir.iterdir())
            if not remaining_items:
                try:
                    year_dir.rmdir()
                    self.changes_made.append(f"Removed empty year folder: {year_dir}")
                    self.log(f"🗑️  Removed empty year: {year_dir.name}")
                except Exception as e:
                    self.errors.append(f"Failed to remove empty year folder {year_dir}: {e}")
    
    def reorganize_all(self):
        """Reorganize all runsheet folders"""
        self.log("🚀 Starting runsheet folder reorganization...")
        self.log(f"📂 Base directory: {self.base_dir.absolute()}")
        
        if not self.base_dir.exists():
            self.log(f"❌ Base directory does not exist: {self.base_dir}")
            return
        
        # Get all year directories
        year_dirs = [d for d in self.base_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        year_dirs = sorted(year_dirs, key=lambda x: x.name)
        
        self.log(f"📅 Found {len(year_dirs)} year directories")
        
        # Process each year
        for year_dir in year_dirs:
            self.reorganize_year_folder(year_dir)
        
        # Clean up empty folders
        self.remove_empty_folders()
        
        # Summary
        self.log("=" * 70)
        self.log("📊 REORGANIZATION COMPLETE")
        self.log("=" * 70)
        
        if self.changes_made:
            self.log(f"✅ Changes made ({len(self.changes_made)}):")
            for change in self.changes_made:
                self.log(f"  • {change}")
        else:
            self.log("ℹ️  No changes needed - all folders already organized correctly")
        
        if self.errors:
            self.log(f"⚠️  Errors encountered ({len(self.errors)}):")
            for error in self.errors:
                self.log(f"  • {error}")
        
        self.log("=" * 70)
        
        # Final verification
        self.verify_organization()
    
    def verify_organization(self):
        """Verify that all folders now follow the correct format"""
        self.log("🔍 Verifying folder organization...")
        
        inconsistent_folders = []
        total_folders = 0
        
        if not self.base_dir.exists():
            return
            
        year_dirs = [d for d in self.base_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        
        for year_dir in year_dirs:
            month_dirs = [d for d in year_dir.iterdir() if d.is_dir()]
            
            for month_dir in month_dirs:
                total_folders += 1
                if not self.is_correct_format(month_dir.name):
                    inconsistent_folders.append(month_dir)
        
        if inconsistent_folders:
            self.log(f"⚠️  Still found {len(inconsistent_folders)} inconsistent folders:")
            for folder in inconsistent_folders:
                self.log(f"  • {folder}")
        else:
            self.log(f"✅ All {total_folders} folders now follow MM-MonthName format!")

def main():
    """Run the reorganization"""
    reorganizer = RunsheetFolderReorganizer()
    reorganizer.reorganize_all()

if __name__ == "__main__":
    main()
