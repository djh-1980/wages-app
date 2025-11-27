"""
Main routes blueprint - handles page rendering routes.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, render_template
import sys
import os

# Add the parent directory to the path to import version
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
try:
    from version import get_version_info
except ImportError:
    # Fallback if version.py doesn't exist
    def get_version_info():
        return {
            'version': '2.0.0',
            'build_date': '2025.11.27',
            'changelog': []
        }

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
    """Settings page - redirect to profile."""
    return render_template('settings/profile.html')

@main_bp.route('/settings/profile')
def settings_profile():
    """Profile settings page."""
    return render_template('settings/profile.html')

@main_bp.route('/settings/sync')
def settings_sync():
    """Data & Sync settings page."""
    return render_template('settings/sync.html')

@main_bp.route('/settings/attendance')
def settings_attendance():
    """Attendance settings page."""
    return render_template('settings/attendance.html')

@main_bp.route('/settings/system')
def settings_system():
    """System settings page."""
    return render_template('settings/system.html')

@main_bp.route('/settings/about')
def settings_about():
    """About page."""
    version_info = get_version_info()
    return render_template('settings/about.html', version_info=version_info)
