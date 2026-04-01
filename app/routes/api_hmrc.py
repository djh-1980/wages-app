"""
HMRC MTD API routes for authentication and submissions.
"""

import json
import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, request, redirect, session

from ..services.hmrc_auth import HMRCAuthService
from ..services.hmrc_client import HMRCClient
from ..services.hmrc_mapper import HMRCMapper
from ..database import get_db_connection, execute_query
from ..middleware import rate_limit

logger = logging.getLogger(__name__)

hmrc_bp = Blueprint('hmrc_api', __name__, url_prefix='/api/hmrc')

# Input validators for HMRC data
def validate_nino(nino):
    """Validate National Insurance number format."""
    pattern = r'^[A-Z]{2}[0-9]{6}[A-D]$'
    if not re.match(pattern, nino.upper()):
        raise ValueError("Invalid National Insurance number format")
    return nino.upper()

def validate_tax_year(tax_year):
    """Validate tax year format and consistency."""
    pattern = r'^\d{4}/\d{4}$'
    if not re.match(pattern, tax_year):
        raise ValueError("Tax year must be in YYYY/YYYY format")
    start, end = tax_year.split('/')
    if int(end) != int(start) + 1:
        raise ValueError("Tax year years must be consecutive")
    return tax_year


@hmrc_bp.route('/auth/start')
@rate_limit(max_requests=5, window_seconds=300)  # 5 requests per 5 minutes
def start_auth():
    """
    Start HMRC OAuth authorization flow.
    
    Returns:
        Redirect to HMRC authorization page
    """
    try:
        auth_service = HMRCAuthService()
        auth_url, state = auth_service.get_authorization_url()
        
        # Store state in session for CSRF protection
        session['hmrc_oauth_state'] = state
        
        return jsonify({
            'success': True,
            'auth_url': auth_url,
            'message': 'Redirect to HMRC for authorization'
        })
    except Exception as e:
        logger.error(f'Error starting HMRC auth: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/auth/callback')
def auth_callback():
    """
    Handle OAuth callback from HMRC.
    
    Query params:
        code: Authorization code
        state: State parameter for CSRF protection
    """
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify state parameter for CSRF protection
        stored_state = session.get('hmrc_oauth_state')
        if not stored_state or stored_state != state:
            return jsonify({
                'success': False, 
                'error': 'Invalid state parameter - possible CSRF attack'
            }), 400
        
        if not code:
            error = request.args.get('error', 'Unknown error')
            return jsonify({'success': False, 'error': f'Authorization failed: {error}'}), 400
        
        # Exchange code for tokens
        auth_service = HMRCAuthService()
        result = auth_service.exchange_code_for_token(code)
        
        # Clear state from session
        session.pop('hmrc_oauth_state', None)
        
        # Log result for debugging (do not log actual tokens)
        if result.get('success'):
            logger.info("HMRC token exchange completed successfully")
            # Redirect to settings page with success message
            return redirect('/settings/hmrc?auth=success')
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.warning(f"HMRC token exchange failed: {error_msg}")
            return redirect(f'/settings/hmrc?auth=error&message={error_msg}')
    
    except Exception as e:
        logger.error(f'Error in HMRC auth callback: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/auth/status')
def auth_status():
    """
    Get current authentication status.
    
    Returns:
        Connection status and details
    """
    try:
        auth_service = HMRCAuthService()
        status = auth_service.get_connection_status()
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        logger.error(f'Error getting HMRC auth status: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/auth/disconnect', methods=['POST'])
def disconnect():
    """
    Disconnect from HMRC (revoke credentials).
    
    Returns:
        Success status
    """
    try:
        auth_service = HMRCAuthService()
        success = auth_service.revoke_credentials()
        
        if success:
            return jsonify({
                'success': True,
                'data': {'message': 'Successfully disconnected from HMRC'}
            })
        else:
            logger.error('Failed to disconnect from HMRC')
            return jsonify({
                'success': False,
                'error': 'Failed to disconnect'
            }), 500
    except Exception as e:
        logger.error(f'Error disconnecting from HMRC: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/test-connection')
def test_connection():
    """
    Test connection to HMRC API.
    
    Returns:
        Connection test result
    """
    try:
        client = HMRCClient()
        result = client.test_connection()
        if result.get('success'):
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error testing HMRC connection: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/obligations')
def get_obligations():
    """
    Get quarterly obligations for self-employment.
    
    Query params:
        nino: National Insurance Number
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        status: 'O' for Open, 'F' for Fulfilled
    
    Returns:
        List of obligations
    """
    try:
        nino = request.args.get('nino')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        status = request.args.get('status')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.get_obligations(nino, from_date, to_date, status)
        
        if result['success']:
            # Store obligations in database
            obligations = result['data'].get('obligations', [])
            _store_obligations(obligations)
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting HMRC obligations: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/obligations/stored')
def get_stored_obligations():
    """
    Get stored obligations from database.
    
    Query params:
        tax_year: Filter by tax year (optional)
        status: Filter by status (optional)
    
    Returns:
        List of stored obligations
    """
    try:
        tax_year = request.args.get('tax_year')
        status = request.args.get('status')
        
        # Validate tax_year if provided
        if tax_year:
            try:
                tax_year = validate_tax_year(tax_year)
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        
        query = "SELECT * FROM hmrc_obligations WHERE 1=1"
        params = []
        
        if tax_year:
            query += " AND tax_year = ?"
            params.append(tax_year)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY due_date ASC"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            obligations = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'data': {
                'obligations': obligations,
                'count': len(obligations)
            }
        })
    except Exception as e:
        logger.error(f'Error getting stored obligations: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/period/preview')
def preview_period():
    """
    Preview period submission data without submitting.
    
    Query params:
        tax_year: Tax year (e.g., '2024/2025')
        period_id: Period ID (Q1, Q2, Q3, Q4)
    
    Returns:
        Formatted submission data
    """
    import traceback
    try:
        tax_year = request.args.get('tax_year')
        period_id = request.args.get('period_id')
        
        if not tax_year or not period_id:
            return jsonify({'success': False, 'error': 'tax_year and period_id are required'}), 400
        
        # Validate tax_year format
        try:
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        logger.info(f"Building submission for {tax_year} {period_id}")
        
        try:
            submission_data = HMRCMapper.build_period_submission(tax_year, period_id)
            logger.debug(f"Submission data built successfully: {type(submission_data)}")
        except Exception as mapper_error:
            logger.error(f"Mapper error: {mapper_error}")
            traceback.print_exc()
            # Return user-friendly error instead of 500
            return jsonify({
                'success': False, 
                'error': f'Failed to build submission: {str(mapper_error)}',
                'details': 'Check that you have expenses and income data for this period'
            }), 200  # Return 200 so JavaScript can handle it gracefully
        
        if not submission_data:
            logger.warning("No submission data returned")
            return jsonify({'success': False, 'error': 'Invalid period or no data available'}), 200
        
        logger.debug("Validating submission...")
        # Validate submission
        try:
            validation = HMRCMapper.validate_submission(submission_data)
            logger.debug(f"Validation complete: {validation}")
        except Exception as val_error:
            logger.error(f"Validation error: {val_error}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Validation failed: {str(val_error)}'
            }), 200
        
        logger.info("Submission validation successful")
        return jsonify({
            'success': True,
            'data': {
                'submission_data': submission_data,
                'validation': validation
            }
        })
    except Exception as e:
        logger.error(f"Submission build exception: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/period/submit', methods=['POST'])
def submit_period():
    """
    Submit period data to HMRC.
    
    Request body:
    {
        "nino": "AA123456A",
        "business_id": "XAIS12345678901",
        "tax_year": "2024/2025",
        "period_id": "Q1"
    }
    
    Returns:
        Submission result
    """
    try:
        data = request.get_json()
        
        required_fields = ['nino', 'business_id', 'tax_year', 'period_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate NINO and tax_year
        try:
            data['nino'] = validate_nino(data['nino'])
            data['tax_year'] = validate_tax_year(data['tax_year'])
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Check for duplicate submission unless force=true
        force = request.args.get('force', 'false').lower() == 'true'
        if not force:
            query = """
                SELECT id, status, hmrc_receipt_id 
                FROM hmrc_submissions 
                WHERE tax_year = ? AND period_id = ? AND status = 'submitted'
                LIMIT 1
            """
            existing = execute_query(query, (data['tax_year'], data['period_id']), fetch_one=True)
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'This period has already been submitted',
                    'existing_submission_id': existing['id'],
                    'hmrc_receipt_id': existing['hmrc_receipt_id']
                }), 409
        
        # Build submission data
        submission_data = HMRCMapper.build_period_submission(data['tax_year'], data['period_id'])
        
        if not submission_data:
            return jsonify({'success': False, 'error': 'Failed to build submission data'}), 400
        
        # Validate submission
        validation = HMRCMapper.validate_submission(submission_data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'validation_errors': validation['errors']
            }), 400
        
        # Submit to HMRC
        client = HMRCClient()
        result = client.create_period(data['nino'], data['business_id'], submission_data)
        
        # Store submission record
        _store_submission(data['tax_year'], data['period_id'], submission_data, result)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error submitting period to HMRC: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/businesses')
def get_businesses():
    """
    Get list of self-employment businesses from HMRC.
    
    Returns:
        List of businesses with their IDs
    """
    try:
        nino = request.args.get('nino')
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.get_business_list(nino)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting HMRC businesses: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/test-obligations')
def test_obligations():
    """
    Get obligations to find business IDs.
    Obligations response includes business IDs.
    """
    try:
        nino = request.args.get('nino')
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Try to get obligations - this will show business IDs if they exist
        client = HMRCClient()
        result = client.get_obligations(nino)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error testing HMRC obligations: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/create-test-business', methods=['POST'])
def create_test_business():
    """
    Create a test self-employment business for sandbox testing.
    Uses HMRC Self Assessment Test Support API.
    """
    try:
        data = request.get_json()
        nino = data.get('nino')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.create_test_business(nino)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error creating test business: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/submissions')
def get_submissions():
    """
    Get submission history from database.
    
    Query params:
        tax_year: Filter by tax year (optional)
        status: Filter by status (optional)
    
    Returns:
        List of submissions
    """
    try:
        tax_year = request.args.get('tax_year')
        status = request.args.get('status')
        
        # Validate tax_year if provided
        if tax_year:
            try:
                tax_year = validate_tax_year(tax_year)
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        
        query = "SELECT * FROM hmrc_submissions WHERE 1=1"
        params = []
        
        if tax_year:
            query += " AND tax_year = ?"
            params.append(tax_year)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            submissions = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON fields
        for submission in submissions:
            if submission.get('submission_data'):
                submission['submission_data'] = json.loads(submission['submission_data'])
            if submission.get('response_data'):
                submission['response_data'] = json.loads(submission['response_data'])
        
        return jsonify({
            'success': True,
            'data': {
                'submissions': submissions,
                'count': len(submissions)
            }
        })
    except Exception as e:
        logger.error(f'Error getting submissions: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


def _store_obligations(obligations):
    """Store or update obligations in database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for obligation in obligations:
            for period in obligation.get('obligationDetails', []):
                cursor.execute("""
                    INSERT OR REPLACE INTO hmrc_obligations 
                    (period_id, tax_year, start_date, end_date, due_date, status, received_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    period.get('periodKey'),
                    obligation.get('typeOfBusiness'),
                    period.get('inboundCorrespondenceFromDate'),
                    period.get('inboundCorrespondenceToDate'),
                    period.get('inboundCorrespondenceDueDate'),
                    period.get('status'),
                    period.get('inboundCorrespondenceDateReceived')
                ))
        
        conn.commit()


def _store_submission(tax_year, period_id, submission_data, result):
    """Store submission record in database."""
    status = 'submitted' if result.get('success') else 'failed'
    receipt_id = result.get('data', {}).get('id') if result.get('success') else None
    error_message = result.get('error') if not result.get('success') else None
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hmrc_submissions 
            (tax_year, period_id, submission_date, status, hmrc_receipt_id, 
             submission_data, response_data, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tax_year,
            period_id,
            datetime.now().isoformat(),
            status,
            receipt_id,
            json.dumps(submission_data),
            json.dumps(result.get('data', {})),
            error_message
        ))
        conn.commit()


@hmrc_bp.route('/final-declaration/status')
def final_declaration_status():
    """
    Check final declaration status for a tax year.
    
    Query params:
        tax_year: Tax year (e.g., '2024/2025')
    
    Returns:
        Status of quarterly submissions and final declaration
    """
    try:
        tax_year = request.args.get('tax_year')
        
        if not tax_year:
            return jsonify({'success': False, 'error': 'tax_year is required'}), 400
        
        try:
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT period_id, status, hmrc_receipt_id, submission_date
                FROM hmrc_submissions
                WHERE tax_year = ? AND period_id IN ('Q1', 'Q2', 'Q3', 'Q4')
                AND status = 'submitted'
                ORDER BY period_id
            """, (tax_year,))
            
            quarters = [dict(row) for row in cursor.fetchall()]
            quarters_submitted = [q['period_id'] for q in quarters]
            all_submitted = len(quarters_submitted) == 4
            
            cursor.execute("""
                SELECT id, calculation_id, estimated_tax, status, hmrc_receipt_id, submitted_at
                FROM hmrc_final_declarations
                WHERE tax_year = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (tax_year,))
            
            declaration = cursor.fetchone()
            declaration_data = dict(declaration) if declaration else None
        
        return jsonify({
            'success': True,
            'data': {
                'tax_year': tax_year,
                'quarters_submitted': quarters_submitted,
                'all_submitted': all_submitted,
                'quarters_detail': quarters,
                'calculation_id': declaration_data.get('calculation_id') if declaration_data else None,
                'declaration_status': declaration_data.get('status') if declaration_data else 'not_started',
                'declaration': declaration_data
            }
        })
    except Exception as e:
        logger.error(f'Error getting final declaration status: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/final-declaration/calculate', methods=['POST'])
def calculate_final_declaration():
    """
    Trigger crystallisation (tax calculation) for a tax year.
    
    Query params:
        tax_year: Tax year (e.g., '2024/2025')
    
    Returns:
        Calculation ID and estimated tax
    """
    try:
        tax_year = request.args.get('tax_year')
        
        if not tax_year:
            return jsonify({'success': False, 'error': 'tax_year is required'}), 400
        
        try:
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM hmrc_submissions
                WHERE tax_year = ? AND period_id IN ('Q1', 'Q2', 'Q3', 'Q4')
                AND status = 'submitted'
            """, (tax_year,))
            
            result = cursor.fetchone()
            if result['count'] < 4:
                return jsonify({
                    'success': False,
                    'error': f'All 4 quarters must be submitted before calculating. Only {result["count"]} submitted.'
                }), 400
        
        query = "SELECT nino FROM hmrc_credentials WHERE is_active = 1 LIMIT 1"
        creds = execute_query(query, fetch_one=True)
        
        if not creds or not creds.get('nino'):
            return jsonify({'success': False, 'error': 'NINO not found in credentials'}), 400
        
        nino = creds['nino']
        
        client = HMRCClient()
        result = client.trigger_crystallisation(nino, tax_year)
        
        if not result.get('success'):
            return jsonify(result)
        
        calculation_id = result.get('data', {}).get('calculationId') or result.get('data', {}).get('id')
        estimated_tax = result.get('data', {}).get('totalIncomeTaxAndNicsDue', 0.0)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hmrc_final_declarations 
                (tax_year, calculation_id, estimated_tax, status)
                VALUES (?, ?, ?, 'calculated')
            """, (tax_year, calculation_id, estimated_tax))
            conn.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'calculation_id': calculation_id,
                'estimated_tax': estimated_tax,
                'message': 'Tax calculation completed successfully'
            }
        })
    except Exception as e:
        logger.error(f'Error calculating final declaration: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/final-declaration/submit', methods=['POST'])
def submit_final_declaration():
    """
    Submit final declaration to HMRC.
    
    Request body:
    {
        "tax_year": "2024/2025",
        "calculation_id": "...",
        "confirmed": true
    }
    
    Returns:
        Submission result with receipt
    """
    try:
        data = request.get_json()
        
        tax_year = data.get('tax_year')
        calculation_id = data.get('calculation_id')
        confirmed = data.get('confirmed', False)
        
        if not tax_year or not calculation_id:
            return jsonify({'success': False, 'error': 'tax_year and calculation_id are required'}), 400
        
        if not confirmed:
            return jsonify({'success': False, 'error': 'You must confirm the declaration is correct'}), 400
        
        try:
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM hmrc_final_declarations
                WHERE tax_year = ? AND calculation_id = ?
            """, (tax_year, calculation_id))
            
            existing = cursor.fetchone()
            if existing and existing['status'] == 'submitted':
                return jsonify({
                    'success': False,
                    'error': 'Final declaration already submitted for this tax year'
                }), 409
        
        query = "SELECT nino FROM hmrc_credentials WHERE is_active = 1 LIMIT 1"
        creds = execute_query(query, fetch_one=True)
        
        if not creds or not creds.get('nino'):
            return jsonify({'success': False, 'error': 'NINO not found in credentials'}), 400
        
        nino = creds['nino']
        
        client = HMRCClient()
        result = client.submit_final_declaration(nino, tax_year, calculation_id)
        
        if not result.get('success'):
            return jsonify(result)
        
        receipt_id = result.get('data', {}).get('id') or result.get('data', {}).get('receiptId')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE hmrc_final_declarations
                SET status = 'submitted',
                    hmrc_receipt_id = ?,
                    submitted_at = ?
                WHERE tax_year = ? AND calculation_id = ?
            """, (receipt_id, datetime.now().isoformat(), tax_year, calculation_id))
            conn.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'receipt_id': receipt_id,
                'message': 'Final declaration submitted successfully',
                'submitted_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f'Error submitting final declaration: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
