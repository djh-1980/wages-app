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
            # Convert DD/MM/YYYY to datetime, then subtract 1 day (Gmail 'after:' is exclusive)
            last_date_parts = last_payslip_result[0].split('/')
            if len(last_date_parts) == 3:
                last_date = datetime(int(last_date_parts[2]), int(last_date_parts[1]), int(last_date_parts[0]))
                # Subtract 1 day to ensure we catch the last date (since Gmail 'after:' is exclusive)
                search_from = last_date - timedelta(days=1)
                search_date = search_from.strftime('%Y/%m/%d')
                write_progress(f'Last payslip found: {last_payslip_result[0]}')
            else:
                search_date = "2025/01/01"  # Fallback
                write_progress('Using fallback date (invalid date format found)')
        else:
            search_date = "2025/01/01"  # No payslips yet, start from beginning of year
            write_progress('No payslips found in database - starting from 2025/01/01')
        
        write_progress(f'Latest payslip: {last_payslip_result[0] if last_payslip_result and last_payslip_result[0] else "None"}, searching after: {search_date}')
        write_progress('Step 2: Connecting to Gmail API...')
        
        download_process = subprocess.Popen(
            [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--payslips', f'--date={search_date}'],
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
            [sys.executable, 'scripts/production/extract_payslips.py', '--recent', '7'],
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
    """Quick sync - download, organize, and import the latest runsheet from Gmail."""
    log_settings_action('SYNC_RUNSHEETS', 'Starting quick sync for latest runsheet')
    
    try:
        # Step 1: Download from Gmail with --recent (gets last 7 days, organizes & imports automatically)
        download_process = subprocess.run(
            [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--runsheets', '--recent'],
            capture_output=True,
            text=True,
            timeout=120  # Allow 2 minutes for download + organize + import
        )
        
        if download_process.returncode != 0:
            log_settings_action('SYNC_RUNSHEETS', f'Sync failed: {download_process.stderr}', 'ERROR')
            return jsonify({
                'success': False,
                'error': f'Sync failed: {download_process.stderr}',
                'output': download_process.stdout
            }), 500
        
        log_settings_action('SYNC_RUNSHEETS', f'Success - sync complete')
        
        return jsonify({
            'success': True,
            'message': 'Latest runsheet downloaded, organized, and imported successfully',
            'output': download_process.stdout
        })
            
    except subprocess.TimeoutExpired:
        log_settings_action('SYNC_RUNSHEETS', 'Sync timed out', 'ERROR')
        return jsonify({
            'success': False,
            'error': 'Sync timed out (took longer than 2 minutes)'
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
            [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--missing'],
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
            [sys.executable, 'scripts/production/import_run_sheets.py'],
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
    """Create a compressed backup of the database."""
    try:
        import gzip
        
        # Create backups directory if it doesn't exist
        backup_dir = Path('data/database/backups')
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'payslips_backup_{timestamp}.db.gz'
        
        # Compress and copy database
        with open('data/database/payslips.db', 'rb') as f_in:
            with gzip.open(backup_file, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Get compressed file size
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        
        # Get original size for comparison
        original_size_mb = Path('data/database/payslips.db').stat().st_size / (1024 * 1024)
        compression_ratio = (1 - (size_mb / original_size_mb)) * 100 if original_size_mb > 0 else 0
        
        return jsonify({
            'success': True,
            'message': f'Backup created successfully (compressed {compression_ratio:.1f}%)',
            'filename': backup_file.name,
            'size_mb': round(size_mb, 2),
            'original_size_mb': round(original_size_mb, 2),
            'path': str(backup_file)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/upload-backup', methods=['POST'])
def api_upload_backup():
    """Upload a database backup file."""
    try:
        # Check if file was uploaded
        if 'backup_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['backup_file']
        
        # Check if filename is empty
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Validate file extension
        is_compressed = file.filename.endswith('.db.gz') or file.filename.endswith('.gz')
        is_db = file.filename.endswith('.db')
        
        if not (is_compressed or is_db):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only .db or .db.gz files are allowed'
            }), 400
        
        # Create backups directory if it doesn't exist
        backup_dir = Path('data/database/backups')
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_name = Path(file.filename).stem
        if file.filename.endswith('.db.gz'):
            original_name = Path(original_name).stem  # Remove .db from .db.gz
        
        backup_file = backup_dir / f'{original_name}_{timestamp}.db.gz' if is_compressed else backup_dir / f'{original_name}_{timestamp}.db'
        
        # Save the uploaded file
        file.save(str(backup_file))
        
        # Get file size
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        
        # Verify it's a valid SQLite database (decompress if needed)
        try:
            import gzip
            import tempfile
            
            if is_compressed:
                # Decompress to temp file for validation
                with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
                    with gzip.open(backup_file, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp_file)
                    temp_db_path = tmp_file.name
                
                try:
                    conn = sqlite3.connect(temp_db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    conn.close()
                    
                    if not tables:
                        backup_file.unlink()
                        Path(temp_db_path).unlink()
                        return jsonify({
                            'success': False,
                            'error': 'Invalid database file - no tables found'
                        }), 400
                finally:
                    if Path(temp_db_path).exists():
                        Path(temp_db_path).unlink()
            else:
                conn = sqlite3.connect(str(backup_file))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                
                if not tables:
                    backup_file.unlink()
                    return jsonify({
                        'success': False,
                        'error': 'Invalid database file - no tables found'
                    }), 400
        except (sqlite3.Error, gzip.BadGzipFile) as e:
            if backup_file.exists():
                backup_file.unlink()
            return jsonify({
                'success': False,
                'error': f'Invalid database file: {str(e)}'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Backup uploaded successfully',
            'filename': backup_file.name,
            'size_mb': round(size_mb, 2)
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
        return jsonify({
            'success': True,
            'validation': validation
        })
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


@data_bp.route('/stats', methods=['GET'])
def api_get_stats():
    """Get database statistics for the settings page."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get payslips count
        cursor.execute("SELECT COUNT(*) FROM payslips")
        payslips_count = cursor.fetchone()[0]
        
        # Get runsheets count
        cursor.execute("SELECT COUNT(DISTINCT date) FROM run_sheet_jobs WHERE date IS NOT NULL AND date != ''")
        runsheets_count = cursor.fetchone()[0]
        
        # Get total jobs count
        cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs")
        jobs_count = cursor.fetchone()[0]
        
        # Get database size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size_bytes = cursor.fetchone()[0]
        
        conn.close()
        
        # Format database size
        if db_size_bytes < 1024:
            db_size = f"{db_size_bytes} B"
        elif db_size_bytes < 1024 * 1024:
            db_size = f"{db_size_bytes / 1024:.1f} KB"
        elif db_size_bytes < 1024 * 1024 * 1024:
            db_size = f"{db_size_bytes / (1024 * 1024):.1f} MB"
        else:
            db_size = f"{db_size_bytes / (1024 * 1024 * 1024):.1f} GB"
        
        return jsonify({
            'success': True,
            'payslips': payslips_count,
            'runsheets': runsheets_count,
            'jobs': jobs_count,
            'size': db_size,
            'total_records': payslips_count + jobs_count
        })
        
    except Exception as e:
        log_settings_action('GET_STATS', f'Failed to get database stats: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e),
            'payslips': 0,
            'runsheets': 0,
            'jobs': 0,
            'size': '0 B',
            'total_records': 0
        }), 500


@data_bp.route('/periodic-sync/status', methods=['GET'])
def api_get_periodic_sync_status():
    """Get periodic sync service status."""
    try:
        from ..services.periodic_sync import periodic_sync_service
        status = periodic_sync_service.get_sync_status()
        
        return jsonify({
            'success': True,
            **status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/periodic-sync/start', methods=['POST'])
def api_start_periodic_sync():
    """Start the periodic sync service."""
    try:
        from ..services.periodic_sync import periodic_sync_service
        periodic_sync_service.start_periodic_sync()
        
        log_settings_action('PERIODIC_SYNC', 'Periodic sync service started')
        
        return jsonify({
            'success': True,
            'message': 'Periodic sync service started'
        })
    except Exception as e:
        log_settings_action('PERIODIC_SYNC', f'Failed to start periodic sync: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/periodic-sync/stop', methods=['POST'])
def api_stop_periodic_sync():
    """Stop the periodic sync service."""
    try:
        from ..services.periodic_sync import periodic_sync_service
        periodic_sync_service.stop_periodic_sync()
        
        log_settings_action('PERIODIC_SYNC', 'Periodic sync service stopped')
        
        return jsonify({
            'success': True,
            'message': 'Periodic sync service stopped'
        })
    except Exception as e:
        log_settings_action('PERIODIC_SYNC', f'Failed to stop periodic sync: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/periodic-sync/force', methods=['POST'])
def api_force_sync():
    """Force an immediate sync."""
    try:
        from ..services.periodic_sync import periodic_sync_service
        success = periodic_sync_service.force_sync_now()
        
        if success:
            log_settings_action('PERIODIC_SYNC', 'Manual sync triggered')
            return jsonify({
                'success': True,
                'message': 'Sync started in background'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Periodic sync service not running'
            }), 400
            
    except Exception as e:
        log_settings_action('PERIODIC_SYNC', f'Failed to force sync: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/sync-runsheets-payslips', methods=['POST'])
def api_sync_runsheets_payslips():
    """Sync runsheet data with payslip data to update prices and addresses."""
    log_settings_action('SYNC_RUNSHEETS_PAYSLIPS', 'Starting runsheet-payslip sync')
    
    try:
        # Run the sync script
        result = subprocess.run(
            [sys.executable, 'scripts/sync_runsheets_with_payslips.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            log_settings_action('SYNC_RUNSHEETS_PAYSLIPS', 'Sync completed successfully')
            return jsonify({
                'success': True,
                'message': 'Runsheet data synced with payslips',
                'output': result.stdout
            })
        else:
            log_settings_action('SYNC_RUNSHEETS_PAYSLIPS', f'Sync failed: {result.stderr}', 'ERROR')
            return jsonify({
                'success': False,
                'error': result.stderr,
                'output': result.stdout
            }), 500
            
    except Exception as e:
        log_settings_action('SYNC_RUNSHEETS_PAYSLIPS', f'Sync failed: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/backups/list', methods=['GET'])
def api_list_backups():
    """List all available database backups."""
    try:
        backup_dir = Path('data/database/backups')
        if not backup_dir.exists():
            return jsonify({
                'success': True,
                'backups': []
            })
        
        backups = []
        # Look for both .db and .db.gz files
        for pattern in ['*.db', '*.db.gz']:
            for backup_file in backup_dir.glob(pattern):
                stat = backup_file.stat()
                
                # Try to parse timestamp from filename (format: *_YYYYMMDD_HHMMSS.db or .db.gz)
                created_timestamp = stat.st_mtime  # Default to file modification time
                try:
                    import re
                    match = re.search(r'_(\d{8})_(\d{6})\.db', backup_file.name)
                    if match:
                        date_str = match.group(1)  # YYYYMMDD
                        time_str = match.group(2)  # HHMMSS
                        # Parse to datetime
                        dt = datetime.strptime(f'{date_str}_{time_str}', '%Y%m%d_%H%M%S')
                        created_timestamp = dt.timestamp()
                except:
                    pass  # Fall back to file mtime if parsing fails
                
                backups.append({
                    'filename': backup_file.name,
                    'size': stat.st_size,
                    'created': created_timestamp
                })
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'backups': backups
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/restore', methods=['POST'])
def api_restore_database():
    """Restore database from a backup file."""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'No filename provided'
            }), 400
        
        backup_path = Path('data/database/backups') / filename
        
        if not backup_path.exists():
            return jsonify({
                'success': False,
                'error': f'Backup file not found: {filename}'
            }), 404
        
        # Create a backup of current database before restoring
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_backup = Path('data/database/backups') / f'pre_restore_backup_{timestamp}.db'
        shutil.copy2(DB_PATH, current_backup)
        
        # Restore the backup
        shutil.copy2(backup_path, DB_PATH)
        
        log_settings_action('RESTORE_DATABASE', f'Database restored from {filename}')
        
        return jsonify({
            'success': True,
            'message': f'Database restored from {filename}',
            'backup_created': current_backup.name
        })
    except Exception as e:
        log_settings_action('RESTORE_DATABASE', f'Restore failed: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/backups/download/<filename>', methods=['GET'])
def api_download_backup(filename):
    """Download a backup file."""
    try:
        # Get the absolute path to the project root
        from pathlib import Path
        import os
        
        # Try multiple possible locations
        possible_paths = [
            Path('data/database/backups') / filename,
            Path('../data/database/backups') / filename,
            Path(__file__).parent.parent.parent / 'data' / 'database' / 'backups' / filename
        ]
        
        backup_path = None
        for path in possible_paths:
            print(f"Trying path: {path.resolve()}")
            if path.exists():
                backup_path = path
                print(f"Found backup at: {path.resolve()}")
                break
        
        if not backup_path:
            return jsonify({
                'success': False,
                'error': f'Backup file not found: {filename}. Tried paths: {[str(p) for p in possible_paths]}'
            }), 404
        
        # Security check - ensure the file is within a backups directory
        if 'backups' not in str(backup_path.resolve()):
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 403
        
        log_settings_action('DOWNLOAD_BACKUP', f'Downloaded backup: {filename}')
        
        # Convert to absolute path for send_file
        absolute_path = backup_path.resolve()
        print(f"Sending file from absolute path: {absolute_path}")
        
        return send_file(
            str(absolute_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/x-sqlite3'
        )
    except Exception as e:
        log_settings_action('DOWNLOAD_BACKUP', f'Download failed: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/backups/delete', methods=['POST'])
def api_delete_backup():
    """Delete a backup file."""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'No filename provided'
            }), 400
        
        backup_path = Path('data/database/backups') / filename
        
        if not backup_path.exists():
            return jsonify({
                'success': False,
                'error': f'Backup file not found: {filename}'
            }), 404
        
        # Delete the backup file
        backup_path.unlink()
        
        # Also delete metadata file if it exists
        metadata_path = Path('data/database/backups') / f'{backup_path.stem}_metadata.json'
        if metadata_path.exists():
            metadata_path.unlink()
        
        log_settings_action('DELETE_BACKUP', f'Deleted backup: {filename}')
        
        return jsonify({
            'success': True,
            'message': f'Backup deleted: {filename}'
        })
    except Exception as e:
        log_settings_action('DELETE_BACKUP', f'Delete failed: {str(e)}', 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/reports/custom', methods=['POST'])
def api_generate_custom_report():
    """Generate custom reports based on type and filters."""
    try:
        data = request.json
        report_type = data.get('report_type', '')
        year = data.get('year', '')
        week = data.get('week', '')
        month = data.get('month', '')
        
        if not report_type:
            return jsonify({
                'success': False,
                'error': 'Report type is required'
            }), 400
        
        # Build date filter - dates are in DD/MM/YYYY format
        date_filter = ""
        if year and week:
            # Filter by week number - get week start/end dates
            from datetime import datetime, timedelta
            year_int = int(year)
            week_int = int(week)
            # Get first day of year
            jan1 = datetime(year_int, 1, 1)
            # Calculate week start (assuming week 1 starts on first Monday)
            days_to_monday = (7 - jan1.weekday()) % 7
            week_start = jan1 + timedelta(days=days_to_monday + (week_int - 1) * 7)
            week_end = week_start + timedelta(days=6)
            
            # Generate list of dates in DD/MM/YYYY format for this week
            week_dates = []
            current = week_start
            while current <= week_end:
                week_dates.append(current.strftime('%d/%m/%Y'))
                current += timedelta(days=1)
            
            # Create IN clause for exact date matching
            date_placeholders = ','.join(['?' for _ in week_dates])
            date_filter = f"AND date IN ({date_placeholders})"
            # Store week_dates for later use in query
            week_dates_filter = week_dates
        elif year and month:
            date_filter = f"AND substr(date, 7, 4) = '{year}' AND substr(date, 4, 2) = '{int(month):02d}'"
        elif year:
            date_filter = f"AND substr(date, 7, 4) = '{year}'"
        elif month:
            date_filter = f"AND substr(date, 4, 2) = '{int(month):02d}'"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if report_type == 'earnings':
                # Earnings Summary Report
                cursor.execute(f"""
                    SELECT 
                        date, week_number, gross_pay, tax, ni, other_deductions, net_pay, status
                    FROM payslips
                    WHERE 1=1 {date_filter}
                    ORDER BY date DESC
                """)
                payslips = cursor.fetchall()
                
                total_gross = sum(p[2] or 0 for p in payslips)
                total_net = sum(p[6] or 0 for p in payslips)
                
                report_data = {
                    'total_records': len(payslips),
                    'summary': {
                        'total_gross': round(total_gross, 2),
                        'total_net': round(total_net, 2),
                        'payslips_count': len(payslips)
                    },
                    'payslips': [{
                        'date': p[0], 'week': p[1], 'gross': p[2], 'net': p[6], 'status': p[7]
                    } for p in payslips]
                }
                
            elif report_type == 'jobs':
                # Jobs Breakdown Report
                cursor.execute(f"""
                    SELECT ji.job_number, ji.customer_name, ji.amount, p.date
                    FROM job_items ji
                    LEFT JOIN payslips p ON ji.payslip_id = p.id
                    WHERE 1=1 {date_filter.replace('date', 'p.date') if date_filter else ''}
                    ORDER BY p.date DESC
                """)
                jobs = cursor.fetchall()
                
                total_amount = sum(j[2] or 0 for j in jobs)
                
                report_data = {
                    'total_records': len(jobs),
                    'summary': {
                        'total_jobs': len(jobs),
                        'total_amount': round(total_amount, 2)
                    },
                    'jobs': [{'job': j[0], 'customer': j[1], 'amount': j[2], 'date': j[3]} for j in jobs]
                }
                
            elif report_type == 'mileage':
                # Mileage Report
                cursor.execute(f"""
                    SELECT date, job_number, customer, pay_amount
                    FROM run_sheet_jobs
                    WHERE pay_amount IS NOT NULL AND pay_amount > 0
                    {date_filter.replace('date', 'run_sheet_jobs.date') if date_filter else ''}
                    ORDER BY date DESC
                """)
                mileage_data = cursor.fetchall()
                
                total_amount = sum(m[3] or 0 for m in mileage_data)
                
                report_data = {
                    'total_records': len(mileage_data),
                    'summary': {
                        'total_amount': round(total_amount, 2),
                        'total_jobs': len(mileage_data)
                    },
                    'mileage': [{'date': m[0], 'job': m[1], 'customer': m[2], 'amount': m[3]} for m in mileage_data]
                }
                
            elif report_type == 'dnco':
                # DNCO Report
                if year and week:
                    # Use week_dates for filtering
                    cursor.execute(f"""
                        SELECT date, job_number, customer, job_address, pay_amount
                        FROM run_sheet_jobs
                        WHERE UPPER(status) = 'DNCO'
                        {date_filter}
                        ORDER BY date DESC
                    """, week_dates_filter)
                else:
                    cursor.execute(f"""
                        SELECT date, job_number, customer, job_address, pay_amount
                        FROM run_sheet_jobs
                        WHERE UPPER(status) = 'DNCO'
                        {date_filter}
                        ORDER BY date DESC
                    """)
                dnco_jobs = cursor.fetchall()
                
                # Calculate estimated loss using historical data for each customer
                total_loss = 0
                dnco_jobs_with_estimates = []
                
                for job in dnco_jobs:
                    estimated_amount = job[4]  # Use pay_amount if exists
                    
                    if not estimated_amount:
                        # Look up average pay for this customer from historical completed jobs
                        cursor.execute("""
                            SELECT AVG(pay_amount)
                            FROM run_sheet_jobs
                            WHERE customer = ? AND pay_amount IS NOT NULL AND pay_amount > 0
                            AND UPPER(status) != 'DNCO'
                        """, (job[2],))
                        avg_result = cursor.fetchone()
                        
                        if avg_result and avg_result[0]:
                            estimated_amount = round(avg_result[0], 2)
                        else:
                            # If no historical data, use £15 default
                            estimated_amount = 15.0
                    
                    total_loss += estimated_amount
                    dnco_jobs_with_estimates.append({
                        'date': job[0],
                        'job': job[1],
                        'customer': job[2],
                        'address': job[3],
                        'amount': estimated_amount
                    })
                
                report_data = {
                    'total_records': len(dnco_jobs),
                    'summary': {
                        'total_dnco': len(dnco_jobs),
                        'estimated_loss': round(total_loss, 2)
                    },
                    'dnco_jobs': dnco_jobs_with_estimates
                }
                
            elif report_type == 'earnings_discrepancy':
                # Earnings Discrepancy Report - Compare payslip vs runsheet earnings by week
                # Get all payslips for the selected period
                cursor.execute(f"""
                    SELECT p.week_number, p.tax_year, p.net_payment, p.period_end
                    FROM payslips p
                    WHERE p.tax_year = ?
                    ORDER BY p.week_number
                """, (year if year else '2025',))
                payslips = cursor.fetchall()
                
                discrepancies = []
                total_discrepancy = 0
                
                for payslip in payslips:
                    week_num, tax_year, payslip_amount, period_end = payslip
                    
                    if not period_end:
                        continue
                    
                    # Calculate week start (period_end is Saturday, so subtract 6 days)
                    from datetime import datetime, timedelta
                    try:
                        saturday = datetime.strptime(period_end, '%d/%m/%Y')
                        sunday = saturday - timedelta(days=6)
                        
                        # Generate all dates in the week
                        week_dates = []
                        current = sunday
                        for _ in range(7):
                            week_dates.append(current.strftime('%d/%m/%Y'))
                            current += timedelta(days=1)
                        
                        # Get runsheet earnings for this week (include completed and extra)
                        placeholders = ','.join(['?' for _ in week_dates])
                        cursor.execute(f"""
                            SELECT SUM(pay_amount)
                            FROM run_sheet_jobs
                            WHERE date IN ({placeholders})
                            AND UPPER(status) IN ('COMPLETED', 'EXTRA')
                        """, week_dates)
                        
                        runsheet_result = cursor.fetchone()
                        runsheet_amount = runsheet_result[0] if runsheet_result and runsheet_result[0] else 0
                        
                        # Get deductions from payslip for this week
                        cursor.execute("""
                            SELECT 
                                ji.client,
                                SUM(ji.amount) as total_amount
                            FROM job_items ji
                            JOIN payslips p ON ji.payslip_id = p.id
                            WHERE p.period_end = ?
                            AND ji.client IN ('Deduction', 'Company Margin')
                            GROUP BY ji.client
                        """, (period_end,))
                        
                        deduction_amount = 0
                        company_margin_amount = 0
                        
                        for row in cursor.fetchall():
                            if row[0] == 'Deduction':
                                deduction_amount = abs(row[1] or 0)
                            elif row[0] == 'Company Margin':
                                company_margin_amount = abs(row[1] or 0)
                        
                        # Subtract deductions from runsheet amount (to match Weekly Summary)
                        total_deductions = deduction_amount + company_margin_amount
                        runsheet_amount_after_deductions = runsheet_amount - total_deductions
                        
                        # Calculate discrepancy
                        discrepancy = runsheet_amount_after_deductions - (payslip_amount or 0)
                        
                        # Only include weeks with discrepancies
                        if abs(discrepancy) > 0.01:  # Ignore tiny differences
                            total_discrepancy += discrepancy
                            discrepancies.append({
                                'week': week_num,
                                'year': tax_year,
                                'payslip_amount': round(payslip_amount or 0, 2),
                                'runsheet_amount': round(runsheet_amount_after_deductions, 2),
                                'discrepancy': round(discrepancy, 2),
                                'period_end': period_end
                            })
                    except Exception as e:
                        print(f"Error processing week {week_num}: {e}")
                        continue
                
                report_data = {
                    'total_records': len(discrepancies),
                    'summary': {
                        'weeks_with_discrepancy': len(discrepancies),
                        'total_discrepancy': round(total_discrepancy, 2)
                    },
                    'discrepancies': discrepancies
                }
                
            elif report_type == 'discrepancies':
                # Discrepancies Report
                cursor.execute(f"""
                    SELECT ji.job_number, ji.customer_name, ji.amount, p.date
                    FROM job_items ji
                    LEFT JOIN payslips p ON ji.payslip_id = p.id
                    WHERE ji.job_number NOT IN (SELECT job_number FROM run_sheet_jobs WHERE job_number IS NOT NULL)
                    {date_filter.replace('date', 'p.date') if date_filter else ''}
                    ORDER BY p.date DESC
                """)
                missing = cursor.fetchall()
                
                total_value = sum(m[2] or 0 for m in missing)
                
                report_data = {
                    'total_records': len(missing),
                    'summary': {
                        'missing_jobs': len(missing),
                        'total_value': round(total_value, 2)
                    },
                    'discrepancies': [{'job': m[0], 'customer': m[1], 'amount': m[2], 'date': m[3]} for m in missing]
                }
                
            elif report_type == 'missing-runsheets':
                # Missing Run Sheets
                cursor.execute(f"""
                    SELECT DISTINCT date FROM payslips
                    WHERE date NOT IN (SELECT DISTINCT date FROM run_sheet_jobs WHERE date IS NOT NULL)
                    {date_filter}
                    ORDER BY date DESC
                """)
                missing_dates = cursor.fetchall()
                
                report_data = {
                    'total_records': len(missing_dates),
                    'summary': {'missing_dates': len(missing_dates)},
                    'dates': [{'date': d[0]} for d in missing_dates]
                }
                
            elif report_type == 'missing-payslips':
                # Missing Payslips
                cursor.execute(f"""
                    SELECT DISTINCT date FROM run_sheet_jobs
                    WHERE date NOT IN (SELECT DISTINCT date FROM payslips WHERE date IS NOT NULL)
                    {date_filter.replace('date', 'run_sheet_jobs.date') if date_filter else ''}
                    ORDER BY date DESC
                """)
                missing_dates = cursor.fetchall()
                
                report_data = {
                    'total_records': len(missing_dates),
                    'summary': {'missing_dates': len(missing_dates)},
                    'dates': [{'date': d[0]} for d in missing_dates]
                }
                
            elif report_type == 'comprehensive':
                # Comprehensive Report
                cursor.execute(f"SELECT COUNT(*), SUM(gross_pay), SUM(net_pay) FROM payslips WHERE 1=1 {date_filter}")
                earnings = cursor.fetchone()
                
                cursor.execute(f"""
                    SELECT COUNT(*), SUM(amount) FROM job_items ji
                    LEFT JOIN payslips p ON ji.payslip_id = p.id
                    WHERE 1=1 {date_filter.replace('date', 'p.date') if date_filter else ''}
                """)
                jobs = cursor.fetchone()
                
                report_data = {
                    'total_records': (earnings[0] or 0) + (jobs[0] or 0),
                    'summary': {
                        'payslips': earnings[0] or 0,
                        'total_gross': round(earnings[1] or 0, 2),
                        'total_net': round(earnings[2] or 0, 2),
                        'total_jobs': jobs[0] or 0,
                        'total_job_value': round(jobs[1] or 0, 2)
                    }
                }
            else:
                return jsonify({'success': False, 'error': f'Unknown report type: {report_type}'}), 400
        
        return jsonify({'success': True, 'data': report_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_bp.route('/reports/custom/pdf', methods=['POST'])
def api_generate_custom_report_pdf():
    """Generate PDF for custom reports."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO
        from datetime import datetime, timedelta
        
        data = request.json
        report_type = data.get('report_type', '')
        year = data.get('year', '')
        week = data.get('week', '')
        month = data.get('month', '')
        
        if not report_type:
            return jsonify({'success': False, 'error': 'Report type is required'}), 400
        
        # Build date filter - same logic as main report
        date_filter = ""
        week_dates_filter = None
        
        if year and week:
            year_int = int(year)
            week_int = int(week)
            jan1 = datetime(year_int, 1, 1)
            days_to_monday = (7 - jan1.weekday()) % 7
            week_start = jan1 + timedelta(days=days_to_monday + (week_int - 1) * 7)
            week_end = week_start + timedelta(days=6)
            
            week_dates = []
            current = week_start
            while current <= week_end:
                week_dates.append(current.strftime('%d/%m/%Y'))
                current += timedelta(days=1)
            
            date_placeholders = ','.join(['?' for _ in week_dates])
            date_filter = f"AND date IN ({date_placeholders})"
            week_dates_filter = week_dates
        elif year and month:
            date_filter = f"AND substr(date, 7, 4) = '{year}' AND substr(date, 4, 2) = '{int(month):02d}'"
        elif year:
            date_filter = f"AND substr(date, 7, 4) = '{year}'"
        
        # Get report data
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if report_type == 'dnco':
                if year and week:
                    cursor.execute(f"""
                        SELECT date, job_number, customer, job_address, pay_amount
                        FROM run_sheet_jobs
                        WHERE UPPER(status) = 'DNCO'
                        {date_filter}
                        ORDER BY date DESC
                    """, week_dates_filter)
                else:
                    cursor.execute(f"""
                        SELECT date, job_number, customer, job_address, pay_amount
                        FROM run_sheet_jobs
                        WHERE UPPER(status) = 'DNCO'
                        {date_filter}
                        ORDER BY date DESC
                    """)
                dnco_jobs = cursor.fetchall()
                
                # Calculate estimated loss
                total_loss = 0
                dnco_jobs_with_estimates = []
                
                for job in dnco_jobs:
                    estimated_amount = job[4]
                    
                    if not estimated_amount:
                        cursor.execute("""
                            SELECT AVG(pay_amount)
                            FROM run_sheet_jobs
                            WHERE customer = ? AND pay_amount IS NOT NULL AND pay_amount > 0
                            AND UPPER(status) != 'DNCO'
                        """, (job[2],))
                        avg_result = cursor.fetchone()
                        
                        if avg_result and avg_result[0]:
                            estimated_amount = round(avg_result[0], 2)
                        else:
                            estimated_amount = 15.0
                    
                    total_loss += estimated_amount
                    dnco_jobs_with_estimates.append({
                        'date': job[0],
                        'job': job[1],
                        'customer': job[2],
                        'address': job[3],
                        'amount': estimated_amount
                    })
                
                report_data = {
                    'summary': {
                        'total_dnco': len(dnco_jobs),
                        'estimated_loss': round(total_loss, 2)
                    },
                    'dnco_jobs': dnco_jobs_with_estimates
                }
            else:
                return jsonify({'success': False, 'error': f'PDF export not supported for {report_type}'}), 400
        
        # Create PDF in landscape
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()
        
        # Professional Header
        # Build date range text
        date_range_text = ""
        if year and week:
            date_range_text = f"Week {week}, {year}"
        elif year and month:
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
            date_range_text = f"{month_names[int(month)]} {year}"
        elif year:
            date_range_text = f"Year {year}"
        else:
            date_range_text = "All Time"
        
        # Try to load logo
        from pathlib import Path as PDFPath
        logo_png_path = PDFPath(__file__).parent.parent.parent / 'static' / 'images' / 'logo.png'
        
        logo_element = None
        if logo_png_path.exists():
            try:
                from reportlab.platypus import Image as PDFImage
                logo_element = PDFImage(str(logo_png_path), width=40, height=40)
            except:
                pass
        
        # Header table with logo, branding and date info
        if logo_element:
            header_data = [
                [logo_element,
                 Paragraph('<b><font size=14 color="#1a73e8">TVS - Technical Courier Management System</font></b><br/><font size=12>DNCO Report</font>', styles['Normal']), 
                 Paragraph(f'<b>Period:</b> {date_range_text}<br/><b>Generated:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}', styles['Normal'])]
            ]
            header_table = Table(header_data, colWidths=[0.6*inch, 4.4*inch, 3*inch])
        else:
            header_data = [
                [Paragraph('<b><font size=14 color="#1a73e8">TVS - Technical Courier Management System</font></b><br/><font size=12>DNCO Report</font>', styles['Normal']), 
                 Paragraph(f'<b>Period:</b> {date_range_text}<br/><b>Generated:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}', styles['Normal'])]
            ]
            header_table = Table(header_data, colWidths=[5*inch, 3*inch])
        
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (-1, 0), (-1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 5))
        
        # Compact Summary and Warning in one row
        if 'summary' in report_data and report_type == 'dnco':
            combined_data = [[
                Paragraph(f'<b>Summary:</b> Estimated Loss: £{report_data["summary"]["estimated_loss"]:,.2f} | Total DNCO: {report_data["summary"]["total_dnco"]}', styles['Normal']),
                Paragraph(f'<b>⚠ Jobs Not Completed</b> - These jobs represent potential lost earnings', styles['Normal'])
            ]]
            combined_table = Table(combined_data, colWidths=[4*inch, 4*inch])
            combined_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#d1ecf1')),
                ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fff3cd')),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.black),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#856404')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(combined_table)
            elements.append(Spacer(1, 8))
        
        # DNCO jobs table
        if report_type == 'dnco' and 'dnco_jobs' in report_data:
            jobs_data = [['Date', 'Job Number', 'Customer', 'Address', 'Est. Loss']]
            for job in report_data['dnco_jobs']:
                customer = job.get('customer') or ''
                address = job.get('address') or ''
                
                jobs_data.append([
                    job.get('date', ''),
                    job.get('job', ''),
                    customer[:30] if len(customer) > 30 else customer,
                    address[:40] if len(address) > 40 else address,
                    f"£{job.get('amount', 0):.2f}"
                ])
            
            jobs_table = Table(jobs_data, colWidths=[0.9*inch, 1.1*inch, 2*inch, 3*inch, 0.9*inch])
            jobs_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]))
            elements.append(jobs_table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Generate filename
        filename = f'{report_type}_report'
        if year and week:
            filename += f'_{year}_week{week}'
        elif year and month:
            filename += f'_{year}_{month}'
        elif year:
            filename += f'_{year}'
        filename += '.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"PDF generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
