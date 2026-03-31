"""
Authentication decorator to protect routes.
Apply this to all routes that require authentication.
"""

from functools import wraps
from flask import redirect, url_for, request
from flask_login import current_user


def login_required_for_all(f):
    """
    Decorator to require login for all routes.
    Use this on blueprints to protect all routes at once.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin privileges.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            from flask import jsonify, abort
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Admin privileges required'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
