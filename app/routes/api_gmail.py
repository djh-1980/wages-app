"""
Gmail integration API routes blueprint.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, jsonify, request
from pathlib import Path
import subprocess
import sys

gmail_bp = Blueprint('gmail_api', __name__, url_prefix='/api/gmail')


@gmail_bp.route('/download', methods=['POST'])
def api_gmail_download():
    """Trigger Gmail download for run sheets and/or payslips."""
    try:
        data = request.json
        mode = data.get('mode', 'all')  # all, runsheets, payslips
        after_date = data.get('after_date', '2025/01/01')
        
        # Build command
        cmd = [sys.executable, 'scripts/production/download_runsheets_gmail.py']
        
        if mode == 'runsheets':
            cmd.append('--runsheets')
        elif mode == 'payslips':
            cmd.append('--payslips')
        # 'all' doesn't need a flag
        
        cmd.append(f'--date={after_date}')
        
        # Run in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for completion (with timeout)
        stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
        
        if process.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Download completed successfully',
                'output': stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': stderr or 'Download failed',
                'output': stdout
            }), 500
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Download timed out (took longer than 5 minutes)'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@gmail_bp.route('/status', methods=['GET'])
def api_gmail_status():
    """Check if Gmail credentials are configured."""
    try:
        credentials_path = Path('credentials.json')
        token_path = Path('token.json')
        
        return jsonify({
            'configured': credentials_path.exists(),
            'authenticated': token_path.exists(),
            'credentials_path': str(credentials_path),
            'token_path': str(token_path)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gmail_bp.route('/test-connection', methods=['POST'])
def api_test_gmail_connection():
    """Test Gmail API connection."""
    try:
        # Simple test - try to run the Gmail downloader with a quick test
        result = subprocess.run(
            [sys.executable, '-c', '''
import sys
sys.path.append(".")
try:
    from scripts.production.download_runsheets_gmail import GmailRunSheetDownloader
    downloader = GmailRunSheetDownloader()
    if downloader.authenticate():
        profile = downloader.service.users().getProfile(userId="me").execute()
        print(f"SUCCESS:{profile.get('emailAddress', 'Connected')}")
    else:
        print("ERROR:Authentication failed")
except Exception as e:
    print(f"ERROR:{str(e)}")
'''],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        if output.startswith('SUCCESS:'):
            email = output.split(':', 1)[1] if ':' in output else 'Connected'
            return jsonify({
                'success': True,
                'email': email,
                'message': 'Gmail API connection successful'
            })
        else:
            error_msg = output.split(':', 1)[1] if ':' in output else output
            return jsonify({
                'success': False,
                'error': error_msg or 'Gmail connection failed'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Gmail connection test timed out after 30 seconds'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        })
