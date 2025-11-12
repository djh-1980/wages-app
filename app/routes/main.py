"""
Main routes blueprint - handles page rendering routes.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main landing page - redirect to runsheets."""
    return render_template('runsheets.html')


@main_bp.route('/wages')
def wages():
    """Wages dashboard page."""
    return render_template('wages.html')


@main_bp.route('/paypoint')
def paypoint():
    """Paypoint stock management page."""
    return render_template('paypoint.html')


@main_bp.route('/runsheets')
def runsheets():
    """Run sheets page."""
    return render_template('runsheets.html')


@main_bp.route('/reports')
def reports():
    """Reports page."""
    return render_template('reports.html')


@main_bp.route('/settings')
def settings():
    """Settings page."""
    return render_template('settings.html')
