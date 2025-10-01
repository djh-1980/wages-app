# Payslip Data Extraction Project - Complete

## ✅ What Was Done

Successfully extracted and organized all payslip data from 78 PDF files into a searchable database.

### Data Extracted
- **78 payslips** (Tax Years 2024-2025)
- **4,841 individual job items**
- **£101,567.15** total net earnings
- **92 unique clients**
- **104 unique job types**

### Files Created

#### Core Scripts
1. **extract_payslips.py** - Main extraction script
   - Reads all PDF files from PaySlips directory
   - Extracts header, financial, and job item data
   - Stores in SQLite database
   - Run: `python3 extract_payslips.py`

2. **query_payslips.py** - Interactive query tool
   - Browse all payslips
   - View detailed breakdowns
   - Analyze by client, job type, tax year
   - Search functionality
   - Run: `python3 query_payslips.py`

3. **export_to_csv.py** - CSV export utility
   - Creates 5 CSV files for Excel/spreadsheet analysis
   - Run: `python3 export_to_csv.py`

4. **generate_report.py** - Comprehensive text report
   - Full analysis in readable text format
   - Run: `python3 generate_report.py`

5. **quick_stats.py** - Quick overview
   - Fast summary of key statistics
   - Run: `python3 quick_stats.py`

#### Database
- **payslips.db** (1.3 MB)
  - SQLite database with all extracted data
  - Two tables: `payslips` and `job_items`
  - Can be queried directly with SQL

#### CSV Exports
- **payslips_summary.csv** - Weekly payslip summaries
- **job_items.csv** - All 4,841 individual jobs
- **client_summary.csv** - Earnings by client
- **job_type_summary.csv** - Earnings by job type
- **weekly_summary.csv** - Weekly statistics

#### Reports
- **payslip_report.txt** - Comprehensive analysis report

#### Documentation
- **README.md** - Project overview and setup
- **USAGE_GUIDE.md** - Detailed usage instructions
- **requirements.txt** - Python dependencies

## 📊 Key Insights

### Earnings Summary
- **Average per week**: £1,302.14
- **Estimated annual rate**: £67,711.43
- **Best week**: Tax Year 2024, Week 43 - £1,834.20
- **Average jobs per week**: 62.1

### Tax Year Breakdown
- **2024**: 52 weeks, £69,555.18 (avg £1,337.60/week)
- **2025**: 26 weeks, £32,011.97 (avg £1,231.23/week)

### Top Clients
1. Xerox (UK) Technical - 528 jobs, £17,271.45
2. Fujitsu Services Limited - Star Trains - ME - 329 jobs, £11,612.86
3. Verifone UK LTD - 450 jobs, £7,735.68

### Most Common Job Types
1. TECH EXCHANGE - ND 1700 - 953 times, £16,262.66
2. TECH EXCHANGE - ND 1900 - 572 times, £14,945.62
3. NON TECH EXCHANGE - ND 1700 - 311 times, £3,462.71

## 🚀 Quick Start Commands

```bash
# View quick statistics
python3 quick_stats.py

# Interactive queries
python3 query_payslips.py

# Generate full report
python3 generate_report.py

# Export to CSV
python3 export_to_csv.py

# Re-extract (if PDFs updated)
python3 extract_payslips.py
```

## 💡 Common Use Cases

### 1. Check earnings for a specific week
```bash
python3 query_payslips.py
# Choose option 2, enter: 2024, 15
```

### 2. Get tax year summary
```bash
python3 query_payslips.py
# Choose option 3, enter: 2024
```

### 3. Find all jobs for a client
```bash
python3 query_payslips.py
# Choose option 6, enter: HSBC
```

### 4. Export data for Excel analysis
```bash
python3 export_to_csv.py
# Open job_items.csv in Excel
```

### 5. Direct SQL queries
```bash
sqlite3 payslips.db
# Then run SQL queries
```

## 📈 Example SQL Queries

```sql
-- Total by month
SELECT 
    tax_year,
    CAST((week_number - 1) / 4.33 AS INTEGER) + 1 as month,
    SUM(net_payment) as total
FROM payslips
GROUP BY tax_year, month;

-- High value jobs
SELECT client, job_type, amount
FROM job_items
WHERE amount >= 50
ORDER BY amount DESC;

-- Weekly trend
SELECT tax_year, week_number, net_payment
FROM payslips
ORDER BY tax_year, week_number;
```

## 🔧 Technical Details

### Database Schema

**payslips table:**
- Tax year and week identification
- Financial summaries (gross, net, YTD)
- Reference numbers (verification, UTR, VAT)
- Pay dates

**job_items table:**
- Individual job details
- Client and location information
- Job type and rates
- Linked to payslips via foreign key

### Data Quality
- All 78 PDFs processed successfully
- 100% extraction rate
- Financial totals validated
- Job items properly parsed and categorized

## 📝 Notes

- Database uses UK tax years (April 6 - April 5)
- Week numbers correspond to tax year weeks
- All monetary values in GBP (£)
- Safe to re-run extraction (uses REPLACE for updates)
- CSV files can be opened in Excel/Google Sheets
- Database can be backed up by copying payslips.db

## 🎯 Next Steps (Optional)

Consider adding:
- Expense tracking integration
- Mileage logging
- Tax calculation helpers
- Invoice generation
- Monthly/quarterly reports
- Data visualization (charts/graphs)
- Backup automation
- Multi-year comparison tools

## ✨ Summary

You now have a complete system to:
- ✅ Extract data from payslip PDFs automatically
- ✅ Store data in a searchable database
- ✅ Query and analyze earnings by week, client, job type
- ✅ Export to CSV for spreadsheet analysis
- ✅ Generate comprehensive reports
- ✅ Track earnings trends over time

All your payslip data is now organized, searchable, and ready for analysis!
