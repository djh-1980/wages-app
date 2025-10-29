"""
Payslip model - handles all payslip-related database operations.
Extracted from web_app.py to improve code organization.
"""

from ..database import get_db_connection, execute_query
import json


class PayslipModel:
    """Model for payslip data operations."""
    
    @staticmethod
    def get_summary():
        """Get overall summary statistics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_weeks,
                    SUM(net_payment) as total_earnings,
                    AVG(net_payment) as avg_weekly,
                    MIN(net_payment) as min_weekly,
                    MAX(net_payment) as max_weekly
                FROM payslips
            """)
            overall = dict(cursor.fetchone())
            
            # Total jobs
            cursor.execute("SELECT COUNT(*) as total_jobs FROM job_items")
            overall['total_jobs'] = cursor.fetchone()['total_jobs']
            
            # Current tax year
            cursor.execute("""
                SELECT 
                    tax_year,
                    COUNT(*) as weeks,
                    SUM(net_payment) as total,
                    AVG(net_payment) as avg
                FROM payslips
                WHERE tax_year = (SELECT MAX(tax_year) FROM payslips)
                GROUP BY tax_year
            """)
            current_year_row = cursor.fetchone()
            current_year = dict(current_year_row) if current_year_row else {}
            
            # Last 4 weeks
            cursor.execute("""
                SELECT AVG(net_payment) as avg
                FROM (
                    SELECT net_payment
                    FROM payslips
                    ORDER BY tax_year DESC, week_number DESC
                    LIMIT 4
                )
            """)
            last_4_weeks = cursor.fetchone()['avg']
            
            # Best week
            cursor.execute("""
                SELECT tax_year, week_number, net_payment
                FROM payslips
                ORDER BY net_payment DESC
                LIMIT 1
            """)
            best_week_row = cursor.fetchone()
            best_week = dict(best_week_row) if best_week_row else {}
            
            return {
                'overall': overall,
                'current_year': current_year,
                'last_4_weeks_avg': last_4_weeks,
                'best_week': best_week
            }
    
    @staticmethod
    def get_weekly_trend(limit=52, tax_year=None):
        """Get weekly earnings trend."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if tax_year:
                # Filter by specific tax year
                cursor.execute("""
                    SELECT tax_year, week_number, net_payment, pay_date
                    FROM payslips
                    WHERE tax_year = ?
                    ORDER BY week_number ASC
                """, (tax_year,))
                rows = [dict(row) for row in cursor.fetchall()]
            else:
                # Show last N weeks across all years
                cursor.execute("""
                    SELECT tax_year, week_number, net_payment, pay_date
                    FROM payslips
                    ORDER BY tax_year DESC, week_number DESC
                    LIMIT ?
                """, (limit,))
                rows = [dict(row) for row in cursor.fetchall()]
                rows.reverse()  # Show oldest to newest
            
            return rows
    
    @staticmethod
    def get_all_payslips(tax_year=None):
        """Get all payslips with job counts."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if tax_year:
                cursor.execute("""
                    SELECT 
                        p.*,
                        (SELECT COUNT(*) FROM job_items WHERE payslip_id = p.id) as job_count
                    FROM payslips p
                    WHERE tax_year = ?
                    ORDER BY week_number
                """, (tax_year,))
            else:
                cursor.execute("""
                    SELECT 
                        p.*,
                        (SELECT COUNT(*) FROM job_items WHERE payslip_id = p.id) as job_count
                    FROM payslips p
                    ORDER BY tax_year DESC, week_number DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_payslip_detail(payslip_id):
        """Get detailed payslip information with job items."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get payslip
            cursor.execute("SELECT * FROM payslips WHERE id = ?", (payslip_id,))
            payslip_row = cursor.fetchone()
            
            if not payslip_row:
                return None
            
            payslip = dict(payslip_row)
            
            # Get job items
            cursor.execute("""
                SELECT * FROM job_items
                WHERE payslip_id = ?
                ORDER BY id
            """, (payslip_id,))
            jobs = [dict(row) for row in cursor.fetchall()]
            
            return {
                'payslip': payslip,
                'jobs': jobs
            }
    
    @staticmethod
    def get_tax_years():
        """Get list of all tax years."""
        query = """
            SELECT DISTINCT tax_year
            FROM payslips
            ORDER BY tax_year DESC
        """
        rows = execute_query(query, fetch_all=True)
        return [row['tax_year'] for row in rows]
    
    @staticmethod
    def get_monthly_breakdown():
        """Get monthly breakdown of earnings."""
        query = """
            SELECT 
                tax_year,
                CAST((week_number - 1) / 4.33 AS INTEGER) + 1 as month,
                COUNT(*) as weeks,
                SUM(net_payment) as total
            FROM payslips
            GROUP BY tax_year, month
            ORDER BY tax_year, month
        """
        rows = execute_query(query, fetch_all=True)
        return [dict(row) for row in rows]
    
    @staticmethod
    def check_missing_weeks():
        """Check for missing payslips in each tax year."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all payslips grouped by tax year
            cursor.execute("""
                SELECT tax_year, week_number
                FROM payslips
                ORDER BY tax_year, week_number
            """)
            
            payslips = cursor.fetchall()
            
            # Group by tax year
            by_year = {}
            for row in payslips:
                year = row['tax_year']
                week = row['week_number']
                if year not in by_year:
                    by_year[year] = []
                by_year[year].append(week)
            
            # Check for missing weeks
            result = []
            for year in sorted(by_year.keys()):
                weeks = sorted(by_year[year])
                missing = []
                
                # Check for gaps
                if weeks:
                    min_week = min(weeks)
                    max_week = max(weeks)
                    
                    for week in range(min_week, max_week + 1):
                        if week not in weeks:
                            missing.append(week)
                
                result.append({
                    'tax_year': year,
                    'total_weeks': len(weeks),
                    'min_week': min(weeks) if weeks else 0,
                    'max_week': max(weeks) if weeks else 0,
                    'missing_weeks': missing,
                    'has_missing': len(missing) > 0
                })
            
            return result
    
    @staticmethod
    def clear_all_payslips():
        """Clear all payslip data."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM payslips")
            deleted_payslips = cursor.rowcount
            
            cursor.execute("DELETE FROM job_items")
            deleted_jobs = cursor.rowcount
            
            conn.commit()
            
            return {
                'deleted_payslips': deleted_payslips,
                'deleted_jobs': deleted_jobs
            }
