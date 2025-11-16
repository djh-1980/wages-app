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
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        job_id = data.get('job_id')
        status = data.get('status')
        
        if not job_id or not status:
            return jsonify({'success': False, 'error': 'Job ID and status are required'}), 400
        
        success = RunsheetModel.update_job_status(job_id, status)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Job not found or update failed'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
        status = data.get('status', 'extra')
        pay_amount = data.get('pay_amount')
        
        if not date or not job_number or not customer:
            return jsonify({'success': False, 'error': 'Date, job number, and customer are required'}), 400
        
        job_id = RunsheetModel.add_extra_job(
            date=date, job_number=job_number, customer=customer,
            activity=activity, job_address=job_address, status=status,
            pay_amount=pay_amount
        )
        
        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@runsheets_bp.route('/delete-job/<int:job_id>', methods=['DELETE'])
def api_delete_job(job_id):
    """Delete a job from run sheets."""
    try:
        success = RunsheetModel.delete_job(job_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Job deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
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
