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
