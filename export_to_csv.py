#!/usr/bin/env python3
"""
Export payslip data to CSV files.
"""

import sqlite3
import csv
from pathlib import Path


def export_payslips_summary(db_path="payslips.db", output_file="payslips_summary.csv"):
    """Export payslips summary to CSV."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            tax_year, week_number, verification_number, utr_number,
            pay_date, period_end, vat_number, total_company_income,
            materials, gross_subcontractor_payment,
            gross_subcontractor_payment_ytd, net_payment,
            total_paid_to_bank, pdf_filename
        FROM payslips
        ORDER BY tax_year, week_number
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        print(f"✓ Exported {len(rows)} payslips to {output_file}")
    else:
        print("No payslips found in database")
    
    conn.close()


def export_job_items(db_path="payslips.db", output_file="job_items.csv"):
    """Export all job items to CSV."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.tax_year, p.week_number, p.pay_date,
            ji.job_number, ji.units, ji.rate, ji.amount,
            ji.client, ji.location, ji.job_type,
            ji.agency, ji.weekend_date, ji.description
        FROM job_items ji
        JOIN payslips p ON ji.payslip_id = p.id
        ORDER BY p.tax_year, p.week_number, ji.id
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        print(f"✓ Exported {len(rows)} job items to {output_file}")
    else:
        print("No job items found in database")
    
    conn.close()


def export_client_summary(db_path="payslips.db", output_file="client_summary.csv"):
    """Export client summary to CSV."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            ji.client,
            COUNT(*) as job_count,
            SUM(ji.amount) as total_amount,
            AVG(ji.amount) as avg_amount,
            MIN(ji.amount) as min_amount,
            MAX(ji.amount) as max_amount
        FROM job_items ji
        WHERE ji.client IS NOT NULL
        GROUP BY ji.client
        ORDER BY total_amount DESC
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        print(f"✓ Exported {len(rows)} clients to {output_file}")
    else:
        print("No clients found in database")
    
    conn.close()


def export_job_type_summary(db_path="payslips.db", output_file="job_type_summary.csv"):
    """Export job type summary to CSV."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            ji.job_type,
            COUNT(*) as job_count,
            SUM(ji.amount) as total_amount,
            AVG(ji.amount) as avg_amount,
            MIN(ji.amount) as min_amount,
            MAX(ji.amount) as max_amount
        FROM job_items ji
        WHERE ji.job_type IS NOT NULL
        GROUP BY ji.job_type
        ORDER BY total_amount DESC
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        print(f"✓ Exported {len(rows)} job types to {output_file}")
    else:
        print("No job types found in database")
    
    conn.close()


def export_weekly_summary(db_path="payslips.db", output_file="weekly_summary.csv"):
    """Export weekly summary with job counts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.tax_year,
            p.week_number,
            p.pay_date,
            p.net_payment,
            COUNT(ji.id) as job_count,
            AVG(ji.amount) as avg_job_amount
        FROM payslips p
        LEFT JOIN job_items ji ON p.id = ji.payslip_id
        GROUP BY p.id
        ORDER BY p.tax_year, p.week_number
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        print(f"✓ Exported {len(rows)} weeks to {output_file}")
    else:
        print("No weekly data found in database")
    
    conn.close()


def main():
    print("Exporting payslip data to CSV files...")
    print("=" * 60)
    
    export_payslips_summary()
    export_job_items()
    export_client_summary()
    export_job_type_summary()
    export_weekly_summary()
    
    print("=" * 60)
    print("Export complete!")


if __name__ == "__main__":
    main()
