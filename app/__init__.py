"""
Flask application factory and configuration.
"""

from flask import Flask
from .database import init_database
from .config import get_config, Config
from .utils.logging_utils import LoggerManager
import os
import pytz
from datetime import datetime


def create_app(config_name=None):
    """Create and configure the Flask application."""
    # Configure Flask to look for templates in the correct directory
    import os
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Initialize configuration
    config_class.init_app(app)
    
    # Set application timezone to UK
    os.environ['TZ'] = 'Europe/London'
    app.config['TIMEZONE'] = pytz.timezone('Europe/London')
    
    # Initialize logging system
    LoggerManager.initialize(
        log_dir=config_class.LOG_DIR,
        log_level=config_class.LOG_LEVEL
    )
    
    # Initialize database
    init_database()
    
    # Start auto-sync by default
    from app.services.periodic_sync import periodic_sync_service
    if app.config.get('AUTO_SYNC_ENABLED', True):
        periodic_sync_service.start_periodic_sync()
        app.logger.info("Auto-sync started automatically")
    
    # Register middleware
    from .middleware import register_middleware
    register_middleware(app)
    
    # Register blueprints
    from .routes.main import main_bp
    from .routes.api_payslips import payslips_bp
    from .routes.api_runsheets import runsheets_bp
    from .routes.api_reports import reports_bp
    from .routes.api_settings import settings_bp
    from .routes.api_data import data_bp
    from .routes.api_gmail import gmail_bp
    from .routes.api_search import search_bp
    from .routes.api_notifications import notifications_bp
    from .routes.api_attendance import attendance_bp
    from .routes.api_sync import sync_bp
    from .routes.api_paypoint import paypoint_bp
    from .routes.api_upload import upload_bp
    from .routes.api_verbal_pay import verbal_pay_bp
    from .routes.api_mileage import mileage_bp
    from .routes.api_housekeeping import housekeeping_bp
    from .routes.api_customer_mapping import customer_mapping_bp
    from .routes.api_expenses import expenses_bp
    from .routes.api_bank_import import bank_import_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(payslips_bp)
    app.register_blueprint(runsheets_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(gmail_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(paypoint_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(verbal_pay_bp)
    app.register_blueprint(mileage_bp, url_prefix='/api/mileage')
    app.register_blueprint(housekeeping_bp, url_prefix='/api/housekeeping')
    app.register_blueprint(customer_mapping_bp, url_prefix='/api/customer-mapping')
    app.register_blueprint(expenses_bp)
    app.register_blueprint(bank_import_bp)
    
    return app
