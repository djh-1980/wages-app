"""
Flask application factory and configuration.
"""

from flask import Flask
from .database import init_database
from .config import get_config, Config
from .utils.logging_utils import LoggerManager


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
    
    # Initialize logging system
    LoggerManager.initialize(
        log_dir=config_class.LOG_DIR,
        log_level=config_class.LOG_LEVEL
    )
    
    # Initialize database
    init_database()
    
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
    
    return app
