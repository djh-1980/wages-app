"""
API endpoints for Python dependency management
"""

from flask import Blueprint, jsonify, request
from pathlib import Path
import sys

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

from check_python_deps import PythonDependencyChecker

api_python_deps_bp = Blueprint('api_python_deps', __name__)

@api_python_deps_bp.route('/api/python-deps/check', methods=['GET'])
def check_dependencies():
    """Check for Python dependency updates"""
    try:
        checker = PythonDependencyChecker()
        results = checker.check_all_packages()
        checker.save_check_results(results)
        
        # Calculate summary statistics
        total = len(results)
        updates_available = sum(1 for r in results.values() if r['update_available'])
        major_updates = sum(1 for r in results.values() if r.get('update_type') == 'major')
        minor_updates = sum(1 for r in results.values() if r.get('update_type') == 'minor')
        patch_updates = sum(1 for r in results.values() if r.get('update_type') == 'patch')
        
        return jsonify({
            'success': True,
            'packages': results,
            'summary': {
                'total': total,
                'updates_available': updates_available,
                'major_updates': major_updates,
                'minor_updates': minor_updates,
                'patch_updates': patch_updates
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_python_deps_bp.route('/api/python-deps/status', methods=['GET'])
def get_status():
    """Get last dependency check results"""
    try:
        checker = PythonDependencyChecker()
        data = checker.load_check_results()
        
        if not data:
            # No previous check, run one now
            results = checker.check_all_packages()
            checker.save_check_results(results)
            data = checker.load_check_results()
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_python_deps_bp.route('/api/python-deps/info/<package_name>', methods=['GET'])
def get_package_info(package_name):
    """Get detailed information about a specific package"""
    try:
        checker = PythonDependencyChecker()
        info = checker.get_package_info(package_name)
        
        if info:
            return jsonify({
                'success': True,
                'info': info
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Could not fetch info for {package_name}'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_python_deps_bp.route('/api/python-deps/update', methods=['POST'])
def update_packages():
    """Update specific Python packages"""
    try:
        data = request.get_json()
        packages = data.get('packages', {})  # Dict of {package_name: version}
        
        if not packages:
            return jsonify({
                'success': False,
                'error': 'No packages specified'
            }), 400
        
        checker = PythonDependencyChecker()
        results = checker.update_multiple_packages(packages)
        
        all_success = all(results.values())
        success_count = sum(results.values())
        
        return jsonify({
            'success': all_success,
            'results': results,
            'message': f"Updated {success_count} of {len(results)} packages"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_python_deps_bp.route('/api/python-deps/update-by-type', methods=['POST'])
def update_by_type():
    """Update packages by type (patch, minor, major, all)"""
    try:
        data = request.get_json()
        update_type = data.get('type', 'patch')  # patch, minor, major, all
        
        checker = PythonDependencyChecker()
        
        # Check for updates
        check_results = checker.check_all_packages()
        
        # Filter packages based on update type
        updates = {}
        for pkg_id, info in check_results.items():
            if info['update_available']:
                pkg_update_type = info.get('update_type', 'none')
                
                should_update = False
                if update_type == 'all':
                    should_update = True
                elif update_type == 'patch' and pkg_update_type == 'patch':
                    should_update = True
                elif update_type == 'minor' and pkg_update_type in ['patch', 'minor']:
                    should_update = True
                elif update_type == 'major':
                    should_update = True
                
                if should_update and info['latest'] != 'Unknown':
                    updates[info['clean_name']] = info['latest']
        
        if not updates:
            return jsonify({
                'success': True,
                'message': 'No packages need updating',
                'results': {}
            })
        
        # Perform updates
        results = checker.update_multiple_packages(updates)
        
        # Save updated check
        checker.save_check_results(checker.check_all_packages())
        
        all_success = all(results.values())
        success_count = sum(results.values())
        
        return jsonify({
            'success': all_success,
            'results': results,
            'message': f"Updated {success_count} of {len(results)} packages"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
