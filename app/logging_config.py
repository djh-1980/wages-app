"""
Central logging configuration for TVS TCMS.
Provides consistent logging setup across all modules.
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_dir='logs', log_level='INFO', environment='production'):
    """
    Configure application-wide logging.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: 'development' or 'production' (affects console output)
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Standard format for all loggers
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()  # Remove any existing handlers
    
    # Console handler (development only)
    if environment == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
    
    # Error log - captures ERROR and above from all loggers
    error_handler = logging.handlers.RotatingFileHandler(
        f'{log_dir}/error.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # Configure specialized loggers
    _setup_app_logger(log_dir, formatter, numeric_level)
    _setup_migration_logger(log_dir, formatter, numeric_level)
    _setup_hmrc_logger(log_dir, formatter, numeric_level)
    
    logging.info(f"Logging configured: level={log_level}, environment={environment}")


def _setup_app_logger(log_dir, formatter, level):
    """Configure general application logger."""
    app_logger = logging.getLogger('app')
    app_logger.setLevel(level)
    app_logger.propagate = True  # Also send to root logger for error.log
    
    handler = logging.handlers.RotatingFileHandler(
        f'{log_dir}/app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)


def _setup_migration_logger(log_dir, formatter, level):
    """Configure database migration logger."""
    migration_logger = logging.getLogger('migration')
    migration_logger.setLevel(level)
    migration_logger.propagate = True
    
    handler = logging.handlers.RotatingFileHandler(
        f'{log_dir}/migration.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    handler.setFormatter(formatter)
    migration_logger.addHandler(handler)


def _setup_hmrc_logger(log_dir, formatter, level):
    """Configure HMRC API logger."""
    hmrc_logger = logging.getLogger('hmrc')
    hmrc_logger.setLevel(level)
    hmrc_logger.propagate = True
    
    handler = logging.handlers.RotatingFileHandler(
        f'{log_dir}/hmrc.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    handler.setFormatter(formatter)
    hmrc_logger.addHandler(handler)


def get_logger(name):
    """
    Get a logger instance.
    
    Args:
        name: Logger name (use __name__ from calling module)
        
    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)
