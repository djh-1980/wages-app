#!/usr/bin/env python3
"""
Query and analyze payslip data from the database.
"""

import sqlite3
import sys
from datetime import datetime
from typing import Optional


class PayslipQuery:
    def __init__(self, db_path: str = "data/payslips.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def list_all_payslips(self):
        """List all payslips with summary info."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tax_year, week_number, pay_date, net_payment,
                   (SELECT COUNT(*) FROM job_items WHERE payslip_id = payslips.id) as job_count
            FROM payslips
            ORDER BY tax_year, week_number
        """)
        
        print("\n" + "=" * 80)
        print("ALL PAYSLIPS")
        print("=" * 80)
        print(f"{'Year':<6} {'Week':<6} {'Pay Date':<12} {'Net Payment':<15} {'Jobs':<6}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            print(f"{row['tax_year']:<6} {row['week_number']:<6} {row['pay_date'] or 'N/A':<12} "
                  f"£{row['net_payment']:>12,.2f} {row['job_count']:<6}")
    
    def get_payslip_detail(self, tax_year: str, week_number: int):
        """Get detailed information for a specific payslip."""
        cursor = self.conn.cursor()
        
        # Get payslip summary
        cursor.execute("""
            SELECT * FROM payslips
            WHERE tax_year = ? AND week_number = ?
        """, (tax_year, week_number))
        
        payslip = cursor.fetchone()
        if not payslip:
            print(f"No payslip found for {tax_year} Week {week_number}")
            return
        
        print("\n" + "=" * 80)
        print(f"PAYSLIP DETAIL - Tax Year {tax_year}, Week {week_number}")
        print("=" * 80)
        print(f"Pay Date: {payslip['pay_date']}")
        print(f"Period End: {payslip['period_end']}")
        print(f"Verification Number: {payslip['verification_number']}")
        print(f"UTR Number: {payslip['utr_number']}")
        print(f"VAT Number: {payslip['vat_number']}")
        print()
        print(f"Total Company Income:           £{payslip['total_company_income']:>12,.2f}")
        print(f"Materials:                      £{payslip['materials']:>12,.2f}")
        print(f"Gross Subcontractor Payment:    £{payslip['gross_subcontractor_payment']:>12,.2f}")
        print(f"Gross Subcontractor Payment YTD:£{payslip['gross_subcontractor_payment_ytd']:>12,.2f}")
        print(f"Net Payment:                    £{payslip['net_payment']:>12,.2f}")
        print(f"Total Paid To Bank:             £{payslip['total_paid_to_bank']:>12,.2f}")
        
        # Get job items
        cursor.execute("""
            SELECT * FROM job_items
            WHERE payslip_id = ?
            ORDER BY id
        """, (payslip['id'],))
        
        jobs = cursor.fetchall()
        if jobs:
            print("\n" + "-" * 80)
            print("JOB ITEMS")
            print("-" * 80)
            for i, job in enumerate(jobs, 1):
                print(f"\n{i}. Job #{job['job_number']}")
                if job['client']:
                    print(f"   Client: {job['client']}")
                if job['location']:
                    print(f"   Location: {job['location']}")
                if job['job_type']:
                    print(f"   Type: {job['job_type']}")
                if job['units'] and job['rate']:
                    print(f"   Units: {job['units']}, Rate: £{job['rate']:.2f}, Amount: £{job['amount']:.2f}")
                if job['weekend_date']:
                    print(f"   Date: {job['weekend_date']}")
    
    def get_tax_year_summary(self, tax_year: str):
        """Get summary for a specific tax year."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as week_count,
                SUM(net_payment) as total_net,
                AVG(net_payment) as avg_net,
                MIN(net_payment) as min_net,
                MAX(net_payment) as max_net,
                SUM(gross_subcontractor_payment) as total_gross
            FROM payslips
            WHERE tax_year = ?
        """, (tax_year,))
        
        summary = cursor.fetchone()
        
        print("\n" + "=" * 80)
        print(f"TAX YEAR {tax_year} SUMMARY")
        print("=" * 80)
        print(f"Weeks worked: {summary['week_count']}")
        print(f"Total net payment: £{summary['total_net']:,.2f}")
        print(f"Total gross payment: £{summary['total_gross']:,.2f}")
        print(f"Average per week: £{summary['avg_net']:,.2f}")
        print(f"Minimum week: £{summary['min_net']:,.2f}")
        print(f"Maximum week: £{summary['max_net']:,.2f}")
        
        # Get job statistics
        cursor.execute("""
            SELECT COUNT(*) as job_count
            FROM job_items ji
            JOIN payslips p ON ji.payslip_id = p.id
            WHERE p.tax_year = ?
        """, (tax_year,))
        
        job_stats = cursor.fetchone()
        print(f"Total jobs: {job_stats['job_count']}")
        
        if summary['week_count'] > 0:
            avg_jobs_per_week = job_stats['job_count'] / summary['week_count']
            print(f"Average jobs per week: {avg_jobs_per_week:.1f}")
    
    def get_client_breakdown(self, tax_year: Optional[str] = None):
        """Get breakdown by client."""
        cursor = self.conn.cursor()
        
        if tax_year:
            cursor.execute("""
                SELECT 
                    ji.client,
                    COUNT(*) as job_count,
                    SUM(ji.amount) as total_amount
                FROM job_items ji
                JOIN payslips p ON ji.payslip_id = p.id
                WHERE p.tax_year = ? AND ji.client IS NOT NULL
                GROUP BY ji.client
                ORDER BY total_amount DESC
                LIMIT 20
            """, (tax_year,))
            title = f"TOP CLIENTS - Tax Year {tax_year}"
        else:
            cursor.execute("""
                SELECT 
                    ji.client,
                    COUNT(*) as job_count,
                    SUM(ji.amount) as total_amount
                FROM job_items ji
                WHERE ji.client IS NOT NULL
                GROUP BY ji.client
                ORDER BY total_amount DESC
                LIMIT 20
            """)
            title = "TOP CLIENTS - All Time"
        
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)
        print(f"{'Client':<50} {'Jobs':<8} {'Total':<15}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            client = row['client'][:48]
            print(f"{client:<50} {row['job_count']:<8} £{row['total_amount']:>12,.2f}")
    
    def get_job_type_breakdown(self, tax_year: Optional[str] = None):
        """Get breakdown by job type."""
        cursor = self.conn.cursor()
        
        if tax_year:
            cursor.execute("""
                SELECT 
                    ji.job_type,
                    COUNT(*) as job_count,
                    SUM(ji.amount) as total_amount,
                    AVG(ji.amount) as avg_amount
                FROM job_items ji
                JOIN payslips p ON ji.payslip_id = p.id
                WHERE p.tax_year = ? AND ji.job_type IS NOT NULL
                GROUP BY ji.job_type
                ORDER BY total_amount DESC
            """, (tax_year,))
            title = f"JOB TYPE BREAKDOWN - Tax Year {tax_year}"
        else:
            cursor.execute("""
                SELECT 
                    ji.job_type,
                    COUNT(*) as job_count,
                    SUM(ji.amount) as total_amount,
                    AVG(ji.amount) as avg_amount
                FROM job_items ji
                WHERE ji.job_type IS NOT NULL
                GROUP BY ji.job_type
                ORDER BY total_amount DESC
            """)
            title = "JOB TYPE BREAKDOWN - All Time"
        
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)
        print(f"{'Job Type':<40} {'Count':<8} {'Total':<15} {'Avg':<12}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            job_type = row['job_type'][:38]
            print(f"{job_type:<40} {row['job_count']:<8} £{row['total_amount']:>12,.2f} £{row['avg_amount']:>9,.2f}")
    
    def search_jobs(self, search_term: str):
        """Search for jobs by description."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.tax_year, p.week_number, ji.job_number,
                ji.client, ji.location, ji.job_type, ji.amount
            FROM job_items ji
            JOIN payslips p ON ji.payslip_id = p.id
            WHERE ji.description LIKE ?
            ORDER BY p.tax_year, p.week_number
        """, (f'%{search_term}%',))
        
        results = cursor.fetchall()
        
        print("\n" + "=" * 80)
        print(f"SEARCH RESULTS for '{search_term}' - {len(results)} matches")
        print("=" * 80)
        
        for row in results:
            print(f"{row['tax_year']} Week {row['week_number']:2d} | Job #{row['job_number']} | "
                  f"{row['client'] or 'N/A':<30} | £{row['amount']:>8,.2f}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def print_menu():
    print("\n" + "=" * 80)
    print("PAYSLIP QUERY MENU")
    print("=" * 80)
    print("1. List all payslips")
    print("2. View payslip detail")
    print("3. Tax year summary")
    print("4. Client breakdown")
    print("5. Job type breakdown")
    print("6. Search jobs")
    print("0. Exit")
    print()


def main():
    query = PayslipQuery()
    
    try:
        while True:
            print_menu()
            choice = input("Enter choice: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                query.list_all_payslips()
            elif choice == "2":
                tax_year = input("Enter tax year (e.g., 2024): ").strip()
                week_number = input("Enter week number: ").strip()
                try:
                    query.get_payslip_detail(tax_year, int(week_number))
                except ValueError:
                    print("Invalid week number")
            elif choice == "3":
                tax_year = input("Enter tax year (e.g., 2024): ").strip()
                query.get_tax_year_summary(tax_year)
            elif choice == "4":
                tax_year = input("Enter tax year (or press Enter for all): ").strip()
                query.get_client_breakdown(tax_year if tax_year else None)
            elif choice == "5":
                tax_year = input("Enter tax year (or press Enter for all): ").strip()
                query.get_job_type_breakdown(tax_year if tax_year else None)
            elif choice == "6":
                search_term = input("Enter search term: ").strip()
                query.search_jobs(search_term)
            else:
                print("Invalid choice")
            
            input("\nPress Enter to continue...")
    
    finally:
        query.close()


if __name__ == "__main__":
    main()
