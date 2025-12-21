# Deploying Camelot as Primary Runsheet Parser

## Overview
Camelot table-based extraction provides 99% quality data vs 90% with text parsing.

## Benefits
- ✅ **Higher accuracy** - 99.1% vs 90.9% quality
- ✅ **Cleaner data** - No phone numbers, technical jargon filtered
- ✅ **Full activity details** - Preserves "DESK & CHAIR SP INSTALL" etc.
- ✅ **Better postcodes** - Handles split formats like "M18, 7EH"
- ✅ **Less code** - 350 lines vs 2,600 lines

## Prerequisites
```bash
# Camelot is already installed
pip3 install 'camelot-py[cv]'
```

## Testing (Already Done)
You've tested Camelot extraction at:
- http://localhost:5001/runsheet-testing
- Compared with database data
- Verified manual entries are flagged correctly

## Deployment Steps

### Option 1: Replace Text Parser (Recommended)
Replace the current text-based parser with Camelot in `import_run_sheets.py`:

```python
# In scripts/production/import_run_sheets.py
# Replace parse_pdf_run_sheet method with:

def parse_pdf_run_sheet(self, pdf_path: str) -> List[Dict]:
    """Parse PDF using Camelot table extraction."""
    from camelot_runsheet_parser import CamelotRunsheetParser
    
    parser = CamelotRunsheetParser(driver_name=self.name)
    return parser.parse_pdf(pdf_path)
```

### Option 2: Hybrid Approach
Use Camelot as primary, fall back to text parsing:

```python
def parse_pdf_run_sheet(self, pdf_path: str) -> List[Dict]:
    """Parse PDF using Camelot with text fallback."""
    try:
        from camelot_runsheet_parser import CamelotRunsheetParser
        parser = CamelotRunsheetParser(driver_name=self.name)
        jobs = parser.parse_pdf(pdf_path)
        
        if len(jobs) > 0:
            return jobs
    except Exception as e:
        self.logger.warning(f"Camelot failed: {e}, falling back to text parsing")
    
    # Fall back to original text parsing
    return self._parse_pdf_text_method(pdf_path)
```

## Re-importing Existing Data

### Re-import December 2025 (Test Month)
```bash
# STEP 1: Preview what will change (shows new jobs that would be added)
python3 scripts/production/reimport_with_camelot.py --year 2025 --month 12 --replace

# STEP 2: Review the new jobs listed, then confirm if OK
python3 scripts/production/reimport_with_camelot.py --year 2025 --month 12 --replace --confirm
```

### Re-import Single File
```bash
python3 scripts/production/reimport_with_camelot.py --file "data/documents/runsheets/2025/12-December/DH_22-12-2025.pdf" --replace
```

### Re-import All of 2025
```bash
for month in {01..12}; do
    python3 scripts/production/reimport_with_camelot.py --year 2025 --month $month --replace
done
```

## Verification

After re-importing, check quality:

1. **Visit Runsheets Page**
   - http://localhost:5001/runsheets
   - Check addresses are clean (no phone numbers, jargon)
   - Verify activities show full details

2. **Check Database**
   ```sql
   SELECT COUNT(*) FROM run_sheet_jobs WHERE postcode IS NOT NULL;
   SELECT COUNT(*) FROM run_sheet_jobs WHERE postcode = '';
   ```

3. **Compare Before/After**
   - Use the testing page to compare a few dates
   - Verify quality scores improved

## Rollback Plan

If issues arise:

1. **Restore from backup**
   ```bash
   # You created a backup at: data/database/backups/payslips_backup_20251221_192802.db.gz
   gunzip -c data/database/backups/payslips_backup_20251221_192802.db.gz > data/database/payslips.db
   ```

2. **Revert code changes**
   ```bash
   git checkout scripts/production/import_run_sheets.py
   ```

## Recommended Deployment

1. **Backup database first**
   ```bash
   python3 -c "from app.routes.api_data import backup_database; backup_database()"
   ```

2. **Test on December 2025**
   ```bash
   python3 scripts/production/reimport_with_camelot.py --year 2025 --month 12 --replace
   ```

3. **Verify quality** via runsheets page

4. **If satisfied, deploy to production**
   - Replace parser in `import_run_sheets.py`
   - Re-import other months as needed

5. **Monitor future imports**
   - New runsheets will use Camelot automatically
   - Quality should be consistently 95-100%

## Notes

- Manual entries (like job 4316807) are preserved
- Source file tracking ensures proper attribution
- Failed jobs are logged for review
- Camelot warnings about PDF headers are harmless

## Support

If you encounter issues:
1. Check `/api/runsheet-testing/compare` for specific files
2. Review quality scores
3. Test individual files before batch re-import
