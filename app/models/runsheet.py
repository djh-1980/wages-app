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
            where_conditions = ["date IS NOT NULL"]
            
            if filter_year:
                where_conditions.append(f"substr(date, 7, 4) = '{filter_year}'")
            
            if filter_month:
                where_conditions.append(f"substr(date, 4, 2) = '{filter_month}'")
            
            if filter_week and filter_week.strip():
                # Calculate week number from date
                try:
                    week_num = int(filter_week)
                    where_conditions.append(f"""
                        CAST(strftime('%U', substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)) AS INTEGER) = {week_num - 1}
                    """)
                except ValueError:
                    pass  # Invalid week number, skip filter
            
            if filter_day:
                # Day of week (0=Sunday, 1=Monday, etc.)
                where_conditions.append(f"CAST(strftime('%w', substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)) AS INTEGER) = {filter_day}")
            
            where_clause = " AND ".join(where_conditions)
            
            # Get total count with filters
            count_query = f"SELECT COUNT(DISTINCT date) FROM run_sheet_jobs WHERE {where_clause}"
            cursor.execute(count_query)
            total = cursor.fetchone()[0]
            
            # Get run sheets grouped by date with sorting and filters
            if sort_column == 'date':
                order_clause = f"substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2) {sort_order.upper()}"
            else:
                order_clause = f"{sort_column} {sort_order.upper()}"
            
            query = f"""
                SELECT 
                    date,
                    COUNT(*) as job_count,
                    GROUP_CONCAT(DISTINCT customer) as customers,
                    GROUP_CONCAT(DISTINCT activity) as activities
                FROM run_sheet_jobs
                WHERE {where_clause}
                GROUP BY date
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
                
                if job_id and status in ['completed', 'missed', 'dnco', 'extra', 'pending']:
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
                    CASE WHEN d.mileage IS NOT NULL AND d.mileage > 0 THEN 1 ELSE 0 END as has_mileage
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
    def clear_all_runsheets():
        """Clear all run sheet data."""
        query = "DELETE FROM run_sheet_jobs"
        deleted = execute_query(query)
        return deleted
