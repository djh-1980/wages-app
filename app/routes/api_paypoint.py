"""
Paypoint API routes - Handle Paypoint stock management endpoints.
"""

from flask import Blueprint, jsonify, request
from ..models.paypoint import PaypointModel

paypoint_bp = Blueprint('paypoint_api', __name__, url_prefix='/api/paypoint')


@paypoint_bp.route('/stock', methods=['GET'])
def api_get_stock():
    """Get all stock items."""
    try:
        items = PaypointModel.get_all_stock_items()
        return jsonify({
            'success': True,
            'items': items
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paypoint_bp.route('/devices', methods=['POST'])
def api_add_paypoint_device():
    """Add a new Paypoint device."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        paypoint_type = data.get('paypoint_type')
        serial_ptid = data.get('serial_ptid')
        trace_stock = data.get('trace_stock')
        notes = data.get('notes', '')
        
        if not paypoint_type or not serial_ptid or not trace_stock:
            return jsonify({'error': 'Paypoint type, serial/TID, and trace/stock are required'}), 400
        
        device_id = PaypointModel.add_paypoint_device(
            paypoint_type, serial_ptid, trace_stock, notes
        )
        
        return jsonify({
            'success': True,
            'message': 'Paypoint device added successfully',
            'device_id': device_id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@paypoint_bp.route('/devices/<int:device_id>/deploy', methods=['POST'])
def api_deploy_device(device_id):
    """Deploy a Paypoint device to a job."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        job_number = data.get('job_number')
        customer = data.get('customer', '')
        location = data.get('location', '')
        installation_notes = data.get('installation_notes', '')
        
        # Return information (optional - for immediate deploy+return)
        return_notes = data.get('return_notes', '')
        return_immediately = data.get('return_immediately', False)
        
        if not job_number:
            return jsonify({'error': 'Job number is required'}), 400
        
        deployment_id = PaypointModel.deploy_device(
            device_id, job_number, customer, location, installation_notes
        )
        
        # If return_immediately is True, also create the return record
        if return_immediately:
            # Extract return serial and trace from notes (format: "Return Serial: X, Return Trace: Y, ...")
            import re
            return_serial = None
            return_trace = None
            return_reason = ''
            
            if return_notes:
                serial_match = re.search(r'Return Serial:\s*([^,]+)', return_notes)
                trace_match = re.search(r'Return Trace:\s*([^,]+)', return_notes)
                reason_match = re.search(r'Reason:\s*([^,]+)', return_notes)
                
                if serial_match:
                    val = serial_match.group(1).strip()
                    if val and val != 'N/A':
                        return_serial = val
                if trace_match:
                    val = trace_match.group(1).strip()
                    if val and val != 'N/A':
                        return_trace = val
                if reason_match:
                    return_reason = reason_match.group(1).strip()
            
            # If return serial/trace not provided, use the device's own serial/trace
            if not return_serial or not return_trace:
                from ..models.paypoint import PaypointModel as PM
                with PM.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT serial_ptid, trace_stock 
                        FROM paypoint_stock 
                        WHERE id = ?
                    """, (device_id,))
                    device_info = cursor.fetchone()
                    if device_info:
                        if not return_serial:
                            return_serial = device_info[0]
                        if not return_trace:
                            return_trace = device_info[1]
            
            PaypointModel.return_device(deployment_id, return_serial, return_trace, return_reason, return_notes)
            message = f'Device deployed and returned for job {job_number}'
        else:
            message = f'Device deployed to job {job_number}'
        
        return jsonify({
            'success': True,
            'message': message,
            'deployment_id': deployment_id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@paypoint_bp.route('/deployments/<int:deployment_id>/return', methods=['POST'])
def api_return_device(deployment_id):
    """Return a deployed Paypoint device."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        return_serial_ptid = data.get('return_serial_ptid')
        return_trace = data.get('return_trace')
        return_reason = data.get('return_reason', '')
        return_notes = data.get('return_notes', '')
        
        if not return_serial_ptid:
            return jsonify({'error': 'Return serial/TID is required'}), 400
        
        if not return_trace:
            return jsonify({'error': 'Return trace number is required for audit trail'}), 400
        
        return_id = PaypointModel.return_device(
            deployment_id, return_serial_ptid, return_trace, return_reason, return_notes
        )
        
        return jsonify({
            'success': True,
            'message': f'Device returned successfully',
            'return_id': return_id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@paypoint_bp.route('/deployments', methods=['GET'])
def api_get_deployments():
    """Get deployment history."""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        deployments = PaypointModel.get_deployments(limit)
        
        return jsonify({
            'success': True,
            'deployments': deployments
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paypoint_bp.route('/returns', methods=['GET'])
def api_get_returns():
    """Get return history."""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        returns = PaypointModel.get_returns(limit)
        
        return jsonify({
            'success': True,
            'returns': returns
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paypoint_bp.route('/deployed', methods=['GET'])
def api_get_deployed_devices():
    """Get currently deployed devices."""
    try:
        devices = PaypointModel.get_deployed_devices()
        
        return jsonify({
            'success': True,
            'devices': devices
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paypoint_bp.route('/audit', methods=['GET'])
def api_get_audit_history():
    """Get complete audit history."""
    try:
        limit = request.args.get('limit', 200, type=int)
        
        audit_history = PaypointModel.get_audit_history(limit)
        
        return jsonify({
            'success': True,
            'audit_history': audit_history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paypoint_bp.route('/summary', methods=['GET'])
def api_get_summary():
    """Get stock summary statistics."""
    try:
        summary = PaypointModel.get_stock_summary()
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paypoint_bp.route('/initialize', methods=['POST'])
def api_initialize_tables():
    """Initialize Paypoint database tables."""
    try:
        PaypointModel.init_tables()
        
        return jsonify({
            'success': True,
            'message': 'Paypoint tables initialized successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
