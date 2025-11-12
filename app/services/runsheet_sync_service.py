"""
RunsheetSyncService - Handles synchronization between payslips and runsheets.
Automatically updates runsheet data when payslips are processed.
"""

from ..database import get_db_connection
from datetime import datetime


class RunsheetSyncService:
    """Service for synchronizing payslip data with runsheet records."""
    
    @staticmethod
    def sync_payslip_data_to_runsheets():
        """
        Sync payslip data to runsheets after payslip processing.
        Updates pay information and addresses for runsheet jobs.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            print("🔗 Syncing payslip data to runsheets...")
            
            # Add pay columns if they don't exist (for new installations)
            pay_columns = [
                "pay_amount REAL",
                "pay_rate REAL", 
                "pay_units REAL",
                "pay_week INTEGER",
                "pay_year TEXT",
                "pay_updated_at TIMESTAMP"
            ]
            
            for column in pay_columns:
                try:
                    cursor.execute(f"ALTER TABLE run_sheet_jobs ADD COLUMN {column}")
                except:
                    pass  # Column already exists
            
            # Update runsheet jobs with payslip pay data
            cursor.execute("""
                UPDATE run_sheet_jobs 
                SET 
                    pay_amount = (
                        SELECT j.amount 
                        FROM job_items j 
                        JOIN payslips p ON j.payslip_id = p.id
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_rate = (
                        SELECT j.rate 
                        FROM job_items j 
                        JOIN payslips p ON j.payslip_id = p.id
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_units = (
                        SELECT j.units 
                        FROM job_items j 
                        JOIN payslips p ON j.payslip_id = p.id
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_week = (
                        SELECT p.week_number 
                        FROM job_items j 
                        JOIN payslips p ON j.payslip_id = p.id
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_year = (
                        SELECT p.tax_year 
                        FROM job_items j 
                        JOIN payslips p ON j.payslip_id = p.id
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_updated_at = CURRENT_TIMESTAMP
                WHERE run_sheet_jobs.job_number IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM job_items j 
                    WHERE j.job_number = run_sheet_jobs.job_number
                )
            """)
            
            pay_updated_count = cursor.rowcount
            
            # Update address information for jobs with N/A addresses
            cursor.execute("""
                UPDATE run_sheet_jobs 
                SET 
                    job_address = (
                        SELECT j.location 
                        FROM job_items j 
                        WHERE j.job_number = run_sheet_jobs.job_number
                        AND j.location IS NOT NULL 
                        AND j.location != ''
                        AND j.location != 'N/A'
                        LIMIT 1
                    ),
                    customer = COALESCE(
                        (SELECT j.client 
                         FROM job_items j 
                         WHERE j.job_number = run_sheet_jobs.job_number
                         AND j.client IS NOT NULL 
                         AND j.client != ''
                         AND j.client != 'N/A'
                         LIMIT 1), 
                        customer
                    )
                WHERE run_sheet_jobs.job_number IS NOT NULL
                AND (
                    run_sheet_jobs.job_address IN ('N/A', '', 'n/a', 'N/a') 
                    OR run_sheet_jobs.job_address IS NULL
                    OR run_sheet_jobs.customer IN ('N/A', '', 'n/a', 'N/a') 
                    OR run_sheet_jobs.customer IS NULL
                )
                AND EXISTS (
                    SELECT 1 FROM job_items j 
                    WHERE j.job_number = run_sheet_jobs.job_number
                    AND (
                        (j.location IS NOT NULL AND j.location != '' AND j.location != 'N/A')
                        OR (j.client IS NOT NULL AND j.client != '' AND j.client != 'N/A')
                    )
                )
            """)
            
            address_updated_count = cursor.rowcount
            conn.commit()
            
            # Log results
            if pay_updated_count > 0:
                print(f"✅ Updated {pay_updated_count} runsheet jobs with pay information")
            
            if address_updated_count > 0:
                print(f"✅ Updated {address_updated_count} runsheet jobs with address/customer information")
            
            if pay_updated_count == 0 and address_updated_count == 0:
                print("✅ All runsheet data is already up to date")
            
            return {
                'pay_updated': pay_updated_count,
                'address_updated': address_updated_count,
                'success': True
            }
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error syncing payslip data: {e}")
            return {
                'pay_updated': 0,
                'address_updated': 0,
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    @staticmethod
    def get_sync_statistics():
        """Get statistics about payslip-runsheet synchronization."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get pay sync statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(pay_amount) as jobs_with_pay,
                    ROUND(AVG(pay_amount), 2) as avg_pay,
                    ROUND(SUM(pay_amount), 2) as total_pay
                FROM run_sheet_jobs
                WHERE job_number IS NOT NULL
            """)
            
            pay_stats = cursor.fetchone()
            total_jobs, jobs_with_pay, avg_pay, total_pay = pay_stats
            
            # Get address statistics
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN job_address NOT IN ('N/A', '', 'n/a', 'N/a') AND job_address IS NOT NULL THEN 1 END) as jobs_with_address,
                    COUNT(CASE WHEN customer NOT IN ('N/A', '', 'n/a', 'N/a') AND customer IS NOT NULL THEN 1 END) as jobs_with_customer
                FROM run_sheet_jobs
                WHERE job_number IS NOT NULL
            """)
            
            address_stats = cursor.fetchone()
            jobs_with_address, jobs_with_customer = address_stats
            
            return {
                'total_jobs': total_jobs,
                'jobs_with_pay': jobs_with_pay,
                'pay_match_rate': (jobs_with_pay / total_jobs * 100) if total_jobs > 0 else 0,
                'avg_pay': avg_pay or 0,
                'total_pay': total_pay or 0,
                'jobs_with_address': jobs_with_address,
                'address_completion_rate': (jobs_with_address / total_jobs * 100) if total_jobs > 0 else 0,
                'jobs_with_customer': jobs_with_customer,
                'customer_completion_rate': (jobs_with_customer / total_jobs * 100) if total_jobs > 0 else 0
            }
            
        except Exception as e:
            print(f"Error getting sync statistics: {e}")
            return None
        finally:
            conn.close()
