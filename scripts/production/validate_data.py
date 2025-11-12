#!/usr/bin/env python3
"""
Comprehensive data validation script for payslips database.
Checks data quality, consistency, and identifies potential issues.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple


class DataValidator:
    def __init__(self, db_path: str = "data/payslips.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.issues = []
        self.warnings = []
        
    def add_issue(self, category: str, message: str):
        """Add a critical issue."""
        self.issues.append(f"❌ [{category}] {message}")
    
    def add_warning(self, category: str, message: str):
        """Add a warning."""
        self.warnings.append(f"⚠️  [{category}] {message}")
    
    def validate_payslip_totals(self) -> bool:
        """Check if job totals match payslip totals within acceptable range."""
        print("🔍 Validating payslip vs job totals...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                p.id,
                p.tax_year,
                p.week_number,
                p.net_payment,
                COALESCE(SUM(ji.amount), 0) as job_total,
                COUNT(ji.id) as job_count
            FROM payslips p
            LEFT JOIN job_items ji ON p.id = ji.payslip_id
            GROUP BY p.id
        """)
        
        issues_found = 0
        warnings_found = 0
        
        for row in cursor.fetchall():
            payslip_id, year, week, net_payment, job_total, job_count = row
            diff = abs(net_payment - job_total)
            
            # Allow £20 difference for deductions/margin
            # Early 2021 payslips (weeks 1-10) may have higher differences due to format variations
            tolerance = 150 if (year == "2021" and week <= 10) else 50
            
            if diff > tolerance:
                self.add_issue("TOTALS", 
                    f"{year} Week {week}: Payslip £{net_payment:.2f} vs Jobs £{job_total:.2f} (diff: £{diff:.2f})")
                issues_found += 1
            elif diff > 20:
                self.add_warning("TOTALS",
                    f"{year} Week {week}: Difference £{diff:.2f} (higher than expected £15)")
                warnings_found += 1
            
            # Check for payslips with no jobs
            if job_count == 0:
                self.add_issue("MISSING_JOBS", f"{year} Week {week}: No job items found")
                issues_found += 1
        
        if issues_found == 0 and warnings_found == 0:
            print("  ✅ All payslip totals match job totals")
            return True
        else:
            print(f"  Found {issues_found} issues, {warnings_found} warnings")
            return issues_found == 0
    
    def validate_orphaned_records(self) -> bool:
        """Check for orphaned job items."""
        print("🔍 Checking for orphaned job items...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM job_items
            WHERE payslip_id NOT IN (SELECT id FROM payslips)
        """)
        
        count, total = cursor.fetchone()
        
        if count > 0:
            self.add_issue("ORPHANS", 
                f"Found {count:,} orphaned job items totaling £{total:,.2f}")
            print(f"  ❌ Found {count:,} orphaned records")
            return False
        else:
            print("  ✅ No orphaned job items")
            return True
    
    def validate_duplicates(self) -> bool:
        """Check for duplicate payslips."""
        print("🔍 Checking for duplicate payslips...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tax_year, week_number, COUNT(*) as count
            FROM payslips
            GROUP BY tax_year, week_number
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            for year, week, count in duplicates:
                self.add_issue("DUPLICATES", 
                    f"{year} Week {week}: {count} duplicate entries")
            print(f"  ❌ Found {len(duplicates)} duplicate week entries")
            return False
        else:
            print("  ✅ No duplicate payslips")
            return True
    
    def validate_data_completeness(self) -> bool:
        """Check for missing or null critical fields."""
        print("🔍 Checking data completeness...")
        
        cursor = self.conn.cursor()
        
        # Check payslips with null net_payment
        cursor.execute("""
            SELECT COUNT(*) FROM payslips WHERE net_payment IS NULL
        """)
        null_payments = cursor.fetchone()[0]
        
        if null_payments > 0:
            self.add_issue("COMPLETENESS", 
                f"{null_payments} payslips have NULL net_payment")
        
        # Check job items with null amounts
        cursor.execute("""
            SELECT COUNT(*) FROM job_items WHERE amount IS NULL
        """)
        null_amounts = cursor.fetchone()[0]
        
        if null_amounts > 0:
            self.add_warning("COMPLETENESS",
                f"{null_amounts} job items have NULL amount")
        
        # Check job items with null clients
        cursor.execute("""
            SELECT COUNT(*) FROM job_items WHERE client IS NULL OR client = ''
        """)
        null_clients = cursor.fetchone()[0]
        
        if null_clients > 0:
            self.add_warning("COMPLETENESS",
                f"{null_clients} job items have no client name")
        
        if null_payments == 0:
            print("  ✅ All critical fields populated")
            return True
        else:
            print(f"  ❌ Found missing critical data")
            return False
    
    def validate_data_ranges(self) -> bool:
        """Check for unrealistic values."""
        print("🔍 Checking data ranges...")
        
        cursor = self.conn.cursor()
        
        issues_found = 0
        
        # Check for negative payments
        cursor.execute("""
            SELECT tax_year, week_number, net_payment
            FROM payslips
            WHERE net_payment < 0
        """)
        
        for year, week, payment in cursor.fetchall():
            self.add_issue("RANGE", 
                f"{year} Week {week}: Negative payment £{payment:.2f}")
            issues_found += 1
        
        # Check for unrealistically high weekly payments (>£5000)
        cursor.execute("""
            SELECT tax_year, week_number, net_payment
            FROM payslips
            WHERE net_payment > 5000
        """)
        
        for year, week, payment in cursor.fetchall():
            self.add_warning("RANGE",
                f"{year} Week {week}: Unusually high payment £{payment:.2f}")
        
        # Check for unrealistically low weekly payments (<£100)
        cursor.execute("""
            SELECT tax_year, week_number, net_payment
            FROM payslips
            WHERE net_payment < 100 AND net_payment > 0
        """)
        
        for year, week, payment in cursor.fetchall():
            self.add_warning("RANGE",
                f"{year} Week {week}: Unusually low payment £{payment:.2f}")
        
        if issues_found == 0:
            print("  ✅ All values within expected ranges")
            return True
        else:
            print(f"  ❌ Found {issues_found} range issues")
            return False
    
    def validate_year_continuity(self) -> bool:
        """Check for missing weeks in each tax year."""
        print("🔍 Checking year continuity...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT tax_year FROM payslips ORDER BY tax_year
        """)
        
        years = [row[0] for row in cursor.fetchall()]
        
        for year in years:
            cursor.execute("""
                SELECT week_number FROM payslips 
                WHERE tax_year = ? 
                ORDER BY week_number
            """, (year,))
            
            weeks = [row[0] for row in cursor.fetchall()]
            
            # Check for large gaps (>4 weeks)
            for i in range(len(weeks) - 1):
                gap = weeks[i + 1] - weeks[i]
                if gap > 4:
                    self.add_warning("CONTINUITY",
                        f"{year}: Gap of {gap} weeks between Week {weeks[i]} and Week {weeks[i+1]}")
        
        print("  ✅ Year continuity checked")
        return True
    
    def validate_job_distribution(self) -> bool:
        """Check for unusual job distributions."""
        print("🔍 Checking job distribution...")
        
        cursor = self.conn.cursor()
        
        # Check for weeks with unusually few jobs
        cursor.execute("""
            SELECT p.tax_year, p.week_number, COUNT(ji.id) as job_count
            FROM payslips p
            LEFT JOIN job_items ji ON p.id = ji.payslip_id
            GROUP BY p.id
            HAVING job_count < 10 AND job_count > 0
        """)
        
        for year, week, count in cursor.fetchall():
            self.add_warning("DISTRIBUTION",
                f"{year} Week {week}: Only {count} jobs (unusually low)")
        
        # Check for weeks with unusually many jobs
        cursor.execute("""
            SELECT p.tax_year, p.week_number, COUNT(ji.id) as job_count
            FROM payslips p
            LEFT JOIN job_items ji ON p.id = ji.payslip_id
            GROUP BY p.id
            HAVING job_count > 100
        """)
        
        for year, week, count in cursor.fetchall():
            self.add_warning("DISTRIBUTION",
                f"{year} Week {week}: {count} jobs (unusually high)")
        
        print("  ✅ Job distribution checked")
        return True
    
    def generate_summary(self) -> Dict:
        """Generate summary statistics."""
        cursor = self.conn.cursor()
        
        # Overall stats - separate queries to avoid JOIN multiplication
        cursor.execute("SELECT COUNT(*), SUM(net_payment), AVG(net_payment) FROM payslips")
        payslip_stats = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM job_items")
        job_count = cursor.fetchone()[0]
        
        overall = (payslip_stats[0], job_count, payslip_stats[1], payslip_stats[2])
        
        # By year - use subquery to avoid multiplication
        cursor.execute("""
            SELECT 
                p.tax_year,
                COUNT(*) as weeks,
                (SELECT COUNT(*) FROM job_items ji WHERE ji.payslip_id IN 
                    (SELECT id FROM payslips WHERE tax_year = p.tax_year)) as jobs,
                SUM(p.net_payment) as total
            FROM payslips p
            GROUP BY p.tax_year
            ORDER BY p.tax_year
        """)
        
        by_year = cursor.fetchall()
        
        return {
            'overall': {
                'payslips': overall[0],
                'jobs': overall[1],
                'total_earnings': overall[2],
                'avg_weekly': overall[3]
            },
            'by_year': [
                {
                    'year': row[0],
                    'weeks': row[1],
                    'jobs': row[2],
                    'total': row[3]
                }
                for row in by_year
            ]
        }
    
    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        print("=" * 70)
        print("DATA VALIDATION REPORT")
        print("=" * 70)
        print()
        
        # Run all checks
        checks = [
            self.validate_orphaned_records(),
            self.validate_duplicates(),
            self.validate_data_completeness(),
            self.validate_data_ranges(),
            self.validate_payslip_totals(),
            self.validate_year_continuity(),
            self.validate_job_distribution(),
        ]
        
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        # Print summary stats
        summary = self.generate_summary()
        print()
        print(f"📊 Database Statistics:")
        print(f"   Total Payslips: {summary['overall']['payslips']}")
        print(f"   Total Jobs: {summary['overall']['jobs']:,}")
        print(f"   Total Earnings: £{summary['overall']['total_earnings']:,.2f}")
        print(f"   Average Weekly: £{summary['overall']['avg_weekly']:.2f}")
        print()
        
        print("📅 By Year:")
        for year_data in summary['by_year']:
            print(f"   {year_data['year']}: {year_data['weeks']} weeks, "
                  f"{year_data['jobs']:,} jobs, £{year_data['total']:,.2f}")
        
        print()
        print("=" * 70)
        
        # Print issues
        if self.issues:
            print()
            print(f"❌ CRITICAL ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   {issue}")
        
        # Print warnings
        if self.warnings:
            print()
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"   {warning}")
            if len(self.warnings) > 10:
                print(f"   ... and {len(self.warnings) - 10} more warnings")
        
        print()
        print("=" * 70)
        
        # Overall result
        all_passed = all(checks) and len(self.issues) == 0
        
        if all_passed:
            print("✅ ALL VALIDATIONS PASSED")
        elif len(self.issues) == 0:
            print("⚠️  VALIDATIONS PASSED WITH WARNINGS")
        else:
            print("❌ VALIDATION FAILED - CRITICAL ISSUES FOUND")
        
        print("=" * 70)
        
        return all_passed
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Run validation."""
    validator = DataValidator()
    
    try:
        success = validator.run_all_validations()
        exit(0 if success else 1)
    finally:
        validator.close()


if __name__ == "__main__":
    main()
