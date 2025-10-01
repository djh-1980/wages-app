#!/usr/bin/env python3
"""
Quick statistics and common queries - run this for a fast overview.
"""

import sqlite3
import sys


def quick_stats(db_path="payslips.db"):
    """Display quick statistics."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("QUICK PAYSLIP STATISTICS")
    print("="*80)
    
    # Current status
    cursor.execute("""
        SELECT tax_year, week_number, net_payment
        FROM payslips
        ORDER BY tax_year DESC, week_number DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    print(f"\n📅 Latest payslip: Tax Year {row[0]}, Week {row[1]} - £{row[2]:,.2f}")
    
    # This tax year
    cursor.execute("""
        SELECT COUNT(*), SUM(net_payment), AVG(net_payment)
        FROM payslips
        WHERE tax_year = (SELECT MAX(tax_year) FROM payslips)
    """)
    weeks, total, avg = cursor.fetchone()
    print(f"\n💰 Current tax year ({row[0]}):")
    print(f"   Weeks worked: {weeks}")
    print(f"   Total earned: £{total:,.2f}")
    print(f"   Average/week: £{avg:,.2f}")
    print(f"   Projected annual: £{avg * 52:,.2f}")
    
    # Last 4 weeks average
    cursor.execute("""
        SELECT AVG(net_payment)
        FROM (
            SELECT net_payment
            FROM payslips
            ORDER BY tax_year DESC, week_number DESC
            LIMIT 4
        )
    """)
    last_4_avg = cursor.fetchone()[0]
    print(f"\n📊 Last 4 weeks average: £{last_4_avg:,.2f}")
    
    # This month (last 4.33 weeks)
    cursor.execute("""
        SELECT SUM(net_payment)
        FROM (
            SELECT net_payment
            FROM payslips
            ORDER BY tax_year DESC, week_number DESC
            LIMIT 4
        )
    """)
    this_month = cursor.fetchone()[0]
    print(f"📊 Last 4 weeks total: £{this_month:,.2f}")
    
    # Best week ever
    cursor.execute("""
        SELECT tax_year, week_number, net_payment
        FROM payslips
        ORDER BY net_payment DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    print(f"\n🏆 Best week ever: {row[0]} Week {row[1]} - £{row[2]:,.2f}")
    
    # Total all time
    cursor.execute("SELECT SUM(net_payment) FROM payslips")
    total_all = cursor.fetchone()[0]
    print(f"\n💎 Total earned (all time): £{total_all:,.2f}")
    
    # Top 3 clients
    print(f"\n👔 Top 3 clients:")
    cursor.execute("""
        SELECT client, COUNT(*) as jobs, SUM(amount) as total
        FROM job_items
        WHERE client IS NOT NULL
        GROUP BY client
        ORDER BY total DESC
        LIMIT 3
    """)
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {row[0][:50]} - {row[1]} jobs, £{row[2]:,.2f}")
    
    # Most common job type
    cursor.execute("""
        SELECT job_type, COUNT(*) as count
        FROM job_items
        WHERE job_type IS NOT NULL
        GROUP BY job_type
        ORDER BY count DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    print(f"\n🔨 Most common job: {row[0]} ({row[1]} times)")
    
    print("\n" + "="*80)
    print("Run 'python3 query_payslips.py' for detailed analysis")
    print("Run 'python3 generate_report.py' for full report")
    print("="*80 + "\n")
    
    conn.close()


if __name__ == "__main__":
    try:
        quick_stats()
    except sqlite3.OperationalError:
        print("\n❌ Error: Database not found. Run 'python3 extract_payslips.py' first.\n")
        sys.exit(1)
