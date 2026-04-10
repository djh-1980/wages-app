"""
HMRC Sandbox Testing API Routes.

WARNING: SANDBOX TESTING ONLY
These routes are for development and testing purposes only.
Remove this entire file before production deployment.
"""

import logging
from flask import Blueprint, request, jsonify
from flask_wtf.csrf import CSRFProtect

from ..services.hmrc_sandbox import HMRCSandboxService
from ..services.hmrc_auth import HMRCAuthService

logger = logging.getLogger(__name__)

# Blueprint for sandbox testing routes
sandbox_bp = Blueprint('hmrc_sandbox', __name__, url_prefix='/api/hmrc/sandbox')

# Get CSRF instance
csrf = CSRFProtect()


@sandbox_bp.route('/create-test-user', methods=['POST'])
@csrf.exempt
def create_test_user():
    """
    Create a complete test user with business.
    
    Steps:
    1. Create test individual using Create Test User API
    2. Authenticate the test user to get OAuth token
    3. Create test business using Self Assessment Test Support API
    4. Store all details in database
    
    WARNING: SANDBOX ONLY - Remove before production
    
    Returns:
        Test user and business details
    """
    try:
        # Detailed logging for debugging
        logger.info('=== CREATE TEST USER REQUEST ===')
        logger.info(f'Request method: {request.method}')
        logger.info(f'Request headers: {dict(request.headers)}')
        logger.info(f'Request content type: {request.content_type}')
        logger.info(f'Request data: {request.get_data(as_text=True)}')
        logger.info(f'Request JSON: {request.get_json(silent=True)}')
        
        sandbox_service = HMRCSandboxService()
        
        # Step 1: Create test individual
        logger.info('Step 1: Creating test individual')
        user_result = sandbox_service.create_test_individual()
        
        if not user_result.get('success'):
            return jsonify(user_result), 400
        
        user_data = user_result.get('data')
        nino = user_data.get('nino')
        
        logger.info(f'Test user created: {nino}')
        
        # Step 2: Get OAuth token for the test user
        # Note: In sandbox, we need to use the HMRCClient with test credentials
        # For now, we'll store the user without the business and let the user
        # authenticate manually to create the business
        
        # Store test user (without business for now)
        store_result = sandbox_service.store_test_user(user_data)
        
        if not store_result.get('success'):
            return jsonify(store_result), 500
        
        return jsonify({
            'success': True,
            'message': 'Test user created successfully. Please authenticate via OAuth to create business.',
            'data': {
                'userId': user_data.get('userId'),
                'nino': user_data.get('nino'),
                'saUtr': user_data.get('saUtr'),
                'password': user_data.get('password'),
                'userFullName': user_data.get('userFullName'),
                'emailAddress': user_data.get('emailAddress'),
                'note': 'Use these credentials to authenticate via /api/hmrc/auth/start'
            }
        })
    
    except Exception as e:
        logger.error(f'Error creating test user: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@sandbox_bp.route('/create-test-business', methods=['POST'])
@csrf.exempt
def create_test_business():
    """
    Retrieve auto-provisioned test business for an authenticated test user.
    
    HMRC automatically creates a test business when a test user is created
    with 'mtd-income-tax' service. This endpoint fetches that business.
    Requires active OAuth session.
    
    WARNING: SANDBOX ONLY - Remove before production
    
    Returns:
        Business details
    """
    try:
        data = request.get_json() or {}
        nino = data.get('nino')
        
        if not nino:
            return jsonify({'success': False, 'error': 'nino is required'}), 400
        
        # Get OAuth token from session
        auth_service = HMRCAuthService()
        access_token = auth_service.get_valid_access_token()
        
        if not access_token:
            return jsonify({
                'success': False,
                'error': 'Not authenticated. Please authenticate via OAuth first.'
            }), 401
        
        # Retrieve auto-provisioned test business
        sandbox_service = HMRCSandboxService()
        business_result = sandbox_service.create_test_business(nino, access_token)
        
        if not business_result.get('success'):
            return jsonify(business_result), 400
        
        business_data = business_result.get('data')
        
        # Update stored test user with business details
        # Get current test user
        test_user = sandbox_service.get_active_test_user()
        if test_user and test_user.get('nino') == nino:
            user_data = {
                'userId': test_user.get('user_id'),
                'password': test_user.get('password'),
                'nino': test_user.get('nino'),
                'saUtr': test_user.get('sa_utr')
            }
            sandbox_service.store_test_user(user_data, business_data)
        
        return jsonify({
            'success': True,
            'message': 'Test business retrieved successfully',
            'data': business_data
        })
    
    except Exception as e:
        logger.error(f'Error creating test business: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@sandbox_bp.route('/active-test-user')
def get_active_test_user():
    """
    Get the currently active test user.
    
    WARNING: SANDBOX ONLY - Remove before production
    
    Returns:
        Active test user details
    """
    try:
        sandbox_service = HMRCSandboxService()
        test_user = sandbox_service.get_active_test_user()
        
        if not test_user:
            return jsonify({
                'success': True,
                'data': None,
                'message': 'No active test user found'
            })
        
        # Don't expose password in API response
        test_user_safe = {
            'userId': test_user.get('user_id'),
            'nino': test_user.get('nino'),
            'saUtr': test_user.get('sa_utr'),
            'businessId': test_user.get('business_id'),
            'tradingName': test_user.get('trading_name'),
            'accountingType': test_user.get('accounting_type'),
            'commencementDate': test_user.get('commencement_date'),
            'createdAt': test_user.get('created_at')
        }
        
        return jsonify({
            'success': True,
            'data': test_user_safe
        })
    
    except Exception as e:
        logger.error(f'Error getting active test user: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@sandbox_bp.route('/test-users')
def get_all_test_users():
    """
    Get all test users (for history/debugging).
    
    WARNING: SANDBOX ONLY - Remove before production
    
    Returns:
        List of all test users
    """
    try:
        sandbox_service = HMRCSandboxService()
        test_users = sandbox_service.get_all_test_users()
        
        return jsonify({
            'success': True,
            'data': test_users,
            'count': len(test_users)
        })
    
    except Exception as e:
        logger.error(f'Error getting test users: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@sandbox_bp.route('/test-users/<int:user_id>', methods=['DELETE'])
@csrf.exempt
def delete_test_user(user_id):
    """
    Delete a test user record.
    
    WARNING: SANDBOX ONLY - Remove before production
    
    Args:
        user_id: ID of test user to delete
        
    Returns:
        Success status
    """
    try:
        sandbox_service = HMRCSandboxService()
        result = sandbox_service.delete_test_user(user_id)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f'Error deleting test user: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
