"""
Reports and analytics API routes blueprint.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, jsonify, request
from ..models.payslip import PayslipModel
from ..models.runsheet import RunsheetModel
from ..database import get_db_connection
from ..services.report_service import ReportService

reports_bp = Blueprint('reports_api', __name__, url_prefix='/api')


@reports_bp.route('/clients')
def api_clients():
    """Get client breakdown."""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    client,
                    COUNT(*) as job_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM job_items
                WHERE client IS NOT NULL
                GROUP BY client
                ORDER BY total_amount DESC
                LIMIT ?
            """, (limit,))
            
            rows = [dict(row) for row in cursor.fetchall()]
            return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/job_types')
def api_job_types():
    """Get job type breakdown."""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    job_type,
                    COUNT(*) as job_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM job_items
                WHERE job_type IS NOT NULL
                GROUP BY job_type
                ORDER BY job_count DESC
                LIMIT ?
            """, (limit,))
            
            rows = [dict(row) for row in cursor.fetchall()]
            return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/all_clients')
def api_all_clients():
    """Get list of all unique clients."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT client
                FROM job_items
                WHERE client IS NOT NULL
                ORDER BY client
            """)
            
            clients = [row['client'] for row in cursor.fetchall()]
            return jsonify(clients)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/all_job_types')
def api_all_job_types():
    """Get list of all unique job types."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT job_type
                FROM job_items
                WHERE job_type IS NOT NULL
                ORDER BY job_type
            """)
            
            job_types = [row['job_type'] for row in cursor.fetchall()]
            return jsonify(job_types)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/custom_report')
def api_custom_report():
    """Generate custom filtered report with grouping support."""
    try:
        # Get filters from query params
        tax_year = request.args.get('tax_year')
        client = request.args.get('client')
        job_type = request.args.get('job_type')
        week_from = request.args.get('week_from', type=int)
        week_to = request.args.get('week_to', type=int)
        use_groups = request.args.get('use_groups', 'false') == 'true'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Load groupings if needed
            groupings = {}
            if use_groups:
                cursor.execute("SELECT value FROM settings WHERE key = 'groupings'")
                row = cursor.fetchone()
                if row:
                    import json
                    groupings = json.loads(row['value'])
            
            # Build dynamic query
            query = """
                SELECT 
                    p.tax_year,
                    p.week_number,
                    p.pay_date,
                    ji.job_number,
                    ji.client,
                    ji.location,
                    ji.job_type,
                    ji.date,
                    ji.time,
                    ji.amount,
                    ji.description
                FROM job_items ji
                JOIN payslips p ON ji.payslip_id = p.id
                WHERE 1=1
            """
            
            params = []
            
            if tax_year:
                query += " AND p.tax_year = ?"
                params.append(tax_year)
            
            if client:
                # Check if this is a group name
                if use_groups and 'client_groups' in groupings and client in groupings['client_groups']:
                    # Filter by any client in the group
                    client_list = groupings['client_groups'][client]
                    placeholders = ','.join(['?' for _ in client_list])
                    query += f" AND ji.client IN ({placeholders})"
                    params.extend(client_list)
                else:
                    query += " AND ji.client = ?"
                    params.append(client)
            
            if job_type:
                # Check if this is a group name
                if use_groups and 'job_type_groups' in groupings and job_type in groupings['job_type_groups']:
                    # Filter by any job type in the group
                    job_type_list = groupings['job_type_groups'][job_type]
                    placeholders = ','.join(['?' for _ in job_type_list])
                    query += f" AND ji.job_type IN ({placeholders})"
                    params.extend(job_type_list)
                else:
                    query += " AND ji.job_type = ?"
                    params.append(job_type)
            
            if week_from:
                query += " AND p.week_number >= ?"
                params.append(week_from)
            
            if week_to:
                query += " AND p.week_number <= ?"
                params.append(week_to)
            
            query += " ORDER BY p.tax_year DESC, p.week_number DESC, ji.id"
            
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            
            # Apply grouping to display names if requested
            if use_groups and groupings:
                for row in rows:
                    # Replace client with group name
                    if 'client_groups' in groupings:
                        for group_name, clients in groupings['client_groups'].items():
                            if row['client'] in clients:
                                row['client_group'] = group_name
                                break
                    
                    # Replace job type with group name
                    if 'job_type_groups' in groupings:
                        for group_name, job_types in groupings['job_type_groups'].items():
                            if row['job_type'] in job_types:
                                row['job_type_group'] = group_name
                                break
            
            return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/year_comparison')
def api_year_comparison():
    """Get year-over-year comparison data."""
    try:
        comparison_data = {}
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all tax years
            cursor.execute("SELECT DISTINCT tax_year FROM payslips ORDER BY tax_year")
            years = [row['tax_year'] for row in cursor.fetchall()]
            
            for year in years:
                cursor.execute("""
                    SELECT 
                        week_number,
                        net_payment
                    FROM payslips
                    WHERE tax_year = ?
                    ORDER BY week_number
                """, (year,))
                
                comparison_data[year] = [
                    {'week': row['week_number'], 'amount': row['net_payment']}
                    for row in cursor.fetchall()
                ]
        
        return jsonify(comparison_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/earnings_forecast')
def api_earnings_forecast():
    """Predict future earnings based on historical trends."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current year data
            cursor.execute("""
                SELECT tax_year, week_number, net_payment
                FROM payslips
                WHERE tax_year = (SELECT MAX(tax_year) FROM payslips)
                ORDER BY week_number
            """)
            
            current_year_data = [dict(row) for row in cursor.fetchall()]
            
            if not current_year_data:
                return jsonify({'error': 'No data available'}), 404
            
            current_year = current_year_data[0]['tax_year']
            weeks_worked = len(current_year_data)
            total_earned = sum(row['net_payment'] for row in current_year_data)
            avg_weekly = total_earned / weeks_worked if weeks_worked > 0 else 0
            
            # Calculate trend (simple linear regression on last 12 weeks)
            recent_weeks = current_year_data[-12:] if len(current_year_data) >= 12 else current_year_data
            if len(recent_weeks) >= 2:
                # Simple trend calculation
                x_values = list(range(len(recent_weeks)))
                y_values = [row['net_payment'] for row in recent_weeks]
                
                n = len(x_values)
                sum_x = sum(x_values)
                sum_y = sum(y_values)
                sum_xy = sum(x * y for x, y in zip(x_values, y_values))
                sum_x2 = sum(x * x for x in x_values)
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
                trend = 'increasing' if slope > 10 else 'decreasing' if slope < -10 else 'stable'
            else:
                slope = 0
                trend = 'stable'
            
            # Forecast remaining weeks
            weeks_remaining = 52 - weeks_worked
            forecast_data = []
            
            for i in range(1, weeks_remaining + 1):
                week_num = weeks_worked + i
                # Use average with trend adjustment
                predicted_amount = avg_weekly + (slope * i)
                forecast_data.append({
                    'week': week_num,
                    'predicted_amount': max(0, predicted_amount),  # Don't predict negative
                    'confidence': 'high' if i <= 4 else 'medium' if i <= 12 else 'low'
                })
            
            projected_year_end = total_earned + sum(f['predicted_amount'] for f in forecast_data)
            
            return jsonify({
                'current_year': current_year,
                'weeks_worked': weeks_worked,
                'total_earned': total_earned,
                'avg_weekly': avg_weekly,
                'trend': trend,
                'slope': slope,
                'forecast': forecast_data,
                'projected_year_end': projected_year_end
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/client_heatmap')
def api_client_heatmap():
    """Get client activity heatmap data (clients by month)."""
    try:
        tax_year = request.args.get('tax_year')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if tax_year:
                query = """
                    SELECT 
                        ji.client,
                        p.tax_year,
                        CAST((p.week_number - 1) / 4.33 AS INTEGER) + 1 as month,
                        COUNT(*) as job_count,
                        SUM(ji.amount) as total_amount
                    FROM job_items ji
                    JOIN payslips p ON ji.payslip_id = p.id
                    WHERE ji.client IS NOT NULL AND p.tax_year = ?
                    GROUP BY ji.client, p.tax_year, month
                    ORDER BY total_amount DESC
                """
                cursor.execute(query, (tax_year,))
            else:
                query = """
                    SELECT 
                        ji.client,
                        p.tax_year,
                        CAST((p.week_number - 1) / 4.33 AS INTEGER) + 1 as month,
                        COUNT(*) as job_count,
                        SUM(ji.amount) as total_amount
                    FROM job_items ji
                    JOIN payslips p ON ji.payslip_id = p.id
                    WHERE ji.client IS NOT NULL
                    GROUP BY ji.client, p.tax_year, month
                    ORDER BY total_amount DESC
                """
                cursor.execute(query)
            
            rows = [dict(row) for row in cursor.fetchall()]
            
            # Get top 10 clients overall
            cursor.execute("""
                SELECT client, SUM(amount) as total
                FROM job_items
                WHERE client IS NOT NULL
                GROUP BY client
                ORDER BY total DESC
                LIMIT 10
            """)
            top_clients = [row['client'] for row in cursor.fetchall()]
            
            return jsonify({
                'heatmap_data': rows,
                'top_clients': top_clients
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/weekly_performance')
def api_weekly_performance():
    """Analyze best and worst performing weeks with context."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get best weeks
            cursor.execute("""
                SELECT 
                    p.id,
                    p.tax_year,
                    p.week_number,
                    p.pay_date,
                    p.net_payment,
                    COUNT(ji.id) as job_count,
                    GROUP_CONCAT(DISTINCT ji.client) as clients
                FROM payslips p
                LEFT JOIN job_items ji ON p.id = ji.payslip_id
                GROUP BY p.id
                ORDER BY p.net_payment DESC
                LIMIT 10
            """)
            best_weeks = [dict(row) for row in cursor.fetchall()]
            
            # Get worst weeks (but not zero)
            cursor.execute("""
                SELECT 
                    p.id,
                    p.tax_year,
                    p.week_number,
                    p.pay_date,
                    p.net_payment,
                    COUNT(ji.id) as job_count,
                    GROUP_CONCAT(DISTINCT ji.client) as clients
                FROM payslips p
                LEFT JOIN job_items ji ON p.id = ji.payslip_id
                WHERE p.net_payment > 0
                GROUP BY p.id
                ORDER BY p.net_payment ASC
                LIMIT 10
            """)
            worst_weeks = [dict(row) for row in cursor.fetchall()]
            
            # Get average for comparison
            cursor.execute("SELECT AVG(net_payment) as avg FROM payslips WHERE net_payment > 0")
            average = cursor.fetchone()['avg']
            
            return jsonify({
                'best_weeks': best_weeks,
                'worst_weeks': worst_weeks,
                'average': average
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/discrepancies')
def api_reports_discrepancies():
    """Comprehensive reconciliation between runsheet jobs and payslip jobs by week."""
    try:
        from datetime import datetime, timedelta
        from ..utils.company_calendar import company_calendar
        
        # Get filter parameters - week_number and tax_year
        week_number = request.args.get('week_number', type=int)
        tax_year = request.args.get('tax_year', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # If no week specified, use the most recent payslip week
            if not week_number or not tax_year:
                cursor.execute("""
                    SELECT week_number, tax_year, period_end
                    FROM payslips 
                    WHERE period_end IS NOT NULL 
                    ORDER BY tax_year DESC, week_number DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    week_number = result['week_number']
                    tax_year = result['tax_year']
                else:
                    return jsonify({'error': 'No payslips found'}), 404
            
            # Get the date range for this week using company calendar
            sunday, saturday = company_calendar.get_week_dates(week_number, tax_year)
            week_start = company_calendar.format_date_string(sunday)
            week_end = company_calendar.format_date_string(saturday)
            
            # Generate all dates in the week range
            dates_in_week = []
            current = sunday
            while current <= saturday:
                dates_in_week.append(current.strftime('%d/%m/%Y'))
                current += timedelta(days=1)
            
            placeholders = ','.join('?' * len(dates_in_week))
            
            # Get all job numbers from payslips for this week
            cursor.execute(f"""
                SELECT ji.job_number, ji.client, ji.location, ji.amount, ji.date, ji.description,
                       p.week_number, p.tax_year
                FROM job_items ji
                JOIN payslips p ON ji.payslip_id = p.id
                WHERE p.week_number = ? AND p.tax_year = ?
                AND ji.job_number IS NOT NULL AND ji.job_number != ''
                AND ji.client NOT IN ('Deduction', 'Company Margin')
            """, (week_number, tax_year))
            
            payslip_jobs = {}
            for row in cursor.fetchall():
                job_num = row['job_number']
                if job_num not in payslip_jobs:
                    payslip_jobs[job_num] = {
                        'job_number': job_num,
                        'client': row['client'],
                        'location': row['location'],
                        'amount': row['amount'] or 0,
                        'date': row['date'],
                        'description': row['description'],
                        'week_number': row['week_number'],
                        'tax_year': row['tax_year']
                    }
            
            # Get all job numbers from run sheets for the same week date range
            cursor.execute(f"""
                SELECT job_number, customer, activity, job_address, pay_amount, date, status
                FROM run_sheet_jobs
                WHERE date IN ({placeholders})
                AND job_number IS NOT NULL AND job_number != ''
            """, dates_in_week)
            
            runsheet_jobs = {}
            for row in cursor.fetchall():
                job_num = row['job_number']
                if job_num not in runsheet_jobs:
                    runsheet_jobs[job_num] = {
                        'job_number': job_num,
                        'customer': row['customer'],
                        'activity': row['activity'],
                        'address': row['job_address'],
                        'pay_amount': row['pay_amount'] or 0,
                        'date': row['date'],
                        'status': row['status']
                    }
            
            # Reconciliation analysis
            payslip_job_numbers = set(payslip_jobs.keys())
            runsheet_job_numbers = set(runsheet_jobs.keys())
            
            # 1. Jobs on payslip but missing from runsheets (paid but no record)
            missing_from_runsheets = []
            missing_from_runsheets_value = 0
            for job_num in payslip_job_numbers - runsheet_job_numbers:
                job = payslip_jobs[job_num]
                missing_from_runsheets.append(job)
                missing_from_runsheets_value += job['amount']
            
            # 2. Jobs on runsheet but missing from payslip (worked but not paid)
            missing_from_payslips = []
            missing_from_payslips_value = 0
            for job_num in runsheet_job_numbers - payslip_job_numbers:
                job = runsheet_jobs[job_num]
                # Only include if status suggests it should be paid
                if job['status'] not in ['DNCO', 'missed', 'pending']:
                    missing_from_payslips.append(job)
                    missing_from_payslips_value += job['pay_amount']
            
            # 3. Jobs on both but with amount mismatches
            amount_mismatches = []
            mismatch_total_difference = 0
            for job_num in payslip_job_numbers & runsheet_job_numbers:
                payslip_job = payslip_jobs[job_num]
                runsheet_job = runsheet_jobs[job_num]
                
                payslip_amount = payslip_job['amount']
                runsheet_amount = runsheet_job['pay_amount']
                
                # Check for mismatch (allow 0.01 tolerance for rounding)
                if abs(payslip_amount - runsheet_amount) > 0.01:
                    difference = payslip_amount - runsheet_amount
                    amount_mismatches.append({
                        'job_number': job_num,
                        'customer': runsheet_job['customer'],
                        'date': runsheet_job['date'],
                        'payslip_amount': payslip_amount,
                        'runsheet_amount': runsheet_amount,
                        'difference': difference,
                        'status': runsheet_job['status']
                    })
                    mismatch_total_difference += difference
            
            # Calculate statistics
            total_payslip_jobs = len(payslip_job_numbers)
            total_runsheet_jobs = len(runsheet_job_numbers)
            matched_jobs = len(payslip_job_numbers & runsheet_job_numbers)
            match_rate = round((matched_jobs / total_payslip_jobs * 100), 1) if total_payslip_jobs > 0 else 0
            
            return jsonify({
                'summary': {
                    'week_number': week_number,
                    'tax_year': tax_year,
                    'week_start': week_start,
                    'week_end': week_end,
                    'total_payslip_jobs': total_payslip_jobs,
                    'total_runsheet_jobs': total_runsheet_jobs,
                    'matched_jobs': matched_jobs,
                    'match_rate': match_rate,
                    'missing_from_runsheets_count': len(missing_from_runsheets),
                    'missing_from_runsheets_value': round(missing_from_runsheets_value, 2),
                    'missing_from_payslips_count': len(missing_from_payslips),
                    'missing_from_payslips_value': round(missing_from_payslips_value, 2),
                    'amount_mismatches_count': len(amount_mismatches),
                    'amount_mismatches_difference': round(mismatch_total_difference, 2)
                },
                'missing_from_runsheets': missing_from_runsheets,
                'missing_from_payslips': missing_from_payslips,
                'amount_mismatches': amount_mismatches,
                'payslip_jobs': payslip_jobs,
                'runsheet_jobs': runsheet_jobs
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/email-audit')
def api_email_audit_trail():
    """Get email confirmation audit trail."""
    try:
        # Get filter parameters
        year = request.args.get('year', '')
        month = request.args.get('month', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            if year and month:
                where_conditions.append("strftime('%Y', sent_at) = ? AND strftime('%m', sent_at) = ?")
                params.extend([year, month.zfill(2)])
            elif year:
                where_conditions.append("strftime('%Y', sent_at) = ?")
                params.append(year)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Get email audit log
            cursor.execute(f"""
                SELECT 
                    id,
                    job_number,
                    customer,
                    location,
                    agreed_rate,
                    job_date,
                    sent_to,
                    cc_to,
                    user_name,
                    email_subject,
                    message_id,
                    sent_at,
                    status
                FROM email_audit_log
                WHERE {where_clause}
                ORDER BY sent_at DESC
            """, params)
            
            emails = [dict(row) for row in cursor.fetchall()]
            
            # Get summary statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_emails,
                    SUM(agreed_rate) as total_agreed_value,
                    COUNT(DISTINCT job_number) as unique_jobs
                FROM email_audit_log
                WHERE {where_clause}
            """, params)
            
            summary = dict(cursor.fetchone())
            
            return jsonify({
                'success': True,
                'emails': emails,
                'summary': summary
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/comprehensive')
def api_comprehensive_report():
    """Generate comprehensive business report."""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        report = ReportService.generate_comprehensive_report(year, month)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/earnings-jobs-correlation')
def api_earnings_jobs_correlation():
    """Analyze correlation between earnings and job counts."""
    try:
        correlation = ReportService.analyze_earnings_vs_jobs_correlation()
        return jsonify(correlation)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/client-profitability')
def api_client_profitability():
    """Get detailed client profitability analysis."""
    try:
        profitability = ReportService.generate_client_profitability_report()
        return jsonify(profitability)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/seasonal-patterns')
def api_seasonal_patterns():
    """Analyze seasonal patterns in earnings and activity."""
    try:
        patterns = ReportService.analyze_seasonal_patterns()
        return jsonify(patterns)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/export-custom')
def api_export_custom():
    """Export custom filtered report."""
    try:
        filters = {
            'tax_year': request.args.get('tax_year'),
            'client': request.args.get('client'),
            'week_from': request.args.get('week_from', type=int),
            'week_to': request.args.get('week_to', type=int)
        }
        format_type = request.args.get('format', 'csv')
        
        export_data = ReportService.export_custom_report(filters, format_type)
        
        if format_type.lower() == 'csv':
            from flask import make_response
            response = make_response(export_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=custom_report.csv'
            return response
        else:
            return jsonify({'data': export_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== MILEAGE REPORTS =====

@reports_bp.route('/data/reports/mileage-summary')
def api_mileage_summary():
    """Get mileage summary statistics."""
    try:
        year = request.args.get('year', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Base query
            where_clause = "WHERE mileage IS NOT NULL"
            params = []
            
            if year:
                where_clause += " AND substr(date, 7, 4) = ?"
                params.append(year)
            
            # Get summary statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_days,
                    COALESCE(SUM(mileage), 0) as total_miles,
                    COALESCE(SUM(fuel_cost), 0) as total_fuel_cost,
                    COALESCE(AVG(mileage), 0) as avg_miles_per_day
                FROM runsheet_daily_data 
                {where_clause}
            """, params)
            
            summary = cursor.fetchone()
            
            # Calculate cost per mile
            cost_per_mile = 0
            if summary['total_miles'] > 0 and summary['total_fuel_cost'] > 0:
                cost_per_mile = summary['total_fuel_cost'] / summary['total_miles']
            
            # Get monthly breakdown (date format is DD/MM/YYYY)
            cursor.execute(f"""
                SELECT 
                    substr(date, 4, 7) as month,
                    SUM(mileage) as total_miles,
                    SUM(fuel_cost) as total_fuel_cost,
                    substr(date, 7, 4) as year,
                    substr(date, 4, 2) as month_num
                FROM runsheet_daily_data 
                {where_clause}
                GROUP BY substr(date, 4, 7)
                ORDER BY substr(date, 7, 4), substr(date, 4, 2)
            """, params)
            
            monthly_data = [dict(row) for row in cursor.fetchall()]
            
            # Get fuel cost breakdown (ranges)
            cursor.execute(f"""
                SELECT 
                    CASE 
                        WHEN fuel_cost = 0 THEN '£0'
                        WHEN fuel_cost <= 20 THEN '£0-20'
                        WHEN fuel_cost <= 40 THEN '£20-40'
                        WHEN fuel_cost <= 60 THEN '£40-60'
                        ELSE '£60+'
                    END as range,
                    COUNT(*) as count
                FROM runsheet_daily_data 
                {where_clause} AND fuel_cost IS NOT NULL
                GROUP BY 
                    CASE 
                        WHEN fuel_cost = 0 THEN '£0'
                        WHEN fuel_cost <= 20 THEN '£0-20'
                        WHEN fuel_cost <= 40 THEN '£20-40'
                        WHEN fuel_cost <= 60 THEN '£40-60'
                        ELSE '£60+'
                    END
                ORDER BY count DESC
            """, params)
            
            fuel_breakdown = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'summary': {
                    'total_miles': summary['total_miles'],
                    'total_fuel_cost': summary['total_fuel_cost'],
                    'avg_miles_per_day': summary['avg_miles_per_day'],
                    'cost_per_mile': cost_per_mile,
                    'total_days': summary['total_days']
                },
                'monthly_data': monthly_data,
                'fuel_breakdown': fuel_breakdown
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/data/reports/recent-mileage')
def api_recent_mileage():
    """Get recent mileage records."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT date, mileage, fuel_cost
                FROM runsheet_daily_data 
                WHERE mileage IS NOT NULL
                ORDER BY 
                    substr(date, 7, 4) DESC,  -- Year
                    substr(date, 4, 2) DESC,  -- Month  
                    substr(date, 1, 2) DESC   -- Day
                LIMIT 10
            """)
            
            records = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'records': records
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/data/reports/monthly-mileage', methods=['POST'])
def api_generate_monthly_mileage_report():
    """Generate monthly mileage report."""
    try:
        format_type = request.json.get('format', 'csv') if request.json else 'csv'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    substr(date, 4, 7) as month,
                    COUNT(*) as days_worked,
                    SUM(mileage) as total_miles,
                    AVG(mileage) as avg_miles_per_day,
                    SUM(fuel_cost) as total_fuel_cost,
                    AVG(fuel_cost) as avg_fuel_per_day
                FROM runsheet_daily_data 
                WHERE mileage IS NOT NULL
                GROUP BY substr(date, 4, 7)
                ORDER BY substr(date, 7, 4), substr(date, 4, 2)
            """)
            
            data = [dict(row) for row in cursor.fetchall()]
            
            if format_type.lower() == 'pdf':
                # Generate PDF report
                from ..services.pdf_report_service import MileagePDFReportService
                from flask import send_file
                
                pdf_service = MileagePDFReportService()
                pdf_path = pdf_service.create_monthly_mileage_pdf(data)
                
                return send_file(pdf_path, as_attachment=True, 
                               download_name='monthly_mileage_report.pdf',
                               mimetype='application/pdf')
            else:
                # Generate CSV report
                import csv
                import io
                from flask import make_response
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow(['Month', 'Days Worked', 'Total Miles', 'Avg Miles/Day', 'Total Fuel Cost', 'Avg Fuel/Day', 'Cost per Mile'])
                
                # Write data
                for row in data:
                    cost_per_mile = 0
                    if row['total_miles'] > 0 and row['total_fuel_cost'] > 0:
                        cost_per_mile = row['total_fuel_cost'] / row['total_miles']
                    
                    writer.writerow([
                        row['month'],
                        row['days_worked'],
                        f"{row['total_miles']:.1f}",
                        f"{row['avg_miles_per_day']:.1f}",
                        f"£{row['total_fuel_cost']:.2f}",
                        f"£{row['avg_fuel_per_day']:.2f}",
                        f"£{cost_per_mile:.3f}"
                    ])
                
                # Create response
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = 'attachment; filename=monthly_mileage_report.csv'
                
                return response
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/data/reports/high-mileage-days', methods=['POST'])
def api_generate_high_mileage_report():
    """Generate high mileage days report."""
    try:
        format_type = request.json.get('format', 'csv') if request.json else 'csv'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT date, mileage, fuel_cost,
                       CASE 
                           WHEN fuel_cost > 0 AND mileage > 0 THEN fuel_cost / mileage
                           ELSE 0
                       END as cost_per_mile
                FROM runsheet_daily_data 
                WHERE mileage >= 200
                ORDER BY mileage DESC
            """)
            
            data = [dict(row) for row in cursor.fetchall()]
            
            if format_type.lower() == 'pdf':
                # Generate PDF report
                from ..services.pdf_report_service import MileagePDFReportService
                from flask import send_file
                
                pdf_service = MileagePDFReportService()
                pdf_path = pdf_service.create_high_mileage_pdf(data)
                
                return send_file(pdf_path, as_attachment=True,
                               download_name='high_mileage_days.pdf',
                               mimetype='application/pdf')
            else:
                # Generate CSV report
                import csv
                import io
                from flask import make_response
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow(['Date', 'Miles', 'Fuel Cost', 'Cost per Mile'])
                
                # Write data
                for row in data:
                    writer.writerow([
                        row['date'],
                        f"{row['mileage']:.1f}",
                        f"£{row['fuel_cost']:.2f}",
                        f"£{row['cost_per_mile']:.3f}"
                    ])
                
                # Create response
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = 'attachment; filename=high_mileage_days.csv'
                
                return response
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/extra-jobs')
def api_extra_jobs_report():
    """Get extra jobs report with filtering options."""
    try:
        # Get filter parameters
        year = request.args.get('year', '')
        month = request.args.get('month', '')
        status = request.args.get('status', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = ["status = 'extra'"]
            params = []
            
            if year:
                where_conditions.append("date LIKE ?")
                if month:
                    # Format: DD/MM/YYYY, so for month 11 and year 2025: %/11/2025
                    params.append(f"%/{month.zfill(2)}/{year}")
                else:
                    # Just year: %/2025
                    params.append(f"%/{year}")
            elif month:
                # Month without year: %/MM/%
                where_conditions.append("date LIKE ?")
                params.append(f"%/{month.zfill(2)}/%")
            
            where_clause = " AND ".join(where_conditions)
            
            # Get extra jobs with details including agreed price and discrepancy
            cursor.execute(f"""
                SELECT 
                    job_number,
                    date,
                    customer,
                    activity,
                    job_address,
                    postcode,
                    status,
                    pay_amount,
                    price_agreed,
                    pay_rate,
                    notes,
                    imported_at,
                    CASE 
                        WHEN price_agreed IS NOT NULL AND pay_amount IS NOT NULL 
                        THEN pay_amount - price_agreed
                        ELSE NULL
                    END as discrepancy
                FROM run_sheet_jobs 
                WHERE {where_clause}
                ORDER BY date DESC, job_number DESC
            """, params)
            
            extra_jobs = [dict(row) for row in cursor.fetchall()]
            
            # Get summary statistics including discrepancy info
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(DISTINCT date) as total_days,
                    COUNT(DISTINCT customer) as unique_customers,
                    SUM(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as total_pay,
                    AVG(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as avg_pay,
                    SUM(CASE WHEN price_agreed IS NOT NULL THEN price_agreed ELSE 0 END) as total_agreed,
                    COUNT(CASE WHEN price_agreed IS NOT NULL AND pay_amount IS NOT NULL AND pay_amount != price_agreed THEN 1 END) as jobs_with_discrepancy,
                    SUM(CASE WHEN price_agreed IS NOT NULL AND pay_amount IS NOT NULL THEN pay_amount - price_agreed ELSE 0 END) as total_discrepancy
                FROM run_sheet_jobs 
                WHERE {where_clause}
            """, params)
            
            summary = cursor.fetchone()
            
            # Get customer breakdown
            cursor.execute(f"""
                SELECT 
                    customer,
                    COUNT(*) as job_count,
                    SUM(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as total_pay
                FROM run_sheet_jobs 
                WHERE {where_clause}
                GROUP BY customer
                ORDER BY job_count DESC, total_pay DESC
            """, params)
            
            customer_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # Get activity breakdown
            cursor.execute(f"""
                SELECT 
                    activity,
                    COUNT(*) as job_count,
                    SUM(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as total_pay
                FROM run_sheet_jobs 
                WHERE {where_clause}
                GROUP BY activity
                ORDER BY job_count DESC
            """, params)
            
            activity_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # Get monthly breakdown if not filtering by specific month
            monthly_data = []
            if not month:
                cursor.execute(f"""
                    SELECT 
                        substr(date, 4, 7) as month,
                        COUNT(*) as job_count,
                        SUM(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as total_pay,
                        COUNT(DISTINCT customer) as unique_customers
                    FROM run_sheet_jobs 
                    WHERE {where_clause}
                    GROUP BY substr(date, 4, 7)
                    ORDER BY substr(date, 7, 4) DESC, substr(date, 4, 2) DESC
                """, params)
                
                monthly_data = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'extra_jobs': extra_jobs,
                'summary': dict(summary) if summary else {},
                'customer_breakdown': customer_breakdown,
                'activity_breakdown': activity_breakdown,
                'monthly_breakdown': monthly_data
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/extra-jobs/export')
def api_export_extra_jobs():
    """Export extra jobs report as CSV."""
    try:
        # Get same filter parameters
        year = request.args.get('year', '')
        month = request.args.get('month', '')
        format_type = request.args.get('format', 'csv')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause (same as above)
            where_conditions = ["status = 'extra'"]
            params = []
            
            if year:
                where_conditions.append("date LIKE ?")
                if month:
                    params.append(f"%/{month.zfill(2)}/{year}")
                else:
                    params.append(f"%/{year}")
            elif month:
                where_conditions.append("date LIKE ?")
                params.append(f"%/{month.zfill(2)}/%")
            
            where_clause = " AND ".join(where_conditions)
            
            # Get extra jobs data including agreed price and discrepancy
            cursor.execute(f"""
                SELECT 
                    job_number,
                    date,
                    customer,
                    activity,
                    job_address,
                    postcode,
                    pay_amount,
                    price_agreed,
                    pay_rate,
                    notes,
                    CASE 
                        WHEN price_agreed IS NOT NULL AND pay_amount IS NOT NULL 
                        THEN pay_amount - price_agreed
                        ELSE NULL
                    END as discrepancy
                FROM run_sheet_jobs 
                WHERE {where_clause}
                ORDER BY date DESC, job_number DESC
            """, params)
            
            jobs = [dict(row) for row in cursor.fetchall()]
            
            if format_type.lower() == 'csv':
                import csv
                import io
                from flask import make_response
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow([
                    'Job Number', 'Date', 'Customer', 'Activity', 
                    'Address', 'Postcode', 'Pay Amount', 'Agreed Price', 'Discrepancy', 'Pay Rate', 'Notes'
                ])
                
                # Write data
                for job in jobs:
                    writer.writerow([
                        job['job_number'],
                        job['date'],
                        job['customer'],
                        job['activity'],
                        job['job_address'],
                        job['postcode'],
                        f"£{job['pay_amount']:.2f}" if job['pay_amount'] else '',
                        f"£{job['price_agreed']:.2f}" if job['price_agreed'] else '',
                        f"£{job['discrepancy']:.2f}" if job['discrepancy'] else '',
                        f"£{job['pay_rate']:.2f}" if job['pay_rate'] else '',
                        job['notes'] or ''
                    ])
                
                # Create response
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                
                # Generate filename with filters
                filename = 'extra_jobs_report'
                if year and month:
                    filename += f'_{year}_{month.zfill(2)}'
                elif year:
                    filename += f'_{year}'
                elif month:
                    filename += f'_month_{month.zfill(2)}'
                filename += '.csv'
                
                response.headers['Content-Disposition'] = f'attachment; filename={filename}'
                return response
            else:
                return jsonify({'jobs': jobs})
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/data/reports/fuel-efficiency', methods=['POST'])
def api_generate_fuel_efficiency_report():
    """Generate fuel efficiency report."""
    try:
        import csv
        import io
        from flask import make_response
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    substr(date, 4, 7) as month,
                    COUNT(*) as days,
                    SUM(mileage) as total_miles,
                    SUM(fuel_cost) as total_fuel_cost,
                    AVG(CASE WHEN fuel_cost > 0 AND mileage > 0 THEN fuel_cost / mileage ELSE NULL END) as avg_cost_per_mile,
                    MIN(CASE WHEN fuel_cost > 0 AND mileage > 0 THEN fuel_cost / mileage ELSE NULL END) as best_efficiency,
                    MAX(CASE WHEN fuel_cost > 0 AND mileage > 0 THEN fuel_cost / mileage ELSE NULL END) as worst_efficiency
                FROM runsheet_daily_data 
                WHERE mileage IS NOT NULL AND mileage > 0
                GROUP BY substr(date, 4, 7)
                ORDER BY substr(date, 7, 4), substr(date, 4, 2)
            """)
            
            data = cursor.fetchall()
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Month', 'Days', 'Total Miles', 'Total Fuel Cost', 'Avg Cost/Mile', 'Best Efficiency', 'Worst Efficiency'])
            
            # Write data
            for row in data:
                writer.writerow([
                    row['month'],
                    row['days'],
                    f"{row['total_miles']:.1f}",
                    f"£{row['total_fuel_cost']:.2f}",
                    f"£{row['avg_cost_per_mile']:.3f}" if row['avg_cost_per_mile'] else 'N/A',
                    f"£{row['best_efficiency']:.3f}" if row['best_efficiency'] else 'N/A',
                    f"£{row['worst_efficiency']:.3f}" if row['worst_efficiency'] else 'N/A'
                ])
            
            # Create response
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=fuel_efficiency_report.csv'
            
            return response
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/data/reports/missing-mileage-data', methods=['POST'])
def api_generate_missing_mileage_report():
    """Generate missing mileage data report."""
    try:
        format_type = request.json.get('format', 'csv') if request.json else 'csv'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all run sheet dates (working days)
            cursor.execute("""
                SELECT DISTINCT date 
                FROM run_sheet_jobs 
                WHERE date IS NOT NULL AND date != ''
                ORDER BY substr(date, 7, 4), substr(date, 4, 2), substr(date, 1, 2)
            """)
            
            runsheet_dates = [row['date'] for row in cursor.fetchall()]
            
            # Get all mileage dates
            cursor.execute("""
                SELECT DISTINCT date 
                FROM runsheet_daily_data 
                WHERE mileage IS NOT NULL
            """)
            
            mileage_dates = set(row['date'] for row in cursor.fetchall())
            
            # Find missing dates
            missing_mileage = []
            for date in runsheet_dates:
                if date not in mileage_dates:
                    missing_mileage.append(date)
            
            # Find dates with mileage but no fuel cost
            cursor.execute("""
                SELECT date, mileage
                FROM runsheet_daily_data 
                WHERE mileage IS NOT NULL AND (fuel_cost IS NULL OR fuel_cost = 0)
                ORDER BY substr(date, 7, 4), substr(date, 4, 2), substr(date, 1, 2)
            """)
            
            missing_fuel_cost = [dict(row) for row in cursor.fetchall()]
            
            # Summary statistics
            summary_stats = {
                'total_working_days': len(runsheet_dates),
                'days_with_mileage': len(mileage_dates),
                'missing_mileage': len(missing_mileage),
                'missing_fuel_cost': len(missing_fuel_cost)
            }
            
            if format_type.lower() == 'pdf':
                # Generate PDF report
                from ..services.pdf_report_service import MileagePDFReportService
                from flask import send_file
                
                pdf_service = MileagePDFReportService()
                pdf_path = pdf_service.create_missing_data_pdf(missing_mileage, missing_fuel_cost, summary_stats)
                
                return send_file(pdf_path, as_attachment=True,
                               download_name='missing_mileage_data_report.pdf',
                               mimetype='application/pdf')
            else:
                # Generate CSV report
                import csv
                import io
                from flask import make_response
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write missing mileage section
                writer.writerow(['MISSING MILEAGE DATA'])
                writer.writerow(['Date', 'Issue'])
                
                for date in missing_mileage:
                    writer.writerow([date, 'No mileage recorded'])
                
                writer.writerow([])  # Empty row
                writer.writerow(['MISSING FUEL COST DATA'])
                writer.writerow(['Date', 'Miles', 'Issue'])
                
                for row in missing_fuel_cost:
                    writer.writerow([row['date'], f"{row['mileage']:.1f}", 'No fuel cost recorded'])
                
                # Summary
                writer.writerow([])
                writer.writerow(['SUMMARY'])
                writer.writerow(['Total working days', summary_stats['total_working_days']])
                writer.writerow(['Days with mileage data', summary_stats['days_with_mileage']])
                writer.writerow(['Missing mileage data', summary_stats['missing_mileage']])
                writer.writerow(['Missing fuel cost data', summary_stats['missing_fuel_cost']])
                writer.writerow(['Data completeness', f"{(summary_stats['days_with_mileage'] / summary_stats['total_working_days'] * 100):.1f}%" if summary_stats['total_working_days'] else '0%'])
                
                # Create response
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = 'attachment; filename=missing_mileage_data_report.csv'
                
                return response
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/weekly-summary/export-pdf', methods=['POST'])
def api_weekly_summary_export_pdf():
    """Export weekly summary as PDF."""
    try:
        from datetime import datetime, timedelta
        from flask import send_file
        from ..services.weekly_summary_pdf_service import WeeklySummaryPDFService
        from datetime import datetime, timedelta
        
        # Get the week_start parameter
        week_start_param = request.json.get('week_start') if request.json else None
        
        # Get week data (duplicate logic from api_weekly_summary to avoid HTTP call)
        if not week_start_param:
            # Default to the most recent payslip's week
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT period_end
                    FROM payslips
                    ORDER BY period_end DESC
                    LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result and result['period_end']:
                    try:
                        saturday = datetime.strptime(result['period_end'], '%d/%m/%Y')
                        sunday = saturday - timedelta(days=6)
                        week_start_param = sunday.strftime('%Y-%m-%d')
                    except:
                        return jsonify({'error': 'No valid payslip data found'}), 404
                else:
                    return jsonify({'error': 'No payslip data found'}), 404
        
        # Convert to DD/MM/YYYY
        try:
            dt = datetime.strptime(week_start_param, '%Y-%m-%d')
            week_start = dt.strftime('%d/%m/%Y')
        except:
            week_start = week_start_param
        
        # Calculate week end
        start_dt = datetime.strptime(week_start, '%d/%m/%Y')
        end_dt = start_dt + timedelta(days=6)
        week_end = end_dt.strftime('%d/%m/%Y')
        
        # Check if payslip exists for this week
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT week_number, tax_year
                FROM payslips
                WHERE period_end = ?
                LIMIT 1
            """, (week_end,))
            
            payslip_info = cursor.fetchone()
            
            if not payslip_info:
                return jsonify({
                    'error': 'No payslip found for this week',
                    'message': f'Week ending {week_end} does not have a payslip. PDF can only be generated for weeks with payslip records.'
                }), 404
        
        # If we get here, we have a valid week with a payslip
        # Make internal request to get full data (disable SSL verification for localhost)
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        base_url = request.url_root.rstrip('/')
        
        try:
            response = requests.get(
                f"{base_url}/api/weekly-summary?week_start={week_start_param}",
                verify=False,  # Disable SSL verification for localhost
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as req_err:
            return jsonify({
                'error': 'Failed to fetch weekly data',
                'message': str(req_err)
            }), 500
        
        # Generate PDF
        pdf_service = WeeklySummaryPDFService()
        pdf_path = pdf_service.create_weekly_summary_pdf(data)
        
        return send_file(pdf_path, 
                        as_attachment=True,
                        download_name=f"weekly_summary_week{data.get('week_number', 'XX')}.pdf",
                        mimetype='application/pdf')
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"PDF generation error: {error_details}")
        return jsonify({
            'error': 'PDF generation failed',
            'message': str(e),
            'details': error_details if current_app.debug else None
        }), 500


@reports_bp.route('/weekly-summary')
def api_weekly_summary():
    """Get weekly summary report (Sunday to Saturday)."""
    try:
        from datetime import datetime, timedelta
        from ..utils.company_calendar import company_calendar
        
        # Get week parameter (format: YYYY-MM-DD for the Sunday of the week)
        week_start = request.args.get('week_start')
        
        if not week_start:
            # Default to the most recent payslip's week using company calendar
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT period_end, week_number, tax_year
                    FROM payslips 
                    WHERE period_end IS NOT NULL 
                    ORDER BY tax_year DESC, week_number DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result and result['period_end']:
                    # Use company calendar to get proper week dates
                    week_number = result['week_number']
                    tax_year = result['tax_year']
                    sunday, saturday = company_calendar.get_week_dates(week_number, tax_year)
                    week_start = company_calendar.format_date_string(sunday)
                else:
                    # Fallback to current week
                    current_week, current_year = company_calendar.get_current_week()
                    sunday, saturday = company_calendar.get_week_dates(current_week, current_year)
                    week_start = company_calendar.format_date_string(sunday)
        else:
            # Convert from YYYY-MM-DD to DD/MM/YYYY
            try:
                dt = datetime.strptime(week_start, '%Y-%m-%d')
                week_start = dt.strftime('%d/%m/%Y')
            except:
                return jsonify({'error': 'Invalid week_start format'}), 400
        
        # Calculate week end using company calendar (ensures Sunday-Saturday)
        try:
            start_dt = company_calendar.parse_date_string(week_start)
            # Validate it's a Sunday
            if start_dt.weekday() != 6:  # Sunday = 6
                return jsonify({'error': 'Week start must be a Sunday'}), 400
            
            end_dt = start_dt + timedelta(days=6)
            week_end = company_calendar.format_date_string(end_dt)
        except:
            return jsonify({'error': 'Invalid week_start format'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all dates in the week range
            dates_in_week = []
            current = start_dt
            while current <= end_dt:
                dates_in_week.append(current.strftime('%d/%m/%Y'))
                current += timedelta(days=1)
            
            placeholders = ','.join('?' * len(dates_in_week))
            
            # Job statistics by status
            cursor.execute(f"""
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as total_pay
                FROM run_sheet_jobs
                WHERE date IN ({placeholders})
                GROUP BY status
            """, dates_in_week)
            
            status_breakdown = {}
            total_jobs = 0
            total_earnings = 0
            dnco_count = 0
            
            for row in cursor.fetchall():
                status = row['status'] or 'unknown'
                count = row['count']
                pay = row['total_pay'] or 0
                
                # Normalize DNCO to uppercase
                if status.upper() == 'DNCO':
                    status = 'DNCO'
                    pay = 0  # DNCO jobs should always show £0 earnings
                    dnco_count += count
                
                # Aggregate counts if status already exists (handles case variations)
                if status in status_breakdown:
                    status_breakdown[status]['count'] += count
                    status_breakdown[status]['earnings'] += round(pay, 2)
                else:
                    status_breakdown[status] = {
                        'count': count,
                        'earnings': round(pay, 2)
                    }
                
                total_jobs += count
                if status not in ['DNCO', 'missed']:
                    total_earnings += pay
            
            # Get deductions from payslip for this week
            cursor.execute("""
                SELECT 
                    ji.client,
                    SUM(ji.amount) as total_amount
                FROM job_items ji
                JOIN payslips p ON ji.payslip_id = p.id
                WHERE p.period_end = ?
                AND ji.client IN ('Deduction', 'Company Margin')
                GROUP BY ji.client
            """, (week_end,))
            
            deduction_amount = 0
            company_margin_amount = 0
            
            for row in cursor.fetchall():
                if row['client'] == 'Deduction':
                    deduction_amount = abs(row['total_amount'] or 0)
                    status_breakdown['PDA Licence'] = {
                        'count': 1,
                        'earnings': -deduction_amount
                    }
                elif row['client'] == 'Company Margin':
                    company_margin_amount = abs(row['total_amount'] or 0)
                    status_breakdown['SASER Auto Billing'] = {
                        'count': 1,
                        'earnings': -company_margin_amount
                    }
            
            # Subtract deductions from total earnings
            total_deductions = deduction_amount + company_margin_amount
            total_earnings = total_earnings - total_deductions
            
            # Reorder status_breakdown to show in specific order
            # Order: Completed, Extra, DNCO, PDA Licence, SASER Auto Billing, Missed, Pending
            from collections import OrderedDict
            ordered_status_breakdown = OrderedDict()
            
            # Add in specific order (DNCO is now always uppercase)
            if 'completed' in status_breakdown:
                ordered_status_breakdown['completed'] = status_breakdown['completed']
            if 'extra' in status_breakdown:
                ordered_status_breakdown['extra'] = status_breakdown['extra']
            if 'DNCO' in status_breakdown:
                ordered_status_breakdown['DNCO'] = status_breakdown['DNCO']
            if 'PDA Licence' in status_breakdown:
                ordered_status_breakdown['PDA Licence'] = status_breakdown['PDA Licence']
            if 'SASER Auto Billing' in status_breakdown:
                ordered_status_breakdown['SASER Auto Billing'] = status_breakdown['SASER Auto Billing']
            if 'missed' in status_breakdown:
                ordered_status_breakdown['missed'] = status_breakdown['missed']
            if 'pending' in status_breakdown:
                ordered_status_breakdown['pending'] = status_breakdown['pending']
            
            status_breakdown = dict(ordered_status_breakdown)
            
            # Estimate lost earnings from DNCO jobs using customer + activity specific historical averages
            estimated_dnco_loss = 0
            if dnco_count > 0:
                # Get all DNCO jobs for this week with customer and activity
                cursor.execute(f"""
                    SELECT customer, activity, pay_amount
                    FROM run_sheet_jobs
                    WHERE date IN ({placeholders})
                    AND (UPPER(status) = 'DNCO')
                """, dates_in_week)
                dnco_jobs = cursor.fetchall()
                
                # Calculate estimated loss for each DNCO job based on customer + activity history
                jobs_with_history = 0
                jobs_with_activity_history = 0
                jobs_with_default = 0
                
                for dnco_job in dnco_jobs:
                    customer = dnco_job['customer']
                    activity = dnco_job['activity']
                    pay_amount = dnco_job['pay_amount']
                    
                    if pay_amount and pay_amount > 0:
                        # Use actual pay_amount if available (shouldn't happen for DNCO)
                        estimated_dnco_loss += pay_amount
                    elif customer and activity:
                        # First try: Look up average pay for this customer + activity combination
                        cursor.execute("""
                            SELECT AVG(pay_amount) as avg_pay
                            FROM run_sheet_jobs
                            WHERE customer = ? AND activity = ?
                            AND pay_amount IS NOT NULL 
                            AND pay_amount > 0
                            AND status = 'completed'
                        """, (customer, activity))
                        avg_result = cursor.fetchone()
                        
                        if avg_result and avg_result['avg_pay']:
                            estimated_dnco_loss += avg_result['avg_pay']
                            jobs_with_activity_history += 1
                        else:
                            # Second try: Look up average pay for just this customer (any activity)
                            cursor.execute("""
                                SELECT AVG(pay_amount) as avg_pay
                                FROM run_sheet_jobs
                                WHERE customer = ? 
                                AND pay_amount IS NOT NULL 
                                AND pay_amount > 0
                                AND status = 'completed'
                            """, (customer,))
                            avg_result = cursor.fetchone()
                            
                            if avg_result and avg_result['avg_pay']:
                                estimated_dnco_loss += avg_result['avg_pay']
                                jobs_with_history += 1
                            else:
                                # If no historical data, use £15 default
                                estimated_dnco_loss += 15.0
                                jobs_with_default += 1
                    elif customer:
                        # No activity, just use customer average
                        cursor.execute("""
                            SELECT AVG(pay_amount) as avg_pay
                            FROM run_sheet_jobs
                            WHERE customer = ? 
                            AND pay_amount IS NOT NULL 
                            AND pay_amount > 0
                            AND status = 'completed'
                        """, (customer,))
                        avg_result = cursor.fetchone()
                        
                        if avg_result and avg_result['avg_pay']:
                            estimated_dnco_loss += avg_result['avg_pay']
                            jobs_with_history += 1
                        else:
                            estimated_dnco_loss += 15.0
                            jobs_with_default += 1
                    else:
                        # No customer name, use default
                        estimated_dnco_loss += 15.0
                        jobs_with_default += 1
                
                estimated_dnco_loss = round(estimated_dnco_loss, 2)
                
                # Log for debugging
                import logging
                logger = logging.getLogger('api')
                logger.info(f"DNCO Loss Calculation: {dnco_count} jobs, {jobs_with_activity_history} with customer+activity history, {jobs_with_history} with customer history only, {jobs_with_default} with default, Total: £{estimated_dnco_loss}")
                
                # Add estimated loss to DNCO status breakdown
                for status_key in ['DNCO', 'dnco']:
                    if status_key in status_breakdown:
                        status_breakdown[status_key]['estimated_loss'] = estimated_dnco_loss
            
            # Daily breakdown - maintain Sunday-Saturday order
            cursor.execute(f"""
                SELECT 
                    date,
                    COUNT(*) as jobs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'extra' THEN 1 ELSE 0 END) as extra,
                    SUM(CASE WHEN status = 'DNCO' OR status = 'dnco' THEN 1 ELSE 0 END) as dnco,
                    SUM(CASE WHEN status = 'missed' THEN 1 ELSE 0 END) as missed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as earnings
                FROM run_sheet_jobs
                WHERE date IN ({placeholders})
                GROUP BY date
            """, dates_in_week)
            
            # Create a dict for quick lookup
            daily_data = {row['date']: row for row in cursor.fetchall()}
            
            # Build daily breakdown in correct order (Sunday to Saturday)
            # Only include days where you actually worked (had jobs)
            daily_breakdown = []
            for date_str in dates_in_week:
                if date_str in daily_data:
                    row = daily_data[date_str]
                    # Only add days with jobs > 0
                    if row['jobs'] > 0:
                        daily_breakdown.append({
                            'date': row['date'],
                            'day_name': datetime.strptime(row['date'], '%d/%m/%Y').strftime('%A'),
                            'jobs': row['jobs'],
                            'completed': row['completed'],
                            'extra': row['extra'],
                            'dnco': row['dnco'],
                            'missed': row['missed'],
                            'pending': row['pending'],
                            'earnings': round(row['earnings'] or 0, 2)
                        })
                # Skip days with no jobs (absent days)
            
            # Mileage data
            cursor.execute(f"""
                SELECT 
                    date,
                    mileage,
                    fuel_cost
                FROM runsheet_daily_data
                WHERE date IN ({placeholders})
                ORDER BY date
            """, dates_in_week)
            
            mileage_data = []
            mileage_dict = {}
            total_mileage = 0
            total_fuel_cost = 0
            days_with_mileage = 0
            
            for row in cursor.fetchall():
                date = row['date']
                mileage = row['mileage'] or 0
                fuel_cost = row['fuel_cost'] or 0
                
                # Only include mileage data for days where you actually worked
                if date in daily_data and daily_data[date]['jobs'] > 0:
                    if mileage > 0:
                        days_with_mileage += 1
                        total_mileage += mileage
                        total_fuel_cost += fuel_cost
                    
                    mileage_dict[date] = {
                        'date': date,
                        'mileage': mileage,
                        'fuel_cost': round(fuel_cost, 2)
                    }
                    
                    mileage_data.append({
                        'date': date,
                        'mileage': mileage,
                        'fuel_cost': round(fuel_cost, 2)
                    })
            
            # Check for days with jobs but missing mileage
            # Exclude days with attendance entries (absent days)
            cursor.execute(f"""
                SELECT date FROM attendance 
                WHERE date IN ({placeholders})
            """, dates_in_week)
            attendance_dates = set(row['date'] for row in cursor.fetchall())
            
            missing_mileage_dates = []
            for day in daily_breakdown:
                # Skip if day has attendance entry (absent)
                if day['date'] in attendance_dates:
                    continue
                    
                if day['jobs'] > 0:  # Day has jobs
                    mileage_info = mileage_dict.get(day['date'])
                    # Only flag as missing if no record exists (not if mileage is 0 - could be working from home)
                    if not mileage_info:
                        missing_mileage_dates.append(day['date'])
            
            # Top customers this week
            cursor.execute(f"""
                SELECT 
                    customer,
                    COUNT(*) as jobs,
                    SUM(CASE WHEN pay_amount IS NOT NULL THEN pay_amount ELSE 0 END) as earnings
                FROM run_sheet_jobs
                WHERE date IN ({placeholders})
                AND customer IS NOT NULL
                GROUP BY customer
                ORDER BY jobs DESC
                LIMIT 10
            """, dates_in_week)
            
            top_customers = []
            for row in cursor.fetchall():
                top_customers.append({
                    'customer': row['customer'],
                    'jobs': row['jobs'],
                    'earnings': round(row['earnings'] or 0, 2)
                })
            
            # Job types breakdown
            cursor.execute(f"""
                SELECT 
                    activity,
                    COUNT(*) as count
                FROM run_sheet_jobs
                WHERE date IN ({placeholders})
                AND activity IS NOT NULL
                GROUP BY activity
                ORDER BY count DESC
                LIMIT 10
            """, dates_in_week)
            
            job_types = []
            for row in cursor.fetchall():
                job_types.append({
                    'type': row['activity'],
                    'count': row['count']
                })
            
            # Calculate averages and metrics
            working_days = len([d for d in daily_breakdown if d['jobs'] > 0])
            avg_jobs_per_day = round(total_jobs / working_days, 1) if working_days > 0 else 0
            avg_earnings_per_day = round(total_earnings / working_days, 2) if working_days > 0 else 0
            avg_earnings_per_job = round(total_earnings / total_jobs, 2) if total_jobs > 0 else 0
            avg_mileage_per_day = round(total_mileage / days_with_mileage, 1) if days_with_mileage > 0 else 0
            
            # Fuel efficiency
            cost_per_mile = round(total_fuel_cost / total_mileage, 3) if total_mileage > 0 else 0
            earnings_per_mile = round(total_earnings / total_mileage, 2) if total_mileage > 0 else 0
            
            # Completion rate (completed + extra + DNCO are successful, only missed counts as not completed)
            completed_jobs = status_breakdown.get('completed', {}).get('count', 0) + status_breakdown.get('extra', {}).get('count', 0)
            dnco_jobs = status_breakdown.get('DNCO', {}).get('count', 0) + status_breakdown.get('dnco', {}).get('count', 0)
            missed_jobs = status_breakdown.get('missed', {}).get('count', 0)
            
            # Exclude pending from calculation (not yet processed)
            pending_jobs = status_breakdown.get('pending', {}).get('count', 0)
            processed_jobs = total_jobs - pending_jobs
            
            # Successful = completed + extra + DNCO (DNCO is not your fault - parts didn't arrive)
            successful_jobs = completed_jobs + dnco_jobs
            completion_rate = round((successful_jobs / processed_jobs * 100), 1) if processed_jobs > 0 else 0
            
            # Get discrepancies for this week (jobs in payslips but not in runsheets)
            cursor.execute(f"""
                SELECT COUNT(DISTINCT j.job_number) as discrepancy_count
                FROM job_items j
                LEFT JOIN run_sheet_jobs r ON j.job_number = r.job_number
                WHERE j.date IN ({placeholders})
                AND r.job_number IS NULL
            """, dates_in_week)
            
            discrepancies = cursor.fetchone()['discrepancy_count'] or 0
            
            # Get week number and payslip net payment using period_end (Saturday of the week)
            cursor.execute("""
                SELECT week_number, tax_year, net_payment
                FROM payslips
                WHERE period_end = ?
                LIMIT 1
            """, (week_end,))
            
            payslip_info = cursor.fetchone()
            
            # Always use payslip week numbers (not ISO weeks)
            if payslip_info:
                week_number = payslip_info['week_number']
                tax_year = payslip_info['tax_year']
            else:
                # No payslip for this week - check if we have runsheet jobs
                if total_jobs > 0:
                    # We have runsheet data but no payslip - use company calendar to calculate week
                    try:
                        saturday_date = company_calendar.parse_date_string(week_end)
                        week_number = company_calendar.get_week_number_from_date(saturday_date, 2025)
                        tax_year = 2025
                    except:
                        week_number = None
                        tax_year = None
                else:
                    # No runsheet jobs either - redirect to latest available week
                    cursor.execute("""
                        SELECT week_number, tax_year, period_end
                        FROM payslips 
                        WHERE period_end IS NOT NULL 
                        ORDER BY tax_year DESC, week_number DESC 
                        LIMIT 1
                    """)
                    latest_payslip = cursor.fetchone()
                    
                    if latest_payslip:
                        # Redirect to the latest available week
                        try:
                            latest_saturday = datetime.strptime(latest_payslip['period_end'], '%d/%m/%Y')
                            latest_sunday = latest_saturday - timedelta(days=6)
                            latest_week_start = latest_sunday.strftime('%d/%m/%Y')
                            
                            # Return a redirect response with the latest week
                            return jsonify({
                                'redirect': True,
                                'latest_week_start': latest_week_start,
                                'message': f'Week ending {week_end} not available. Showing latest week: {latest_payslip["week_number"]}'
                            })
                        except:
                            pass
                    
                    # Fallback error message
                    return jsonify({
                        'error': 'No data found for this week',
                        'message': f'Week ending {week_end} has no runsheet or payslip data.',
                        'week_start': week_start,
                        'week_end': week_end,
                        'week_label': f"{start_dt.strftime('%d %b')} - {end_dt.strftime('%d %b %Y')}"
                    }), 404
            
            # Check if weekly earnings match payslip net payment
            payslip_net_payment = payslip_info['net_payment'] if payslip_info else None
            earnings_discrepancy = 0
            if payslip_net_payment is not None:
                earnings_discrepancy = round(total_earnings - payslip_net_payment, 2)
            
            # Generate proper week label using company calendar
            if week_number:
                week_label = company_calendar.get_week_label(week_number, tax_year or 2025)
            else:
                week_label = f"{start_dt.strftime('%d %b')} - {end_dt.strftime('%d %b %Y')}"
            
            return jsonify({
                'week_start': week_start,
                'week_end': week_end,
                'week_label': week_label,
                'week_number': week_number,
                'tax_year': tax_year,
                'summary': {
                    'total_jobs': total_jobs,
                    'total_earnings': round(total_earnings, 2),
                    'total_mileage': total_mileage,
                    'total_fuel_cost': round(total_fuel_cost, 2),
                    'working_days': working_days,
                    'completion_rate': completion_rate,
                    'discrepancies': discrepancies,
                    'payslip_net_payment': payslip_net_payment,
                    'earnings_discrepancy': earnings_discrepancy,
                    'missing_mileage_dates': missing_mileage_dates
                },
                'status_breakdown': status_breakdown,
                'daily_breakdown': daily_breakdown,
                'mileage_data': mileage_data,
                'top_customers': top_customers,
                'job_types': job_types,
                'metrics': {
                    'avg_jobs_per_day': avg_jobs_per_day,
                    'avg_earnings_per_day': avg_earnings_per_day,
                    'avg_earnings_per_job': avg_earnings_per_job,
                    'avg_mileage_per_day': avg_mileage_per_day,
                    'cost_per_mile': cost_per_mile,
                    'earnings_per_mile': earnings_per_mile
                }
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/customers')
def api_customers():
    """Get list of customers for parsing quality report."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT customer, COUNT(*) as job_count
                FROM run_sheet_jobs 
                WHERE customer IS NOT NULL AND customer != ''
                GROUP BY customer
                ORDER BY customer
            """)
            
            customers = []
            for row in cursor.fetchall():
                customers.append({
                    'name': row[0],
                    'job_count': row[1]
                })
            
            return jsonify(customers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/customer_parsing')
def api_customer_parsing():
    """Get customer parsing quality report."""
    try:
        customer = request.args.get('customer')
        if not customer:
            return jsonify({'error': 'Customer parameter required'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    job_number,
                    date,
                    activity,
                    job_address,
                    postcode,
                    status,
                    pay_amount,
                    CASE 
                        WHEN activity IS NULL THEN 'Missing Activity'
                        WHEN job_address IS NULL THEN 'Missing Address'
                        WHEN postcode IS NULL THEN 'Missing Postcode'
                        ELSE 'Complete'
                    END as parsing_status
                FROM run_sheet_jobs 
                WHERE customer = ?
                ORDER BY date DESC, job_number DESC
            """, (customer,))
            
            jobs = []
            total_jobs = 0
            complete_jobs = 0
            missing_activity = 0
            missing_address = 0
            missing_postcode = 0
            
            for row in cursor.fetchall():
                job_number, date, activity, address, postcode, status, pay_amount, parsing_status = row
                
                total_jobs += 1
                if parsing_status == 'Complete':
                    complete_jobs += 1
                if not activity:
                    missing_activity += 1
                if not address:
                    missing_address += 1
                if not postcode:
                    missing_postcode += 1
                
                jobs.append({
                    'job_number': job_number,
                    'date': date,
                    'activity': activity or 'N/A',
                    'job_address': address or 'N/A',
                    'postcode': postcode or 'N/A',
                    'status': status,
                    'pay_amount': pay_amount,
                    'parsing_status': parsing_status
                })
            
            # Calculate quality metrics
            quality_metrics = {
                'total_jobs': total_jobs,
                'complete_jobs': complete_jobs,
                'completion_rate': round((complete_jobs / total_jobs * 100), 1) if total_jobs > 0 else 0,
                'missing_activity': missing_activity,
                'missing_address': missing_address,
                'missing_postcode': missing_postcode,
                'activity_success_rate': round(((total_jobs - missing_activity) / total_jobs * 100), 1) if total_jobs > 0 else 0,
                'address_success_rate': round(((total_jobs - missing_address) / total_jobs * 100), 1) if total_jobs > 0 else 0,
                'postcode_success_rate': round(((total_jobs - missing_postcode) / total_jobs * 100), 1) if total_jobs > 0 else 0
            }
            
            return jsonify({
                'customer': customer,
                'jobs': jobs,
                'metrics': quality_metrics
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/earnings-analytics')
def api_earnings_analytics():
    """Get comprehensive earnings analytics data."""
    try:
        from datetime import datetime, timedelta
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current year for comparisons
            current_year = datetime.now().year
            
            # 1. EARNINGS TRENDS - Monthly comparison current vs previous year
            cursor.execute("""
                SELECT 
                    p.tax_year,
                    CAST((p.week_number - 1) / 4.33 AS INTEGER) + 1 as month_num,
                    SUM(p.net_payment) as total_earnings,
                    COUNT(*) as weeks,
                    AVG(p.net_payment) as avg_weekly
                FROM payslips p
                GROUP BY p.tax_year, month_num
                ORDER BY p.tax_year, month_num
            """)
            monthly_trends = [dict(row) for row in cursor.fetchall()]
            
            # 2. YEAR OVER YEAR COMPARISON
            cursor.execute("""
                SELECT 
                    tax_year,
                    COUNT(*) as weeks_worked,
                    SUM(net_payment) as total_earnings,
                    AVG(net_payment) as avg_weekly,
                    MAX(net_payment) as best_week,
                    MIN(net_payment) as worst_week
                FROM payslips
                GROUP BY tax_year
                ORDER BY tax_year DESC
            """)
            year_comparison = [dict(row) for row in cursor.fetchall()]
            
            # 3. CUSTOMER EARNINGS BREAKDOWN
            cursor.execute("""
                SELECT 
                    ji.client,
                    COUNT(*) as job_count,
                    SUM(ji.amount) as total_earnings,
                    AVG(ji.amount) as avg_per_job,
                    ROUND(SUM(ji.amount) * 100.0 / (SELECT SUM(amount) FROM job_items WHERE client NOT IN ('Deduction', 'Company Margin')), 2) as percentage
                FROM job_items ji
                WHERE ji.client NOT IN ('Deduction', 'Company Margin')
                GROUP BY ji.client
                ORDER BY total_earnings DESC
                LIMIT 15
            """)
            customer_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # 4. ACTIVITY TYPE BREAKDOWN
            cursor.execute("""
                SELECT 
                    activity,
                    COUNT(*) as job_count,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings,
                    AVG(COALESCE(pay_amount, 0)) as avg_per_job
                FROM run_sheet_jobs
                WHERE status NOT IN ('DNCO', 'missed') AND pay_amount IS NOT NULL
                GROUP BY activity
                ORDER BY total_earnings DESC
                LIMIT 10
            """)
            activity_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # 5. PERFORMANCE METRICS OVER TIME
            cursor.execute("""
                SELECT 
                    p.tax_year,
                    p.week_number,
                    p.net_payment,
                    COUNT(ji.id) as job_count,
                    ROUND(p.net_payment / NULLIF(COUNT(ji.id), 0), 2) as earnings_per_job
                FROM payslips p
                LEFT JOIN job_items ji ON p.id = ji.payslip_id AND ji.client NOT IN ('Deduction', 'Company Margin')
                GROUP BY p.id, p.tax_year, p.week_number, p.net_payment
                ORDER BY p.tax_year DESC, p.week_number DESC
                LIMIT 26
            """)
            performance_metrics = [dict(row) for row in cursor.fetchall()]
            
            # 6. FORECASTING - Current year projection
            cursor.execute("""
                SELECT 
                    COUNT(*) as weeks_worked,
                    SUM(net_payment) as total_earned,
                    AVG(net_payment) as avg_weekly
                FROM payslips
                WHERE tax_year = (SELECT MAX(tax_year) FROM payslips)
            """)
            current_year_data = cursor.fetchone()
            
            weeks_worked = current_year_data['weeks_worked'] or 0
            total_earned = current_year_data['total_earned'] or 0
            avg_weekly = current_year_data['avg_weekly'] or 0
            weeks_remaining = max(0, 52 - weeks_worked)
            projected_year_end = total_earned + (avg_weekly * weeks_remaining)
            
            forecast = {
                'weeks_worked': weeks_worked,
                'weeks_remaining': weeks_remaining,
                'total_earned': round(total_earned, 2),
                'avg_weekly': round(avg_weekly, 2),
                'projected_year_end': round(projected_year_end, 2),
                'on_track_for': round(projected_year_end, 2)
            }
            
            # 7. REGULAR VS EXTRA JOBS
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings
                FROM run_sheet_jobs
                WHERE status IN ('completed', 'extra') AND pay_amount IS NOT NULL
                GROUP BY status
            """)
            job_status_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # 8. WEEKLY EARNINGS DISTRIBUTION (for heatmap)
            cursor.execute("""
                SELECT 
                    date,
                    SUM(COALESCE(pay_amount, 0)) as daily_earnings,
                    COUNT(*) as job_count
                FROM run_sheet_jobs
                WHERE status NOT IN ('DNCO', 'missed') AND pay_amount IS NOT NULL
                AND date IS NOT NULL
                GROUP BY date
                ORDER BY date DESC
                LIMIT 90
            """)
            daily_earnings = [dict(row) for row in cursor.fetchall()]
            
            # 9. BEST/WORST WEEKS CONTEXT
            cursor.execute("""
                SELECT 
                    p.tax_year,
                    p.week_number,
                    p.net_payment,
                    p.pay_date,
                    COUNT(ji.id) as job_count
                FROM payslips p
                LEFT JOIN job_items ji ON p.id = ji.payslip_id
                GROUP BY p.id
                ORDER BY p.net_payment DESC
                LIMIT 5
            """)
            best_weeks = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT 
                    p.tax_year,
                    p.week_number,
                    p.net_payment,
                    p.pay_date,
                    COUNT(ji.id) as job_count
                FROM payslips p
                LEFT JOIN job_items ji ON p.id = ji.payslip_id
                WHERE p.net_payment > 0
                GROUP BY p.id
                ORDER BY p.net_payment ASC
                LIMIT 5
            """)
            worst_weeks = [dict(row) for row in cursor.fetchall()]
            
            # 10. COMPLETION RATE IMPACT
            cursor.execute("""
                SELECT 
                    ROUND(AVG(CASE WHEN status = 'completed' THEN 1.0 ELSE 0.0 END) * 100, 1) as completion_rate,
                    COUNT(*) as total_jobs,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings
                FROM run_sheet_jobs
                WHERE status IN ('completed', 'extra', 'DNCO', 'missed')
            """)
            completion_stats = dict(cursor.fetchone())
            
            return jsonify({
                'success': True,
                'monthly_trends': monthly_trends,
                'year_comparison': year_comparison,
                'customer_breakdown': customer_breakdown,
                'activity_breakdown': activity_breakdown,
                'performance_metrics': performance_metrics,
                'forecast': forecast,
                'job_status_breakdown': job_status_breakdown,
                'daily_earnings': daily_earnings,
                'best_weeks': best_weeks,
                'worst_weeks': worst_weeks,
                'completion_stats': completion_stats
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
