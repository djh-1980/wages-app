#!/usr/bin/env python3
"""
Generate a comprehensive text report of payslip data.
"""

import sqlite3
from datetime import datetime


def generate_report(db_path="data/payslips.db", output_file="data/output/payslip_report.txt"):
    """Generate a comprehensive text report."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(output_file, 'w') as f:
        # Header
        f.write("="*80 + "\n")
        f.write("PAYSLIP DATA ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        
        # Overall Summary
        f.write("OVERALL SUMMARY\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("SELECT COUNT(*), SUM(net_payment) FROM payslips")
        total_weeks, total_earnings = cursor.fetchone()
        f.write(f"Total weeks worked: {total_weeks}\n")
        f.write(f"Total net earnings: £{total_earnings:,.2f}\n")
        if total_weeks > 0:
            f.write(f"Average per week: £{total_earnings/total_weeks:,.2f}\n")
            f.write(f"Estimated annual rate: £{(total_earnings/total_weeks)*52:,.2f}\n\n")
        else:
            f.write(f"Average per week: £0.00\n")
            f.write(f"Estimated annual rate: £0.00\n\n")
        
        cursor.execute("SELECT COUNT(*) FROM job_items")
        total_jobs = cursor.fetchone()[0]
        f.write(f"Total jobs completed: {total_jobs}\n")
        if total_weeks > 0:
            f.write(f"Average jobs per week: {total_jobs/total_weeks:.1f}\n\n")
        else:
            f.write(f"Average jobs per week: 0.0\n\n")
        
        # By Tax Year
        f.write("\nBY TAX YEAR\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("""
            SELECT 
                tax_year,
                COUNT(*) as weeks,
                SUM(net_payment) as total,
                AVG(net_payment) as avg,
                MIN(net_payment) as min,
                MAX(net_payment) as max
            FROM payslips
            GROUP BY tax_year
            ORDER BY tax_year
        """)
        
        for row in cursor.fetchall():
            f.write(f"\nTax Year {row[0]}:\n")
            f.write(f"  Weeks worked: {row[1]}\n")
            f.write(f"  Total earnings: £{row[2]:,.2f}\n")
            f.write(f"  Average per week: £{row[3]:,.2f}\n")
            f.write(f"  Range: £{row[4]:,.2f} - £{row[5]:,.2f}\n")
        
        # Top 10 Weeks
        f.write("\n\nTOP 10 HIGHEST EARNING WEEKS\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Year':<6} {'Week':<6} {'Pay Date':<12} {'Net Payment':<15} {'Jobs':<6}\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("""
            SELECT 
                p.tax_year, p.week_number, p.pay_date, p.net_payment,
                COUNT(ji.id) as job_count
            FROM payslips p
            LEFT JOIN job_items ji ON p.id = ji.payslip_id
            GROUP BY p.id
            ORDER BY p.net_payment DESC
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            f.write(f"{row[0]:<6} {row[1]:<6} {row[2] or 'N/A':<12} £{row[3]:>12,.2f} {row[4]:<6}\n")
        
        # Top 10 Clients
        f.write("\n\nTOP 10 CLIENTS BY EARNINGS\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Client':<50} {'Jobs':<8} {'Total':<15}\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("""
            SELECT 
                client,
                COUNT(*) as job_count,
                SUM(amount) as total
            FROM job_items
            WHERE client IS NOT NULL
            GROUP BY client
            ORDER BY total DESC
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            client = row[0][:48]
            f.write(f"{client:<50} {row[1]:<8} £{row[2]:>12,.2f}\n")
        
        # Top 10 Job Types
        f.write("\n\nTOP 10 JOB TYPES BY VOLUME\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Job Type':<45} {'Count':<8} {'Total':<15} {'Avg':<12}\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("""
            SELECT 
                job_type,
                COUNT(*) as count,
                SUM(amount) as total,
                AVG(amount) as avg
            FROM job_items
            WHERE job_type IS NOT NULL
            GROUP BY job_type
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            job_type = row[0][:43]
            f.write(f"{job_type:<45} {row[1]:<8} £{row[2]:>12,.2f} £{row[3]:>9,.2f}\n")
        
        # Weekly Trend (last 12 weeks)
        f.write("\n\nRECENT WEEKLY TREND (Last 12 Weeks)\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Year':<6} {'Week':<6} {'Net Payment':<15} {'Jobs':<6} {'Avg/Job':<12}\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("""
            SELECT 
                p.tax_year, p.week_number, p.net_payment,
                COUNT(ji.id) as job_count,
                AVG(ji.amount) as avg_job
            FROM payslips p
            LEFT JOIN job_items ji ON p.id = ji.payslip_id
            GROUP BY p.id
            ORDER BY p.tax_year DESC, p.week_number DESC
            LIMIT 12
        """)
        
        rows = list(cursor.fetchall())
        rows.reverse()  # Show oldest to newest
        
        for row in rows:
            f.write(f"{row[0]:<6} {row[1]:<6} £{row[2]:>12,.2f} {row[3]:<6} £{row[4]:>9,.2f}\n")
        
        # Monthly Breakdown (approximate)
        f.write("\n\nMONTHLY BREAKDOWN (Approximate - 4.33 weeks/month)\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Tax Year':<10} {'Month':<8} {'Weeks':<8} {'Total':<15}\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("""
            SELECT 
                tax_year,
                CAST((week_number - 1) / 4.33 AS INTEGER) + 1 as month,
                COUNT(*) as weeks,
                SUM(net_payment) as total
            FROM payslips
            GROUP BY tax_year, month
            ORDER BY tax_year, month
        """)
        
        for row in cursor.fetchall():
            f.write(f"{row[0]:<10} {row[1]:<8} {row[2]:<8} £{row[3]:>12,.2f}\n")
        
        # Statistics
        f.write("\n\nSTATISTICS\n")
        f.write("-"*80 + "\n")
        
        cursor.execute("""
            SELECT 
                AVG(net_payment) as avg,
                MIN(net_payment) as min,
                MAX(net_payment) as max
            FROM payslips
        """)
        row = cursor.fetchone()
        f.write(f"Weekly earnings:\n")
        f.write(f"  Average: £{row[0]:,.2f}\n")
        f.write(f"  Minimum: £{row[1]:,.2f}\n")
        f.write(f"  Maximum: £{row[2]:,.2f}\n")
        f.write(f"  Range: £{row[2] - row[1]:,.2f}\n\n")
        
        cursor.execute("""
            SELECT 
                AVG(amount) as avg,
                MIN(amount) as min,
                MAX(amount) as max
            FROM job_items
            WHERE amount > 0
        """)
        row = cursor.fetchone()
        f.write(f"Job earnings:\n")
        f.write(f"  Average: £{row[0]:,.2f}\n")
        f.write(f"  Minimum: £{row[1]:,.2f}\n")
        f.write(f"  Maximum: £{row[2]:,.2f}\n\n")
        
        cursor.execute("""
            SELECT COUNT(DISTINCT client) FROM job_items WHERE client IS NOT NULL
        """)
        f.write(f"Unique clients: {cursor.fetchone()[0]}\n")
        
        cursor.execute("""
            SELECT COUNT(DISTINCT job_type) FROM job_items WHERE job_type IS NOT NULL
        """)
        f.write(f"Unique job types: {cursor.fetchone()[0]}\n")
        
        # Footer
        f.write("\n" + "="*80 + "\n")
        f.write("END OF REPORT\n")
        f.write("="*80 + "\n")
    
    conn.close()
    print(f"✓ Report generated: {output_file}")


if __name__ == "__main__":
    generate_report()
