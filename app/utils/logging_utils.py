"""
Enhanced logging utilities for the application.
Comprehensive logging system with multiple loggers and handlers.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import sys


class CustomFormatter(logging.Formatter):
    """Custom formatter with color support and structured logging."""
    
    # Color codes for terminal output
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to level name for console output
        if hasattr(record, 'color') and record.color:
            level_color = self.COLORS.get(record.levelname, '')
            reset_color = self.COLORS['RESET']
            record.levelname = f"{level_color}{record.levelname}{reset_color}"
        
        # Always add structured field (empty if no structured_data)
        if hasattr(record, 'structured_data'):
            record.structured = json.dumps(record.structured_data, default=str)
        else:
            record.structured = ''
        
        return super().format(record)


class LoggerManager:
    """Centralized logger management."""
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls, log_dir: str = 'logs', log_level: str = 'INFO'):
        """Initialize the logging system."""
        if cls._initialized:
            return
        
        # Create logs directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Set global log level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        logging.getLogger().setLevel(numeric_level)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None, 
                  console_output: bool = True, structured: bool = False) -> logging.Logger:
        """Get or create a logger with specified configuration."""
        if name in cls._loggers:
            return cls._loggers[name]
        
        if not cls._initialized:
            cls.initialize()
        
        logger = logging.getLogger(name)
        logger.handlers.clear()  # Remove any existing handlers
        
        # File handler
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                f'logs/{log_file}',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            
            if structured:
                file_formatter = CustomFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(structured)s'
                )
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = CustomFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            
            # Add color flag for console output
            def add_color_flag(record):
                record.color = True
                return True
            
            console_handler.addFilter(add_color_flag)
            logger.addHandler(console_handler)
        
        logger.setLevel(logging.DEBUG)  # Let handlers control the level
        cls._loggers[name] = logger
        
        return logger


# Specialized loggers for different components
def get_settings_logger():
    """Get logger for settings operations."""
    return LoggerManager.get_logger('settings', 'settings.log', structured=True)


def get_sync_logger():
    """Get logger for sync operations."""
    return LoggerManager.get_logger('sync', 'sync.log', structured=True)


def get_api_logger():
    """Get logger for API operations."""
    return LoggerManager.get_logger('api', 'api.log', structured=True)


def get_data_logger():
    """Get logger for data operations."""
    return LoggerManager.get_logger('data', 'data.log', structured=True)


def get_error_logger():
    """Get logger for error tracking."""
    return LoggerManager.get_logger('errors', 'errors.log', structured=True)


# Enhanced logging functions
def log_settings_action(action: str, message: str, level: str = 'INFO', **kwargs):
    """Log settings actions with structured data."""
    logger = get_settings_logger()
    
    # Create structured data
    structured_data = {
        'action': action,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    # Log with structured data
    extra = {'structured_data': structured_data}
    
    if level == 'ERROR':
        logger.error(message, extra=extra)
    elif level == 'WARNING':
        logger.warning(message, extra=extra)
    elif level == 'DEBUG':
        logger.debug(message, extra=extra)
    else:
        logger.info(message, extra=extra)


def log_api_request(endpoint: str, method: str, status_code: int, 
                   duration_ms: float, user_agent: str = None, **kwargs):
    """Log API requests with performance metrics."""
    logger = get_api_logger()
    
    structured_data = {
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'duration_ms': duration_ms,
        'user_agent': user_agent,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"{method} {endpoint} - {status_code} ({duration_ms:.2f}ms)"
    
    extra = {'structured_data': structured_data}
    
    if status_code >= 500:
        logger.error(message, extra=extra)
    elif status_code >= 400:
        logger.warning(message, extra=extra)
    else:
        logger.info(message, extra=extra)


def log_sync_operation(operation: str, status: str, duration_seconds: float, 
                      records_processed: int = 0, **kwargs):
    """Log sync operations with metrics."""
    logger = get_sync_logger()
    
    structured_data = {
        'operation': operation,
        'status': status,
        'duration_seconds': duration_seconds,
        'records_processed': records_processed,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"Sync {operation} - {status} ({duration_seconds:.2f}s, {records_processed} records)"
    
    extra = {'structured_data': structured_data}
    
    if status == 'failed':
        logger.error(message, extra=extra)
    elif status == 'partial':
        logger.warning(message, extra=extra)
    else:
        logger.info(message, extra=extra)


def log_data_operation(operation: str, table: str, records_affected: int, 
                      operation_type: str = 'unknown', **kwargs):
    """Log database operations."""
    logger = get_data_logger()
    
    structured_data = {
        'operation': operation,
        'table': table,
        'records_affected': records_affected,
        'operation_type': operation_type,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"Data {operation} on {table} - {records_affected} records ({operation_type})"
    
    extra = {'structured_data': structured_data}
    logger.info(message, extra=extra)


def log_error(error: Exception, context: str = None, **kwargs):
    """Log errors with full context."""
    logger = get_error_logger()
    
    structured_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"Error in {context}: {type(error).__name__}: {str(error)}"
    
    extra = {'structured_data': structured_data}
    logger.error(message, extra=extra, exc_info=True)


def log_performance_metric(metric_name: str, value: float, unit: str = 'ms', **kwargs):
    """Log performance metrics."""
    logger = LoggerManager.get_logger('performance', 'performance.log', structured=True)
    
    structured_data = {
        'metric_name': metric_name,
        'value': value,
        'unit': unit,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"Performance: {metric_name} = {value}{unit}"
    
    extra = {'structured_data': structured_data}
    logger.info(message, extra=extra)


# Context manager for operation logging
class LoggedOperation:
    """Context manager for logging operations with timing."""
    
    def __init__(self, operation_name: str, logger_func=None, **kwargs):
        self.operation_name = operation_name
        self.logger_func = logger_func or log_settings_action
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger_func(
            self.operation_name, 
            f"Starting {self.operation_name}", 
            level='INFO',
            **self.kwargs
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is not None:
            self.logger_func(
                self.operation_name,
                f"Failed {self.operation_name}: {exc_val}",
                level='ERROR',
                duration_seconds=duration,
                error_type=exc_type.__name__,
                **self.kwargs
            )
        else:
            self.logger_func(
                self.operation_name,
                f"Completed {self.operation_name}",
                level='INFO',
                duration_seconds=duration,
                **self.kwargs
            )
