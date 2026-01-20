"""
API endpoints for CDN version management
"""

from flask import Blueprint, jsonify, request
from pathlib import Path
import sys

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

from check_cdn_versions import CDNVersionChecker

api_cdn_bp = Blueprint('api_cdn', __name__)

@api_cdn_bp.route('/api/cdn/check', methods=['GET'])
def check_versions():
    """Check for CDN library updates"""
    try:
        checker = CDNVersionChecker()
        results = checker.check_all_versions()
        checker.save_version_check(results)
        
        return jsonify({
            'success': True,
            'libraries': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_cdn_bp.route('/api/cdn/status', methods=['GET'])
def get_status():
    """Get last version check results"""
    try:
        checker = CDNVersionChecker()
        data = checker.load_version_check()
        
        if not data:
            # No previous check, run one now
            results = checker.check_all_versions()
            checker.save_version_check(results)
            data = checker.load_version_check()
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_cdn_bp.route('/api/cdn/update', methods=['POST'])
def update_library():
    """Update specific CDN libraries"""
    try:
        data = request.get_json()
        libraries = data.get('libraries', [])
        
        if not libraries:
            return jsonify({
                'success': False,
                'error': 'No libraries specified'
            }), 400
        
        checker = CDNVersionChecker()
        
        # Get latest versions for requested libraries
        updates = {}
        for lib_id in libraries:
            if lib_id in checker.libraries:
                latest = checker.get_latest_version(lib_id)
                if latest:
                    updates[lib_id] = latest
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No valid libraries to update'
            }), 400
        
        # Perform updates
        results = checker.update_all_libraries(updates)
        
        # Check if all succeeded
        all_success = all(results.values())
        
        return jsonify({
            'success': all_success,
            'results': results,
            'message': f"Updated {sum(results.values())} of {len(results)} libraries"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_cdn_bp.route('/api/cdn/update-all', methods=['POST'])
def update_all():
    """Update all CDN libraries with available updates"""
    try:
        checker = CDNVersionChecker()
        
        # Check for updates
        check_results = checker.check_all_versions()
        
        # Get libraries that need updating
        updates = {
            lib_id: info['latest'] 
            for lib_id, info in check_results.items() 
            if info['update_available']
        }
        
        if not updates:
            return jsonify({
                'success': True,
                'message': 'All libraries are already up to date',
                'results': {}
            })
        
        # Perform updates
        results = checker.update_all_libraries(updates)
        
        # Save updated check
        checker.save_version_check(checker.check_all_versions())
        
        all_success = all(results.values())
        
        return jsonify({
            'success': all_success,
            'results': results,
            'message': f"Updated {sum(results.values())} of {len(results)} libraries"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
