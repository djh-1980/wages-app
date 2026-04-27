"""
File upload and manual processing API routes.
Handles drag-and-drop uploads, local file processing, and hybrid sync.
"""

import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import magic
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from ..utils.logging_utils import log_settings_action
from ..database import get_db_connection

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload_api', __name__, url_prefix='/api/upload')

ALLOWED_EXTENSIONS = {'.pdf'}
ALLOWED_MIMES = {'application/pdf', 'application/octet-stream', 'text/csv', 'text/plain'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_upload_file(file):
    """Validate uploaded file for security: size, MIME type, and filename."""
    # Check size before reading whole file
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 50 * 1024 * 1024:
        raise ValueError("File exceeds 50MB limit")

    # Verify actual MIME type or file extension
    mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)
    
    # Get file extension
    filename = secure_filename(file.filename) if file.filename else ''
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Allow if MIME type is in allowed list OR file extension is .pdf
    is_valid = (mime in ALLOWED_MIMES) or (file_ext in ALLOWED_EXTENSIONS)
    
    if not is_valid:
        raise ValueError(f"File type not allowed: {mime} (extension: {file_ext})")

    # Secure filename with fallback
    if not filename:
        filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
    return filename

def get_upload_path(file_type='general'):
    """Get appropriate upload path based on file type."""
    base_paths = {
        'payslips': Path('data/processing/manual'),
        'runsheets': Path('data/processing/manual'), 
        'general': Path('data/uploads/pending')
    }
    
    path = base_paths.get(file_type, base_paths['general'])
    path.mkdir(parents=True, exist_ok=True)
    return path

@upload_bp.route('/files', methods=['POST'])
def api_upload_files():
    """Handle multiple file uploads with automatic processing."""
    try:
        log_settings_action('FILE_UPLOAD', f'Upload request received. Content-Type: {request.content_type}')
        
        if 'files' not in request.files:
            log_settings_action('FILE_UPLOAD', 'No files in request', 'ERROR')
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        file_type = request.form.get('type', 'general')  # payslips, runsheets, general
        auto_process = request.form.get('auto_process', 'true').lower() == 'true'
        overwrite = request.form.get('overwrite', 'false').lower() == 'true'
        
        log_settings_action('FILE_UPLOAD', f'Processing {len(files)} files, type: {file_type}, auto_process: {auto_process}, overwrite: {overwrite}')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        uploaded_files = []
        errors = []
        
        upload_path = get_upload_path(file_type)
        
        # Process each file
        for file in files:
            if file and file.filename:
                try:
                    # Validate file security (size, MIME type, filename)
                    filename = validate_upload_file(file)
                    
                    # Add timestamp to avoid conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    name, ext = os.path.splitext(filename)
                    
                    # Ensure we have an extension
                    if not ext:
                        ext = '.pdf'
                    
                    unique_filename = f"{name}_{timestamp}{ext}"
                    
                    file_path = upload_path / unique_filename
                    file.save(str(file_path))
                    
                    uploaded_files.append({
                        'original_name': file.filename,
                        'saved_name': unique_filename,
                        'path': str(file_path),
                        'size': file_path.stat().st_size,
                        'type': file_type
                    })
                    
                    log_settings_action('FILE_UPLOAD', f'Uploaded {file.filename} as {unique_filename}')
                    
                except ValueError as e:
                    # Security validation failed
                    error_msg = f"{file.filename}: {str(e)}"
                    errors.append(error_msg)
                    log_settings_action('FILE_UPLOAD', error_msg, 'ERROR')
                    continue
                except Exception as e:
                    error_msg = f"Failed to upload {file.filename}: {str(e)}"
                    errors.append(error_msg)
                    log_settings_action('FILE_UPLOAD', error_msg, 'ERROR')
            else:
                errors.append(f"Invalid file: {file.filename}")
        
        # Auto-process if requested (run in background to avoid timeout)
        processing_results = []
        if auto_process and uploaded_files:
            try:
                # Start processing in background thread to avoid gateway timeout
                import threading
                thread = threading.Thread(
                    target=process_uploaded_files_background,
                    args=(uploaded_files, file_type, overwrite)
                )
                thread.daemon = True
                thread.start()
                
                processing_results = [{
                    'file': f['original_name'],
                    'result': {'success': True, 'message': 'Processing started in background'}
                } for f in uploaded_files]
            except Exception as e:
                errors.append(f"Processing failed: {str(e)}")
        
        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'processing_results': processing_results,
            'errors': errors,
            'message': f'Uploaded {len(uploaded_files)} files successfully'
        })
        
    except Exception as e:
        logger.error(f'File upload failed: {e}')
        log_settings_action('FILE_UPLOAD', f'Upload failed: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

@upload_bp.route('/process-local', methods=['POST'])
def process_local_files():
    """Process files already in local directories."""
    try:
        data = request.json
        file_type = data.get('type', 'all')  # payslips, runsheets, all
        directory = data.get('directory', '')
        days_back = data.get('days_back', 7)
        
        results = []
        
        if file_type in ['payslips', 'all']:
            payslip_result = process_local_payslips(directory, days_back)
            results.append(payslip_result)
        
        if file_type in ['runsheets', 'all']:
            runsheet_result = process_local_runsheets(directory, days_back)
            results.append(runsheet_result)
        
        return jsonify({
            'success': True,
            'results': results,
            'message': 'Local file processing completed'
        })
        
    except Exception as e:
        logger.error(f'Local file processing failed: {e}')
        log_settings_action('LOCAL_PROCESS', f'Processing failed: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

@upload_bp.route('/hybrid-sync', methods=['POST'])
def hybrid_sync():
    """Intelligent hybrid sync: Gmail + local + manual processing."""
    try:
        data = request.json
        sync_mode = data.get('mode', 'smart')  # smart, force_all, local_only
        
        log_settings_action('HYBRID_SYNC', f'Starting hybrid sync in {sync_mode} mode')
        
        results = {
            'gmail_sync': None,
            'local_processing': None,
            'manual_processing': None,
            'total_processed': 0
        }
        
        # Step 1: Try Gmail sync (unless local_only mode)
        if sync_mode != 'local_only':
            try:
                gmail_result = attempt_gmail_sync()
                results['gmail_sync'] = gmail_result
                if gmail_result['success']:
                    results['total_processed'] += gmail_result.get('count', 0)
            except Exception as e:
                log_settings_action('HYBRID_SYNC', f'Gmail sync failed: {str(e)}', 'WARNING')
                results['gmail_sync'] = {'success': False, 'error': str(e)}
        
        # Step 2: Process local files
        try:
            local_result = process_all_local_files()
            results['local_processing'] = local_result
            results['total_processed'] += local_result.get('count', 0)
        except Exception as e:
            log_settings_action('HYBRID_SYNC', f'Local processing failed: {str(e)}', 'WARNING')
            results['local_processing'] = {'success': False, 'error': str(e)}
        
        # Step 3: Process manual uploads
        try:
            manual_result = process_manual_uploads()
            results['manual_processing'] = manual_result
            results['total_processed'] += manual_result.get('count', 0)
        except Exception as e:
            log_settings_action('HYBRID_SYNC', f'Manual processing failed: {str(e)}', 'WARNING')
            results['manual_processing'] = {'success': False, 'error': str(e)}
        
        # Determine overall success
        any_success = any(
            result and result.get('success', False) 
            for result in [results['gmail_sync'], results['local_processing'], results['manual_processing']]
            if result is not None
        )
        
        return jsonify({
            'success': any_success,
            'results': results,
            'message': f'Hybrid sync completed. Processed {results["total_processed"]} items total.'
        })
        
    except Exception as e:
        logger.error(f'Hybrid sync failed: {e}')
        log_settings_action('HYBRID_SYNC', f'Hybrid sync failed: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

@upload_bp.route('/scan-directories', methods=['GET'])
def scan_directories():
    """Scan for unprocessed files in various directories."""
    try:
        from app.config import Config
        directories_to_scan = [
            Path(Config.PAYSLIPS_DIR),
            Path(Config.RUNSHEETS_DIR), 
            Path('data/uploads'),
            Path('data/processing/manual')
        ]
        
        found_files = {}
        
        for directory in directories_to_scan:
            if directory.exists():
                pdf_files = list(directory.glob('**/*.pdf'))
                if pdf_files:
                    found_files[str(directory)] = [
                        {
                            'name': f.name,
                            'path': str(f),
                            'size': f.stat().st_size,
                            'modified': f.stat().st_mtime,
                            'relative_path': str(f.relative_to(directory))
                        }
                        for f in pdf_files
                    ]
        
        return jsonify({
            'success': True,
            'directories': found_files,
            'total_files': sum(len(files) for files in found_files.values())
        })
        
    except Exception as e:
        logger.error(f'Error scanning for files: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper functions
def process_uploaded_files(uploaded_files, file_type, overwrite=False):
    """Process uploaded files based on type."""
    results = []
    
    for file_info in uploaded_files:
        file_path = file_info['path']
        
        if file_type == 'runsheets':
            result = process_single_runsheet(file_path, overwrite)
        elif file_type == 'payslips':
            result = process_single_payslip(file_path)
        else:
            # Auto-detect and process
            result = auto_detect_and_process(file_path, overwrite)
        
        results.append({
            'file': file_info['original_name'],
            'result': result
        })
    
    return results


def process_uploaded_files_background(uploaded_files, file_type, overwrite=False):
    """Process uploaded files in background to avoid timeout."""
    try:
        log_settings_action('FILE_UPLOAD', f'Background processing started for {len(uploaded_files)} files (overwrite={overwrite})')
        results = process_uploaded_files(uploaded_files, file_type, overwrite)
        
        success_count = sum(1 for r in results if r['result'].get('success'))
        log_settings_action('FILE_UPLOAD', f'Background processing complete: {success_count}/{len(results)} successful')
    except Exception as e:
        log_settings_action('FILE_UPLOAD', f'Background processing failed: {str(e)}', 'ERROR')


def process_single_payslip(file_path):
    """Process a single payslip file."""
    process = subprocess.run(
        [sys.executable, 'scripts/production/extract_payslips.py', '--file', file_path],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    return {
        'success': process.returncode == 0,
        'output': process.stdout,
        'error': process.stderr if process.returncode != 0 else None
    }

def process_single_runsheet(file_path, overwrite=False):
    """Process a single runsheet file: import to DB, then copy to NAS canonical path.

    Replaces the previous flow which called two scripts that no longer exist
    (`organize_uploaded_runsheets.py`, `sync_runsheets_with_payslips.py`).
    The PDF is now copied directly to
    `<Config.RUNSHEETS_DIR>/<YYYY>/<MM-Month>/DH_DD-MM-YYYY.pdf`
    using the runsheet date already extracted by the importer.
    """
    from app.config import Config

    cmd = [sys.executable, 'scripts/production/import_run_sheets.py', '--file', file_path]
    if overwrite:
        cmd.append('--overwrite')

    import_process = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60
    )

    if import_process.returncode != 0:
        return {
            'success': False,
            'output': import_process.stdout,
            'error': import_process.stderr
        }

    source_filename = Path(file_path).name
    output_lines = [import_process.stdout]
    runsheet_date = None

    # Mark jobs as manually uploaded and look up the runsheet date in one go.
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE run_sheet_jobs
                SET manually_uploaded = 1
                WHERE source_file = ?
                AND imported_at >= datetime('now', '-1 minute')
            """, (source_filename,))
            updated = cursor.rowcount
            conn.commit()
            log_settings_action(
                'MANUAL_UPLOAD',
                f'Marked {updated} jobs as manually uploaded from {source_filename}'
            )

            cursor.execute("""
                SELECT date FROM run_sheet_jobs
                WHERE source_file = ? AND date IS NOT NULL AND LENGTH(date) = 10
                ORDER BY imported_at DESC
                LIMIT 1
            """, (source_filename,))
            row = cursor.fetchone()
            if row:
                runsheet_date = row[0] if not hasattr(row, 'keys') else row['date']
    except Exception as e:
        log_settings_action(
            'MANUAL_UPLOAD',
            f'Failed to mark jobs as manually uploaded: {str(e)}',
            'ERROR'
        )

    # Copy file to NAS canonical path: <RUNSHEETS_DIR>/<YYYY>/<MM-Month>/DH_DD-MM-YYYY.pdf
    if runsheet_date:
        try:
            dt = datetime.strptime(runsheet_date, '%d/%m/%Y')
            target_dir = Path(Config.RUNSHEETS_DIR) / str(dt.year) / dt.strftime('%m-%B')
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"DH_{dt.strftime('%d-%m-%Y')}.pdf"

            if target_path.exists():
                log_settings_action(
                    'MANUAL_UPLOAD',
                    f'Canonical file already exists, skipping copy: {target_path}'
                )
                output_lines.append(f"Canonical file already exists: {target_path}")
            else:
                shutil.copy2(file_path, target_path)
                log_settings_action(
                    'MANUAL_UPLOAD',
                    f'Copied {source_filename} to NAS: {target_path}'
                )
                output_lines.append(f"Copied to NAS: {target_path}")
        except Exception as e:
            log_settings_action(
                'MANUAL_UPLOAD',
                f'Failed to copy {source_filename} to NAS: {str(e)}',
                'ERROR'
            )
            output_lines.append(f"WARNING: Failed to copy to NAS: {e}")
    else:
        log_settings_action(
            'MANUAL_UPLOAD',
            f'No runsheet date found for {source_filename}; file not copied to NAS',
            'WARNING'
        )
        output_lines.append('WARNING: No runsheet date found in DB; file not copied to NAS')

    return {
        'success': True,
        'output': '\n'.join(output_lines),
        'error': None
    }

def auto_detect_and_process(file_path, overwrite=False):
    """Auto-detect file type and process accordingly."""
    # Simple heuristic based on filename and content
    filename = Path(file_path).name.lower()
    
    if 'payslip' in filename or 'saser' in filename:
        return process_single_payslip(file_path)
    elif 'runsheet' in filename or 'run' in filename:
        return process_single_runsheet(file_path, overwrite)
    else:
        # Try both and see which succeeds
        try:
            payslip_result = process_single_payslip(file_path)
            if payslip_result['success']:
                return payslip_result
        except:
            pass
        
        try:
            runsheet_result = process_single_runsheet(file_path, overwrite)
            if runsheet_result['success']:
                return runsheet_result
        except:
            pass
        
        return {'success': False, 'error': 'Could not determine file type'}

def attempt_gmail_sync():
    """Attempt Gmail sync with fallback."""
    try:
        # Try payslips first
        payslip_process = subprocess.run(
            [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--payslips', '--recent'],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        # Try runsheets
        runsheet_process = subprocess.run(
            [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--runsheets', '--recent'],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        success_count = 0
        if payslip_process.returncode == 0:
            success_count += 1
        if runsheet_process.returncode == 0:
            success_count += 1
        
        return {
            'success': success_count > 0,
            'count': success_count,
            'payslips': payslip_process.returncode == 0,
            'runsheets': runsheet_process.returncode == 0
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def process_all_local_files():
    """Process all local files in standard directories."""
    try:
        # Process payslips
        payslip_process = subprocess.run(
            [sys.executable, 'scripts/production/extract_payslips.py', '--recent', '30'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Process runsheets
        runsheet_process = subprocess.run(
            [sys.executable, 'scripts/production/import_run_sheets.py', '--recent', '30'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return {
            'success': True,
            'count': 2,  # Simplified count
            'payslips_success': payslip_process.returncode == 0,
            'runsheets_success': runsheet_process.returncode == 0
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def process_manual_uploads():
    """Process files in manual upload directories."""
    manual_dirs = [
        Path('data/processing/manual'),
        Path('data/processing/manual'),
        Path('data/uploads/pending')
    ]
    
    processed_count = 0
    
    for directory in manual_dirs:
        if directory.exists():
            pdf_files = list(directory.glob('*.pdf'))
            for pdf_file in pdf_files:
                try:
                    # Move to appropriate processing directory
                    if 'PaySlips' in str(directory):
                        target_dir = Path('PaySlips')
                    elif 'RunSheets' in str(directory):
                        target_dir = Path('RunSheets')
                    else:
                        continue
                    
                    target_path = target_dir / pdf_file.name
                    if not target_path.exists():
                        shutil.move(str(pdf_file), str(target_path))
                        processed_count += 1
                        
                except Exception as e:
                    log_settings_action('MANUAL_PROCESS', f'Failed to process {pdf_file}: {str(e)}', 'WARNING')
    
    return {
        'success': True,
        'count': processed_count
    }

def process_local_payslips(directory, days_back):
    """Process payslips from specific directory."""
    try:
        cmd = [sys.executable, 'scripts/production/extract_payslips.py', '--recent', str(days_back)]
        if directory:
            cmd.extend(['--directory', directory])
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        return {
            'type': 'payslips',
            'success': process.returncode == 0,
            'output': process.stdout,
            'error': process.stderr if process.returncode != 0 else None
        }
    except Exception as e:
        return {'type': 'payslips', 'success': False, 'error': str(e)}

def process_local_runsheets(directory, days_back):
    """Process runsheets from specific directory."""
    try:
        cmd = [sys.executable, 'scripts/production/import_run_sheets.py', '--recent', str(days_back)]
        if directory:
            cmd.extend(['--directory', directory])
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        return {
            'type': 'runsheets',
            'success': process.returncode == 0,
            'output': process.stdout,
            'error': process.stderr if process.returncode != 0 else None
        }
    except Exception as e:
        return {'type': 'runsheets', 'success': False, 'error': str(e)}
