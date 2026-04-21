"""
Automatic route protection for authentication.
This module adds @login_required to all routes automatically.
"""

from flask import request, redirect, url_for
from flask_login import current_user


def protect_all_routes(app):
    """
    Add authentication requirement to all routes except login and static files.
    Call this after all blueprints are registered.
    """
    
    @app.before_request
    def require_login():
        """Require login for all routes except public ones."""
        
        # Public routes that don't require authentication
        public_endpoints = [
            'auth.login',
            'auth.logout',
            'static',
            'main.privacy',
            'main.terms',
            'health.healthz',
            'health.readyz',
        ]

        # Public URL prefixes
        public_prefixes = [
            '/static/',
            '/login',
            '/logout',
            '/privacy',
            '/terms',
            '/healthz',
            '/readyz',
        ]
        
        # Check if current endpoint is public
        if request.endpoint in public_endpoints:
            return None
        
        # Check if current path starts with public prefix
        for prefix in public_prefixes:
            if request.path.startswith(prefix):
                return None
        
        # Require authentication for all other routes
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        
        return None
