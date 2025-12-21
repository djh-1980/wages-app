# Runsheet Extraction Testing

Standalone testing environment for perfecting runsheet parsing logic before integrating into the main system.

## Quick Start

### Test a Single Runsheet
```bash
python3 scripts/testing/test_runsheet_extraction.py data/documents/runsheets/RUN\ SHEETS\ -\ WARRINGTON\ -\ TUESDAY\ 25th\ MARCH\ 2025.pdf
```

### Test with Details
```bash
python3 scripts/testing/test_runsheet_extraction.py data/documents/runsheets/RUN\ SHEETS\ -\ WARRINGTON\ -\ TUESDAY\ 25th\ MARCH\ 2025.pdf --details
```

### Test Multiple Files
```bash
python3 scripts/testing/test_runsheet_extraction.py data/documents/runsheets/ --limit 10
```

### Save Results
```bash
python3 scripts/testing/test_runsheet_extraction.py data/documents/runsheets/ --save
```

## Features

### Quality Scoring
Each extracted job is scored 0-100 based on:
- **Job Number** (20 pts) - Required field
- **Customer** (20 pts) - Company name
- **Activity** (15 pts) - Job type
- **Address** (20 pts + 5 bonus) - Location with street name
- **Postcode** (15 pts + 5 bonus) - UK postcode format

### Quality Categories
- **High (80-100)**: Complete, well-formatted data
- **Medium (50-79)**: Missing some fields
- **Low (0-49)**: Significant data gaps

### Output
- Job count extracted
- Individual job details (with --details flag)
- Quality score per job
- Average quality score
- Quality distribution summary

## Workflow

### 1. Test Current Extraction
```bash
python3 scripts/testing/test_runsheet_extraction.py path/to/runsheet.pdf --details --save
```

### 2. Modify Parsing Logic
Edit `scripts/production/import_run_sheets.py` with improvements

### 3. Test Again
```bash
python3 scripts/testing/test_runsheet_extraction.py path/to/runsheet.pdf --details
```

### 4. Compare Results
Review quality scores and job details to see improvements

### 5. Iterate
Repeat steps 2-4 until satisfied

### 6. Deploy
Once perfected, the changes in `import_run_sheets.py` are ready for production

## Testing Database

All test runs use a separate database: `data/testing/test_runsheets.db`

This ensures no impact on your production data during testing.

## Results Storage

Results can be saved to `data/testing/extraction_results.json` for:
- Historical comparison
- Quality tracking over time
- Documentation of improvements

## Example Output

```
================================================================================
Testing: RUN SHEETS - WARRINGTON - TUESDAY 25th MARCH 2025.pdf
================================================================================

✓ Extracted 8 jobs

Job #1: 4313279
  Customer:  Hays Recruitment
  Activity:  DELIVERY
  Address:   16/12/2025 13:37, THORNDALE COURT, TIMPERLEY, ALTRINCHAM
  Postcode:  WA15 7SE
  Quality:   85/100 (HIGH)

Job #2: 4314181
  Customer:  POSTURITE LIMITED
  Activity:  INSTALL
  Address:   N/A
  Postcode:  
  Quality:   55/100 (MEDIUM)

...

================================================================================
QUALITY SUMMARY
================================================================================
Average Quality Score: 72.5/100
High Quality (80+): 5 jobs
Medium Quality (50-79): 2 jobs
Low Quality (<50): 1 jobs
================================================================================
```

## Tips

1. **Start Small**: Test with 1-2 files first
2. **Use --details**: See exactly what's being extracted
3. **Save Results**: Track improvements over time
4. **Test Edge Cases**: Try different runsheet formats
5. **Iterate Quickly**: Make small changes and test immediately

## Next Steps

Once you're happy with the extraction quality:
1. Review the changes in `import_run_sheets.py`
2. Test with a larger sample (10-20 files)
3. Deploy to production when confident
4. Monitor quality scores in production
