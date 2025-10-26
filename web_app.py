#!/usr/bin/env python3
"""
Flask web application for payslip data visualization.
"""

from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
from pathlib import Path
import json
import os
import subprocess
import threading

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = 'PaySlips'
ALLOWED_EXTENSIONS = {'pdf'}

DB_PATH = "data/payslips.db"


def init_attendance_table():
    """Initialize attendance tracking table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            reason TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Main landing page - redirect to runsheets."""
    return render_template('runsheets.html')


@app.route('/wages')
def wages():
    """Wages dashboard page."""
    return render_template('wages.html')


@app.route('/runsheets')
def runsheets():
    """Run sheets page."""
    return render_template('runsheets.html')


@app.route('/reports')
def reports():
    """Reports page."""
    return render_template('reports.html')


@app.route('/settings')
def settings():
    """Settings page."""
    return render_template('settings.html')


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
    payslip_row = cursor.fetchone()
    
    if not payslip_row:
        conn.close()
        return jsonify({'error': 'Payslip not found'}), 404
    
    payslip = dict(payslip_row)
    
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
                    ['python3', 'scripts/extract_payslips.py'],
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
                ['python3', 'scripts/extract_payslips.py'],
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


@app.route('/api/year_comparison')
def api_year_comparison():
    """Get year-over-year comparison data."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all tax years
    cursor.execute("SELECT DISTINCT tax_year FROM payslips ORDER BY tax_year")
    years = [row['tax_year'] for row in cursor.fetchall()]
    
    comparison_data = {}
    for year in years:
        cursor.execute("""
            SELECT 
                week_number,
                net_payment
            FROM payslips
            WHERE tax_year = ?
            ORDER BY week_number
        """, (year,))
        
        comparison_data[year] = [
            {'week': row['week_number'], 'amount': row['net_payment']}
            for row in cursor.fetchall()
        ]
    
    conn.close()
    return jsonify(comparison_data)


@app.route('/api/earnings_forecast')
def api_earnings_forecast():
    """Predict future earnings based on historical trends."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get current year data
    cursor.execute("""
        SELECT tax_year, week_number, net_payment
        FROM payslips
        WHERE tax_year = (SELECT MAX(tax_year) FROM payslips)
        ORDER BY week_number
    """)
    
    current_year_data = [dict(row) for row in cursor.fetchall()]
    
    if not current_year_data:
        conn.close()
        return jsonify({'error': 'No data available'}), 404
    
    current_year = current_year_data[0]['tax_year']
    weeks_worked = len(current_year_data)
    total_earned = sum(row['net_payment'] for row in current_year_data)
    avg_weekly = total_earned / weeks_worked if weeks_worked > 0 else 0
    
    # Calculate trend (simple linear regression on last 12 weeks)
    recent_weeks = current_year_data[-12:] if len(current_year_data) >= 12 else current_year_data
    if len(recent_weeks) >= 2:
        # Simple trend calculation
        x_values = list(range(len(recent_weeks)))
        y_values = [row['net_payment'] for row in recent_weeks]
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        trend = 'increasing' if slope > 10 else 'decreasing' if slope < -10 else 'stable'
    else:
        slope = 0
        trend = 'stable'
    
    # Forecast remaining weeks
    weeks_remaining = 52 - weeks_worked
    forecast_data = []
    
    for i in range(1, weeks_remaining + 1):
        week_num = weeks_worked + i
        # Use average with trend adjustment
        predicted_amount = avg_weekly + (slope * i)
        forecast_data.append({
            'week': week_num,
            'predicted_amount': max(0, predicted_amount),  # Don't predict negative
            'confidence': 'high' if i <= 4 else 'medium' if i <= 12 else 'low'
        })
    
    projected_year_end = total_earned + sum(f['predicted_amount'] for f in forecast_data)
    
    conn.close()
    return jsonify({
        'current_year': current_year,
        'weeks_worked': weeks_worked,
        'total_earned': total_earned,
        'avg_weekly': avg_weekly,
        'trend': trend,
        'slope': slope,
        'forecast': forecast_data,
        'projected_year_end': projected_year_end
    })


@app.route('/api/client_heatmap')
def api_client_heatmap():
    """Get client activity heatmap data (clients by month)."""
    conn = get_db()
    cursor = conn.cursor()
    
    tax_year = request.args.get('tax_year')
    
    if tax_year:
        query = """
            SELECT 
                ji.client,
                p.tax_year,
                CAST((p.week_number - 1) / 4.33 AS INTEGER) + 1 as month,
                COUNT(*) as job_count,
                SUM(ji.amount) as total_amount
            FROM job_items ji
            JOIN payslips p ON ji.payslip_id = p.id
            WHERE ji.client IS NOT NULL AND p.tax_year = ?
            GROUP BY ji.client, p.tax_year, month
            ORDER BY total_amount DESC
        """
        cursor.execute(query, (tax_year,))
    else:
        query = """
            SELECT 
                ji.client,
                p.tax_year,
                CAST((p.week_number - 1) / 4.33 AS INTEGER) + 1 as month,
                COUNT(*) as job_count,
                SUM(ji.amount) as total_amount
            FROM job_items ji
            JOIN payslips p ON ji.payslip_id = p.id
            WHERE ji.client IS NOT NULL
            GROUP BY ji.client, p.tax_year, month
            ORDER BY total_amount DESC
        """
        cursor.execute(query)
    
    rows = [dict(row) for row in cursor.fetchall()]
    
    # Get top 10 clients overall
    cursor.execute("""
        SELECT client, SUM(amount) as total
        FROM job_items
        WHERE client IS NOT NULL
        GROUP BY client
        ORDER BY total DESC
        LIMIT 10
    """)
    top_clients = [row['client'] for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'heatmap_data': rows,
        'top_clients': top_clients
    })


@app.route('/api/weekly_performance')
def api_weekly_performance():
    """Analyze best and worst performing weeks with context."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get best weeks
    cursor.execute("""
        SELECT 
            p.id,
            p.tax_year,
            p.week_number,
            p.pay_date,
            p.net_payment,
            COUNT(ji.id) as job_count,
            GROUP_CONCAT(DISTINCT ji.client) as clients
        FROM payslips p
        LEFT JOIN job_items ji ON p.id = ji.payslip_id
        GROUP BY p.id
        ORDER BY p.net_payment DESC
        LIMIT 10
    """)
    best_weeks = [dict(row) for row in cursor.fetchall()]
    
    # Get worst weeks (but not zero)
    cursor.execute("""
        SELECT 
            p.id,
            p.tax_year,
            p.week_number,
            p.pay_date,
            p.net_payment,
            COUNT(ji.id) as job_count,
            GROUP_CONCAT(DISTINCT ji.client) as clients
        FROM payslips p
        LEFT JOIN job_items ji ON p.id = ji.payslip_id
        WHERE p.net_payment > 0
        GROUP BY p.id
        ORDER BY p.net_payment ASC
        LIMIT 10
    """)
    worst_weeks = [dict(row) for row in cursor.fetchall()]
    
    # Get average for comparison
    cursor.execute("SELECT AVG(net_payment) as avg FROM payslips WHERE net_payment > 0")
    average = cursor.fetchone()['avg']
    
    conn.close()
    
    return jsonify({
        'best_weeks': best_weeks,
        'worst_weeks': worst_weeks,
        'average': average
    })


@app.route('/api/runsheets/summary')
def api_runsheets_summary():
    """Get run sheets summary statistics."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Overall stats
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT date) as total_days,
            COUNT(*) as total_jobs,
            COUNT(DISTINCT customer) as unique_customers,
            MIN(date) as first_date,
            MAX(date) as last_date
        FROM run_sheet_jobs
        WHERE date IS NOT NULL
    """)
    overall = dict(cursor.fetchone())
    
    # Top customers
    cursor.execute("""
        SELECT customer, COUNT(*) as job_count
        FROM run_sheet_jobs
        WHERE customer IS NOT NULL
        GROUP BY customer
        ORDER BY job_count DESC
        LIMIT 10
    """)
    top_customers = [dict(row) for row in cursor.fetchall()]
    
    # Activity breakdown
    cursor.execute("""
        SELECT activity, COUNT(*) as count
        FROM run_sheet_jobs
        WHERE activity IS NOT NULL
        GROUP BY activity
        ORDER BY count DESC
    """)
    activities = [dict(row) for row in cursor.fetchall()]
    
    # Jobs per day average
    cursor.execute("""
        SELECT AVG(jobs_per_day) as avg_jobs_per_day
        FROM (
            SELECT date, COUNT(*) as jobs_per_day
            FROM run_sheet_jobs
            WHERE date IS NOT NULL
            GROUP BY date
        )
    """)
    avg_jobs = cursor.fetchone()['avg_jobs_per_day']
    
    conn.close()
    
    return jsonify({
        'overall': overall,
        'top_customers': top_customers,
        'activities': activities,
        'avg_jobs_per_day': avg_jobs
    })


@app.route('/api/runsheets/list')
def api_runsheets_list():
    """Get list of all run sheets."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    offset = (page - 1) * per_page
    
    # Get sorting parameters
    sort_column = request.args.get('sort', 'date')
    sort_order = request.args.get('order', 'desc').upper()
    
    # Get filter parameters
    filter_year = request.args.get('year', '')
    filter_month = request.args.get('month', '')
    filter_week = request.args.get('week', '')
    filter_day = request.args.get('day', '')
    
    # Validate sort parameters
    valid_columns = ['date', 'job_count']
    if sort_column not in valid_columns:
        sort_column = 'date'
    if sort_order not in ['ASC', 'DESC']:
        sort_order = 'DESC'
    
    # Build WHERE clause for filters
    where_conditions = ["date IS NOT NULL"]
    
    if filter_year:
        where_conditions.append(f"substr(date, 7, 4) = '{filter_year}'")
    
    if filter_month:
        where_conditions.append(f"substr(date, 4, 2) = '{filter_month}'")
    
    if filter_week and filter_week.strip():
        # Calculate week number from date (Sunday-Saturday weeks)
        try:
            week_num = int(filter_week)
            # Use %W for week number with Sunday as first day (%W uses Monday, %U uses Sunday)
            # %U: Week number (00-53), Sunday as first day
            where_conditions.append(f"""
                CAST(strftime('%U', substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)) AS INTEGER) = {week_num - 1}
            """)
        except ValueError:
            pass  # Invalid week number, skip filter
    
    if filter_day:
        # Day of week (0=Sunday, 1=Monday, etc.)
        where_conditions.append(f"CAST(strftime('%w', substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)) AS INTEGER) = {filter_day}")
    
    where_clause = " AND ".join(where_conditions)
    
    # Get total count with filters
    count_query = f"SELECT COUNT(DISTINCT date) FROM run_sheet_jobs WHERE {where_clause}"
    cursor.execute(count_query)
    total = cursor.fetchone()[0]
    
    # Get run sheets grouped by date with sorting and filters
    # For date sorting, convert DD/MM/YYYY to YYYY-MM-DD for proper sorting
    if sort_column == 'date':
        order_clause = f"substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2) {sort_order}"
    else:
        order_clause = f"{sort_column} {sort_order}"
    
    query = f"""
        SELECT 
            date,
            COUNT(*) as job_count,
            GROUP_CONCAT(DISTINCT customer) as customers,
            GROUP_CONCAT(DISTINCT activity) as activities
        FROM run_sheet_jobs
        WHERE {where_clause}
        GROUP BY date
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, (per_page, offset))
    
    runsheets = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'runsheets': runsheets,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@app.route('/api/runsheets/jobs')
def api_runsheets_jobs():
    """Get all jobs for a specific date."""
    date = request.args.get('date')
    
    if not date:
        return jsonify({'error': 'Date parameter required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT *
        FROM run_sheet_jobs
        WHERE date = ?
        ORDER BY job_number
    """, (date,))
    
    jobs = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({'jobs': jobs, 'date': date})


@app.route('/api/runsheets/update-statuses', methods=['POST'])
def api_update_job_statuses():
    """Update job statuses for multiple jobs and save mileage/fuel data."""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    updates = data.get('updates', [])
    date = data.get('date')
    mileage = data.get('mileage')
    fuel_cost = data.get('fuel_cost')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Update each job status
        for update in updates:
            job_id = update.get('job_id')
            status = update.get('status')
            
            if job_id and status in ['completed', 'missed', 'dnco', 'extra', 'pending']:
                cursor.execute("""
                    UPDATE run_sheet_jobs
                    SET status = ?
                    WHERE id = ?
                """, (status, job_id))
        
        # Save mileage and fuel cost if provided
        if date and (mileage is not None or fuel_cost is not None):
            cursor.execute("""
                INSERT INTO runsheet_daily_data (date, mileage, fuel_cost, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    mileage = COALESCE(excluded.mileage, mileage),
                    fuel_cost = COALESCE(excluded.fuel_cost, fuel_cost),
                    updated_at = CURRENT_TIMESTAMP
            """, (date, mileage, fuel_cost))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'updated': len(updates)})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/runsheets/daily-data')
def api_get_daily_data():
    """Get mileage and fuel cost for a specific date."""
    date = request.args.get('date')
    
    if not date:
        return jsonify({'error': 'Date parameter required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT mileage, fuel_cost
            FROM runsheet_daily_data
            WHERE date = ?
        """, (date,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'mileage': row['mileage'],
                'fuel_cost': row['fuel_cost']
            })
        else:
            return jsonify({
                'mileage': None,
                'fuel_cost': None
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/runsheets/update-job-status', methods=['POST'])
def api_update_job_status():
    """Update a single job's status immediately."""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    job_id = data.get('job_id')
    status = data.get('status')
    
    if not job_id or not status:
        return jsonify({'success': False, 'error': 'Job ID and status are required'}), 400
    
    if status not in ['completed', 'missed', 'dnco', 'extra', 'pending']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE run_sheet_jobs
            SET status = ?
            WHERE id = ?
        """, (status, job_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/runsheets/add-job', methods=['POST'])
def api_add_extra_job():
    """Add an extra job to a run sheet."""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    date = data.get('date')
    job_number = data.get('job_number')
    customer = data.get('customer')
    activity = data.get('activity', '')
    job_address = data.get('job_address', '')
    status = data.get('status', 'extra')
    
    if not date or not job_number or not customer:
        return jsonify({'success': False, 'error': 'Date, job number, and customer are required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Insert the new job
        cursor.execute("""
            INSERT INTO run_sheet_jobs 
            (date, job_number, customer, activity, job_address, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, job_number, customer, activity, job_address, status))
        
        conn.commit()
        job_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/notifications/runsheets')
def get_runsheet_notifications():
    """Get new run sheet notifications."""
    notification_file = Path('data/new_runsheets.json')
    
    if not notification_file.exists():
        return jsonify({'has_new': False, 'count': 0})
    
    try:
        with open(notification_file, 'r') as f:
            notification = json.load(f)
        
        return jsonify({
            'has_new': not notification.get('read', False),
            'count': notification.get('count', 0),
            'date': notification.get('date', ''),
            'timestamp': notification.get('timestamp', '')
        })
    except:
        return jsonify({'has_new': False, 'count': 0})


@app.route('/api/notifications/runsheets/mark-read', methods=['POST'])
def mark_runsheet_notifications_read():
    """Mark run sheet notifications as read."""
    notification_file = Path('data/new_runsheets.json')
    
    if notification_file.exists():
        try:
            with open(notification_file, 'r') as f:
                notification = json.load(f)
            
            notification['read'] = True
            
            with open(notification_file, 'w') as f:
                json.dump(notification, f)
            
            return jsonify({'success': True})
        except:
            return jsonify({'success': False, 'error': 'Failed to update notification'})
    
    return jsonify({'success': True})


@app.route('/api/settings/test-gmail')
def api_test_gmail():
    """Test Gmail OAuth connection."""
    import os
    from pathlib import Path
    
    token_path = Path('token.json')
    creds_path = Path('credentials.json')
    
    result = {
        'token_exists': token_path.exists(),
        'credentials_exists': creds_path.exists(),
        'connected': False,
        'message': ''
    }
    
    if not creds_path.exists():
        result['message'] = 'credentials.json not found. Please set up Gmail OAuth first.'
        return jsonify(result)
    
    if not token_path.exists():
        result['message'] = 'token.json not found. Please authorize Gmail access first.'
        return jsonify(result)
    
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        
        creds = Credentials.from_authorized_user_file('token.json')
        
        if creds and creds.valid:
            result['connected'] = True
            result['message'] = 'Gmail connection successful! OAuth token is valid.'
        elif creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            result['connected'] = True
            result['message'] = 'Gmail connection successful! Token was refreshed.'
        else:
            result['message'] = 'OAuth token is invalid. Please re-authorize.'
    except Exception as e:
        result['message'] = f'Error testing connection: {str(e)}'
    
    return jsonify(result)


@app.route('/api/settings/sync-status')
def api_sync_status():
    """Get auto-sync status."""
    import os
    from pathlib import Path
    from datetime import datetime
    
    log_path = Path('logs/runsheet_sync.log')
    
    result = {
        'active': False,
        'last_sync': None,
        'log_exists': log_path.exists()
    }
    
    if log_path.exists():
        result['active'] = True
        # Get last modified time of log
        mtime = os.path.getmtime(log_path)
        result['last_sync'] = datetime.fromtimestamp(mtime).isoformat()
    
    return jsonify(result)


@app.route('/api/reports/discrepancies')
def api_reports_discrepancies():
    """Get all job numbers from payslips and run sheets for discrepancy analysis."""
    print("\n=== DISCREPANCY REPORT API CALLED ===")
    conn = get_db()
    cursor = conn.cursor()
    
    # Get filter parameters
    year = request.args.get('year', '')
    month = request.args.get('month', '')
    print(f"Received parameters: year={year}, month={month}")
    
    try:
        # Build WHERE clause for payslips (filter by date field in job_items)
        payslip_where = "WHERE ji.job_number IS NOT NULL AND ji.job_number != ''"
        payslip_params = []
        
        if year and month:
            # Filter by specific month and year (date format: DD/MM/YY in job_items - 2 digit year!)
            year_2digit = year[-2:]  # Get last 2 digits of year (2025 -> 25)
            payslip_where += " AND ji.date LIKE ?"
            payslip_params.append(f"%/{month}/{year_2digit}")
        elif year:
            # Filter by year only (2 digit year)
            year_2digit = year[-2:]
            payslip_where += " AND ji.date LIKE ?"
            payslip_params.append(f"%/{year_2digit}")
        
        print(f"DEBUG: Payslip filter - year={year}, month={month}, pattern={payslip_params}")
        
        # Get all job numbers from payslips
        cursor.execute(f"""
            SELECT DISTINCT ji.job_number, ji.description, ji.client
            FROM job_items ji
            {payslip_where}
        """, payslip_params)
        payslip_jobs = {}
        for row in cursor.fetchall():
            payslip_jobs[row[0]] = {
                'description': row[1],
                'client': row[2]
            }
        
        print(f"DEBUG: Found {len(payslip_jobs)} payslip jobs")
        
        # Build WHERE clause for run sheets (dates are in DD/MM/YYYY format)
        runsheet_where = "WHERE job_number IS NOT NULL AND job_number != ''"
        runsheet_params = []
        if year or month:
            if year and month:
                # Match DD/MM/YYYY format (e.g., %/09/2025)
                runsheet_where += " AND date LIKE ?"
                runsheet_params.append(f"%/{month}/{year}")
            elif year:
                # Match any month in the year (e.g., %/2025)
                runsheet_where += " AND date LIKE ?"
                runsheet_params.append(f"%/{year}")
        
        print(f"DEBUG: Runsheet filter - year={year}, month={month}, pattern={runsheet_params}")
        
        # Get all job numbers from run sheets
        cursor.execute(f"""
            SELECT DISTINCT job_number, customer, date
            FROM run_sheet_jobs
            {runsheet_where}
        """, runsheet_params)
        runsheet_jobs = {}
        for row in cursor.fetchall():
            runsheet_jobs[row[0]] = {
                'customer': row[1],
                'date': row[2]
            }
        
        print(f"DEBUG: Found {len(runsheet_jobs)} runsheet jobs")
        
        return jsonify({
            'payslip_jobs': payslip_jobs,
            'runsheet_jobs': runsheet_jobs
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search/job/<job_number>')
def api_search_job(job_number):
    """Search for a job number across run sheets and payslips."""
    print(f"\n=== SEARCH REQUEST for job number: {job_number} ===")
    conn = get_db()
    cursor = conn.cursor()
    
    results = {
        'found': False,
        'job_number': job_number,
        'runsheets': [],
        'payslips': []
    }
    
    try:
        # Search in run sheets (try both exact match and LIKE for flexibility)
        print("Searching run_sheet_jobs table...")
        cursor.execute("""
            SELECT date, customer, job_address, job_number, activity
            FROM run_sheet_jobs
            WHERE job_number = ? OR job_number LIKE ? OR CAST(job_number AS TEXT) = ?
            ORDER BY date DESC
        """, (job_number, f'%{job_number}%', job_number))
        print(f"Query executed")
        
        runsheets = cursor.fetchall()
        print(f"Found {len(runsheets)} run sheet results")
        if runsheets:
            results['found'] = True
            results['runsheets'] = [
                {
                    'date': row[0],
                    'customer': row[1],
                    'address': row[2],
                    'job_number': row[3],
                    'status': row[4]  # activity
                }
                for row in runsheets
            ]
        
        # Search in payslip jobs
        print("Searching job_items table...")
        cursor.execute("""
            SELECT ji.*, p.tax_year, p.week_number
            FROM job_items ji
            JOIN payslips p ON ji.payslip_id = p.id
            WHERE ji.job_number = ? OR ji.job_number LIKE ? OR CAST(ji.job_number AS TEXT) = ?
            ORDER BY p.tax_year DESC, p.week_number DESC
        """, (job_number, f'%{job_number}%', job_number))
        print(f"Query executed")
        
        payslips = cursor.fetchall()
        print(f"Found {len(payslips)} payslip results")
        if payslips:
            results['found'] = True
            results['payslips'] = [
                {
                    'job_number': row[6],  # job_number is column 6
                    'description': row[5],  # description is column 5
                    'client': row[7],  # client is column 7
                    'amount': row[4],  # amount is column 4
                    'tax_year': row[-2],
                    'week_number': row[-1]
                }
                for row in payslips
            ]
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e), 'found': False}), 500


@app.route('/api/attendance', methods=['GET'])
def api_get_attendance():
    """Get all attendance records."""
    conn = get_db()
    cursor = conn.cursor()
    
    year = request.args.get('year', '')
    
    try:
        if year:
            cursor.execute("""
                SELECT id, date, reason, notes, created_at
                FROM attendance
                WHERE date LIKE ?
                ORDER BY date DESC
            """, (f'%/{year}',))
        else:
            cursor.execute("""
                SELECT id, date, reason, notes, created_at
                FROM attendance
                ORDER BY date DESC
            """)
        
        records = []
        for row in cursor.fetchall():
            records.append({
                'id': row[0],
                'date': row[1],
                'reason': row[2],
                'notes': row[3],
                'created_at': row[4]
            })
        
        return jsonify(records)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/attendance', methods=['POST'])
def api_add_attendance():
    """Add attendance record."""
    data = request.json
    date = data.get('date')
    reason = data.get('reason')
    notes = data.get('notes', '')
    
    if not date or not reason:
        return jsonify({'error': 'Date and reason are required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO attendance (date, reason, notes)
            VALUES (?, ?, ?)
        """, (date, reason, notes))
        conn.commit()
        
        return jsonify({'success': True, 'id': cursor.lastrowid})
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Record already exists for this date'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/attendance/<int:record_id>', methods=['DELETE'])
def api_delete_attendance(record_id):
    """Delete attendance record."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Record not found'}), 404
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/gmail/download', methods=['POST'])
def api_gmail_download():
    """Trigger Gmail download for run sheets and/or payslips."""
    data = request.json
    mode = data.get('mode', 'all')  # all, runsheets, payslips
    after_date = data.get('after_date', '2025/01/01')
    
    try:
        import subprocess
        import sys
        
        # Build command
        cmd = [sys.executable, 'scripts/download_runsheets_gmail.py']
        
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


@app.route('/api/gmail/status', methods=['GET'])
def api_gmail_status():
    """Check if Gmail credentials are configured."""
    from pathlib import Path
    
    credentials_exist = Path('credentials.json').exists()
    token_exist = Path('token.json').exists()
    
    return jsonify({
        'configured': credentials_exist,
        'authenticated': token_exist,
        'credentials_path': 'credentials.json',
        'token_path': 'token.json'
    })


@app.route('/api/data/sync-payslips', methods=['POST'])
def api_sync_payslips():
    """Sync payslips from PaySlips folder."""
    try:
        import subprocess
        import sys
        
        process = subprocess.Popen(
            [sys.executable, 'scripts/extract_payslips.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=180)
        
        if process.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Payslips synced successfully',
                'output': stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': stderr or 'Sync failed',
                'output': stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Sync timed out (took longer than 3 minutes)'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data/sync-runsheets', methods=['POST'])
def api_sync_runsheets():
    """Sync run sheets from RunSheets folder."""
    try:
        import subprocess
        import sys
        
        process = subprocess.Popen(
            [sys.executable, 'scripts/import_run_sheets.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=300)
        
        if process.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Run sheets synced successfully',
                'output': stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': stderr or 'Sync failed',
                'output': stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Sync timed out (took longer than 5 minutes)'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data/reorganize-runsheets', methods=['POST'])
def api_reorganize_runsheets():
    """Reorganize run sheets by date and driver."""
    data = request.json
    dry_run = data.get('dry_run', False)
    
    try:
        import subprocess
        import sys
        
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


if __name__ == '__main__':
    # Initialize attendance table on startup
    init_attendance_table()
    print("\n" + "="*80)
    print("WAGES APP - WEB INTERFACE")
    print("="*80)
    print("\n🌐 Starting web server...")
    print("📊 Open your browser to: http://localhost:5001")
    print("⏹️  Press Ctrl+C to stop\n")
    print("="*80 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
