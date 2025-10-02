#!/usr/bin/env python3
"""
Flask web application for payslip data visualization.
"""

from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
import json
import os
import subprocess
import threading

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = 'PaySlips'
ALLOWED_EXTENSIONS = {'pdf'}

DB_PATH = "payslips.db"


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html')


@app.route('/api/summary')
def api_summary():
    """Get overall summary statistics."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Overall stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_weeks,
            SUM(net_payment) as total_earnings,
            AVG(net_payment) as avg_weekly,
            MIN(net_payment) as min_weekly,
            MAX(net_payment) as max_weekly
        FROM payslips
    """)
    overall = dict(cursor.fetchone())
    
    # Total jobs
    cursor.execute("SELECT COUNT(*) as total_jobs FROM job_items")
    overall['total_jobs'] = cursor.fetchone()['total_jobs']
    
    # Current tax year
    cursor.execute("""
        SELECT 
            tax_year,
            COUNT(*) as weeks,
            SUM(net_payment) as total,
            AVG(net_payment) as avg
        FROM payslips
        WHERE tax_year = (SELECT MAX(tax_year) FROM payslips)
        GROUP BY tax_year
    """)
    current_year = dict(cursor.fetchone())
    
    # Last 4 weeks
    cursor.execute("""
        SELECT AVG(net_payment) as avg
        FROM (
            SELECT net_payment
            FROM payslips
            ORDER BY tax_year DESC, week_number DESC
            LIMIT 4
        )
    """)
    last_4_weeks = cursor.fetchone()['avg']
    
    # Best week
    cursor.execute("""
        SELECT tax_year, week_number, net_payment
        FROM payslips
        ORDER BY net_payment DESC
        LIMIT 1
    """)
    best_week = dict(cursor.fetchone())
    
    conn.close()
    
    return jsonify({
        'overall': overall,
        'current_year': current_year,
        'last_4_weeks_avg': last_4_weeks,
        'best_week': best_week
    })


@app.route('/api/weekly_trend')
def api_weekly_trend():
    """Get weekly earnings trend."""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', 52, type=int)
    tax_year = request.args.get('tax_year')
    
    if tax_year:
        # Filter by specific tax year
        cursor.execute("""
            SELECT tax_year, week_number, net_payment, pay_date
            FROM payslips
            WHERE tax_year = ?
            ORDER BY week_number ASC
        """, (tax_year,))
    else:
        # Show last N weeks across all years
        cursor.execute("""
            SELECT tax_year, week_number, net_payment, pay_date
            FROM payslips
            ORDER BY tax_year DESC, week_number DESC
            LIMIT ?
        """, (limit,))
        
        rows = [dict(row) for row in cursor.fetchall()]
        rows.reverse()  # Show oldest to newest
        conn.close()
        return jsonify(rows)
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/clients')
def api_clients():
    """Get client breakdown."""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', 10, type=int)
    
    cursor.execute("""
        SELECT 
            client,
            COUNT(*) as job_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount
        FROM job_items
        WHERE client IS NOT NULL
        GROUP BY client
        ORDER BY total_amount DESC
        LIMIT ?
    """, (limit,))
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/job_types')
def api_job_types():
    """Get job type breakdown."""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', 10, type=int)
    
    cursor.execute("""
        SELECT 
            job_type,
            COUNT(*) as job_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount
        FROM job_items
        WHERE job_type IS NOT NULL
        GROUP BY job_type
        ORDER BY job_count DESC
        LIMIT ?
    """, (limit,))
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/payslips')
def api_payslips():
    """Get all payslips."""
    conn = get_db()
    cursor = conn.cursor()
    
    tax_year = request.args.get('tax_year')
    
    if tax_year:
        cursor.execute("""
            SELECT 
                p.*,
                (SELECT COUNT(*) FROM job_items WHERE payslip_id = p.id) as job_count
            FROM payslips p
            WHERE tax_year = ?
            ORDER BY week_number
        """, (tax_year,))
    else:
        cursor.execute("""
            SELECT 
                p.*,
                (SELECT COUNT(*) FROM job_items WHERE payslip_id = p.id) as job_count
            FROM payslips p
            ORDER BY tax_year DESC, week_number DESC
        """)
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/payslip/<int:payslip_id>')
def api_payslip_detail(payslip_id):
    """Get detailed payslip information."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get payslip
    cursor.execute("SELECT * FROM payslips WHERE id = ?", (payslip_id,))
    payslip = dict(cursor.fetchone())
    
    # Get job items
    cursor.execute("""
        SELECT * FROM job_items
        WHERE payslip_id = ?
        ORDER BY id
    """, (payslip_id,))
    jobs = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({
        'payslip': payslip,
        'jobs': jobs
    })


@app.route('/api/search')
def api_search():
    """Search jobs."""
    conn = get_db()
    cursor = conn.cursor()
    
    query = request.args.get('q', '')
    
    if not query:
        return jsonify([])
    
    cursor.execute("""
        SELECT 
            p.tax_year,
            p.week_number,
            ji.job_number,
            ji.client,
            ji.location,
            ji.job_type,
            ji.amount,
            ji.description
        FROM job_items ji
        JOIN payslips p ON ji.payslip_id = p.id
        WHERE ji.description LIKE ? OR ji.client LIKE ? OR ji.location LIKE ?
        ORDER BY p.tax_year DESC, p.week_number DESC
        LIMIT 50
    """, (f'%{query}%', f'%{query}%', f'%{query}%'))
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/monthly_breakdown')
def api_monthly_breakdown():
    """Get monthly breakdown."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            tax_year,
            CAST((week_number - 1) / 4.33 AS INTEGER) + 1 as month,
            COUNT(*) as weeks,
            SUM(net_payment) as total
        FROM payslips
        GROUP BY tax_year, month
        ORDER BY tax_year, month
    """)
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/tax_years')
def api_tax_years():
    """Get list of tax years."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT tax_year
        FROM payslips
        ORDER BY tax_year DESC
    """)
    
    years = [row['tax_year'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(years)


@app.route('/api/all_clients')
def api_all_clients():
    """Get list of all unique clients."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT client
        FROM job_items
        WHERE client IS NOT NULL
        ORDER BY client
    """)
    
    clients = [row['client'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(clients)


@app.route('/api/all_job_types')
def api_all_job_types():
    """Get list of all unique job types."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT job_type
        FROM job_items
        WHERE job_type IS NOT NULL
        ORDER BY job_type
    """)
    
    job_types = [row['job_type'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(job_types)


@app.route('/api/custom_report')
def api_custom_report():
    """Generate custom filtered report with grouping support."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get filters from query params
    tax_year = request.args.get('tax_year')
    client = request.args.get('client')
    job_type = request.args.get('job_type')
    week_from = request.args.get('week_from', type=int)
    week_to = request.args.get('week_to', type=int)
    use_groups = request.args.get('use_groups', 'false') == 'true'
    
    # Load groupings if needed
    groupings = {}
    if use_groups:
        cursor.execute("SELECT value FROM settings WHERE key = 'groupings'")
        row = cursor.fetchone()
        if row:
            groupings = json.loads(row['value'])
    
    # Build dynamic query
    query = """
        SELECT 
            p.tax_year,
            p.week_number,
            p.pay_date,
            ji.job_number,
            ji.client,
            ji.location,
            ji.job_type,
            ji.date,
            ji.time,
            ji.amount,
            ji.description
        FROM job_items ji
        JOIN payslips p ON ji.payslip_id = p.id
        WHERE 1=1
    """
    
    params = []
    
    if tax_year:
        query += " AND p.tax_year = ?"
        params.append(tax_year)
    
    if client:
        # Check if this is a group name
        if use_groups and 'client_groups' in groupings and client in groupings['client_groups']:
            # Filter by any client in the group
            client_list = groupings['client_groups'][client]
            placeholders = ','.join(['?' for _ in client_list])
            query += f" AND ji.client IN ({placeholders})"
            params.extend(client_list)
        else:
            query += " AND ji.client = ?"
            params.append(client)
    
    if job_type:
        # Check if this is a group name
        if use_groups and 'job_type_groups' in groupings and job_type in groupings['job_type_groups']:
            # Filter by any job type in the group
            job_type_list = groupings['job_type_groups'][job_type]
            placeholders = ','.join(['?' for _ in job_type_list])
            query += f" AND ji.job_type IN ({placeholders})"
            params.extend(job_type_list)
        else:
            query += " AND ji.job_type = ?"
            params.append(job_type)
    
    if week_from:
        query += " AND p.week_number >= ?"
        params.append(week_from)
    
    if week_to:
        query += " AND p.week_number <= ?"
        params.append(week_to)
    
    query += " ORDER BY p.tax_year DESC, p.week_number DESC, ji.id"
    
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    
    # Apply grouping to display names if requested
    if use_groups and groupings:
        for row in rows:
            # Replace client with group name
            if 'client_groups' in groupings:
                for group_name, clients in groupings['client_groups'].items():
                    if row['client'] in clients:
                        row['client_group'] = group_name
                        break
            
            # Replace job type with group name
            if 'job_type_groups' in groupings:
                for group_name, job_types in groupings['job_type_groups'].items():
                    if row['job_type'] in job_types:
                        row['job_type_group'] = group_name
                        break
    
    conn.close()
    return jsonify(rows)


@app.route('/api/settings/groups', methods=['GET', 'POST'])
def api_settings_groups():
    """Manage client and job type groupings."""
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Save groupings
        data = request.json
        # For now, store in a simple settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES ('groupings', ?)
        """, (json.dumps(data),))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    else:
        # Get groupings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        cursor.execute("""
            SELECT value FROM settings WHERE key = 'groupings'
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify(json.loads(row['value']))
        else:
            return jsonify({'client_groups': {}, 'job_type_groups': {}})


@app.route('/api/check_missing')
def api_check_missing():
    """Check for missing payslips in each tax year."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all payslips grouped by tax year
    cursor.execute("""
        SELECT tax_year, week_number
        FROM payslips
        ORDER BY tax_year, week_number
    """)
    
    payslips = cursor.fetchall()
    conn.close()
    
    # Group by tax year
    by_year = {}
    for row in payslips:
        year = row['tax_year']
        week = row['week_number']
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(week)
    
    # Check for missing weeks
    result = []
    for year in sorted(by_year.keys()):
        weeks = sorted(by_year[year])
        missing = []
        
        # Check for gaps
        if weeks:
            min_week = min(weeks)
            max_week = max(weeks)
            
            for week in range(min_week, max_week + 1):
                if week not in weeks:
                    missing.append(week)
        
        result.append({
            'tax_year': year,
            'total_weeks': len(weeks),
            'min_week': min(weeks) if weeks else 0,
            'max_week': max(weeks) if weeks else 0,
            'missing_weeks': missing,
            'has_missing': len(missing) > 0
        })
    
    return jsonify(result)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/upload_payslips', methods=['POST'])
def api_upload_payslips():
    """Upload and process payslip PDFs."""
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided'}), 400
    
    # Get tax year
    tax_year = request.form.get('tax_year', '2025')
    
    # Create year folder if it doesn't exist
    year_folder = os.path.join(app.config['UPLOAD_FOLDER'], tax_year)
    os.makedirs(year_folder, exist_ok=True)
    
    files = request.files.getlist('files')
    uploaded_count = 0
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(year_folder, filename)
            file.save(filepath)
            uploaded_count += 1
            print(f"✅ Saved: {filepath}")
    
    if uploaded_count > 0:
        # Run extraction on uploaded files
        def run_extraction():
            try:
                result = subprocess.run(
                    ['python3', 'extract_payslips.py'],
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                print(f"Extraction completed: {result.returncode}")
                if result.stdout:
                    print(result.stdout)
            except Exception as e:
                print(f"Extraction error: {e}")
        
        thread = threading.Thread(target=run_extraction)
        thread.start()
        
        return jsonify({
            'success': True,
            'uploaded': uploaded_count,
            'tax_year': tax_year,
            'message': f'Uploaded {uploaded_count} file(s) to {tax_year}'
        })
    
    return jsonify({'success': False, 'message': 'No valid PDF files uploaded'}), 400


@app.route('/api/process_payslips', methods=['POST'])
def api_process_payslips():
    """Trigger payslip extraction process."""
    def run_extraction():
        try:
            result = subprocess.run(
                ['python3', 'extract_payslips.py'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            print("Extraction completed:", result.returncode)
            if result.stdout:
                print(result.stdout)
        except Exception as e:
            print("Extraction error:", e)
    
    # Run in background thread
    thread = threading.Thread(target=run_extraction)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Processing started'})


@app.route('/api/backup_database')
def api_backup_database():
    """Download database backup."""
    from flask import send_file
    from datetime import datetime
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return send_file(
        DB_PATH,
        as_attachment=True,
        download_name=f'payslips_backup_{timestamp}.db',
        mimetype='application/x-sqlite3'
    )


@app.route('/api/clear_database', methods=['POST'])
def api_clear_database():
    """Clear all data from database and optionally delete PDF files."""
    try:
        data = request.get_json() or {}
        delete_pdfs = data.get('delete_pdfs', False)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Delete all data from database
        cursor.execute("DELETE FROM job_items")
        cursor.execute("DELETE FROM payslips")
        cursor.execute("DELETE FROM settings")
        
        conn.commit()
        conn.close()
        
        message = 'Database cleared'
        
        # Delete PDF files if requested
        if delete_pdfs:
            import shutil
            payslips_folder = 'PaySlips'
            if os.path.exists(payslips_folder):
                for item in os.listdir(payslips_folder):
                    item_path = os.path.join(payslips_folder, item)
                    if os.path.isdir(item_path):
                        # Delete year folders (2021, 2022, etc.)
                        shutil.rmtree(item_path)
                    elif item.endswith('.pdf'):
                        # Delete any PDFs in root PaySlips folder
                        os.remove(item_path)
                message = 'Database and PDF files cleared'
        
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*80)
    print("WAGES APP - WEB INTERFACE")
    print("="*80)
    print("\n🌐 Starting web server...")
    print("📊 Open your browser to: http://localhost:5001")
    print("⏹️  Press Ctrl+C to stop\n")
    print("="*80 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
