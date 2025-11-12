"""
Sync API routes - Handle synchronization between different data sources.
"""

from flask import Blueprint, jsonify
from ..services.runsheet_sync_service import RunsheetSyncService

sync_bp = Blueprint('sync_api', __name__, url_prefix='/api/sync')


@sync_bp.route('/payslip-to-runsheets', methods=['POST'])
def api_sync_payslip_to_runsheets():
    """Manually trigger sync of payslip data to runsheets."""
    try:
        result = RunsheetSyncService.sync_payslip_data_to_runsheets()
        
        if result['success']:
            # Get updated statistics
            stats = RunsheetSyncService.get_sync_statistics()
            
            return jsonify({
                'success': True,
                'message': 'Payslip data synced to runsheets successfully',
                'pay_updated': result['pay_updated'],
                'address_updated': result['address_updated'],
                'statistics': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'pay_updated': 0,
                'address_updated': 0
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'pay_updated': 0,
            'address_updated': 0
        }), 500


@sync_bp.route('/statistics', methods=['GET'])
def api_sync_statistics():
    """Get current synchronization statistics."""
    try:
        stats = RunsheetSyncService.get_sync_statistics()
        
        if stats:
            return jsonify({
                'success': True,
                'statistics': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not retrieve statistics'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
