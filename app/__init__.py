"""
Flask application factory and configuration.
"""

import logging
import os
from datetime import datetime

import pytz
from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .database import init_database
from .config import get_config, Config
from .utils.logging_utils import LoggerManager

logger = logging.getLogger(__name__)

# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


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
    
    # Initialize CSRF Protection
    csrf = CSRFProtect(app)
    
    # Initialize Rate Limiter
    limiter.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        logger.debug(f"Loading user with ID: {user_id}")
        user = User.get_by_id(int(user_id))
        if user:
            logger.debug(f"User loaded: {user.username}, is_active: {user.is_active}, is_authenticated: {user.is_authenticated}")
        else:
            logger.debug(f"User not found for ID: {user_id}")
        return user
    
    @login_manager.unauthorized_handler
    def unauthorized():
        """Handle unauthorized access - return 401 JSON for API requests, redirect otherwise."""
        from flask import request, jsonify, redirect, url_for
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized', 'message': 'Please log in to access this resource'}), 401
        return redirect(url_for('auth.login', next=request.url))
    
    # Set application timezone to UK
    os.environ['TZ'] = 'Europe/London'
    app.config['TIMEZONE'] = pytz.timezone('Europe/London')
    
    # Initialize logging system
    LoggerManager.initialize(
        log_dir=config_class.LOG_DIR,
        log_level=config_class.LOG_LEVEL
    )
    
    # Configure root logger
    logging.basicConfig(
        level=app.config.get('LOG_LEVEL', 'INFO'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    from .routes.auth import auth_bp
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
    from .routes.api_recurring import recurring_bp
    from .routes.api_runsheet_testing import runsheet_testing_bp
    from .routes.api_cdn import api_cdn_bp
    from .routes.api_python_deps import api_python_deps_bp
    from .routes.api_job_notes import job_notes_bp
    from .routes.api_route_planning import route_planning_bp
    from .routes.api_hmrc import hmrc_bp
    
    app.register_blueprint(auth_bp)
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
    app.register_blueprint(recurring_bp)
    app.register_blueprint(runsheet_testing_bp)
    app.register_blueprint(api_cdn_bp)
    app.register_blueprint(api_python_deps_bp)
    app.register_blueprint(job_notes_bp)
    app.register_blueprint(route_planning_bp)
    app.register_blueprint(hmrc_bp)
    
    # Protect all routes with authentication
    from .auth_protection import protect_all_routes
    protect_all_routes(app)
    
    # Error handler for rate limiting
    @app.errorhandler(429)
    def ratelimit_handler(e):
        flash('Too many login attempts. Please wait 5 minutes and try again.', 'error')
        return redirect(url_for('auth.login'))
    
    return app
