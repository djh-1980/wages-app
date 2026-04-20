"""
Flask application factory and configuration.
"""

import logging
import os
from datetime import datetime, timedelta

import pytz
from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .database import init_database
from .config import get_config, Config
from .utils.logging_utils import LoggerManager
from .logging_config import setup_logging

logger = logging.getLogger('app')

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
    
    # Session security is configured in Config/ProductionConfig:
    # - SESSION_COOKIE_SAMESITE = 'Lax' (critical for OAuth redirects)
    # - SESSION_COOKIE_HTTPONLY = True
    # - SESSION_COOKIE_SECURE is True in production (FLASK_ENV=production) and False in dev
    # Do not override those here or the production cookie will fall back to insecure.
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    
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
    
    # Initialize central logging configuration
    environment = os.environ.get('FLASK_ENV', 'production')
    setup_logging(
        log_dir=config_class.LOG_DIR,
        log_level=config_class.LOG_LEVEL,
        environment=environment
    )
    
    # Log application startup
    version = config_class.VERSION if hasattr(config_class, 'VERSION') else '2.1.0'
    logger.info(f"TVS TCMS v{version} starting up (environment: {environment})")
    
    # Initialize database
    init_database()
    
    # Run database migrations
    from .services.migration_runner import run_migrations
    logger.info("Running database migrations...")
    migration_success, migration_count = run_migrations()
    if not migration_success:
        logger.error("Database migrations failed - application may not function correctly")
    else:
        if migration_count > 0:
            logger.info(f"Database migrations completed successfully - {migration_count} migration(s) applied")
        else:
            logger.info("Database migrations up to date - no new migrations to apply")
    
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

    # HMRC sandbox-only helper endpoints (test users, create-test-business, etc.).
    # Gated on HMRC_ENVIRONMENT so the routes are not exposed in production.
    if config_class.HMRC_ENVIRONMENT != 'production':
        from .routes.api_hmrc_sandbox import sandbox_bp
        app.register_blueprint(sandbox_bp)
        logger.info("HMRC sandbox blueprint registered (HMRC_ENVIRONMENT=%s)", config_class.HMRC_ENVIRONMENT)
    else:
        logger.info("HMRC sandbox blueprint NOT registered (production environment)")
    
    # Protect all routes with authentication
    from .auth_protection import protect_all_routes
    protect_all_routes(app)
    
    # Error handler for rate limiting
    @app.errorhandler(429)
    def ratelimit_handler(e):
        flash('Too many login attempts. Please wait 5 minutes and try again.', 'error')
        return redirect(url_for('auth.login'))

    # Custom branded error pages. API requests (anything under /api/) get JSON
    # so the frontend can surface a useful message instead of a full HTML page.
    from flask import render_template, request as _request

    def _api_json_error(code, title, message):
        from flask import jsonify
        return jsonify({'success': False, 'error': title, 'message': message}), code

    @app.errorhandler(403)
    def forbidden(e):
        if _request.path.startswith('/api/'):
            return _api_json_error(403, 'Forbidden', 'You do not have permission to perform this action.')
        return render_template(
            'errors/error.html',
            code=403, title='Forbidden', accent='warning',
            message='You are not allowed to view this page.',
        ), 403

    @app.errorhandler(404)
    def not_found(e):
        if _request.path.startswith('/api/'):
            return _api_json_error(404, 'Not Found', 'The requested resource was not found.')
        return render_template(
            'errors/error.html',
            code=404, title='Page not found', accent='info',
            message='We could not find the page you requested.',
        ), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f'500 error on {_request.path}: {e}', exc_info=True)
        if _request.path.startswith('/api/'):
            return _api_json_error(500, 'Server Error', 'An internal error occurred.')
        return render_template(
            'errors/error.html',
            code=500, title='Server error', accent='danger',
            message='An unexpected error has occurred. The issue has been logged.',
        ), 500
    
    return app
