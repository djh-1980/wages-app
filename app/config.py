"""
Application configuration management.
Centralized configuration with environment support and feature flags.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Base configuration class."""
    
    # Application Version
    VERSION = '2.7.0'
    BUILD_DATE = '2026.03.10'
    
    # Base Directory
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY environment variable is not set. "
            "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file upload
    
    # Session Security Configuration
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)  # 4 hours (matches HMRC token lifetime)
    
    # Database Configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'data/database/payslips.db'
    DATABASE_BACKUP_DIR = os.environ.get('BACKUP_DIR') or 'data/database/backups'
    DATABASE_BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
    
    # Document Storage Configuration
    RUNSHEETS_DIR = os.environ.get('RUNSHEETS_DIR') or 'data/documents/runsheets'
    PAYSLIPS_DIR = os.environ.get('PAYSLIPS_DIR') or 'data/documents/payslips'
    
    # Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'PaySlips'
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.environ.get('LOG_DIR') or 'logs'
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))
    
    # Gmail Integration
    GMAIL_CREDENTIALS_FILE = os.environ.get('GMAIL_CREDENTIALS') or 'credentials.json'
    GMAIL_TOKEN_FILE = os.environ.get('GMAIL_TOKEN') or 'token.json'
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    
    # HMRC MTD API Configuration
    HMRC_CLIENT_ID = os.environ.get('HMRC_CLIENT_ID', '')
    HMRC_CLIENT_SECRET = os.environ.get('HMRC_CLIENT_SECRET', '')
    HMRC_REDIRECT_URI = os.environ.get('HMRC_REDIRECT_URI', 'http://localhost:5000/api/hmrc/auth/callback')
    HMRC_ENVIRONMENT = os.environ.get('HMRC_ENVIRONMENT', 'sandbox')  # sandbox or production
    HMRC_SERVER_TOKEN = os.environ.get('HMRC_SERVER_TOKEN', '')  # For server-to-server auth
    
    @property
    def HMRC_API_BASE_URL(self):
        """Get HMRC API base URL based on environment."""
        if self.HMRC_ENVIRONMENT == 'production':
            return 'https://api.service.hmrc.gov.uk'
        return 'https://test-api.service.hmrc.gov.uk'
    
    @property
    def HMRC_AUTH_URL(self):
        """Get HMRC authorization URL."""
        if self.HMRC_ENVIRONMENT == 'production':
            return 'https://api.service.hmrc.gov.uk/oauth/authorize'
        return 'https://test-api.service.hmrc.gov.uk/oauth/authorize'
    
    @property
    def HMRC_TOKEN_URL(self):
        """Get HMRC token URL."""
        if self.HMRC_ENVIRONMENT == 'production':
            return 'https://api.service.hmrc.gov.uk/oauth/token'
        return 'https://test-api.service.hmrc.gov.uk/oauth/token'
    
    # Sync Configuration
    AUTO_SYNC_ENABLED = os.environ.get('AUTO_SYNC_ENABLED', 'true').lower() == 'true'
    SYNC_TIMEOUT_SECONDS = int(os.environ.get('SYNC_TIMEOUT', '300'))  # 5 minutes
    SYNC_RETRY_ATTEMPTS = int(os.environ.get('SYNC_RETRY_ATTEMPTS', '3'))
    
    # Performance Configuration
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', '300'))  # 5 minutes
    DATABASE_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', '5'))
    
    # Feature Flags
    FEATURE_ADVANCED_ANALYTICS = os.environ.get('FEATURE_ADVANCED_ANALYTICS', 'true').lower() == 'true'
    FEATURE_ROUTE_OPTIMIZATION = os.environ.get('FEATURE_ROUTE_OPTIMIZATION', 'true').lower() == 'true'
    FEATURE_PREDICTIVE_ANALYTICS = os.environ.get('FEATURE_PREDICTIVE_ANALYTICS', 'true').lower() == 'true'
    FEATURE_DATA_VALIDATION = os.environ.get('FEATURE_DATA_VALIDATION', 'true').lower() == 'true'
    FEATURE_INTELLIGENT_SYNC = os.environ.get('FEATURE_INTELLIGENT_SYNC', 'true').lower() == 'true'
    
    # API Configuration
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '1000 per hour')
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', '30'))
    
    # UI Configuration
    UI_THEME = os.environ.get('UI_THEME', 'light')  # light, dark, auto
    UI_ITEMS_PER_PAGE = int(os.environ.get('UI_ITEMS_PER_PAGE', '20'))
    UI_CHART_COLORS = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#20c997']
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        # Ensure required directories exist
        Path(Config.DATABASE_BACKUP_DIR).mkdir(exist_ok=True)
        Path(Config.LOG_DIR).mkdir(exist_ok=True)
        Path(Config.UPLOAD_FOLDER).mkdir(exist_ok=True)
        Path('data').mkdir(exist_ok=True)
        
        # Set Flask configuration
        app.config['SECRET_KEY'] = Config.SECRET_KEY
        app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
        app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Shorter timeouts for faster development
    SYNC_TIMEOUT_SECONDS = 180  # 3 minutes
    CACHE_TIMEOUT = 60  # 1 minute
    
    # Enable all features in development
    FEATURE_ADVANCED_ANALYTICS = True
    FEATURE_ROUTE_OPTIMIZATION = True
    FEATURE_PREDICTIVE_ANALYTICS = True
    FEATURE_DATA_VALIDATION = True
    FEATURE_INTELLIGENT_SYNC = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Enforce SECRET_KEY in production
    def __init__(self):
        if not os.environ.get('SECRET_KEY') or os.environ.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
            raise ValueError(
                "SECRET_KEY must be set in production environment!\n"
                "Set it in .env file or as environment variable."
            )
    
    # Production logging
    LOG_LEVEL = 'INFO'
    
    # Longer timeouts for production stability
    SYNC_TIMEOUT_SECONDS = 600  # 10 minutes
    CACHE_TIMEOUT = 900  # 15 minutes
    
    # Conservative feature flags for production
    FEATURE_ADVANCED_ANALYTICS = True
    FEATURE_ROUTE_OPTIMIZATION = True
    FEATURE_PREDICTIVE_ANALYTICS = True
    FEATURE_DATA_VALIDATION = True
    FEATURE_INTELLIGENT_SYNC = False  # Disable until thoroughly tested


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    
    # Use in-memory database for testing
    DATABASE_PATH = ':memory:'
    
    # Minimal timeouts for fast tests
    SYNC_TIMEOUT_SECONDS = 30
    CACHE_TIMEOUT = 10
    
    # Disable external integrations in tests
    AUTO_SYNC_ENABLED = False
    FEATURE_INTELLIGENT_SYNC = False


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration class based on environment."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])


class FeatureFlags:
    """Feature flag management."""
    
    @staticmethod
    def is_enabled(feature_name, config_obj=None):
        """Check if a feature is enabled."""
        if config_obj is None:
            config_obj = get_config()
        
        return getattr(config_obj, f'FEATURE_{feature_name.upper()}', False)
    
    @staticmethod
    def get_all_features(config_obj=None):
        """Get all feature flags and their status."""
        if config_obj is None:
            config_obj = get_config()
        
        features = {}
        for attr in dir(config_obj):
            if attr.startswith('FEATURE_'):
                feature_name = attr.replace('FEATURE_', '').lower()
                features[feature_name] = getattr(config_obj, attr)
        
        return features
    
    @staticmethod
    def require_feature(feature_name):
        """Decorator to require a feature flag."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not FeatureFlags.is_enabled(feature_name):
                    from flask import jsonify
                    return jsonify({
                        'error': f'Feature {feature_name} is not enabled',
                        'feature_required': feature_name
                    }), 403
                return func(*args, **kwargs)
            wrapper.__name__ = func.__name__
            return wrapper
        return decorator
