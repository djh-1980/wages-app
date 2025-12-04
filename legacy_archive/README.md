# Legacy Archive

This directory contains archived code, documentation, and data from previous versions of the TVS Wages App.

## 📁 Structure

### `archived_code/`
Archived source code and scripts that are no longer in active use.

- **`scripts/`** - One-time utility scripts and old automation
  - parsing_improvement_tracker.py
  - parsing_manager.py
  - Various cleanup and fix scripts (22 total)
  
- **`web_app/`** - Old web application files
  - web_app_original.py - Original monolithic web app
  - new_web_app.py - Duplicate entry point
  
- **`settings/`** - Old settings page implementations
  - settings_old.html - Original 7-tab settings page
  - Settings refactor cleanup files

### `archived_docs/`
Documentation from previous versions and completed features.

- **`2024-11/`** - November 2024 documentation archive
  - Original deployment guides
  - Version changelogs
  - Setup instructions
  
- **`2024-11-27/`** - Settings refactor documentation
  
- **`2024-12-04/`** - December 2024 cleanup
  - AUTO_SYNC_IMPROVEMENTS.md
  - DEPLOYMENT_READY.md
  - MULTI_DRIVER_PARSING_FIX.md
  - PARSING_TEST_RESULTS.md
  - RUNSHEET_PARSING_IMPROVEMENTS.md
  - WEEKLY_SUMMARY_FIX.md
  - And more...

### `archived_data/`
Old data files and duplicates.

- **`runsheets/`** - Duplicate runsheet PDFs (93 files)
  - These were duplicates from the root RunSheets/ folder
  - Originals are in data/documents/runsheets/

## 🗂️ Archive History

### December 4, 2025
- Cleaned up 22 unused utility scripts
- Archived duplicate web app entry points
- Moved 8 completed feature docs to archive
- Removed 93 duplicate runsheet PDFs
- Removed 2 empty directories (PaySlips/, RunSheets/)

### November 27, 2024
- Settings page refactor cleanup
- Moved old 7-tab settings implementation

### November 12, 2024
- Production deployment cleanup
- Documentation archive

## 🔍 Finding Archived Items

### Looking for a script?
Check `archived_code/scripts/` - all one-time utilities are here.

### Looking for old documentation?
Check `archived_docs/` by date - organized chronologically.

### Looking for old runsheets?
Check `archived_data/runsheets/` - but note these are duplicates.
Active runsheets are in `data/documents/runsheets/`.

## ⚠️ Important Notes

- **All files are safe** - Nothing was deleted, only moved to archive
- **Easy to restore** - Just copy files back to their original locations
- **Duplicates removed** - Runsheets in this archive are duplicates only
- **Active code untouched** - All production scripts remain in place

## 📊 Archive Statistics

- **Scripts archived**: 22
- **Documentation files**: 16+
- **Runsheet PDFs**: 93 (duplicates)
- **Web app files**: 2
- **Settings files**: Multiple

## 🔄 Restoring Files

To restore any archived file:

```bash
# Restore a script
cp legacy_archive/archived_code/scripts/[filename] scripts/

# Restore documentation
cp legacy_archive/archived_docs/[date]/[filename] docs/

# Restore web app file
cp legacy_archive/archived_code/web_app/[filename] ./
```

---

**Last Updated**: December 4, 2025  
**Maintained By**: Automated cleanup process
