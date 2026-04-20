"""
Payslip API routes blueprint.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, jsonify, request
from ..models.payslip import PayslipModel
from ..services.payslip_service import PayslipService

payslips_bp = Blueprint('payslips_api', __name__, url_prefix='/api')


@payslips_bp.route('/summary')
def api_summary():
    """Get enhanced dashboard summary with business intelligence."""
    try:
        summary = PayslipService.get_dashboard_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/weekly_trend')
def api_weekly_trend():
    """Get weekly earnings trend."""
    try:
        limit = request.args.get('limit', 52, type=int)
        tax_year = request.args.get('tax_year')
        
        trend_data = PayslipModel.get_weekly_trend(limit=limit, tax_year=tax_year)
        return jsonify(trend_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/payslips')
def api_payslips():
    """Get all payslips."""
    try:
        tax_year = request.args.get('tax_year')
        payslips = PayslipModel.get_all_payslips(tax_year=tax_year)
        return jsonify(payslips)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/payslip/<int:payslip_id>')
def api_payslip_detail(payslip_id):
    """Get detailed payslip information."""
    try:
        payslip_detail = PayslipModel.get_payslip_detail(payslip_id)
        
        if not payslip_detail:
            return jsonify({'error': 'Payslip not found'}), 404
        
        return jsonify(payslip_detail)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/tax_years')
def api_tax_years():
    """Get list of tax years."""
    try:
        years = PayslipModel.get_tax_years()
        return jsonify(years)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/monthly_breakdown')
def api_monthly_breakdown():
    """Get monthly breakdown."""
    try:
        breakdown = PayslipModel.get_monthly_breakdown()
        return jsonify(breakdown)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/check_missing')
def api_check_missing():
    """Check for missing payslips in each tax year."""
    try:
        missing_data = PayslipModel.check_missing_weeks()
        return jsonify(missing_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/earnings_analysis')
def api_earnings_analysis():
    """Get advanced earnings trend analysis."""
    try:
        weeks = request.args.get('weeks', 12, type=int)
        analysis = PayslipService.analyze_earnings_trend(weeks=weeks)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/tax_year_report/<int:tax_year>')
def api_tax_year_report(tax_year):
    """Get comprehensive tax year report."""
    try:
        report = PayslipService.generate_tax_year_report(tax_year)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/earnings_forecast')
def api_enhanced_earnings_forecast():
    """Get enhanced earnings forecast with multiple prediction methods."""
    try:
        forecast = PayslipService.predict_year_end_earnings()
        return jsonify(forecast)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payslips_bp.route('/payslips/<int:payslip_id>/missing-jobs')
def api_missing_jobs(payslip_id):
    """Get jobs from payslip that don't exist in run_sheet_jobs."""
    try:
        from ..database import get_db_connection
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all job_items for this payslip
            cursor.execute("""
                SELECT 
                    job_number,
                    client,
                    job_type as activity,
                    location as job_address,
                    date,
                    amount,
                    postcode
                FROM job_items
                WHERE payslip_id = ?
                AND job_number IS NOT NULL
                AND job_number != ''
            """, (payslip_id,))
            
            payslip_jobs = [dict(row) for row in cursor.fetchall()]
            
            # Check which jobs don't exist in run_sheet_jobs
            # Note: run_sheet_jobs has UNIQUE(date, job_number) constraint
            missing_jobs = []
            for job in payslip_jobs:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM run_sheet_jobs
                    WHERE job_number = ? AND date = ?
                """, (job['job_number'], job['date']))
                
                result = cursor.fetchone()
                if result['count'] == 0:
                    missing_jobs.append(job)
            
            return jsonify({
                'success': True,
                'missing_jobs': missing_jobs,
                'total_jobs': len(payslip_jobs),
                'missing_count': len(missing_jobs)
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payslips_bp.route('/payslips/add-missing-jobs', methods=['POST'])
def api_add_missing_jobs():
    """Add missing jobs to run_sheet_jobs table."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from ..database import get_db_connection
        
        # Get and log the request data
        data = request.get_json()
        logger.info(f'Add missing jobs request: {data}')
        
        if not data:
            logger.error('No JSON data in request')
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        jobs = data.get('jobs', [])
        logger.info(f'Number of jobs to add: {len(jobs)}')
        
        if not jobs:
            logger.error('No jobs in request data')
            return jsonify({'success': False, 'error': 'No jobs provided'}), 400
        
        added_count = 0
        errors = []
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for i, job in enumerate(jobs):
                try:
                    logger.info(f'Processing job {i+1}/{len(jobs)}: {job.get("job_number")} on {job.get("date")}')
                    
                    # Use INSERT OR IGNORE to handle UNIQUE(date, job_number) constraint
                    cursor.execute("""
                        INSERT OR IGNORE INTO run_sheet_jobs (
                            date, job_number, customer, activity, 
                            job_address, postcode, status, source_file
                        ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 'payslip_import')
                    """, (
                        job.get('date'),
                        job.get('job_number'),
                        job.get('client'),  # Note: frontend sends 'client' not 'customer'
                        job.get('activity'),
                        job.get('job_address'),
                        job.get('postcode')
                    ))
                    
                    # Check if row was actually inserted (rowcount > 0)
                    if cursor.rowcount > 0:
                        added_count += 1
                        logger.info(f'Successfully added job {job.get("job_number")} on {job.get("date")}')
                    else:
                        logger.info(f'Job {job.get("job_number")} on {job.get("date")} already exists, skipped')
                        errors.append({
                            'job_number': job.get('job_number'),
                            'error': 'Already exists in runsheets'
                        })
                except Exception as e:
                    logger.error(f'Error adding job {job.get("job_number")}: {str(e)}')
                    errors.append({
                        'job_number': job.get('job_number'),
                        'error': str(e)
                    })
            
            conn.commit()
            logger.info(f'Committed {added_count} jobs to database')
        
        return jsonify({
            'success': True,
            'added_count': added_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f'Error in add_missing_jobs endpoint: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
