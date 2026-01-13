"""
Runsheet API routes blueprint.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, jsonify, request
from ..models.runsheet import RunsheetModel
from ..services.runsheet_service import RunsheetService
from pathlib import Path
import json

runsheets_bp = Blueprint('runsheets_api', __name__, url_prefix='/api/runsheets')


@runsheets_bp.route('/summary')
def api_runsheets_summary():
    """Get enhanced run sheets summary with business intelligence."""
    try:
        summary = RunsheetService.get_dashboard_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/list')
def api_runsheets_list():
    """Get list of all run sheets."""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get sorting parameters
        sort_column = request.args.get('sort', 'date')
        sort_order = request.args.get('order', 'desc')
        
        # Get filter parameters
        filter_year = request.args.get('year', '')
        filter_month = request.args.get('month', '')
        filter_week = request.args.get('week', '')
        filter_day = request.args.get('day', '')
        
        result = RunsheetModel.get_runsheets_list(
            page=page, per_page=per_page,
            sort_column=sort_column, sort_order=sort_order,
            filter_year=filter_year, filter_month=filter_month,
            filter_week=filter_week, filter_day=filter_day
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/jobs')
def api_runsheets_jobs():
    """Get all jobs for a specific date."""
    try:
        date = request.args.get('date')
        
        if not date:
            return jsonify({'error': 'Date parameter required'}), 400
        
        jobs = RunsheetModel.get_jobs_for_date(date)
        return jsonify({'jobs': jobs, 'date': date})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/update-statuses', methods=['POST'])
def api_update_job_statuses():
    """Update job statuses for multiple jobs and save mileage/fuel data."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        updates = data.get('updates', [])
        date = data.get('date')
        mileage = data.get('mileage')
        fuel_cost = data.get('fuel_cost')
        
        updated_count = RunsheetModel.update_job_statuses(
            updates=updates, date=date, mileage=mileage, fuel_cost=fuel_cost
        )
        
        return jsonify({'success': True, 'updated': updated_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@runsheets_bp.route('/daily-data')
def api_get_daily_data():
    """Get mileage and fuel cost for a specific date."""
    try:
        date = request.args.get('date')
        
        if not date:
            return jsonify({'error': 'Date parameter required'}), 400
        
        daily_data = RunsheetModel.get_daily_data(date)
        return jsonify(daily_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/update-job-status', methods=['POST'])
def api_update_job_status():
    """Update a single job's status immediately."""
    import logging
    from ..utils.validators import validate_status
    
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("Update job status called with no data")
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        job_id = data.get('job_id')
        status = data.get('status')
        
        if not job_id or not status:
            logger.warning(f"Missing required fields: job_id={job_id}, status={status}")
            return jsonify({'success': False, 'error': 'Job ID and status are required'}), 400
        
        # Validate status
        is_valid, error_msg = validate_status(status)
        if not is_valid:
            logger.warning(f"Invalid status '{status}': {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        success = RunsheetModel.update_job_status(job_id, status)
        
        if success:
            logger.info(f"Updated job {job_id} status to {status}")
            return jsonify({'success': True})
        else:
            logger.error(f"Failed to update job {job_id} - not found")
            return jsonify({'success': False, 'error': 'Job not found or update failed'}), 404
    except ValueError as e:
        logger.error(f"Validation error updating job status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception(f"Unexpected error updating job status: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@runsheets_bp.route('/add-job', methods=['POST'])
def api_add_extra_job():
    """Add an extra job to a run sheet."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        date = data.get('date')
        job_number = data.get('job_number')
        customer = data.get('customer')
        activity = data.get('activity', '')
        job_address = data.get('job_address') or data.get('location', '')
        postcode = data.get('postcode', '')
        status = data.get('status', 'extra')
        pay_amount = data.get('pay_amount')
        agreed_price = data.get('agreed_price')
        send_email = data.get('send_email_confirmation', False)
        
        if not date or not job_number or not customer:
            return jsonify({'success': False, 'error': 'Date, job number, and customer are required'}), 400
        
        job_id = RunsheetModel.add_extra_job(
            date=date, job_number=job_number, customer=customer,
            activity=activity, job_address=job_address, postcode=postcode,
            status=status, pay_amount=pay_amount, agreed_price=agreed_price
        )
        
        # Send email confirmation if requested and agreed_price is set
        email_sent = False
        if send_email and agreed_price:
            try:
                from ..utils.email_notifications import email_service
                from ..database import get_db_connection
                
                # Get manager and user email from settings
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'manager_email'")
                    manager_row = cursor.fetchone()
                    cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'user_email'")
                    user_row = cursor.fetchone()
                    
                    manager_email = manager_row['setting_value'] if manager_row else None
                    user_email = user_row['setting_value'] if user_row else None
                
                if manager_email and user_email:
                    job_data = {
                        'job_number': job_number,
                        'customer': customer,
                        'location': job_address,
                        'agreed_rate': float(agreed_price),
                        'date': date
                    }
                    
                    email_sent = email_service.send_extra_job_confirmation(
                        job_data, manager_email, user_email
                    )
            except Exception as email_error:
                print(f"Email sending failed: {email_error}")
                # Don't fail the whole request if email fails
        
        return jsonify({
            'success': True, 
            'job_id': job_id,
            'email_sent': email_sent
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@runsheets_bp.route('/edit-job/<int:job_id>', methods=['PUT'])
def api_edit_job(job_id):
    """Edit an existing job."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Get original job to check if agreed price changed
        from ..database import get_db_connection
        email_sent = False
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT price_agreed, job_number, customer, job_address, postcode, date
                FROM run_sheet_jobs
                WHERE id = ?
            ''', (job_id,))
            original_job = cursor.fetchone()
        
        new_agreed_price = data.get('agreed_price')
        send_email = data.get('send_email_confirmation', False)
        
        # Check if agreed price changed
        price_changed = False
        if original_job and new_agreed_price is not None:
            old_price = original_job['price_agreed']
            if old_price is None or abs(float(old_price) - float(new_agreed_price)) > 0.01:
                price_changed = True
        
        success = RunsheetModel.update_job(
            job_id=job_id,
            job_number=data.get('job_number'),
            customer=data.get('customer'),
            activity=data.get('activity'),
            job_address=data.get('job_address'),
            postcode=data.get('postcode'),
            pay_amount=data.get('pay_amount'),
            agreed_price=new_agreed_price,
            status=data.get('status')
        )
        
        # Only send email if price changed and auto-send is enabled
        if success and send_email and price_changed and new_agreed_price:
            try:
                from ..utils.email_notifications import email_service
                from ..models.settings import SettingsModel
                
                manager_email = SettingsModel.get_setting('manager_email')
                user_email = SettingsModel.get_setting('user_email')
                
                if manager_email and user_email:
                    job_data = {
                        'job_number': data.get('job_number') or original_job['job_number'],
                        'customer': data.get('customer') or original_job['customer'],
                        'location': data.get('job_address') or original_job['job_address'],
                        'agreed_rate': float(new_agreed_price),
                        'date': original_job['date']
                    }
                    
                    email_sent = email_service.send_extra_job_confirmation(
                        job_data, manager_email, user_email
                    )
            except Exception as email_error:
                print(f"Email sending failed: {email_error}")
        
        if success:
            return jsonify({
                'success': True,
                'email_sent': email_sent,
                'price_changed': price_changed
            })
        else:
            return jsonify({'success': False, 'error': 'Job not found or update failed'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@runsheets_bp.route('/delete-job/<int:job_id>', methods=['DELETE'])
def api_delete_job(job_id):
    """Delete a job from run sheets and prevent it from being re-imported."""
    try:
        from ..database import get_db_connection
        
        # First, get the job details before deleting
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT job_number, date FROM run_sheet_jobs WHERE id = ?", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            job_number = job['job_number']
            date = job['date']
            
            # Add to deleted_jobs table to prevent re-import
            cursor.execute("""
                INSERT OR IGNORE INTO deleted_jobs (job_number, date)
                VALUES (?, ?)
            """, (job_number, date))
            
            conn.commit()
        
        # Now delete the job
        success = RunsheetModel.delete_job(job_id)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Job {job_number} deleted and will not be re-imported'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete job'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@runsheets_bp.route('/autocomplete-data')
def api_runsheets_autocomplete_data():
    """Get unique customers and activities for autocomplete."""
    try:
        autocomplete_data = RunsheetModel.get_autocomplete_data()
        return jsonify(autocomplete_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/completion-status')
def api_runsheets_completion_status():
    """Get completion status for all run sheet dates."""
    try:
        status_map = RunsheetModel.get_completion_status()
        return jsonify(status_map)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/debug-status')
def api_debug_completion_status():
    """Debug endpoint to check completion status data."""
    try:
        # This would need to be implemented in the model if needed
        # For now, return the same as completion-status
        status_map = RunsheetModel.get_completion_status()
        return jsonify(status_map)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/completion-analysis')
def api_completion_analysis():
    """Get detailed job completion rate analysis."""
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        analysis = RunsheetService.analyze_job_completion_rates(date_from, date_to)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/customer-performance')
def api_customer_performance():
    """Get customer performance analysis."""
    try:
        analysis = RunsheetService.get_customer_performance_analysis()
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/route-optimization/<date>')
def api_route_optimization(date):
    """Get route optimization suggestions for a specific date."""
    try:
        suggestions = RunsheetService.optimize_route_suggestions(date)
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/daily-progress/<date>')
def api_daily_progress(date):
    """Get comprehensive daily progress tracking."""
    try:
        progress = RunsheetService.track_daily_progress(date)
        return jsonify(progress)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/update-pay-info', methods=['POST'])
def api_update_pay_info():
    """Update runsheet jobs with pay information from payslips."""
    try:
        result = RunsheetModel.update_job_pay_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/jobs-with-pay')
def api_jobs_with_pay():
    """Get runsheet jobs that have pay information."""
    try:
        date = request.args.get('date')
        limit = request.args.get('limit', 50, type=int)
        
        jobs = RunsheetModel.get_jobs_with_pay_info(date=date, limit=limit)
        return jsonify({
            'jobs': jobs,
            'count': len(jobs)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/discrepancy-report')
def api_discrepancy_report():
    """Get discrepancy report showing jobs paid but not in runsheets."""
    try:
        from ..models.runsheet import RunsheetModel
        
        # Get filter parameters
        year = request.args.get('year', '')
        month = request.args.get('month', '')
        limit = request.args.get('limit', 100, type=int)
        
        # Call the model with filters
        report = RunsheetModel.get_discrepancy_report(
            limit=limit,
            year=year if year else None,
            month=month if month else None
        )
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/discrepancy-pdf', methods=['POST'])
def api_discrepancy_pdf():
    """Generate PDF discrepancy report."""
    try:
        from flask import Response
        from datetime import datetime
        from ..models.runsheet import RunsheetModel
        from ..utils.pdf_generator import DiscrepancyPDFGenerator
        
        # Get filter parameters from request
        data = request.get_json() or {}
        year = data.get('year', '')
        month = data.get('month', '')
        
        # Get the discrepancy data
        report_data = RunsheetModel.get_discrepancy_report(
            limit=1000,  # Get comprehensive data for PDF
            year=year if year else None,
            month=month if month else None
        )
        
        # Prepare filters for PDF header
        filters = {}
        if year:
            filters['year'] = year
        if month:
            filters['month'] = month
        
        # Generate the PDF
        pdf_generator = DiscrepancyPDFGenerator()
        pdf_data = pdf_generator.generate_discrepancy_report(report_data, filters)
        
        # Generate filename with filters
        filename = 'discrepancy_report'
        if year:
            filename += f'_{year}'
        if month:
            filename += f'_{month}'
        filename += f'_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        # Return PDF as download
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
            
    except Exception as e:
        import traceback
        print(f"PDF Generation Error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


@runsheets_bp.route('/discrepancy-csv', methods=['POST'])
def api_discrepancy_csv():
    """Generate CSV discrepancy report (alternative to PDF)."""
    try:
        from flask import Response
        from datetime import datetime
        from ..models.runsheet import RunsheetModel
        import csv
        import io
        
        # Get filter parameters from request
        data = request.get_json() or {}
        year = data.get('year', '')
        month = data.get('month', '')
        
        # Get the discrepancy data
        report_data = RunsheetModel.get_discrepancy_report(
            limit=1000,  # Get more data for the CSV
            year=year if year else None,
            month=month if month else None
        )
        
        if report_data['missing_jobs']:
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Job Number', 'Client', 'Location', 'Postcode', 'Job Type',
                'Date', 'Amount', 'Rate', 'Units', 'Week Number', 'Tax Year', 'Pay Date'
            ])
            
            # Write data
            for job in report_data['missing_jobs']:
                writer.writerow([
                    job['job_number'],
                    job['client'] or '',
                    job['location'] or '',
                    job['postcode'] or '',
                    job['job_type'] or '',
                    job['date'] or '',
                    job['amount'] or 0,
                    job['rate'] or 0,
                    job['units'] or 0,
                    job['week_number'] or '',
                    job['tax_year'] or '',
                    job['pay_date'] or ''
                ])
            
            # Create response
            output.seek(0)
            
            # Generate filename with filters
            filename = 'discrepancy_report'
            if year:
                filename += f'_{year}'
            if month:
                filename += f'_{month}'
            filename += f'_{datetime.now().strftime("%Y%m%d")}.csv'
            
            # Return as file download
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
        else:
            return jsonify({'error': 'No missing jobs found for the selected criteria'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheets_bp.route('/analytics')
def api_runsheets_analytics():
    """Get comprehensive runsheet analytics for Overview, Customers, and Activities tabs."""
    try:
        from ..database import get_db_connection
        
        # Get filter parameters
        year = request.args.get('year', '')
        month = request.args.get('month', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause for filtering
            where_conditions = []
            params = []
            
            if year:
                where_conditions.append("substr(date, 7, 4) = ?")
                params.append(year)
            if month:
                where_conditions.append("substr(date, 4, 2) = ?")
                params.append(month.zfill(2))
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 1. STATUS BREAKDOWN (normalize DNCO case variations)
            cursor.execute(f"""
                SELECT 
                    CASE 
                        WHEN UPPER(status) = 'DNCO' THEN 'DNCO'
                        ELSE status
                    END as status,
                    COUNT(*) as count,
                    SUM(COALESCE(pay_amount, 0)) as total_pay
                FROM run_sheet_jobs
                WHERE {where_clause}
                GROUP BY CASE 
                    WHEN UPPER(status) = 'DNCO' THEN 'DNCO'
                    ELSE status
                END
                ORDER BY count DESC
            """, params)
            status_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # Calculate estimated DNCO loss (same logic as weekly reporting)
            estimated_dnco_loss = 0
            dnco_count = 0
            for status in status_breakdown:
                if status['status'] == 'DNCO':
                    dnco_count = status['count']
                    break
            
            if dnco_count > 0:
                # Get all DNCO jobs with customer and activity
                cursor.execute(f"""
                    SELECT customer, activity, pay_amount
                    FROM run_sheet_jobs
                    WHERE {where_clause} AND UPPER(status) = 'DNCO'
                """, params)
                
                dnco_jobs = cursor.fetchall()
                jobs_with_history = 0
                jobs_with_activity_history = 0
                jobs_with_default = 0
                
                for job in dnco_jobs:
                    customer = job['customer']
                    activity = job['activity']
                    pay_amount = job['pay_amount']
                    
                    if pay_amount and pay_amount > 0:
                        estimated_dnco_loss += pay_amount
                    elif customer and activity:
                        # First try: Look up average pay for this customer + activity combination
                        cursor.execute("""
                            SELECT AVG(pay_amount) as avg_pay
                            FROM run_sheet_jobs
                            WHERE customer = ? AND activity = ? AND status = 'completed' AND pay_amount > 0
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
                                WHERE customer = ? AND status = 'completed' AND pay_amount > 0
                            """, (customer,))
                            
                            avg_result = cursor.fetchone()
                            
                            if avg_result and avg_result['avg_pay']:
                                estimated_dnco_loss += avg_result['avg_pay']
                                jobs_with_history += 1
                            else:
                                estimated_dnco_loss += 15.0
                                jobs_with_default += 1
                    elif customer:
                        # No activity, just use customer average
                        cursor.execute("""
                            SELECT AVG(pay_amount) as avg_pay
                            FROM run_sheet_jobs
                            WHERE customer = ? AND status = 'completed' AND pay_amount > 0
                        """, (customer,))
                        
                        avg_result = cursor.fetchone()
                        
                        if avg_result and avg_result['avg_pay']:
                            estimated_dnco_loss += avg_result['avg_pay']
                            jobs_with_history += 1
                        else:
                            estimated_dnco_loss += 15.0
                            jobs_with_default += 1
                    else:
                        estimated_dnco_loss += 15.0
                        jobs_with_default += 1
                
                estimated_dnco_loss = round(estimated_dnco_loss, 2)
                
                # Log for debugging
                import logging
                logger = logging.getLogger('api')
                logger.info(f"DNCO Loss Calculation: {dnco_count} jobs, {jobs_with_activity_history} with customer+activity history, {jobs_with_history} with customer history only, {jobs_with_default} with default, Total: £{estimated_dnco_loss}")
                
                # Add estimated loss to DNCO status breakdown
                for i, status in enumerate(status_breakdown):
                    if status['status'] == 'DNCO':
                        status_breakdown[i]['estimated_loss'] = estimated_dnco_loss
                        logger.info(f"Added estimated_loss to DNCO status: {status_breakdown[i]}")
                        break
            
            # 2. CUSTOMER BREAKDOWN (with earnings and job counts)
            cursor.execute(f"""
                SELECT 
                    customer,
                    COUNT(*) as job_count,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings,
                    AVG(COALESCE(pay_amount, 0)) as avg_pay,
                    COUNT(DISTINCT date) as days_worked,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN status = 'extra' THEN 1 END) as extra_count,
                    COUNT(CASE WHEN status = 'DNCO' THEN 1 END) as dnco_count,
                    COUNT(CASE WHEN status = 'missed' THEN 1 END) as missed_count
                FROM run_sheet_jobs
                WHERE {where_clause} AND customer IS NOT NULL AND customer != ''
                GROUP BY customer
                ORDER BY job_count DESC
            """, params)
            customer_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # 3. ACTIVITY BREAKDOWN (with earnings and counts)
            cursor.execute(f"""
                SELECT 
                    activity,
                    COUNT(*) as job_count,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings,
                    AVG(COALESCE(pay_amount, 0)) as avg_pay,
                    COUNT(DISTINCT customer) as unique_customers,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN status = 'extra' THEN 1 END) as extra_count
                FROM run_sheet_jobs
                WHERE {where_clause} AND activity IS NOT NULL AND activity != ''
                GROUP BY activity
                ORDER BY job_count DESC
            """, params)
            activity_breakdown = [dict(row) for row in cursor.fetchall()]
            
            # 4. DAILY ACTIVITY TREND (last 30 days or filtered period)
            cursor.execute(f"""
                SELECT 
                    date,
                    COUNT(*) as job_count,
                    SUM(COALESCE(pay_amount, 0)) as daily_earnings,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'extra' THEN 1 END) as extra,
                    COUNT(CASE WHEN status = 'DNCO' THEN 1 END) as dnco
                FROM run_sheet_jobs
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date DESC
                LIMIT 30
            """, params)
            daily_trend = [dict(row) for row in cursor.fetchall()]
            
            # 5. CUSTOMER TRENDS OVER TIME (monthly aggregation)
            cursor.execute(f"""
                SELECT 
                    customer,
                    substr(date, 4, 7) as month,
                    COUNT(*) as job_count,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings
                FROM run_sheet_jobs
                WHERE {where_clause} AND customer IS NOT NULL
                GROUP BY customer, month
                ORDER BY month DESC, job_count DESC
            """, params)
            customer_trends = [dict(row) for row in cursor.fetchall()]
            
            # 6. ACTIVITY TRENDS OVER TIME (monthly aggregation)
            cursor.execute(f"""
                SELECT 
                    activity,
                    substr(date, 4, 7) as month,
                    COUNT(*) as job_count,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings
                FROM run_sheet_jobs
                WHERE {where_clause} AND activity IS NOT NULL
                GROUP BY activity, month
                ORDER BY month DESC, job_count DESC
            """, params)
            activity_trends = [dict(row) for row in cursor.fetchall()]
            
            # 7. SUMMARY STATISTICS
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(DISTINCT date) as total_days,
                    COUNT(DISTINCT customer) as unique_customers,
                    COUNT(DISTINCT activity) as unique_activities,
                    SUM(COALESCE(pay_amount, 0)) as total_earnings,
                    AVG(COALESCE(pay_amount, 0)) as avg_pay_per_job,
                    ROUND(AVG(CASE WHEN status = 'completed' THEN 1.0 ELSE 0.0 END) * 100, 1) as completion_rate
                FROM run_sheet_jobs
                WHERE {where_clause}
            """, params)
            summary_stats = dict(cursor.fetchone())
            
            return jsonify({
                'success': True,
                'status_breakdown': status_breakdown,
                'customer_breakdown': customer_breakdown,
                'activity_breakdown': activity_breakdown,
                'daily_trend': daily_trend,
                'customer_trends': customer_trends,
                'activity_trends': activity_trends,
                'summary_stats': summary_stats
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
