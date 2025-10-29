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
        job_address = data.get('job_address', '')
        status = data.get('status', 'extra')
        
        if not date or not job_number or not customer:
            return jsonify({'success': False, 'error': 'Date, job number, and customer are required'}), 400
        
        job_id = RunsheetModel.add_extra_job(
            date=date, job_number=job_number, customer=customer,
            activity=activity, job_address=job_address, status=status
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
