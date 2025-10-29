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
    """Get all job numbers from payslips and run sheets for discrepancy analysis."""
    try:
        # Get filter parameters
        year = request.args.get('year', '')
        month = request.args.get('month', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause for payslips (filter by date field in job_items)
            payslip_where = "WHERE ji.job_number IS NOT NULL AND ji.job_number != ''"
            payslip_params = []
            
            if year and month:
                # Filter by specific month and year (date format: DD/MM/YY in job_items - 2 digit year!)
                year_2digit = year[-2:]  # Get last 2 digits of year (2025 -> 25)
                payslip_where += " AND ji.date LIKE ?"
                payslip_params.append(f"%/{month}/{year_2digit}")
            elif year:
                # Filter by year only (2 digit year)
                year_2digit = year[-2:]
                payslip_where += " AND ji.date LIKE ?"
                payslip_params.append(f"%/{year_2digit}")
            
            # Get all job numbers from payslips
            cursor.execute(f"""
                SELECT DISTINCT ji.job_number, ji.description, ji.client
                FROM job_items ji
                {payslip_where}
            """, payslip_params)
            payslip_jobs = {}
            for row in cursor.fetchall():
                payslip_jobs[row[0]] = {
                    'description': row[1],
                    'client': row[2]
                }
            
            # Build WHERE clause for run sheets (dates are in DD/MM/YYYY format)
            runsheet_where = "WHERE job_number IS NOT NULL AND job_number != ''"
            runsheet_params = []
            if year or month:
                if year and month:
                    # Match DD/MM/YYYY format (e.g., %/09/2025)
                    runsheet_where += " AND date LIKE ?"
                    runsheet_params.append(f"%/{month}/{year}")
                elif year:
                    # Match any month in the year (e.g., %/2025)
                    runsheet_where += " AND date LIKE ?"
                    runsheet_params.append(f"%/{year}")
            
            # Get all job numbers from run sheets
            cursor.execute(f"""
                SELECT DISTINCT job_number, customer, date
                FROM run_sheet_jobs
                {runsheet_where}
            """, runsheet_params)
            runsheet_jobs = {}
            for row in cursor.fetchall():
                runsheet_jobs[row[0]] = {
                    'customer': row[1],
                    'date': row[2]
                }
            
            return jsonify({
                'payslip_jobs': payslip_jobs,
                'runsheet_jobs': runsheet_jobs
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

@reports_bp.route('/reports/mileage-summary')
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
                where_clause += " AND date LIKE ?"
                params.append(f"%/{year}")
            
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
            
            # Get monthly breakdown
            cursor.execute(f"""
                SELECT 
                    substr(date, 4, 7) as month,
                    SUM(mileage) as total_miles,
                    SUM(fuel_cost) as total_fuel_cost
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


@reports_bp.route('/reports/recent-mileage')
def api_recent_mileage():
    """Get recent mileage records."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT date, mileage, fuel_cost
                FROM runsheet_daily_data 
                WHERE mileage IS NOT NULL
                ORDER BY date DESC
                LIMIT 10
            """)
            
            records = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'records': records
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/reports/monthly-mileage', methods=['POST'])
def api_generate_monthly_mileage_report():
    """Generate monthly mileage report."""
    try:
        # This would generate a downloadable report
        # For now, return success with placeholder
        return jsonify({
            'success': True,
            'message': 'Monthly mileage report generated',
            'download_url': '/api/reports/download/monthly-mileage.csv'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/reports/high-mileage-days', methods=['POST'])
def api_generate_high_mileage_report():
    """Generate high mileage days report."""
    try:
        return jsonify({
            'success': True,
            'message': 'High mileage days report generated',
            'download_url': '/api/reports/download/high-mileage.csv'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/reports/fuel-efficiency', methods=['POST'])
def api_generate_fuel_efficiency_report():
    """Generate fuel efficiency report."""
    try:
        return jsonify({
            'success': True,
            'message': 'Fuel efficiency report generated',
            'download_url': '/api/reports/download/fuel-efficiency.csv'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
