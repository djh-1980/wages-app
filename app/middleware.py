"""
Application middleware for error handling, logging, and request processing.
"""

from flask import request, jsonify, g
from functools import wraps
from datetime import datetime
import time
import traceback
from .utils.logging_utils import log_api_request, log_error
from .config import FeatureFlags


def register_middleware(app):
    """Register all middleware with the Flask app."""
    
    @app.before_request
    def before_request():
        """Execute before each request."""
        g.start_time = time.time()
        g.request_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(request)}"
    
    @app.after_request
    def after_request(response):
        """Execute after each request."""
        try:
            # Calculate request duration
            duration_ms = (time.time() - g.start_time) * 1000
            
            # Log API request
            log_api_request(
                endpoint=request.endpoint or request.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_agent=request.headers.get('User-Agent'),
                request_id=getattr(g, 'request_id', 'unknown'),
                ip_address=request.remote_addr
            )
            
            # Add performance headers
            response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"
            response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
            
        except Exception as e:
            # Don't let middleware errors break the response
            log_error(e, context='after_request_middleware')
        
        return response
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404,
            'request_id': getattr(g, 'request_id', 'unknown')
        }), 404
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 errors."""
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request was invalid or malformed',
            'status_code': 400,
            'request_id': getattr(g, 'request_id', 'unknown')
        }), 400
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        log_error(error, context='internal_server_error', request_id=getattr(g, 'request_id', 'unknown'))
        
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500,
            'request_id': getattr(g, 'request_id', 'unknown')
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions."""
        log_error(error, context='unhandled_exception', 
                 request_id=getattr(g, 'request_id', 'unknown'),
                 endpoint=request.endpoint,
                 method=request.method,
                 path=request.path)
        
        # Return JSON error for API endpoints
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'status_code': 500,
                'request_id': getattr(g, 'request_id', 'unknown')
            }), 500
        
        # For non-API endpoints, you might want to render an error template
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500,
            'request_id': getattr(g, 'request_id', 'unknown')
        }), 500


def require_feature(feature_name):
    """Decorator to require a feature flag."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not FeatureFlags.is_enabled(feature_name):
                return jsonify({
                    'error': 'Feature Not Available',
                    'message': f'The {feature_name} feature is not enabled',
                    'feature_required': feature_name,
                    'status_code': 403
                }), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_json(required_fields=None):
    """Decorator to validate JSON input."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'error': 'Invalid Content Type',
                    'message': 'Request must be JSON',
                    'status_code': 400
                }), 400
            
            data = request.get_json()
            if data is None:
                return jsonify({
                    'error': 'Invalid JSON',
                    'message': 'Request body must contain valid JSON',
                    'status_code': 400
                }), 400
            
            # Check required fields
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or data[field] is None:
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'error': 'Missing Required Fields',
                        'message': f'The following fields are required: {", ".join(missing_fields)}',
                        'missing_fields': missing_fields,
                        'status_code': 400
                    }), 400
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(max_requests=100, window_seconds=3600):
    """Simple rate limiting decorator (in-memory, not production-ready)."""
    request_counts = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Clean old entries
            cutoff_time = current_time - window_seconds
            request_counts[client_ip] = [
                req_time for req_time in request_counts.get(client_ip, [])
                if req_time > cutoff_time
            ]
            
            # Check rate limit
            if len(request_counts.get(client_ip, [])) >= max_requests:
                return jsonify({
                    'error': 'Rate Limit Exceeded',
                    'message': f'Maximum {max_requests} requests per {window_seconds} seconds',
                    'status_code': 429
                }), 429
            
            # Record this request
            if client_ip not in request_counts:
                request_counts[client_ip] = []
            request_counts[client_ip].append(current_time)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def handle_database_errors(func):
    """Decorator to handle common database errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_type = type(e).__name__
            
            # Handle specific database errors
            if 'sqlite3' in str(type(e)):
                if 'UNIQUE constraint failed' in str(e):
                    return jsonify({
                        'error': 'Duplicate Entry',
                        'message': 'A record with this information already exists',
                        'status_code': 409
                    }), 409
                elif 'no such table' in str(e):
                    return jsonify({
                        'error': 'Database Error',
                        'message': 'Database table not found. Please check database initialization.',
                        'status_code': 500
                    }), 500
                elif 'database is locked' in str(e):
                    return jsonify({
                        'error': 'Database Busy',
                        'message': 'Database is currently busy. Please try again.',
                        'status_code': 503
                    }), 503
            
            # Log the error and re-raise for general error handler
            log_error(e, context=f'database_error_in_{func.__name__}')
            raise
    
    return wrapper


def cors_headers(func):
    """Add CORS headers to response."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        
        # If it's a tuple (response, status_code), handle accordingly
        if isinstance(response, tuple):
            response_obj, status_code = response
            if hasattr(response_obj, 'headers'):
                response_obj.headers['Access-Control-Allow-Origin'] = '*'
                response_obj.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response_obj.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response_obj, status_code
        else:
            if hasattr(response, 'headers'):
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
    
    return wrapper


class RequestValidator:
    """Request validation utilities."""
    
    @staticmethod
    def validate_pagination_params():
        """Validate pagination parameters."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        errors = []
        
        if page < 1:
            errors.append('Page number must be 1 or greater')
        
        if per_page < 1 or per_page > 100:
            errors.append('Per page must be between 1 and 100')
        
        if errors:
            return None, jsonify({
                'error': 'Invalid Pagination Parameters',
                'message': '; '.join(errors),
                'status_code': 400
            }), 400
        
        return {'page': page, 'per_page': per_page}, None, None
    
    @staticmethod
    def validate_date_range():
        """Validate date range parameters."""
        from .utils.date_utils import DateUtils
        
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        if date_from and not DateUtils.is_valid_date(date_from):
            return None, jsonify({
                'error': 'Invalid Date Format',
                'message': 'date_from parameter has invalid format',
                'status_code': 400
            }), 400
        
        if date_to and not DateUtils.is_valid_date(date_to):
            return None, jsonify({
                'error': 'Invalid Date Format',
                'message': 'date_to parameter has invalid format',
                'status_code': 400
            }), 400
        
        if date_from and date_to:
            validation_result = DateUtils.validate_date_range(date_from, date_to)
            if not validation_result['valid']:
                return None, jsonify({
                    'error': 'Invalid Date Range',
                    'message': '; '.join(validation_result['errors']),
                    'status_code': 400
                }), 400
        
        return {'date_from': date_from, 'date_to': date_to}, None, None
