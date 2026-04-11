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


@sandbox_bp.route('/generate-test-expenses', methods=['POST'])
@csrf.exempt
def generate_test_expenses():
    """
    Generate test expenses for MTD sandbox testing.
    
    Creates sample expenses across all 4 quarters of tax year 2024/2025
    for testing quarterly submissions.
    
    WARNING: SANDBOX ONLY - Remove before production
    
    Returns:
        Success status with count of generated expenses
    """
    try:
        from ..database import get_db_connection
        
        # Test expenses data for 2024/2025 tax year
        # Category IDs: 1=Vehicle Costs (hmrc_box='Vehicle costs'), 6=Admin Costs (hmrc_box='Admin costs')
        test_expenses = [
            # Q1 (06 Apr 2024 - 05 Jul 2024)
            ('15/04/2024', 1, 'TEST - Test fuel expense Q1', 250.00, '2024/2025'),  # Vehicle Costs → travelCosts
            ('01/05/2024', 6, 'TEST - Test office supplies Q1', 45.00, '2024/2025'),  # Admin Costs → adminCosts
            ('20/06/2024', 1, 'TEST - Test van repair Q1', 180.00, '2024/2025'),  # Vehicle Costs → travelCosts
            
            # Q2 (06 Jul 2024 - 05 Oct 2024)
            ('10/07/2024', 1, 'TEST - Test fuel expense Q2', 220.00, '2024/2025'),  # Vehicle Costs → travelCosts
            ('01/08/2024', 6, 'TEST - Test software subscription Q2', 60.00, '2024/2025'),  # Admin Costs → adminCosts
            ('15/09/2024', 1, 'TEST - Test parking Q2', 95.00, '2024/2025'),  # Vehicle Costs → travelCosts
            
            # Q3 (06 Oct 2024 - 05 Jan 2025)
            ('12/10/2024', 1, 'TEST - Test fuel expense Q3', 310.00, '2024/2025'),  # Vehicle Costs → travelCosts
            ('05/11/2024', 6, 'TEST - Test equipment Q3', 120.00, '2024/2025'),  # Admin Costs → adminCosts
            ('20/12/2024', 1, 'TEST - Test toll charges Q3', 75.00, '2024/2025'),  # Vehicle Costs → travelCosts
            
            # Q4 (06 Jan 2025 - 05 Apr 2025)
            ('15/01/2025', 1, 'TEST - Test fuel expense Q4', 290.00, '2024/2025'),  # Vehicle Costs → travelCosts
            ('10/02/2025', 6, 'TEST - Test stationery Q4', 85.00, '2024/2025'),  # Admin Costs → adminCosts
            ('20/03/2025', 1, 'TEST - Test van service Q4', 150.00, '2024/2025'),  # Vehicle Costs → travelCosts
        ]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if test expenses already exist
            cursor.execute("""
                SELECT COUNT(*) as count FROM expenses 
                WHERE description LIKE 'TEST - %'
            """)
            existing_count = cursor.fetchone()['count']
            
            if existing_count > 0:
                return jsonify({
                    'success': False,
                    'error': f'{existing_count} test expenses already exist. Delete them first before generating new ones.'
                }), 400
            
            # Insert test expenses
            for date, category_id, description, amount, tax_year in test_expenses:
                cursor.execute("""
                    INSERT INTO expenses (date, category_id, description, amount, tax_year)
                    VALUES (?, ?, ?, ?, ?)
                """, (date, category_id, description, amount, tax_year))
            
            conn.commit()
            logger.info(f'Generated {len(test_expenses)} test expenses for sandbox testing')
        
        return jsonify({
            'success': True,
            'message': f'Successfully generated {len(test_expenses)} test expenses',
            'count': len(test_expenses)
        })
    
    except Exception as e:
        logger.error(f'Error generating test expenses: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@sandbox_bp.route('/delete-test-expenses', methods=['POST'])
@csrf.exempt
def delete_test_expenses():
    """
    Delete all test expenses (those with description starting with "TEST - ").
    
    WARNING: SANDBOX ONLY - Remove before production
    
    Returns:
        Success status with count of deleted expenses
    """
    try:
        from ..database import get_db_connection
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count test expenses before deletion
            cursor.execute("""
                SELECT COUNT(*) as count FROM expenses 
                WHERE description LIKE 'TEST - %'
            """)
            count = cursor.fetchone()['count']
            
            if count == 0:
                return jsonify({
                    'success': False,
                    'error': 'No test expenses found to delete'
                }), 400
            
            # Delete test expenses
            cursor.execute("""
                DELETE FROM expenses 
                WHERE description LIKE 'TEST - %'
            """)
            
            conn.commit()
            logger.info(f'Deleted {count} test expenses from sandbox')
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {count} test expenses',
            'count': count
        })
    
    except Exception as e:
        logger.error(f'Error deleting test expenses: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@sandbox_bp.route('/debug-token')
def debug_token():
    """
    Get current HMRC access token for debugging API calls.
    
    WARNING: SANDBOX ONLY - This exposes the access token for curl testing.
    Never use this in production!
    
    Returns:
        JSON with access token and expiry info
    """
    try:
        auth_service = HMRCAuthService()
        
        # Get stored credentials (includes access token, expiry, etc.)
        credentials = auth_service.get_stored_credentials()
        
        if not credentials:
            return jsonify({
                'success': False,
                'error': 'No valid credentials available. Please authenticate with HMRC first.'
            }), 401
        
        # Get a valid access token (will refresh if needed)
        access_token = auth_service.get_valid_access_token()
        
        if not access_token:
            return jsonify({
                'success': False,
                'error': 'Could not get valid access token. Token may have expired.'
            }), 401
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'expires_at': credentials['expires_at'],
            'environment': credentials['environment'],
            'scope': credentials['scope'],
            'warning': 'SANDBOX ONLY - Never expose tokens in production!'
        })
    
    except Exception as e:
        logger.error(f'Error getting debug token: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
