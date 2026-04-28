"""
HMRC MTD API routes for authentication and submissions.
"""

import json
import logging
import re
from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, current_app, jsonify, request, redirect, session

from ..services.hmrc_auth import HMRCAuthService
from ..services.hmrc_client import HMRCClient
from ..services.hmrc_mapper import HMRCMapper
from ..services.hmrc_fraud_headers import record_browser_context
from ..database import get_db_connection, execute_query
from .. import limiter

logger = logging.getLogger(__name__)

hmrc_bp = Blueprint('hmrc_api', __name__, url_prefix='/api/hmrc')


def require_property_enabled(view):
    """Return 404 unless the HMRC_PROPERTY_ENABLED feature flag is on.

    UK / foreign property income is intentionally out of scope for the current
    HMRC Software Approvals submission. The route stays in the codebase so it
    can be reactivated later, but is invisible (404) by default to keep the
    application's observable behaviour aligned with what we declared to HMRC.
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_app.config.get('HMRC_PROPERTY_ENABLED', False):
            abort(404)
        return view(*args, **kwargs)
    return wrapper

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


@hmrc_bp.route('/fraud-headers/record', methods=['POST'])
@limiter.limit("120 per hour", override_defaults=True)
def fraud_headers_record():
    """
    Capture browser-supplied fraud-prevention context for HMRC API calls.

    Called by static/js/hmrc-fraud-headers.js on page load of any HMRC-related
    screen. The captured values are stored in the Flask session and replayed
    on every HMRC API call made during that session.
    """
    try:
        data = request.get_json(silent=True) or {}
        record_browser_context(data)
        return jsonify({'success': True})
    except Exception as e:  # noqa: BLE001
        logger.error(f'Error recording HMRC fraud headers context: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/auth/start')
@limiter.limit("20 per hour", override_defaults=True)
def start_auth():
    """
    Start HMRC OAuth authorization flow.
    
    Returns:
        JSON response with auth_url for client-side redirect
    """
    logger.debug("auth/start called")
    try:
        from flask_login import current_user
        
        auth_service = HMRCAuthService()
        auth_url, state = auth_service.get_authorization_url()
        
        # Store state in session for CSRF protection
        session['hmrc_oauth_state'] = state
        
        # Store user ID before OAuth redirect to restore session after callback
        if current_user.is_authenticated:
            session['pre_oauth_user_id'] = current_user.id
            session.permanent = True
            session.modified = True
            logger.debug(f"Stored user ID {current_user.id} in session before OAuth redirect")
        
        logger.debug(f"Generated auth_url: {auth_url[:100]}...")
        
        return jsonify({
            'success': True,
            'auth_url': auth_url,
            'message': 'Redirect to HMRC for authorization'
        })
    except Exception as e:
        logger.error(f'auth/start error: {e}', exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e), 
            'type': type(e).__name__
        }), 500


@hmrc_bp.route('/auth/callback')
@limiter.limit("20 per hour", override_defaults=True)
def auth_callback():
    """
    Handle OAuth callback from HMRC.
    Restores user session if lost during external OAuth redirect.
    
    Query params:
        code: Authorization code
        state: State parameter for CSRF protection
    """
    try:
        from flask_login import current_user, login_user
        from flask import url_for
        
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify state parameter for CSRF protection
        stored_state = session.get('hmrc_oauth_state')
        if not stored_state or stored_state != state:
            logger.error("CSRF state mismatch in OAuth callback")
            return redirect(url_for('main.settings_hmrc', auth='error', message='Invalid state parameter'))
        
        if not code:
            error = request.args.get('error', 'Unknown error')
            logger.error(f"OAuth callback missing code: {error}")
            return redirect(url_for('main.settings_hmrc', auth='error', message=f'Authorization failed: {error}'))
        
        # Restore user session if lost during OAuth redirect
        if not current_user.is_authenticated:
            user_id = session.get('pre_oauth_user_id')
            if user_id:
                logger.debug(f"Restoring user session for user ID {user_id}")
                try:
                    # Import User model
                    from ..models.user import User
                    user = User.query.get(user_id)
                    if user:
                        login_user(user, remember=True)
                        logger.info(f"Successfully restored session for user {user.username}")
                    else:
                        logger.warning(f"Could not find user with ID {user_id}")
                except Exception as e:
                    logger.error(f"Error restoring user session: {e}")
            else:
                logger.warning("User not authenticated and no pre_oauth_user_id in session")
        
        # Exchange code for tokens
        auth_service = HMRCAuthService()
        result = auth_service.exchange_code_for_token(code)
        
        # Clear OAuth state from session
        session.pop('hmrc_oauth_state', None)
        session.pop('pre_oauth_user_id', None)
        
        # Log result for debugging (do not log actual tokens)
        if result.get('success'):
            logger.info("HMRC token exchange completed successfully")
            # Redirect to settings page with success message
            return redirect(url_for('main.settings_hmrc', auth='success'))
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.warning(f"HMRC token exchange failed: {error_msg}")
            return redirect(url_for('main.settings_hmrc', auth='error', message=error_msg))
    
    except Exception as e:
        logger.error(f'Error in HMRC auth callback: {e}', exc_info=True)
        return redirect(url_for('main.settings_hmrc', auth='error', message='Callback error'))


@hmrc_bp.route('/auth/status')
@limiter.limit("20 per hour", override_defaults=True)
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


@hmrc_bp.route('/auth/disconnect', methods=['GET', 'POST'])
@limiter.limit("20 per hour", override_defaults=True)
def disconnect():
    """
    Disconnect from HMRC (revoke credentials).
    Always succeeds locally even if HMRC revocation fails.
    
    Returns:
        Success status (always returns success)
    """
    try:
        auth_service = HMRCAuthService()
        
        # Always deactivate local token - this must succeed
        try:
            auth_service.revoke_credentials()
            logger.info("Local HMRC credentials deactivated successfully")
        except Exception as e:
            logger.warning(f"Failed to deactivate local credentials (continuing anyway): {e}")
        
        # Try to revoke with HMRC but ignore any errors
        # (user is disconnected locally regardless of HMRC response)
        try:
            # Note: HMRC doesn't provide a token revocation endpoint in sandbox
            # So we just deactivate locally
            logger.debug("HMRC token revocation not attempted (not supported in sandbox)")
        except Exception as e:
            logger.debug(f"HMRC revocation skipped: {e}")
        
        # Always return success - user is disconnected locally
        return jsonify({
            'success': True,
            'message': 'Disconnected from HMRC'
        })
        
    except Exception as e:
        # Even if everything fails, still return success
        # The worst case is the token stays in DB but user can reconnect
        logger.error(f'Error in disconnect flow (returning success anyway): {e}', exc_info=True)
        return jsonify({
            'success': True,
            'message': 'Disconnected from HMRC'
        })


@hmrc_bp.route('/test-connection')
@limiter.limit("20 per hour", override_defaults=True)
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
@limiter.limit("20 per hour", override_defaults=True)
def get_obligations():
    """
    Get quarterly obligations for self-employment.
    
    Query params:
        nino: National Insurance Number
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        status: 'O' for Open, 'F' for Fulfilled
        test_scenario: Optional Gov-Test-Scenario for sandbox testing
    
    Returns:
        List of obligations
    """
    try:
        nino = request.args.get('nino')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        status = request.args.get('status')
        test_scenario = request.args.get('test_scenario')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.get_obligations(nino, from_date, to_date, status, test_scenario)
        
        # Fall back to mock data if 404 in sandbox mode
        if not result.get('success'):
            from flask import current_app
            status_code = result.get('status_code')
            error_details = result.get('details', {})
            error_code = error_details.get('code', '')
            
            if (status_code == 404 and 
                error_code == 'MATCHING_RESOURCE_NOT_FOUND' and 
                current_app.config.get('HMRC_ENVIRONMENT') == 'sandbox'):
                logger.info('Using mock obligations data for sandbox testing')
                result = client.get_mock_obligations()
        
        if result['success']:
            # Store obligations in database
            obligations = result['data'].get('obligations', [])
            logger.info(f'Attempting to store {len(obligations)} obligation(s) from result')
            try:
                _store_obligations(obligations)
                logger.info('Obligations stored successfully')
            except Exception as store_error:
                logger.error(f'Error storing obligations: {store_error}', exc_info=True)
                return jsonify({'success': False, 'error': f'Failed to store obligations: {str(store_error)}'}), 500
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting HMRC obligations: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/obligations/stored')
@limiter.limit("20 per hour", override_defaults=True)
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
@limiter.limit("20 per hour", override_defaults=True)
def preview_period():
    """
    Preview period submission data without submitting.
    
    Query params:
        tax_year: Tax year (e.g., '2024/2025')
        period_id: Period ID (Q1, Q2, Q3, Q4)
        from_date: Optional start date (YYYY-MM-DD)
        to_date: Optional end date (YYYY-MM-DD)
    
    Returns:
        Formatted submission data
    """
    import traceback
    try:
        tax_year = request.args.get('tax_year')
        period_id = request.args.get('period_id')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        if not tax_year or not period_id:
            return jsonify({'success': False, 'error': 'tax_year and period_id are required'}), 400
        
        # Validate tax_year format
        try:
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        logger.info(f"Building submission preview for {tax_year} {period_id} (from: {from_date}, to: {to_date})")
        
        try:
            submission_data = HMRCMapper.build_period_submission(
                tax_year, 
                period_id,
                from_date=from_date,
                to_date=to_date
            )
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
@limiter.limit("20 per hour", override_defaults=True)
def submit_period():
    """
    Submit period data to HMRC.
    
    Request body:
    {
        "nino": "AA123456A",
        "business_id": "XAIS12345678901",
        "tax_year": "2024/2025",
        "period_id": "Q1",
        "from_date": "2024-04-06" (optional),
        "to_date": "2024-07-05" (optional)
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
        # Only block if the SAME NINO submitted this period (allows new test users to re-submit)
        force = request.args.get('force', 'false').lower() == 'true'
        if not force:
            query = """
                SELECT id, status, hmrc_receipt_id, nino
                FROM hmrc_submissions 
                WHERE tax_year = ? AND period_id = ? AND nino = ? AND status = 'submitted'
                LIMIT 1
            """
            existing = execute_query(query, (data['tax_year'], data['period_id'], data['nino']), fetch_one=True)
            if existing:
                return jsonify({
                    'success': False,
                    'error': f'This period has already been submitted for NINO {data["nino"]}',
                    'existing_submission_id': existing['id'],
                    'hmrc_receipt_id': existing['hmrc_receipt_id']
                }), 409
        
        # Build submission data with optional date override
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        submission_data = HMRCMapper.build_period_submission(
            data['tax_year'], 
            data['period_id'],
            from_date=from_date,
            to_date=to_date
        )
        
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
        result = client.create_period(data['nino'], data['business_id'], data['tax_year'], submission_data)
        
        # Check if this is a duplicate submission (already submitted successfully)
        if not result.get('success') and 'error' in result:
            error_msg = result.get('error', '')
            # HMRC returns RULE_DUPLICATE_SUBMISSION if period already submitted
            if 'RULE_DUPLICATE_SUBMISSION' in error_msg or 'duplicate' in error_msg.lower():
                # Treat as success - period was already submitted
                logger.info(f'Period {data["period_id"]} for {data["tax_year"]} already submitted to HMRC')
                
                # Store/update submission record as submitted
                _store_submission(data['tax_year'], data['period_id'], submission_data, {
                    'success': True,
                    'message': 'Already submitted',
                    'data': {}
                }, nino=data['nino'], from_date=from_date, to_date=to_date)
                
                return jsonify({
                    'success': True,
                    'message': 'This period has already been submitted to HMRC.',
                    'already_submitted': True
                })
        
        # Store submission record for new submissions
        _store_submission(data['tax_year'], data['period_id'], submission_data, result,
                          nino=data['nino'], from_date=from_date, to_date=to_date)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error submitting period to HMRC: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/period/cumulative/<tax_year>', methods=['POST'])
@limiter.limit("20 per hour", override_defaults=True)
def submit_cumulative_period(tax_year):
    """
    Submit a cumulative period summary to HMRC (Self-Employment Business v5.0).

    Replaces the legacy POST /period flow. The submitted figures must be
    running totals from 6 April of the tax year up to the period end.

    URL:
        POST /api/hmrc/period/cumulative/<tax_year>
        ``tax_year`` accepts 'YYYY-YY' or 'YYYY/YYYY'.

    Request JSON:
        {
            'nino': 'AA123456A',
            'business_id': 'XAIS12345678901',
            'period_id': 'Q1' | 'Q2' | 'Q3' | 'Q4'        # optional
            'period_end_date': 'YYYY-MM-DD'               # optional
        }
        Exactly one of ``period_id`` / ``period_end_date`` must be provided.

    Returns:
        200 on success with calculation reference and submission row id.
        400 / 401 / 409 / 5xx on the obvious failure modes.
    """
    from ..services.hmrc_cumulative_calculator import (
        calculate_cumulative_totals,
        strip_meta,
    )

    try:
        # Auth guard - delegate to the connected-to-HMRC check, not just
        # local Flask-Login. Both must pass.
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Login required'}), 401

        is_preview = request.args.get('preview', 'false').lower() in ('1', 'true', 'yes')

        # Preview mode skips the HMRC connection requirement: it never
        # talks to HMRC and never writes a row, so a connected OAuth
        # session is not required to compute the running totals.
        if not is_preview:
            auth_status = HMRCAuthService().get_connection_status()
            if not auth_status.get('connected'):
                return jsonify({
                    'success': False,
                    'error': 'Not connected to HMRC. Please connect first.',
                }), 400

        data = request.get_json(silent=True) or {}

        # Preview only needs a window argument; submission additionally
        # needs nino + business_id.
        if not is_preview:
            for required in ('nino', 'business_id'):
                if not data.get(required):
                    return jsonify({
                        'success': False,
                        'error': f'Missing required field: {required}',
                    }), 400

        period_id = data.get('period_id')
        period_end_date = data.get('period_end_date')
        if (period_id is None) == (period_end_date is None):
            return jsonify({
                'success': False,
                'error': 'Provide exactly one of period_id or period_end_date',
            }), 400

        # Build the cumulative payload. ValueError -> 400 (malformed input).
        try:
            payload = calculate_cumulative_totals(
                tax_year,
                period_end_date=period_end_date,
                period_id=period_id,
            )
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        # Preview short-circuit: return the calculated totals and the
        # per-quarter breakdown without contacting HMRC and without
        # writing anything to hmrc_submissions. The response shape
        # matches a successful submission (sans submission_id) so the
        # UI can render the same panel.
        if is_preview:
            return jsonify({
                'success': True,
                'preview': True,
                'data': {
                    'submission_data': strip_meta(payload),
                },
                'period_dates': payload['periodDates'],
                'breakdown': payload['meta'].get('breakdown_by_quarter', []),
            })

        period_dates = payload['periodDates']
        from_date = period_dates['periodStartDate']
        to_date = period_dates['periodEndDate']
        effective_period_id = (
            payload['meta'].get('period_id')
            or f"cumulative:{to_date}"
        )

        # Duplicate detection: same NINO + tax_year + cumulative end date
        # already submitted successfully? Caller may force=true to override.
        force = request.args.get('force', 'false').lower() == 'true'
        if not force:
            existing = execute_query(
                """
                SELECT id, hmrc_receipt_id
                  FROM hmrc_submissions
                 WHERE submission_type = 'cumulative'
                   AND status = 'submitted'
                   AND tax_year = ?
                   AND nino = ?
                   AND period_end_date = ?
                 LIMIT 1
                """,
                (tax_year, data['nino'], to_date),
                fetch_one=True,
            )
            if existing:
                return jsonify({
                    'success': False,
                    'error': (
                        f'A cumulative submission for {tax_year} ending '
                        f'{to_date} already exists for this NINO.'
                    ),
                    'existing_submission_id': existing['id'],
                    'hmrc_receipt_id': existing['hmrc_receipt_id'],
                }), 409

        # Strip the internal meta block before sending to HMRC.
        outbound = strip_meta(payload)

        client = HMRCClient()
        result = client.submit_cumulative_period(
            data['nino'], data['business_id'], tax_year, outbound,
        )

        submission_row_id = _store_submission(
            tax_year,
            effective_period_id,
            outbound,
            result,
            nino=data['nino'],
            from_date=from_date,
            to_date=to_date,
            submission_type='cumulative',
        )

        if result.get('success'):
            return jsonify({
                'success': True,
                'data': result.get('data', {}),
                'submission_id': submission_row_id,
                'period_dates': period_dates,
                'breakdown': payload['meta'].get('breakdown_by_quarter', []),
            })

        # Surface HMRC error details to the caller, but keep our row stored.
        status_code = result.get('status_code') or 502
        return jsonify({
            'success': False,
            'error': result.get('error', 'HMRC submission failed'),
            'submission_id': submission_row_id,
            'details': result.get('details'),
            'validation_errors': result.get('validation_errors'),
        }), status_code

    except Exception as e:  # noqa: BLE001
        logger.error(f'Error submitting cumulative period: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/period/cumulative/<tax_year>', methods=['GET'])
@limiter.limit("60 per hour", override_defaults=True)
def get_cumulative_period(tax_year):
    """
    Return the latest stored cumulative submission for the given tax year.

    Looks up ``hmrc_submissions`` where ``submission_type='cumulative'``
    and ``status='submitted'``, ordered by submission_date DESC.

    Returns:
        200 with the latest cumulative row, or
        401 if not logged in,
        404 if no cumulative submission exists yet for the tax year.
    """
    try:
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Login required'}), 401

        row = execute_query(
            """
            SELECT id, tax_year, period_id, status, hmrc_receipt_id,
                   submission_data, response_data, submission_date, nino,
                   period_start_date, period_end_date, submission_type
              FROM hmrc_submissions
             WHERE submission_type = 'cumulative'
               AND status = 'submitted'
               AND tax_year = ?
             ORDER BY submission_date DESC
             LIMIT 1
            """,
            (tax_year,),
            fetch_one=True,
        )

        if not row:
            return jsonify({
                'success': False,
                'error': f'No cumulative submission found for {tax_year}',
            }), 404

        record = dict(row)
        # Re-hydrate the JSON blobs for convenience.
        for blob_key in ('submission_data', 'response_data'):
            blob = record.get(blob_key)
            if isinstance(blob, str) and blob:
                try:
                    record[blob_key] = json.loads(blob)
                except json.JSONDecodeError:
                    pass

        return jsonify({'success': True, 'data': record})

    except Exception as e:  # noqa: BLE001
        logger.error(f'Error fetching cumulative period: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/businesses')
@limiter.limit("20 per hour", override_defaults=True)
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
        
        # Try new Business Details API endpoint first (recommended for MTD ITSA)
        result = client.get_business_details(nino)
        
        # If that fails, fall back to Business Income Source Summary API
        if not result.get('success'):
            logger.info(f'Business Details API failed, trying Business Income Source Summary API')
            result = client.get_business_list(nino)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting HMRC businesses: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/test-obligations')
@limiter.limit("20 per hour", override_defaults=True)
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
@limiter.limit("20 per hour", override_defaults=True)
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
@limiter.limit("20 per hour", override_defaults=True)
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
    """Store or update I&E obligations in database."""
    logger.info(f'_store_obligations called with {len(obligations)} obligation(s)')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        stored_count = 0
        
        for obligation in obligations:
            obligation_details = obligation.get('obligationDetails', [])
            logger.info(f'Processing obligation with {len(obligation_details)} period(s)')
            
            for period in obligation_details:
                # Calculate tax year from start date (tax year starts April 6)
                start_date = period.get('inboundCorrespondenceFromDate')
                tax_year = None
                if start_date:
                    from datetime import datetime
                    date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    # Tax year starts April 6 - if date is April 6 or later, it's current year/next year
                    if date_obj.month > 4 or (date_obj.month == 4 and date_obj.day >= 6):
                        tax_year = f"{date_obj.year}/{date_obj.year + 1}"
                    else:
                        tax_year = f"{date_obj.year - 1}/{date_obj.year}"
                
                logger.info(f'Storing obligation: {period.get("periodKey")} - {tax_year} - {period.get("status")}')
                
                cursor.execute("""
                    INSERT OR REPLACE INTO hmrc_obligations 
                    (period_id, tax_year, start_date, end_date, due_date, status, received_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    period.get('periodKey'),
                    tax_year,
                    period.get('inboundCorrespondenceFromDate'),
                    period.get('inboundCorrespondenceToDate'),
                    period.get('inboundCorrespondenceDueDate'),
                    period.get('status'),
                    period.get('inboundCorrespondenceDateReceived')
                ))
                stored_count += 1
        
        conn.commit()
        logger.info(f'Successfully stored {stored_count} obligation(s) to database')


def _store_final_declaration_obligations(obligations):
    """Store or update final declaration (crystallisation) obligations in database."""
    logger.info(f'_store_final_declaration_obligations called with {len(obligations)} obligation(s)')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        stored_count = 0
        
        for obligation in obligations:
            obligation_details = obligation.get('obligationDetails', [])
            logger.info(f'Processing final declaration obligation with {len(obligation_details)} period(s)')
            
            for period in obligation_details:
                # Calculate tax year from start date
                start_date = period.get('inboundCorrespondenceFromDate')
                tax_year = None
                if start_date:
                    from datetime import datetime
                    date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    if date_obj.month > 4 or (date_obj.month == 4 and date_obj.day >= 6):
                        tax_year = f"{date_obj.year}/{date_obj.year + 1}"
                    else:
                        tax_year = f"{date_obj.year - 1}/{date_obj.year}"
                
                logger.info(f'Storing final declaration obligation: crystallisation - {tax_year} - {period.get("status")}')
                
                # Store with period_id='crystallisation' to distinguish from quarterly obligations
                cursor.execute("""
                    INSERT OR REPLACE INTO hmrc_obligations 
                    (period_id, tax_year, start_date, end_date, due_date, status, received_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    'crystallisation',
                    tax_year,
                    period.get('inboundCorrespondenceFromDate'),
                    period.get('inboundCorrespondenceToDate'),
                    period.get('inboundCorrespondenceDueDate'),
                    period.get('status'),
                    period.get('inboundCorrespondenceDateReceived')
                ))
                stored_count += 1
        
        conn.commit()
        logger.info(f'Successfully stored {stored_count} final declaration obligation(s) to database')


def _update_business_period_type(business_id, period_type):
    """Update quarterly period type for a business in local database."""
    # This is a placeholder - implement if you have a businesses table
    # For now, just log the update
    logger.info(f'Business {business_id} quarterly period type set to: {period_type}')
    # TODO: Implement database update when businesses table is created
    pass


def _get_sandbox_nino():
    """Get NINO from the active sandbox test user, if one exists."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nino, business_id FROM sandbox_test_users
                WHERE is_active = 1
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.warning(f'Could not look up sandbox test user: {e}')
    return None


def _store_submission(tax_year, period_id, submission_data, result, nino=None,
                      from_date=None, to_date=None, submission_type='period'):
    """Store submission record in database.

    If the submission succeeded and from_date/to_date were supplied (or can
    be inferred from submission_data), the record is locked via
    hmrc_lock.lock_submission so that covered expenses cannot be silently
    edited afterwards (MTD digital-records compliance).

    Args:
        submission_type: 'period' (legacy per-quarter) or 'cumulative'
            (Self-Employment Business v5.0). Stored in the
            ``submission_type`` column added by migration 009.
    """
    status = 'submitted' if result.get('success') else 'failed'
    receipt_id = result.get('data', {}).get('id') if result.get('success') else None
    error_message = result.get('error') if not result.get('success') else None

    # Infer period dates from submission payload if not supplied explicitly
    if not from_date:
        from_date = (submission_data or {}).get('fromDate') or (submission_data or {}).get('from')
        if not from_date:
            period_dates = (submission_data or {}).get('periodDates') or {}
            from_date = period_dates.get('periodStartDate')
    if not to_date:
        to_date = (submission_data or {}).get('toDate') or (submission_data or {}).get('to')
        if not to_date:
            period_dates = (submission_data or {}).get('periodDates') or {}
            to_date = period_dates.get('periodEndDate')

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hmrc_submissions
            (tax_year, period_id, submission_date, status, hmrc_receipt_id,
             submission_data, response_data, error_message, nino,
             period_start_date, period_end_date, submission_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tax_year,
            period_id,
            datetime.now().isoformat(),
            status,
            receipt_id,
            json.dumps(submission_data),
            json.dumps(result.get('data', {})),
            error_message,
            nino,
            from_date,
            to_date,
            submission_type,
        ))
        submission_row_id = cursor.lastrowid
        conn.commit()

    # Lock the digital records for the covered period on a successful submission.
    if status == 'submitted' and from_date and to_date:
        try:
            from ..services.hmrc_lock import lock_submission
            lock_submission(submission_row_id, from_date, to_date)
        except Exception as e:  # noqa: BLE001
            logger.error(f'Could not lock submission {submission_row_id}: {e}')

    return submission_row_id


@hmrc_bp.route('/obligations/final-declaration')
@limiter.limit("20 per hour", override_defaults=True)
def get_final_declaration_obligations():
    """
    Get final declaration (crystallisation) obligations.
    
    Query params:
        nino: National Insurance Number
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        status: 'O' for Open, 'F' for Fulfilled
    
    Returns:
        Final declaration obligations
    """
    try:
        nino = request.args.get('nino')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        status = request.args.get('status')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.get_final_declaration_obligations(nino, from_date, to_date, status)
        
        if result.get('success'):
            # Store obligations with type='crystallisation'
            obligations = result.get('data', {}).get('obligations', [])
            if obligations:
                try:
                    _store_final_declaration_obligations(obligations)
                except Exception as store_error:
                    logger.error(f'Error storing final declaration obligations: {store_error}')
            
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting final declaration obligations: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/business/<business_id>')
@limiter.limit("20 per hour", override_defaults=True)
def get_business_detail(business_id):
    """
    Get single business details by ID.
    
    Query params:
        nino: National Insurance Number
    
    Returns:
        Business details
    """
    try:
        nino = request.args.get('nino')
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.get_business_detail(nino, business_id)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting business detail: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/business/<business_id>/quarterly-period-type', methods=['PUT'])
@limiter.limit("20 per hour", override_defaults=True)
def create_amend_quarterly_period_type(business_id):
    """
    Create or amend quarterly period type for a business.
    
    Request body:
    {
        "nino": "AA123456A",
        "period_type": "standard" or "calendar"
    }
    
    Returns:
        Success status
    """
    try:
        data = request.get_json()
        nino = data.get('nino')
        period_type = data.get('period_type')
        
        if not nino or not period_type:
            return jsonify({'success': False, 'error': 'nino and period_type are required'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.create_amend_quarterly_period_type(nino, business_id, period_type)
        
        if result.get('success'):
            # Update local database if you're tracking businesses
            try:
                _update_business_period_type(business_id, period_type)
            except Exception as db_error:
                logger.warning(f'Could not update local business record: {db_error}')
            
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error creating/amending quarterly period type: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/calculations/list')
@limiter.limit("20 per hour", override_defaults=True)
def list_calculations():
    """
    List all tax calculations for a tax year.
    
    Query params:
        nino: National Insurance Number
        tax_year: Tax year (e.g., '2024/2025')
    
    Returns:
        List of calculations
    """
    try:
        nino = request.args.get('nino')
        tax_year = request.args.get('tax_year')
        
        if not nino or not tax_year:
            return jsonify({'success': False, 'error': 'nino and tax_year are required'}), 400
        
        try:
            nino = validate_nino(nino)
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.list_calculations(nino, tax_year)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error listing calculations: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/calculations/<calculation_id>')
@limiter.limit("20 per hour", override_defaults=True)
def retrieve_calculation(calculation_id):
    """
    Retrieve a specific tax calculation by ID.
    
    Query params:
        nino: National Insurance Number
    
    Returns:
        Complete tax calculation with breakdown
    """
    try:
        nino = request.args.get('nino')
        
        if not calculation_id:
            return jsonify({'success': False, 'error': 'calculation_id is required'}), 400
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.retrieve_calculation(nino, calculation_id)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error retrieving calculation: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/self-employment/periods')
@limiter.limit("20 per hour", override_defaults=True)
def list_periods():
    """
    List all periods for a business and tax year.
    
    Query params:
        nino: National Insurance Number
        business_id: Business ID
        tax_year: Tax year (e.g., '2024-25')
    
    Returns:
        List of periods
    """
    try:
        nino = request.args.get('nino')
        business_id = request.args.get('business_id')
        tax_year = request.args.get('tax_year')
        
        if not nino or not business_id or not tax_year:
            return jsonify({'success': False, 'error': 'nino, business_id, and tax_year are required'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.list_periods(nino, business_id, tax_year)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error listing periods: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/self-employment/annual-summary', methods=['GET', 'POST'])
@limiter.limit("20 per hour", override_defaults=True)
def annual_summary():
    """
    Get or update annual summary (allowances & adjustments).
    
    GET - Retrieve annual summary
    Query params:
        nino: National Insurance Number
        business_id: Business ID
        tax_year: Tax year (e.g., '2024-25')
    
    POST - Update annual summary
    Request body:
    {
        "nino": "AA123456A",
        "business_id": "XAIS12345678901",
        "tax_year": "2024-25",
        "annual_data": {
            "allowances": {...},
            "adjustments": {...}
        }
    }
    
    Returns:
        Annual summary data or update confirmation
    """
    try:
        if request.method == 'GET':
            nino = request.args.get('nino')
            business_id = request.args.get('business_id')
            tax_year = request.args.get('tax_year')
            
            if not nino or not business_id or not tax_year:
                return jsonify({'success': False, 'error': 'nino, business_id, and tax_year are required'}), 400
            
            try:
                nino = validate_nino(nino)
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            
            client = HMRCClient()
            result = client.get_annual_summary(nino, business_id, tax_year)
            
            if result.get('success'):
                return jsonify({'success': True, 'data': result.get('data', {})})
            else:
                return jsonify(result)
        
        else:  # POST
            data = request.get_json()
            nino = data.get('nino')
            business_id = data.get('business_id')
            tax_year = data.get('tax_year')
            annual_data = data.get('annual_data')
            
            if not nino or not business_id or not tax_year or not annual_data:
                return jsonify({'success': False, 'error': 'nino, business_id, tax_year, and annual_data are required'}), 400
            
            try:
                nino = validate_nino(nino)
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            
            client = HMRCClient()
            result = client.update_annual_summary(nino, business_id, tax_year, annual_data)
            
            if result.get('success'):
                return jsonify({'success': True, 'data': result.get('data', {})})
            else:
                return jsonify(result)
    
    except Exception as e:
        logger.error(f'Error with annual summary: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/final-declaration/status')
@limiter.limit("20 per hour", override_defaults=True)
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
@limiter.limit("20 per hour", override_defaults=True)
def calculate_final_declaration():
    """
    Trigger crystallisation (tax calculation) for a tax year.
    
    IMPORTANT: This endpoint automatically submits the required Self-Employment Annual Submission
    before triggering the calculation. HMRC requires the annual submission to exist or returns
    MATCHING_RESOURCE_NOT_FOUND.

    Query params:
        tax_year: Tax year (e.g., '2024/2025')
        nino: National Insurance Number (optional in sandbox — auto-resolved from active test user)
        business_id: Business ID (optional in sandbox — auto-resolved from active test user)
        calculation_type: Optional - 'intent-to-finalise' (default), 'intent-to-amend', or 'in-year'

    Returns:
        Calculation ID and estimated tax
    """
    try:
        # Use silent=True to avoid 400 errors when no JSON body is sent
        data = request.get_json(silent=True) or {}
        
        # Read from JSON body first, then fall back to query params
        tax_year = data.get('tax_year') or request.args.get('tax_year')
        nino = data.get('nino') or request.args.get('nino')
        calculation_type = data.get('calculation_type') or request.args.get('calculation_type', 'intent-to-finalise')

        if not tax_year:
            return jsonify({'success': False, 'error': 'tax_year is required'}), 400

        try:
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        # Resolve NINO: use sandbox test user if available, validate against provided NINO
        from flask import current_app
        sandbox_user = None
        if current_app.config.get('HMRC_ENVIRONMENT') == 'sandbox':
            sandbox_user = _get_sandbox_nino()

        if not nino and sandbox_user:
            nino = sandbox_user['nino']
            logger.info(f'Auto-resolved NINO from active sandbox test user: {nino}')
        elif not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400

        # Warn if caller NINO doesn't match sandbox test user
        if sandbox_user and nino.upper() != sandbox_user['nino'].upper():
            logger.warning(
                f'NINO mismatch: caller passed {nino} but active sandbox test user is {sandbox_user["nino"]}'
            )
            return jsonify({
                'success': False,
                'error': f'NINO mismatch: you provided {nino} but the active sandbox test user is {sandbox_user["nino"]}. '
                         f'The OAuth token was issued for the sandbox test user. Use NINO {sandbox_user["nino"]} or re-authenticate.'
            }), 400

        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid NINO: {str(e)}'}), 400

        # Tag the active OAuth credential with this NINO
        auth_service = HMRCAuthService()
        auth_service.update_credential_nino(nino)

        # Only require all 4 quarters for intent-to-finalise
        if calculation_type == 'intent-to-finalise':
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

        client = HMRCClient()
        
        # CRITICAL: Submit annual submission before triggering calculation
        # HMRC requires this or returns MATCHING_RESOURCE_NOT_FOUND
        logger.info('=== ANNUAL SUBMISSION STEP ===')
        
        # Resolve business_id from multiple sources
        business_id = None
        if data:
            business_id = data.get('business_id')
            logger.info(f'Business ID from request body: {business_id}')
        
        if not business_id:
            business_id = request.args.get('business_id')
            logger.info(f'Business ID from query params: {business_id}')
        
        if not business_id:
            # Try to get from sandbox test user
            logger.info('Attempting to auto-resolve Business ID from sandbox test user')
            if sandbox_user and sandbox_user.get('business_id'):
                business_id = sandbox_user['business_id']
                logger.info(f'✓ Auto-resolved Business ID from sandbox test user: {business_id}')
            else:
                logger.warning('No sandbox test user or business_id found in sandbox user')
        
        if not business_id:
            logger.error('Business ID resolution failed - no business_id provided and no sandbox test user')
            return jsonify({
                'success': False,
                'error': 'business_id is required for tax calculation. Provide it in the request or ensure a sandbox test user with business_id exists.'
            }), 400
        
        # Convert tax year to YYYY-YY format for annual submission
        logger.info(f'Converting tax year from {tax_year} to YYYY-YY format')
        try:
            formatted_tax_year = tax_year.replace('/', '-')
            if len(formatted_tax_year.split('-')[1]) == 4:
                parts = formatted_tax_year.split('-')
                formatted_tax_year = f"{parts[0]}-{parts[1][-2:]}"
            logger.info(f'Formatted tax year: {formatted_tax_year}')
        except Exception as format_error:
            logger.error(f'Tax year format conversion failed: {format_error}')
            return jsonify({
                'success': False,
                'error': f'Invalid tax year format: {str(format_error)}'
            }), 400
        
        # Submit minimal annual submission (required before calculation)
        # HMRC SE Business API v5.0 specification
        # Note: structuredBuildingAllowance must be omitted when empty - HMRC rejects empty arrays
        logger.info(f'Preparing annual submission for NINO={nino}, Business ID={business_id}, Tax Year={formatted_tax_year}')
        annual_data = {
            'adjustments': {
                'includedNonTaxableProfits': 0,
                'basisAdjustment': 0,
                'overlapReliefUsed': 0,
                'accountingAdjustment': 0,
                'averagingAdjustment': 0,
                'outstandingBusinessIncome': 0,
                'balancingChargeBPRA': 0,
                'balancingChargeOther': 0,
                'goodsAndServicesOwnUse': 0
            },
            'allowances': {
                'annualInvestmentAllowance': 0,
                'businessPremisesRenovationAllowance': 0,
                'capitalAllowanceMainPool': 0,
                'capitalAllowanceSpecialRatePool': 0,
                'zeroEmissionsGoodsVehicleAllowance': 0,
                'enhancedCapitalAllowance': 0,
                'allowanceOnSales': 0,
                'capitalAllowanceSingleAssetPool': 0
            }
        }
        
        try:
            logger.info('Calling update_annual_summary...')
            annual_result = client.update_annual_summary(nino, business_id, formatted_tax_year, annual_data)
            logger.info(f'Annual submission result: success={annual_result.get("success")}, status_code={annual_result.get("status_code")}')
            
            if not annual_result.get('success'):
                # Log warning but continue - annual submission might already exist
                error_msg = annual_result.get('error', 'Unknown error')
                logger.warning(f'Annual submission failed (may already exist): {error_msg}')
                logger.warning(f'Full annual result: {annual_result}')
            else:
                logger.info('✓ Annual submission successful')
        except Exception as annual_error:
            # Log error but continue - don't let annual submission failure block calculation
            logger.error(f'Annual submission exception: {annual_error}', exc_info=True)
            logger.warning('Continuing to calculation trigger despite annual submission error')
        
        # Now trigger the calculation
        logger.info('=== CALCULATION TRIGGER STEP ===')
        logger.info(f'Calling trigger_crystallisation with NINO={nino}, Tax Year={tax_year}, Type={calculation_type}')
        result = client.trigger_crystallisation(nino, tax_year, calculation_type)

        if not result.get('success'):
            return jsonify(result)

        calculation_id = result.get('data', {}).get('calculationId') or result.get('data', {}).get('id')
        estimated_tax = result.get('data', {}).get('totalIncomeTaxAndNicsDue', 0.0)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hmrc_final_declarations
                (tax_year, calculation_id, estimated_tax, status, nino)
                VALUES (?, ?, ?, 'calculated', ?)
            """, (tax_year, calculation_id, estimated_tax, nino))
            conn.commit()

        return jsonify({
            'success': True,
            'data': {
                'calculation_id': calculation_id,
                'estimated_tax': estimated_tax,
                'calculation_type': calculation_type,
                'nino': nino,
                'message': 'Tax calculation completed successfully'
            }
        })
    except Exception as e:
        logger.error(f'Error calculating final declaration: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/final-declaration/submit', methods=['POST'])
@limiter.limit("20 per hour", override_defaults=True)
def submit_final_declaration():
    """
    Submit final declaration (crystallisation) to HMRC.
    
    Request body:
    {
        "tax_year": "2024/2025",
        "calculation_id": "abc123",
        "nino": "AA123456A",
        "confirmed": true,
        "declaration_type": "final-declaration" or "intent-to-amend"
    }
    
    Returns:
        Receipt ID and confirmation
    """
    try:
        data = request.get_json()
        tax_year = data.get('tax_year')
        calculation_id = data.get('calculation_id')
        nino = data.get('nino')
        confirmed = data.get('confirmed', False)
        declaration_type = data.get('declaration_type', 'final-declaration')

        if not tax_year or not calculation_id:
            return jsonify({'success': False, 'error': 'tax_year and calculation_id are required'}), 400

        if not confirmed:
            return jsonify({'success': False, 'error': 'You must confirm the declaration is correct'}), 400

        try:
            tax_year = validate_tax_year(tax_year)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        # Auto-resolve NINO from sandbox test user if not provided
        from flask import current_app
        if not nino and current_app.config.get('HMRC_ENVIRONMENT') == 'sandbox':
            sandbox_user = _get_sandbox_nino()
            if sandbox_user:
                nino = sandbox_user['nino']
                logger.info(f'Auto-resolved NINO from active sandbox test user: {nino}')

        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM hmrc_final_declarations
                WHERE tax_year = ? AND calculation_id = ?
            """, (tax_year, calculation_id))

            existing = cursor.fetchone()
            if existing and existing['status'] == 'submitted' and declaration_type == 'final-declaration':
                return jsonify({
                    'success': False,
                    'error': 'Final declaration already submitted for this tax year'
                }), 409

        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid NINO: {str(e)}'}), 400
        
        client = HMRCClient()
        result = client.submit_final_declaration(nino, tax_year, calculation_id, declaration_type)
        
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
                'declaration_type': declaration_type,
                'message': 'Final declaration submitted successfully',
                'submitted_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f'Error submitting final declaration: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/property/obligations')
@limiter.limit("20 per hour", override_defaults=True)
@require_property_enabled
def get_property_obligations():
    """
    Get UK property obligations.
    
    Query params:
        nino: National Insurance Number
    
    Returns:
        UK property obligations
    """
    try:
        nino = request.args.get('nino')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.get_uk_property_obligations(nino)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting property obligations: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/property/submit', methods=['POST'])
@limiter.limit("20 per hour", override_defaults=True)
@require_property_enabled
def submit_property_period():
    """
    Submit UK property period data to HMRC.
    
    Request body:
    {
        "nino": "AA123456A",
        "tax_year": "2024-25",
        "from_date": "2024-04-06",
        "to_date": "2024-07-05"
    }
    
    Returns:
        Submission result
    """
    try:
        data = request.get_json()
        
        required_fields = ['nino', 'tax_year', 'from_date', 'to_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        try:
            data['nino'] = validate_nino(data['nino'])
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Build minimal test payload for sandbox
        period_data = {
            'fromDate': data['from_date'],
            'toDate': data['to_date'],
            'income': {
                'premiumsOfLeaseGrant': 0,
                'reversePremiums': 0,
                'periodAmount': 0,
                'taxDeducted': 0,
                'otherIncome': 0,
                'ukFhlRentARoom': {
                    'amountClaimed': 0
                }
            },
            'expenses': {
                'premisesRunningCosts': 0,
                'repairsAndMaintenance': 0,
                'financialCosts': 0,
                'professionalFees': 0,
                'costOfServices': 0,
                'other': 0,
                'travelCosts': 0,
                'rentARoom': {
                    'amountClaimed': 0
                }
            }
        }
        
        # Use a default business ID for sandbox testing
        # In production, this should come from the request or be looked up
        business_id = data.get('business_id', 'XAIS12345678901')
        
        client = HMRCClient()
        result = client.submit_uk_property_period(
            data['nino'],
            business_id,
            data['tax_year'],
            period_data
        )
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error submitting property period: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/bsas/trigger', methods=['POST'])
@limiter.limit("20 per hour", override_defaults=True)
def trigger_bsas():
    """
    Trigger Business Source Adjustable Summary (BSAS).
    
    Request body:
    {
        "nino": "AA123456A",
        "business_id": "XAIS12345678901",
        "tax_year": "2024/2025",
        "type_of_business": "self-employment" (optional, defaults to self-employment)
    }
    
    Returns:
        BSAS trigger result with calculationId
    """
    try:
        data = request.get_json()
        
        required_fields = ['nino', 'business_id', 'tax_year']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        try:
            data['nino'] = validate_nino(data['nino'])
            data['tax_year'] = validate_tax_year(data['tax_year'])
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        type_of_business = data.get('type_of_business', 'self-employment')
        if type_of_business not in ['self-employment', 'uk-property']:
            return jsonify({'success': False, 'error': 'type_of_business must be "self-employment" or "uk-property"'}), 400
        
        client = HMRCClient()
        result = client.trigger_bsas(
            data['nino'],
            data['business_id'],
            data['tax_year'],
            type_of_business
        )
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error triggering BSAS: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/bsas/<bsas_id>')
@limiter.limit("20 per hour", override_defaults=True)
def get_bsas_summary(bsas_id):
    """
    Get Business Source Adjustable Summary by calculationId.
    
    Path params:
        bsas_id: calculationId from trigger response
    
    Query params:
        nino: National Insurance Number
        type_of_business: 'self-employment' or 'uk-property' (optional, defaults to 'self-employment')
    
    Returns:
        BSAS summary data
    """
    try:
        nino = request.args.get('nino')
        type_of_business = request.args.get('type_of_business', 'self-employment')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        if not bsas_id:
            return jsonify({'success': False, 'error': 'bsas_id is required'}), 400
        
        if type_of_business not in ['self-employment', 'uk-property']:
            return jsonify({'success': False, 'error': 'type_of_business must be "self-employment" or "uk-property"'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.get_bsas_summary(nino, bsas_id, type_of_business=type_of_business)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error getting BSAS summary: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/losses/create', methods=['POST'])
@limiter.limit("20 per hour", override_defaults=True)
def create_loss():
    """
    Create a brought forward loss.
    
    Request body:
    {
        "nino": "AA123456A",
        "tax_year": "2023-24",
        "type_of_loss": "self-employment",
        "business_id": "XBIS12345678901",
        "loss_amount": 1000.00
    }
    
    Returns:
        Loss creation result with lossId
    """
    try:
        data = request.get_json()
        
        required_fields = ['nino', 'tax_year', 'type_of_loss', 'business_id', 'loss_amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        try:
            data['nino'] = validate_nino(data['nino'])
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Validate type_of_loss
        valid_loss_types = ['self-employment', 'uk-property-fhl', 'uk-property-non-fhl']
        if data['type_of_loss'] not in valid_loss_types:
            return jsonify({'success': False, 'error': f'type_of_loss must be one of: {", ".join(valid_loss_types)}'}), 400
        
        # Validate loss_amount is a number
        try:
            loss_amount = float(data['loss_amount'])
            if loss_amount <= 0:
                return jsonify({'success': False, 'error': 'loss_amount must be greater than 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'loss_amount must be a valid number'}), 400
        
        client = HMRCClient()
        result = client.create_loss(
            data['nino'],
            data['tax_year'],
            data['type_of_loss'],
            data['business_id'],
            loss_amount
        )
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error creating loss: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/losses/list')
@limiter.limit("20 per hour", override_defaults=True)
def list_losses():
    """
    List brought forward losses.
    
    Query params:
        nino: National Insurance Number (required)
        tax_year: Tax year filter (optional, e.g., '2023-24')
        type_of_loss: Loss type filter (optional)
        business_id: Business ID filter (optional)
    
    Returns:
        List of losses
    """
    try:
        nino = request.args.get('nino')
        tax_year = request.args.get('tax_year')
        type_of_loss = request.args.get('type_of_loss')
        business_id = request.args.get('business_id')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.list_losses(nino, tax_year, type_of_loss, business_id)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error listing losses: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@hmrc_bp.route('/export')
@limiter.limit("10 per hour", override_defaults=True)
def export_data():
    """
    Export all HMRC MTD data for the current user as JSON.
    
    Returns:
        JSON file download with all submissions, obligations, and declarations
    """
    try:
        from flask import make_response
        import json
        from datetime import datetime
        
        # Get all HMRC data from database
        export_data = {
            'export_date': datetime.now().isoformat(),
            'export_version': '1.0',
            'software': 'TVS Wages MTD',
            'submissions': [],
            'obligations': [],
            'final_declarations': [],
            'losses': []
        }
        
        # Fetch submissions from database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get submissions
            cursor.execute('''
                SELECT submission_date, tax_year, period_id, submission_type, 
                       response_data, created_at
                FROM hmrc_submissions
                ORDER BY submission_date DESC
            ''')
            submissions = cursor.fetchall()
            for sub in submissions:
                export_data['submissions'].append({
                    'submission_date': sub[0],
                    'tax_year': sub[1],
                    'period_id': sub[2],
                    'submission_type': sub[3],
                    'response_data': json.loads(sub[4]) if sub[4] else None,
                    'created_at': sub[5]
                })
            
            # Get obligations
            cursor.execute('''
                SELECT tax_year, obligation_type, data, fetched_at
                FROM hmrc_obligations
                ORDER BY fetched_at DESC
            ''')
            obligations = cursor.fetchall()
            for obl in obligations:
                export_data['obligations'].append({
                    'tax_year': obl[0],
                    'obligation_type': obl[1],
                    'data': json.loads(obl[2]) if obl[2] else None,
                    'fetched_at': obl[3]
                })
            
            # Get final declarations
            cursor.execute('''
                SELECT tax_year, calculation_id, declaration_data, submitted_at
                FROM hmrc_final_declarations
                ORDER BY submitted_at DESC
            ''')
            declarations = cursor.fetchall()
            for decl in declarations:
                export_data['final_declarations'].append({
                    'tax_year': decl[0],
                    'calculation_id': decl[1],
                    'declaration_data': json.loads(decl[2]) if decl[2] else None,
                    'submitted_at': decl[3]
                })
            
            conn.close()
            
        except Exception as db_error:
            logger.warning(f'Database query error during export: {db_error}')
            # Continue with empty data if database query fails
        
        # Create JSON response
        json_data = json.dumps(export_data, indent=2, default=str)
        
        # Create downloadable response
        response = make_response(json_data)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=hmrc-mtd-data-{datetime.now().strftime("%Y-%m-%d")}.json'
        
        return response
        
    except Exception as e:
        logger.error(f'Error exporting data: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
