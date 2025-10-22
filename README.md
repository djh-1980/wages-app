# Payslip Data Extraction Tool

This tool extracts data from SASER Limited payslip PDFs and stores it in a SQLite database for easy querying and analysis.

## Features

- **Automated extraction** of payslip data from PDFs
- **SQLite database** storage for efficient querying
- **Comprehensive data capture**:
  - Header information (verification number, UTR, pay dates, etc.)
  - Financial summary (gross/net payments, YTD totals)
  - Individual job items with client, location, and rates
- **Interactive query tool** for data analysis

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

Run the main interface:

```bash
python3 wages.py
```

This provides a menu with all available tools.

### Extract Data from PDFs

Run the extraction script to process all payslip PDFs:

```bash
python3 scripts/extract_payslips.py
```

This will:
- Scan the `PaySlips/` directory for all PDF files
- Extract data from each payslip
- Store the data in `data/payslips.db` (SQLite database)
- Display summary statistics

### Query the Database

Run the interactive query tool:

```bash
python3 scripts/query_payslips.py
```

Available queries:
1. **List all payslips** - Overview of all weeks
2. **View payslip detail** - Detailed breakdown of a specific week
3. **Tax year summary** - Statistics for a full tax year
4. **Client breakdown** - Top clients by earnings
5. **Job type breakdown** - Analysis by job type
6. **Search jobs** - Find jobs by keyword

## Database Schema

### `payslips` table
Stores summary information for each payslip:
- Tax year and week number
- Verification and reference numbers
- Financial totals (gross, net, YTD)
- Pay dates

### `job_items` table
Stores individual job entries:
- Job number and description
- Client and location
- Job type
- Units, rate, and amount
- Dates

## Direct SQL Queries

You can also query the database directly using SQLite:

```bash
sqlite3 data/payslips.db
```

Example queries:

```sql
-- Total earnings by tax year
SELECT tax_year, SUM(net_payment) as total
FROM payslips
GROUP BY tax_year;

-- Top 10 highest paying weeks
SELECT tax_year, week_number, net_payment
FROM payslips
ORDER BY net_payment DESC
LIMIT 10;

-- Jobs by specific client
SELECT p.tax_year, p.week_number, ji.job_type, ji.amount
FROM job_items ji
JOIN payslips p ON ji.payslip_id = p.id
WHERE ji.client LIKE '%HSBC%'
ORDER BY p.tax_year, p.week_number;
```

## File Structure

```
Wages-App/
├── PaySlips/              # PDF files organized by tax year
│   ├── 2024/
│   └── 2025/
├── data/                  # Database files
│   └── payslips.db       # SQLite database (created after extraction)
├── output/                # Generated reports and exports
│   ├── *.csv             # CSV exports
│   └── payslip_report.txt
├── scripts/               # Python scripts
│   ├── extract_payslips.py  # Main extraction script
│   ├── query_payslips.py    # Interactive query tool
│   ├── generate_report.py   # Report generator
│   ├── export_to_csv.py     # CSV export tool
│   └── quick_stats.py       # Quick statistics
├── docs/                  # Documentation
│   ├── USAGE_GUIDE.md
│   ├── WEB_APP_GUIDE.md
│   └── DEBIAN_DEPLOYMENT_GUIDE.md
├── templates/             # Web app HTML templates
├── static/                # Web app static files
├── web_app.py            # Flask web application
├── wages.py              # Main CLI interface
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Notes

- The tool is designed for UK tax years (April 6 - April 5)
- Week numbers correspond to the tax year week
- All monetary values are in GBP (£)
- The extraction handles variations in PDF formatting
- Re-running the extraction will update existing records (using REPLACE)

## Troubleshooting

If extraction fails for specific PDFs:
1. Check the PDF is not corrupted
2. Verify the filename format matches: `SASER Limited Payroll for Daniel Hanson, Week[N] [YEAR].pdf`
3. Review the console output for specific error messages

For parsing issues, the tool will continue processing other files and report errors at the end.
