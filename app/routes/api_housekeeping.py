"""
Housekeeping API Routes
Handles re-parsing runsheets and address validation operations
"""

from flask import Blueprint, request, jsonify
import subprocess
import sys
from pathlib import Path
import os
from datetime import datetime, timedelta

# Create blueprint
housekeeping_bp = Blueprint('api_housekeeping', __name__)

# Get project root
project_root = Path(__file__).parent.parent.parent

@housekeeping_bp.route('/reparse-runsheets', methods=['POST'])
def api_reparse_runsheets():
    """Re-parse runsheets with improved parser."""
    try:
        data = request.json or {}
        
        # Determine what to re-parse
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        recent_days = data.get('recent_days')
        specific_date = data.get('specific_date')
        
        # Build command arguments
        cmd_args = [sys.executable, str(project_root / 'scripts/production/import_run_sheets.py')]
        
        if start_date and end_date:
            # Date range parsing
            cmd_args.extend(['--date-range', start_date, end_date])
        elif recent_days:
            # Recent days parsing
            cmd_args.extend(['--recent', str(recent_days)])
        elif specific_date:
            # Specific date parsing (convert DD/MM/YYYY to YYYY-MM-DD for script)
            try:
                date_parts = specific_date.split('/')
                if len(date_parts) == 3:
                    iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                    cmd_args.extend(['--date', iso_date])
                else:
                    return jsonify({'success': False, 'error': 'Invalid date format. Use DD/MM/YYYY'}), 400
            except Exception as e:
                return jsonify({'success': False, 'error': f'Date parsing error: {str(e)}'}), 400
        else:
            return jsonify({'success': False, 'error': 'No date criteria specified'}), 400
        
        # Add re-parse flag to force re-processing
        cmd_args.append('--force-reparse')
        
        # Execute the import script
        result = subprocess.run(
            cmd_args,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            # Parse output for detailed statistics
            output_lines = result.stdout.split('\n')
            files_processed = 0
            jobs_updated = 0
            jobs_skipped = 0
            rico_skipped = 0
            processing_details = []
            
            for line in output_lines:
                if 'files processed' in line.lower() or 'runsheets imported' in line.lower():
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        files_processed = int(numbers[0])
                elif 'jobs' in line.lower() and ('updated' in line.lower() or 'imported' in line.lower()):
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        jobs_updated = int(numbers[-1])
                elif 'skipping rico depots' in line.lower():
                    rico_skipped += 1
                    processing_details.append(f"Skipped RICO: {line.strip()}")
                elif 'skipping job' in line.lower() and 'previously deleted' in line.lower():
                    jobs_skipped += 1
                    processing_details.append(f"Skipped deleted: {line.strip()}")
                elif 'updated job' in line.lower() or 'imported job' in line.lower():
                    processing_details.append(f"Processed: {line.strip()}")
            
            # Generate detailed report
            report = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'Re-parse Runsheets',
                'parameters': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'recent_days': recent_days,
                    'specific_date': specific_date
                },
                'results': {
                    'files_processed': files_processed,
                    'jobs_updated': jobs_updated,
                    'jobs_skipped': jobs_skipped,
                    'rico_skipped': rico_skipped,
                    'total_actions': files_processed + jobs_skipped + rico_skipped
                },
                'details': processing_details[-20:] if len(processing_details) > 20 else processing_details,  # Last 20 details
                'full_output': result.stdout
            }
            
            return jsonify({
                'success': True,
                'files_processed': files_processed,
                'jobs_updated': jobs_updated,
                'jobs_skipped': jobs_skipped,
                'rico_skipped': rico_skipped,
                'report': report,
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Re-parsing failed: {result.stderr or "Unknown error"}',
                'output': result.stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Re-parsing timed out after 5 minutes'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@housekeeping_bp.route('/validate-addresses', methods=['POST'])
def api_validate_addresses():
    """Validate and clean up addresses."""
    try:
        data = request.json or {}
        
        # Determine what to validate
        recent_days = data.get('recent_days')
        specific_date = data.get('specific_date')
        validate_all = data.get('validate_all', False)
        
        # Build command arguments
        cmd_args = [sys.executable, str(project_root / 'scripts/production/validate_addresses.py')]
        
        if validate_all:
            cmd_args.append('--all')
        elif specific_date:
            cmd_args.extend(['--date', specific_date])
        elif recent_days:
            cmd_args.extend(['--recent', str(recent_days)])
        else:
            # Default to last 7 days
            cmd_args.extend(['--recent', '7'])
        
        # Execute the validation script
        result = subprocess.run(
            cmd_args,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout
        )
        
        if result.returncode == 0:
            # Parse output for detailed statistics
            output_lines = result.stdout.split('\n')
            fixes_applied = 0
            jobs_validated = 0
            issues_remaining = 0
            fixes_details = []
            issues_details = []
            
            for line in output_lines:
                if 'fixes applied:' in line.lower():
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        fixes_applied = int(numbers[0])
                elif 'jobs validated:' in line.lower():
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        jobs_validated = int(numbers[0])
                elif 'issues found:' in line.lower():
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        issues_remaining = int(numbers[0])
                elif '✅ Fixed Job' in line:
                    fixes_details.append(line.strip())
                elif '⚠️  Job' in line and 'issues' in line.lower():
                    issues_details.append(line.strip())
            
            # Generate detailed report
            report = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'Address Validation',
                'parameters': {
                    'recent_days': recent_days,
                    'specific_date': specific_date,
                    'validate_all': validate_all
                },
                'results': {
                    'jobs_validated': jobs_validated,
                    'fixes_applied': fixes_applied,
                    'issues_remaining': issues_remaining,
                    'success_rate': round((fixes_applied / max(jobs_validated, 1)) * 100, 1)
                },
                'fixes_applied': fixes_details[-10:] if len(fixes_details) > 10 else fixes_details,  # Last 10 fixes
                'issues_found': issues_details[-5:] if len(issues_details) > 5 else issues_details,  # Last 5 issues
                'full_output': result.stdout
            }
            
            return jsonify({
                'success': True,
                'fixes_applied': fixes_applied,
                'jobs_validated': jobs_validated,
                'issues_remaining': issues_remaining,
                'report': report,
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Address validation failed: {result.stderr or "Unknown error"}',
                'output': result.stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Address validation timed out after 3 minutes'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@housekeeping_bp.route('/status', methods=['GET'])
def api_housekeeping_status():
    """Get housekeeping system status."""
    try:
        # Check if scripts exist
        import_script = project_root / 'scripts/production/import_run_sheets.py'
        validate_script = project_root / 'scripts/production/validate_addresses.py'
        
        return jsonify({
            'success': True,
            'scripts_available': {
                'import_run_sheets': import_script.exists(),
                'validate_addresses': validate_script.exists()
            },
            'project_root': str(project_root)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
