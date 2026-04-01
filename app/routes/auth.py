"""
Authentication routes for login, logout, and user management.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from ..models.user import User
from ..middleware import rate_limit
from .. import limiter
import re
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Password strength validator
def validate_password_strength(password):
    """Validate password meets security requirements."""
    errors = []
    if len(password) < 12:
        errors.append("At least 12 characters required")
    if not re.search(r'[A-Z]', password):
        errors.append("Must contain an uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("Must contain a lowercase letter")
    if not re.search(r'\d', password):
        errors.append("Must contain a number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Must contain a special character")
    return errors


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per 5 minutes")
def login():
    """Login page and handler."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('auth/login.html')
        
        user = User.get_by_username(username)
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return render_template('auth/login.html')
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'error')
            return render_template('auth/login.html')
        
        # Prevent session fixation attack
        session.clear()
        session.permanent = True
        result = login_user(user, remember=remember)
        print(f"[DEBUG] login_user result: {result}")
        print(f"[DEBUG] current_user after login: {current_user}")
        print(f"[DEBUG] current_user.is_authenticated: {current_user.is_authenticated}")
        print(f"[DEBUG] Session: {dict(session)}")
        user.update_last_login()
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout handler."""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page and handler."""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('auth/change_password.html')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('auth/change_password.html')
        
        # Validate password strength
        password_errors = validate_password_strength(new_password)
        if password_errors:
            for error in password_errors:
                flash(error, 'error')
            return render_template('auth/change_password.html')
        
        if User.change_password(current_user.id, new_password):
            flash('Password changed successfully', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Error changing password', 'error')
    
    return render_template('auth/change_password.html')


# API Routes for password change
@auth_bp.route('/api/user/change-password', methods=['POST'])
@login_required
def api_change_password():
    """Change password via API (AJAX)."""
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    
    if not current_user.check_password(current_password):
        return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'error': 'New passwords do not match'}), 400
    
    # Validate password strength (minimum 8 chars, at least one number)
    if len(new_password) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400
    
    if not re.search(r'\d', new_password):
        return jsonify({'success': False, 'error': 'Password must contain at least one number'}), 400
    
    if User.change_password(current_user.id, new_password):
        logger.info(f"Password changed successfully for user {current_user.username}")
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    else:
        return jsonify({'success': False, 'error': 'Error changing password'}), 500


@auth_bp.route('/api/user/profile', methods=['GET'])
@login_required
def api_get_user_profile():
    """Get current user profile information."""
    return jsonify({
        'success': True,
        'user': {
            'username': current_user.username,
            'email': current_user.email,
            'is_admin': current_user.is_admin,
            'is_active': current_user.is_active
        }
    })


# API Routes for user management (admin only)
@auth_bp.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    """Get all users (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    users = User.get_all_users()
    return jsonify({
        'success': True,
        'users': [user.to_dict() for user in users]
    })


@auth_bp.route('/api/users', methods=['POST'])
@login_required
def api_create_user():
    """Create new user (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    is_admin = data.get('is_admin', False)
    
    if not all([username, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate password strength
    password_errors = validate_password_strength(password)
    if password_errors:
        return jsonify({'error': 'Password does not meet requirements', 'details': password_errors}), 400
    
    # Check if username or email already exists
    if User.get_by_username(username):
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.get_by_email(email):
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User.create_user(username, email, password, is_admin)
    
    if user:
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 201
    else:
        return jsonify({'error': 'Failed to create user'}), 500


@auth_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    """Update user (admin only or own account)."""
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Non-admins can only update their own email
    if not current_user.is_admin:
        allowed_fields = {'email'}
        data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if User.update_user(user_id, **data):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update user'}), 500


@auth_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    """Delete user (admin only, cannot delete self)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if current_user.id == user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    if User.delete_user(user_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete user'}), 500
