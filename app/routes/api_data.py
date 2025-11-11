"""
Data management API routes blueprint - sync, backup, export, clear operations.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, jsonify, request, make_response, send_file
from ..models.payslip import PayslipModel
from ..models.runsheet import RunsheetModel
from ..models.attendance import AttendanceModel
from ..models.settings import SettingsModel
from ..services.data_service import DataService
from ..utils.logging_utils import log_settings_action
from ..database import get_db_connection, DB_PATH
from pathlib import Path
from datetime import datetime
import subprocess
import sys
import sqlite3
import shutil
import csv
import io
import os

data_bp = Blueprint('data_api', __name__, url_prefix='/api/data')


@data_bp.route('/sync-payslips', methods=['POST'])
def api_sync_payslips():
    """Download payslips from Gmail and sync to database."""
    log_settings_action('SYNC_PAYSLIPS', 'Starting payslip sync with Gmail download')
    
    try:
        # Create progress file for real-time updates
        progress_file = Path('logs/payslip_sync_progress.log')
        progress_file.parent.mkdir(exist_ok=True)
        
        def write_progress(message):
            with open(progress_file, 'a') as f:
                f.write(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
            log_settings_action('SYNC_PAYSLIPS', message)
        
        # Clear previous progress
        with open(progress_file, 'w') as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - Starting payslip sync\n")
        
        # Step 1: Check last payslip date and download only newer ones
        write_progress('Step 1: Checking database for last payslip date...')
        
        # Get the most recent payslip date from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(pay_date) FROM payslips WHERE pay_date IS NOT NULL AND pay_date != ''")
        last_payslip_result = cursor.fetchone()
        conn.close()
        
        # Determine the date to search from
        if last_payslip_result and last_payslip_result[0]:
            # Convert DD/MM/YYYY to YYYY/MM/DD for Gmail search
            last_date_parts = last_payslip_result[0].split('/')
            if len(last_date_parts) == 3:
                search_date = f"{last_date_parts[2]}/{last_date_parts[1]}/{last_date_parts[0]}"
                write_progress(f'Last payslip found: {last_payslip_result[0]}')
            else:
                search_date = "2025/01/01"  # Fallback
                write_progress('Using fallback date (invalid date format found)')
        else:
            search_date = "2025/01/01"  # No payslips yet, start from beginning of year
            write_progress('No payslips found in database - starting from 2025/01/01')
        
        write_progress(f'Searching Gmail for payslips after: {search_date}')
        write_progress('Step 2: Connecting to Gmail API...')
        
        download_process = subprocess.Popen(
            [sys.executable, 'scripts/download_runsheets_gmail.py', '--payslips', f'--date={search_date}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        write_progress('Step 3: Downloading payslips from Gmail (this may take up to 2 minutes)...')
        
        try:
            download_stdout, download_stderr = download_process.communicate(timeout=300)  # 5 minutes
        except subprocess.TimeoutExpired:
            download_process.kill()
            write_progress('ERROR: Gmail download timed out after 5 minutes')
            return jsonify({
                'success': False,
                'error': 'Gmail download timed out after 5 minutes. Check Gmail credentials and network connection.',
                'output': 'Timeout occurred during Gmail download'
            }), 500
        
        if download_process.returncode != 0:
            log_settings_action('SYNC_PAYSLIPS', f'Gmail download failed: {download_stderr}', 'WARNING')
            log_settings_action('SYNC_PAYSLIPS', 'Falling back to processing local payslips only')
            download_stdout = "Gmail download failed - processing local files only"
            # Continue to Step 2 instead of failing
        
        log_settings_action('SYNC_PAYSLIPS', f'Gmail download complete: {download_stdout[:200]}...')
        
        # Step 2: Extract payslips to database
        log_settings_action('SYNC_PAYSLIPS', 'Step 2: Extracting payslips to database...')
        
        process = subprocess.Popen(
            [sys.executable, 'scripts/extract_payslips.py', '--recent', '7'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=180)
        
        if process.returncode == 0:
            log_settings_action('SYNC_PAYSLIPS', f'Success - Output: {stdout[:200]}...')
            combined_output = f"=== Gmail Download ===\n{download_stdout}\n\n=== Payslip Extraction ===\n{stdout}"
            return jsonify({
                'success': True,
                'message': 'Payslips downloaded from Gmail and synced successfully',
                'output': combined_output
            })
        else:
            log_settings_action('SYNC_PAYSLIPS', f'Failed - Return code: {process.returncode}, Error: {stderr}', 'ERROR')
            return jsonify({
                'success': False,
                'error': stderr or 'Sync failed',
                'output': stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        log_settings_action('SYNC_PAYSLIPS', 'Sync timed out after 3 minutes', 'ERROR')
        return jsonify({
            'success': False,
            'error': 'Sync timed out (took longer than 3 minutes)'
        }), 500
    except Exception as e:
        log_settings_action('SYNC_PAYSLIPS', f'Exception: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/sync-runsheets', methods=['POST'])
def api_sync_runsheets():
    """Download run sheets from Gmail and sync to database."""
    log_settings_action('SYNC_RUNSHEETS', 'Starting run sheets sync with Gmail download')
    
    try:
        from datetime import timedelta
        
        # Step 1: Check last run sheet date and download only newer ones
        log_settings_action('SYNC_RUNSHEETS', 'Step 1: Checking for new run sheets since last download...')
        
        # Get the most recent run sheet date from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM run_sheet_jobs WHERE date IS NOT NULL AND date != ''")
        last_runsheet_result = cursor.fetchone()
        conn.close()
        
        # Determine the date to search from
        if last_runsheet_result and last_runsheet_result[0]:
            # Convert DD/MM/YYYY to YYYY/MM/DD for Gmail search
            last_date_parts = last_runsheet_result[0].split('/')
            if len(last_date_parts) == 3:
                search_date = f"{last_date_parts[2]}/{last_date_parts[1]}/{last_date_parts[0]}"
            else:
                # Fallback to yesterday
                yesterday = datetime.now() - timedelta(days=1)
                search_date = yesterday.strftime('%Y/%m/%d')
        else:
            # No run sheets yet, start from beginning of year
            search_date = "2025/01/01"
        
        log_settings_action('SYNC_RUNSHEETS', f'Searching for run sheets after: {search_date}')
        
        download_process = subprocess.Popen(
            [sys.executable, 'scripts/download_runsheets_gmail.py', '--runsheets', '--recent'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        download_stdout, download_stderr = download_process.communicate(timeout=300)
        
        if download_process.returncode != 0:
            log_settings_action('SYNC_RUNSHEETS', f'Gmail download failed: {download_stderr}', 'ERROR')
            return jsonify({
                'success': False,
                'error': f'Gmail download failed: {download_stderr}',
                'output': download_stdout
            }), 500
        
        log_settings_action('SYNC_RUNSHEETS', f'Gmail download complete: {download_stdout[:200]}...')
        
        # Check if script exists
        script_path = Path('scripts/import_run_sheets.py')
        if not script_path.exists():
            log_settings_action('SYNC_RUNSHEETS', f'Script not found: {script_path}', 'ERROR')
            return jsonify({
                'success': False,
                'error': f'Script not found: {script_path}'
            }), 500
        
        # Create progress log file
        progress_log = Path('logs/runsheet_sync_progress.log')
        progress_log.parent.mkdir(exist_ok=True)
        
        # Clear previous progress log
        with open(progress_log, 'w') as f:
            f.write(f"Starting run sheets sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Step 1: Gmail download completed\n")
            f.write(f"Step 2: Starting import to database...\n")
        
        # Run process with output redirected to log file
        with open(progress_log, 'a') as log_file:
            process = subprocess.Popen(
                [sys.executable, str(script_path), '--recent', '7'],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(Path.cwd())
            )
        
        # Wait for process (5 minutes should be plenty for recent files only)
        try:
            process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            process.kill()
            raise
        
        # Read the output from log file
        with open(progress_log, 'r') as f:
            stdout = f.read()
        
        if process.returncode == 0:
            log_settings_action('SYNC_RUNSHEETS', f'Success - Output preview: {stdout[:500]}...')
            combined_output = f"=== Gmail Download ===\n{download_stdout}\n\n=== Run Sheets Import ===\n{stdout}"
            return jsonify({
                'success': True,
                'message': 'Run sheets downloaded from Gmail and synced successfully',
                'output': combined_output
            })
        else:
            log_settings_action('SYNC_RUNSHEETS', f'Failed - Return code: {process.returncode}', 'ERROR')
            return jsonify({
                'success': False,
                'error': 'Sync failed',
                'output': stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        log_settings_action('SYNC_RUNSHEETS', 'Sync timed out after 5 minutes', 'ERROR')
        return jsonify({
            'success': False,
            'error': 'Sync timed out (took longer than 5 minutes). This may indicate a problem with the import script.'
        }), 500
    except Exception as e:
        log_settings_action('SYNC_RUNSHEETS', f'Exception: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/payslip-sync-progress', methods=['GET'])
def api_get_payslip_sync_progress():
    """Get current payslip sync progress from log file."""
    try:
        progress_file = Path('logs/payslip_sync_progress.log')
        if progress_file.exists():
            with open(progress_file, 'r') as f:
                lines = f.readlines()
            return jsonify({
                'success': True,
                'progress': ''.join(lines[-10:])  # Last 10 lines
            })
        else:
            return jsonify({
                'success': True,
                'progress': 'No progress available'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/sync-progress', methods=['GET'])
def api_get_sync_progress():
    """Get current sync progress from log file."""
    try:
        progress_log = Path('logs/runsheet_sync_progress.log')
        if not progress_log.exists():
            return jsonify({
                'success': True,
                'progress': '',
                'lines': 0
            })
        
        # Read all lines
        with open(progress_log, 'r') as f:
            content = f.read()
            lines = content.split('\n')
        
        return jsonify({
            'success': True,
            'progress': content,
            'lines': len(lines)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/sync-missing-runsheets', methods=['POST'])
def api_sync_missing_runsheets():
    """Find and download missing run sheets from the last 30 days."""
    log_settings_action('SYNC_MISSING_RUNSHEETS', 'Starting missing run sheets check and download')
    
    try:
        # Run the missing sheets downloader
        download_process = subprocess.Popen(
            [sys.executable, 'scripts/download_runsheets_gmail.py', '--missing'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            download_stdout, download_stderr = download_process.communicate(timeout=300)  # 5 minutes
        except subprocess.TimeoutExpired:
            download_process.kill()
            log_settings_action('SYNC_MISSING_RUNSHEETS', 'ERROR: Missing sheets download timed out after 5 minutes', 'WARNING')
            return jsonify({
                'success': False,
                'error': 'Missing sheets download timed out after 5 minutes. Check Gmail credentials and network connection.',
                'output': 'Timeout occurred during missing sheets download'
            }), 500
        
        if download_process.returncode != 0:
            log_settings_action('SYNC_MISSING_RUNSHEETS', f'Missing sheets download failed: {download_stderr}', 'WARNING')
            return jsonify({
                'success': False,
                'error': f'Missing sheets download failed: {download_stderr}',
                'output': download_stdout
            }), 500
        
        log_settings_action('SYNC_MISSING_RUNSHEETS', f'Missing sheets download complete: {download_stdout[:200]}...')
        
        # Step 2: Import the downloaded files
        log_settings_action('SYNC_MISSING_RUNSHEETS', 'Step 2: Importing downloaded run sheets...')
        
        import_process = subprocess.Popen(
            [sys.executable, 'scripts/import_run_sheets.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            import_stdout, import_stderr = import_process.communicate(timeout=300)  # 5 minutes
        except subprocess.TimeoutExpired:
            import_process.kill()
            log_settings_action('SYNC_MISSING_RUNSHEETS', 'ERROR: Import timed out after 5 minutes', 'WARNING')
            return jsonify({
                'success': False,
                'error': 'Import timed out after 5 minutes.',
                'output': download_stdout + '\n\nImport timeout occurred'
            }), 500
        
        if import_process.returncode != 0:
            log_settings_action('SYNC_MISSING_RUNSHEETS', f'Import failed: {import_stderr}', 'WARNING')
            return jsonify({
                'success': False,
                'error': f'Download succeeded but import failed: {import_stderr}',
                'output': download_stdout + '\n\nImport failed: ' + import_stderr
            }), 500
        
        log_settings_action('SYNC_MISSING_RUNSHEETS', f'Missing sheets sync complete: {import_stdout[:200]}...')
        
        return jsonify({
            'success': True,
            'message': 'Missing run sheets check and sync completed successfully',
            'output': download_stdout + '\n\n' + import_stdout
        })
        
    except Exception as e:
        log_settings_action('SYNC_MISSING_RUNSHEETS', f'Unexpected error: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': f'Unexpected error during missing sheets sync: {str(e)}',
            'output': ''
        }), 500


@data_bp.route('/reorganize-runsheets', methods=['POST'])
def api_reorganize_runsheets():
    """Reorganize run sheets by date and driver."""
    try:
        data = request.json
        dry_run = data.get('dry_run', False)
        
        log_settings_action('REORGANIZE', f'Starting reorganization (dry_run={dry_run})')
        
        cmd = [sys.executable, 'scripts/reorganize_runsheets.py']
        if dry_run:
            cmd.append('--dry-run')
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=600)
        
        if process.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Reorganization complete' if not dry_run else 'Dry run complete',
                'output': stdout,
                'dry_run': dry_run
            })
        else:
            return jsonify({
                'success': False,
                'error': stderr or 'Reorganization failed',
                'output': stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Reorganization timed out (took longer than 10 minutes)'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/backup', methods=['POST'])
def api_backup_database():
    """Create a backup of the database."""
    try:
        # Create Backups directory if it doesn't exist
        backup_dir = Path('Backups')
        backup_dir.mkdir(exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'payslips_backup_{timestamp}.db'
        
        # Copy database
        shutil.copy2('data/payslips.db', backup_file)
        
        # Get file size
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        
        return jsonify({
            'success': True,
            'message': f'Backup created successfully',
            'filename': backup_file.name,
            'size_mb': round(size_mb, 2),
            'path': str(backup_file)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/export-runsheets', methods=['GET'])
def api_export_runsheets():
    """Export run sheets to CSV."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT date, driver, jobs_on_run, job_number, customer, activity, 
                       priority, job_address, postcode, notes, source_file
                FROM run_sheet_jobs
                ORDER BY date DESC, job_number
            """)
            
            rows = cursor.fetchall()
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Date', 'Driver', 'Jobs on Run', 'Job Number', 'Customer', 
                            'Activity', 'Priority', 'Address', 'Postcode', 'Notes', 'Source File'])
            
            # Write data
            writer.writerows(rows)
            
            # Create response
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=runsheets_export.csv'
            
            return response
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/export-payslips', methods=['GET'])
def api_export_payslips():
    """Export payslips to CSV."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT week_ending, week_number, tax_year, gross_pay, tax, ni, 
                       pension, net_pay, hours, hourly_rate
                FROM payslips
                ORDER BY week_ending DESC
            """)
            
            rows = cursor.fetchall()
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Week Ending', 'Week Number', 'Tax Year', 'Gross Pay', 'Tax', 
                            'NI', 'Pension', 'Net Pay', 'Hours', 'Hourly Rate'])
            
            # Write data
            writer.writerows(rows)
            
            # Create response
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=payslips_export.csv'
            
            return response
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/clear-runsheets', methods=['POST'])
def api_clear_runsheets():
    """Clear all run sheet data."""
    try:
        deleted = RunsheetModel.clear_all_runsheets()
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted} run sheet records'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/clear-payslips', methods=['POST'])
def api_clear_payslips():
    """Clear all payslip data."""
    try:
        result = PayslipModel.clear_all_payslips()
        return jsonify({
            'success': True,
            'message': f'Deleted {result["deleted_payslips"]} payslips and {result["deleted_jobs"]} job items'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/clear-all', methods=['POST'])
def api_clear_all():
    """Clear entire database."""
    try:
        # Clear all data using models
        runsheet_deleted = RunsheetModel.clear_all_runsheets()
        payslip_result = PayslipModel.clear_all_payslips()
        attendance_deleted = AttendanceModel.clear_all_records()
        settings_deleted = SettingsModel.clear_all_settings()
        
        return jsonify({
            'success': True,
            'message': f'Database cleared: {payslip_result["deleted_payslips"]} payslips, {payslip_result["deleted_jobs"]} jobs, {runsheet_deleted} run sheets, {attendance_deleted} attendance records, {settings_deleted} settings'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/intelligent-sync', methods=['POST'])
def api_intelligent_sync():
    """Perform intelligent sync based on data analysis."""
    try:
        sync_type = request.json.get('type', 'auto') if request.json else 'auto'
        result = DataService.perform_intelligent_sync(sync_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/validate-integrity', methods=['GET'])
def api_validate_integrity():
    """Comprehensive data integrity validation."""
    try:
        validation = DataService.validate_data_integrity()
        return jsonify(validation)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/intelligent-backup', methods=['POST'])
def api_intelligent_backup():
    """Create intelligent backup with metadata."""
    try:
        backup_type = request.json.get('type', 'manual') if request.json else 'manual'
        result = DataService.create_intelligent_backup(backup_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/optimize-database', methods=['POST'])
def api_optimize_database():
    """Optimize database performance."""
    try:
        result = DataService.optimize_database()
        return jsonify({
            'success': True,
            'optimization_results': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/database/info', methods=['GET'])
def api_database_info():
    """Get database information including size and statistics."""
    try:
        # Get database file size
        db_path = Path(DB_PATH)
        if db_path.exists():
            size_bytes = db_path.stat().st_size
        else:
            size_bytes = 0
        
        # Get record counts
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count payslips
            cursor.execute("SELECT COUNT(*) FROM payslips")
            payslips_count = cursor.fetchone()[0]
            
            # Count run sheets
            cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs")
            runsheets_count = cursor.fetchone()[0]
            
            # Count unique jobs
            cursor.execute("SELECT COUNT(DISTINCT job_number) FROM run_sheet_jobs WHERE job_number IS NOT NULL AND job_number != ''")
            jobs_count = cursor.fetchone()[0]
            
            # Count attendance records
            cursor.execute("SELECT COUNT(*) FROM attendance")
            attendance_count = cursor.fetchone()[0]
        
        return jsonify({
            'success': True,
            'size_bytes': size_bytes,
            'size_mb': round(size_bytes / (1024 * 1024), 2),
            'records': {
                'payslips': payslips_count,
                'runsheets': runsheets_count,
                'jobs': jobs_count,
                'attendance': attendance_count
            },
            'database_path': str(db_path)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
