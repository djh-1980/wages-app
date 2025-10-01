# Payslip Data Extraction - Usage Guide

## Quick Start

### 1. Extract Data from PDFs
```bash
python3 extract_payslips.py
```
This processes all PDF files in the `PaySlips/` directory and creates `payslips.db`.

### 2. Query the Data Interactively
```bash
python3 query_payslips.py
```
Interactive menu with options to:
- List all payslips
- View detailed payslip information
- Get tax year summaries
- Analyze clients and job types
- Search for specific jobs

### 3. Export to CSV
```bash
python3 export_to_csv.py
```
Creates 5 CSV files:
- `payslips_summary.csv` - Weekly payslip summaries
- `job_items.csv` - All individual jobs
- `client_summary.csv` - Earnings by client
- `job_type_summary.csv` - Earnings by job type
- `weekly_summary.csv` - Weekly statistics

## Common Queries

### View a Specific Week
```bash
python3 query_payslips.py
# Choose option 2, then enter: 2024, 15
```

### Get Tax Year Summary
```bash
python3 query_payslips.py
# Choose option 3, then enter: 2024
```

### Find All Jobs for a Client
```bash
python3 query_payslips.py
# Choose option 6, then enter: HSBC
```

## Direct SQL Queries

Open the database:
```bash
sqlite3 payslips.db
```

### Example Queries

**Total earnings by month (approximation):**
```sql
SELECT 
    tax_year,
    CAST((week_number - 1) / 4.33 AS INTEGER) + 1 as month,
    SUM(net_payment) as total
FROM payslips
GROUP BY tax_year, month
ORDER BY tax_year, month;
```

**Top 10 highest paying jobs:**
```sql
SELECT 
    p.tax_year, p.week_number, ji.client, ji.job_type, ji.amount
FROM job_items ji
JOIN payslips p ON ji.payslip_id = p.id
ORDER BY ji.amount DESC
LIMIT 10;
```

**Average earnings by day of week (if pay_date available):**
```sql
SELECT 
    strftime('%w', pay_date) as day_of_week,
    COUNT(*) as weeks,
    AVG(net_payment) as avg_payment
FROM payslips
WHERE pay_date IS NOT NULL
GROUP BY day_of_week;
```

**Jobs by location:**
```sql
SELECT 
    location,
    COUNT(*) as job_count,
    SUM(amount) as total_amount
FROM job_items
WHERE location IS NOT NULL
GROUP BY location
ORDER BY total_amount DESC
LIMIT 20;
```

**Weekly earnings trend:**
```sql
SELECT 
    tax_year,
    week_number,
    net_payment,
    AVG(net_payment) OVER (
        ORDER BY tax_year, week_number 
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ) as moving_avg_4week
FROM payslips
ORDER BY tax_year, week_number;
```

## Useful Scripts

### Quick Overview
```bash
python3 << 'EOF'
from query_payslips import PayslipQuery
q = PayslipQuery()
q.get_tax_year_summary("2024")
q.get_client_breakdown("2024")
q.close()
EOF
```

### Export Specific Tax Year
```bash
sqlite3 payslips.db << 'EOF'
.headers on
.mode csv
.output payslips_2024.csv
SELECT * FROM payslips WHERE tax_year = '2024';
.quit
EOF
```

### Find High-Value Jobs
```bash
sqlite3 payslips.db << 'EOF'
.headers on
.mode column
SELECT 
    p.tax_year, p.week_number, ji.client, ji.job_type, ji.amount
FROM job_items ji
JOIN payslips p ON ji.payslip_id = p.id
WHERE ji.amount >= 50
ORDER BY ji.amount DESC;
.quit
EOF
```

## Database Schema Reference

### `payslips` table
- `id` - Primary key
- `tax_year` - Tax year (2024, 2025, etc.)
- `week_number` - Week number (1-52)
- `verification_number` - Payslip verification number
- `utr_number` - UTR number
- `pay_date` - Payment date
- `period_end` - Period end date
- `vat_number` - VAT number
- `total_company_income` - Total company income
- `materials` - Materials cost
- `gross_subcontractor_payment` - Gross payment for the week
- `gross_subcontractor_payment_ytd` - Year-to-date gross payment
- `net_payment` - Net payment (take-home)
- `total_paid_to_bank` - Total paid to bank
- `pdf_filename` - Original PDF filename
- `extracted_at` - Timestamp of extraction

### `job_items` table
- `id` - Primary key
- `payslip_id` - Foreign key to payslips table
- `units` - Number of units (usually 1)
- `rate` - Rate per unit
- `amount` - Total amount (units × rate)
- `description` - Full job description
- `job_number` - Job reference number
- `client` - Client name
- `location` - Job location
- `job_type` - Type of job
- `agency` - Agency name (usually "Rico")
- `weekend_date` - Weekend date

## Tips

1. **Re-running extraction**: Safe to run multiple times - it will update existing records
2. **CSV files**: Open in Excel, Google Sheets, or any spreadsheet software
3. **Backup**: Keep a backup of `payslips.db` before making changes
4. **Custom queries**: Use the SQLite database directly for complex analysis
5. **Tax calculations**: Remember these are gross/net payments - consult with accountant for tax purposes

## Troubleshooting

**No data extracted:**
- Check that PDF files are in `PaySlips/` directory
- Verify filename format matches expected pattern

**Missing fields:**
- Some PDFs may have different formats
- Check the extraction output for errors

**Database locked:**
- Close any open connections to `payslips.db`
- Only one process can write at a time

## Next Steps

Consider adding:
- Monthly/quarterly reports
- Tax calculation helpers
- Expense tracking
- Mileage logging
- Invoice generation
