"""
Runsheet model - handles all runsheet-related database operations.
Extracted from web_app.py to improve code organization.
"""

from ..database import get_db_connection, execute_query


class RunsheetModel:
    """Model for runsheet data operations."""
    
    @staticmethod
    def get_summary():
        """Get run sheets summary statistics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT date) as total_days,
                    COUNT(*) as total_jobs,
                    COUNT(DISTINCT customer) as unique_customers,
                    MIN(date) as first_date,
                    MAX(date) as last_date
                FROM run_sheet_jobs
                WHERE date IS NOT NULL
            """)
            overall = dict(cursor.fetchone())
            
            # Top customers
            cursor.execute("""
                SELECT customer, COUNT(*) as job_count
                FROM run_sheet_jobs
                WHERE customer IS NOT NULL
                GROUP BY customer
                ORDER BY job_count DESC
                LIMIT 10
            """)
            top_customers = [dict(row) for row in cursor.fetchall()]
            
            # Activity breakdown
            cursor.execute("""
                SELECT activity, COUNT(*) as count
                FROM run_sheet_jobs
                WHERE activity IS NOT NULL
                GROUP BY activity
                ORDER BY count DESC
            """)
            activities = [dict(row) for row in cursor.fetchall()]
            
            # Jobs per day average
            cursor.execute("""
                SELECT AVG(jobs_per_day) as avg_jobs_per_day
                FROM (
                    SELECT date, COUNT(*) as jobs_per_day
                    FROM run_sheet_jobs
                    WHERE date IS NOT NULL
                    GROUP BY date
                )
            """)
            avg_jobs = cursor.fetchone()['avg_jobs_per_day']
            
            return {
                'overall': overall,
                'top_customers': top_customers,
                'activities': activities,
                'avg_jobs_per_day': avg_jobs
            }
    
    @staticmethod
    def get_runsheets_list(page=1, per_page=20, sort_column='date', sort_order='desc', 
                          filter_year='', filter_month='', filter_week='', filter_day=''):
        """Get paginated list of run sheets with filters and sorting."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            offset = (page - 1) * per_page
            
            # Validate sort parameters
            valid_columns = ['date', 'job_count']
            if sort_column not in valid_columns:
                sort_column = 'date'
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'
            
            # Build WHERE clause for filters
            where_conditions = ["r.date IS NOT NULL"]
            
            if filter_year:
                where_conditions.append(f"substr(r.date, 7, 4) = '{filter_year}'")
            
            if filter_month:
                where_conditions.append(f"substr(r.date, 4, 2) = '{filter_month}'")
            
            if filter_week and filter_week.strip():
                # Calculate week number from date
                try:
                    week_num = int(filter_week)
                    where_conditions.append(f"""
                        CAST(strftime('%U', substr(r.date, 7, 4) || '-' || substr(r.date, 4, 2) || '-' || substr(r.date, 1, 2)) AS INTEGER) = {week_num - 1}
                    """)
                except ValueError:
                    pass  # Invalid week number, skip filter
            
            if filter_day:
                # Day of week (0=Sunday, 1=Monday, etc.)
                where_conditions.append(f"CAST(strftime('%w', substr(r.date, 7, 4) || '-' || substr(r.date, 4, 2) || '-' || substr(r.date, 1, 2)) AS INTEGER) = {filter_day}")
            
            where_clause = " AND ".join(where_conditions)
            
            # Get total count with filters
            count_query = f"SELECT COUNT(DISTINCT r.date) FROM run_sheet_jobs r WHERE {where_clause}"
            cursor.execute(count_query)
            total = cursor.fetchone()[0]
            
            # Get run sheets grouped by date with sorting and filters
            if sort_column == 'date':
                order_clause = f"substr(r.date, 7, 4) || '-' || substr(r.date, 4, 2) || '-' || substr(r.date, 1, 2) {sort_order.upper()}"
            else:
                order_clause = f"{sort_column} {sort_order.upper()}"
            
            query = f"""
                SELECT 
                    r.date,
                    COUNT(*) as job_count,
                    GROUP_CONCAT(DISTINCT r.customer) as customers,
                    GROUP_CONCAT(DISTINCT r.activity) as activities,
                    ROUND(SUM(r.pay_amount), 2) as daily_pay,
                    COUNT(CASE WHEN r.pay_amount IS NOT NULL THEN 1 END) as jobs_with_pay,
                    d.mileage,
                    d.fuel_cost
                FROM run_sheet_jobs r
                LEFT JOIN runsheet_daily_data d ON r.date = d.date
                WHERE {where_clause}
                GROUP BY r.date, d.mileage, d.fuel_cost
                ORDER BY {order_clause}
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, (per_page, offset))
            
            runsheets = [dict(row) for row in cursor.fetchall()]
            
            return {
                'runsheets': runsheets,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
    
    @staticmethod
    def get_jobs_for_date(date):
        """Get all jobs for a specific date."""
        query = """
            SELECT *
            FROM run_sheet_jobs
            WHERE date = ?
            ORDER BY job_number
        """
        rows = execute_query(query, (date,), fetch_all=True)
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_job_statuses(updates, date=None, mileage=None, fuel_cost=None):
        """Update job statuses for multiple jobs and save mileage/fuel data."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Update each job status
            for update in updates:
                job_id = update.get('job_id')
                status = update.get('status')
                
                if job_id and status.lower() in ['completed', 'missed', 'dnco', 'extra', 'pending']:
                    cursor.execute("""
                        UPDATE run_sheet_jobs
                        SET status = ?
                        WHERE id = ?
                    """, (status, job_id))
            
            # Save mileage and fuel cost if provided
            if date and (mileage is not None or fuel_cost is not None):
                cursor.execute("""
                    INSERT INTO runsheet_daily_data (date, mileage, fuel_cost, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(date) DO UPDATE SET
                        mileage = COALESCE(excluded.mileage, mileage),
                        fuel_cost = COALESCE(excluded.fuel_cost, fuel_cost),
                        updated_at = CURRENT_TIMESTAMP
                """, (date, mileage, fuel_cost))
            
            conn.commit()
            return len(updates)
    
    @staticmethod
    def get_daily_data(date):
        """Get mileage and fuel cost for a specific date."""
        query = """
            SELECT mileage, fuel_cost
            FROM runsheet_daily_data
            WHERE date = ?
        """
        row = execute_query(query, (date,), fetch_one=True)
        
        if row:
            return {
                'mileage': row['mileage'],
                'fuel_cost': row['fuel_cost']
            }
        else:
            return {
                'mileage': None,
                'fuel_cost': None
            }
    
    @staticmethod
    def update_job_status(job_id, status):
        """Update a single job's status."""
        if status not in ['completed', 'missed', 'dnco', 'extra', 'pending']:
            raise ValueError('Invalid status')
        
        query = """
            UPDATE run_sheet_jobs
            SET status = ?
            WHERE id = ?
        """
        rows_affected = execute_query(query, (status, job_id))
        return rows_affected > 0
    
    @staticmethod
    def add_extra_job(date, job_number, customer, activity='', job_address='', status='extra'):
        """Add an extra job to a run sheet."""
        query = """
            INSERT INTO run_sheet_jobs 
            (date, job_number, customer, activity, job_address, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (date, job_number, customer, activity, job_address, status))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def delete_job(job_id):
        """Delete a job from run sheets."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if job exists
            cursor.execute("SELECT id FROM run_sheet_jobs WHERE id = ?", (job_id,))
            if not cursor.fetchone():
                return False
            
            # Delete the job
            cursor.execute("DELETE FROM run_sheet_jobs WHERE id = ?", (job_id,))
            conn.commit()
            return True
    
    @staticmethod
    def get_autocomplete_data():
        """Get unique customers and activities for autocomplete."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get unique customers
            cursor.execute("""
                SELECT DISTINCT customer 
                FROM run_sheet_jobs 
                WHERE customer IS NOT NULL AND customer != ''
                ORDER BY customer
            """)
            customers = [row[0] for row in cursor.fetchall()]
            
            # Get unique activities
            cursor.execute("""
                SELECT DISTINCT activity 
                FROM run_sheet_jobs 
                WHERE activity IS NOT NULL AND activity != ''
                ORDER BY activity
            """)
            activities = [row[0] for row in cursor.fetchall()]
            
            return {
                'customers': customers,
                'activities': activities
            }
    
    @staticmethod
    def get_completion_status():
        """Get completion status for all run sheet dates."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get completion status for each date
            cursor.execute("""
                SELECT 
                    r.date,
                    COUNT(*) as total_jobs,
                    COUNT(CASE WHEN r.status IS NOT NULL AND r.status != 'pending' THEN 1 END) as jobs_with_actions,
                    CASE WHEN d.mileage IS NOT NULL THEN 1 ELSE 0 END as has_mileage
                FROM run_sheet_jobs r
                LEFT JOIN runsheet_daily_data d ON r.date = d.date
                GROUP BY r.date, d.mileage
                ORDER BY r.date DESC
            """)
            
            results = cursor.fetchall()
            status_map = {}
            
            for row in results:
                date, total, jobs_with_actions, has_mileage = row
                
                # Determine status based on action selections and mileage
                if jobs_with_actions == total and has_mileage:
                    status = 'completed'  # All jobs have actions selected + mileage recorded
                elif jobs_with_actions > 0 or has_mileage:
                    status = 'in_progress'  # Some jobs have actions selected OR mileage recorded
                else:
                    status = 'not_started'  # No actions selected AND no mileage
                
                status_map[date] = {
                    'status': status,
                    'total_jobs': total,
                    'jobs_with_actions': jobs_with_actions,
                    'has_mileage': has_mileage
                }
            
            return status_map
    
    @staticmethod
    def update_job_pay_info():
        """Update runsheet jobs with pay information from payslips using job numbers."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Add pay columns to run_sheet_jobs if they don't exist
            try:
                cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN pay_amount REAL")
                cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN pay_rate REAL") 
                cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN pay_units REAL")
                cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN pay_week INTEGER")
                cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN pay_year TEXT")
                cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN pay_updated_at TIMESTAMP")
            except:
                pass  # Columns already exist
            
            # Update runsheet jobs with payslip data
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
            
            updated_count = cursor.rowcount
            conn.commit()
            
            return {
                'updated_jobs': updated_count,
                'message': f'Successfully updated {updated_count} runsheet jobs with pay information'
            }
    
    @staticmethod
    def get_jobs_with_pay_info(date=None, limit=50):
        """Get runsheet jobs with their pay information."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    r.date,
                    r.job_number,
                    r.customer,
                    r.activity,
                    r.job_address,
                    r.status,
                    r.pay_amount,
                    r.pay_rate,
                    r.pay_units,
                    r.pay_week,
                    r.pay_year,
                    r.pay_updated_at
                FROM run_sheet_jobs r
                WHERE r.pay_amount IS NOT NULL
            """
            
            params = []
            if date:
                query += " AND r.date = ?"
                params.append(date)
            
            query += " ORDER BY r.date DESC, CAST(r.job_number AS INTEGER) DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    'date': row[0],
                    'job_number': row[1], 
                    'customer': row[2],
                    'activity': row[3],
                    'job_address': row[4],
                    'status': row[5],
                    'pay_amount': row[6],
                    'pay_rate': row[7],
                    'pay_units': row[8],
                    'pay_week': row[9],
                    'pay_year': row[10],
                    'pay_updated_at': row[11]
                })
            
            return jobs
    
    @staticmethod
    def get_discrepancy_report(limit=100, year=None, month=None):
        """Get jobs that are in payslips but missing from runsheets."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause for date filtering
            date_filter = ""
            params = []
            
            if year:
                date_filter += " AND p.tax_year = ?"
                params.append(year)
            
            if month:
                # Convert month number to month name for payslip filtering
                month_names = {
                    '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                    '05': 'May', '06': 'June', '07': 'July', '08': 'August', 
                    '09': 'September', '10': 'October', '11': 'November', '12': 'December'
                }
                if month in month_names:
                    date_filter += " AND j.date LIKE ?"
                    params.append(f"%/{month}/%")
            
            # Get jobs in payslips but not in runsheets
            query = f"""
                SELECT 
                    j.job_number,
                    j.client,
                    j.location,
                    j.postcode,
                    j.job_type,
                    j.date,
                    j.amount,
                    j.rate,
                    j.units,
                    p.week_number,
                    p.tax_year,
                    p.pay_date
                FROM job_items j
                JOIN payslips p ON j.payslip_id = p.id
                WHERE j.job_number IS NOT NULL 
                AND j.job_number NOT IN (
                    SELECT DISTINCT job_number 
                    FROM run_sheet_jobs 
                    WHERE job_number IS NOT NULL
                )
                {date_filter}
                ORDER BY p.tax_year DESC, p.week_number DESC, CAST(j.job_number AS INTEGER) DESC
                LIMIT ?
            """
            
            params.append(limit)
            cursor.execute(query, params)
            
            missing_jobs = []
            total_missing_value = 0
            
            for row in cursor.fetchall():
                job_data = {
                    'job_number': row[0],
                    'client': row[1],
                    'location': row[2],
                    'postcode': row[3],
                    'job_type': row[4],
                    'date': row[5],
                    'amount': row[6],
                    'rate': row[7],
                    'units': row[8],
                    'week_number': row[9],
                    'tax_year': row[10],
                    'pay_date': row[11]
                }
                missing_jobs.append(job_data)
                if row[6]:  # amount
                    total_missing_value += row[6]
            
            # Get total counts
            cursor.execute("SELECT COUNT(*) FROM job_items WHERE job_number IS NOT NULL")
            total_payslip_jobs = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE job_number IS NOT NULL")
            total_runsheet_jobs = cursor.fetchone()[0]
            
            # Get total missing count (not limited) with date filters
            total_query = f"""
                SELECT COUNT(*)
                FROM job_items j
                JOIN payslips p ON j.payslip_id = p.id
                WHERE j.job_number IS NOT NULL 
                AND j.job_number NOT IN (
                    SELECT DISTINCT job_number 
                    FROM run_sheet_jobs 
                    WHERE job_number IS NOT NULL
                )
                {date_filter}
            """
            cursor.execute(total_query, params[:-1])  # Exclude the LIMIT parameter
            total_missing_count = cursor.fetchone()[0]
            
            return {
                'missing_jobs': missing_jobs,
                'total_missing_count': total_missing_count,
                'total_missing_value': round(total_missing_value, 2),
                'total_payslip_jobs': total_payslip_jobs,
                'total_runsheet_jobs': total_runsheet_jobs,
                'match_rate': round((total_payslip_jobs - total_missing_count) / total_payslip_jobs * 100, 1) if total_payslip_jobs > 0 else 0
            }
    
    @staticmethod
    def clear_all_runsheets():
        """Clear all run sheet data."""
        query = "DELETE FROM run_sheet_jobs"
        deleted = execute_query(query)
        return deleted
