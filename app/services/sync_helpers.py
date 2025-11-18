"""
Helper methods for periodic sync service.
Database queries and email notifications.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = "data/database/payslips.db"


def get_latest_runsheet_date():
    """Get the most recent runsheet date from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Convert DD/MM/YYYY to YYYY-MM-DD for proper sorting, then convert back
        cursor.execute("""
            SELECT date 
            FROM run_sheet_jobs 
            WHERE date IS NOT NULL AND date != ''
            ORDER BY 
                substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2) DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        print(f"Error getting latest runsheet date: {e}")
        return None


def get_latest_payslip_week():
    """Get the most recent payslip week number from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT week_number, tax_year 
            FROM payslips 
            ORDER BY 
                CAST(tax_year AS INTEGER) DESC, 
                CAST(week_number AS INTEGER) DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return f"Week {result[0]}, {result[1]}"
        return None
    except Exception as e:
        print(f"Error getting latest payslip week: {e}")
        return None


def sync_payslips_to_runsheets():
    """Sync payslip data to runsheet jobs. Returns count of jobs updated."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update pay information
        cursor.execute("""
            UPDATE run_sheet_jobs 
            SET 
                pay_amount = (
                    SELECT j.amount 
                    FROM job_items j 
                    WHERE j.job_number = run_sheet_jobs.job_number
                    AND j.job_number IS NOT NULL
                    LIMIT 1
                ),
                pay_rate = (
                    SELECT j.rate 
                    FROM job_items j 
                    WHERE j.job_number = run_sheet_jobs.job_number
                    AND j.job_number IS NOT NULL
                    LIMIT 1
                ),
                pay_units = (
                    SELECT j.units 
                    FROM job_items j 
                    WHERE j.job_number = run_sheet_jobs.job_number
                    AND j.job_number IS NOT NULL
                    LIMIT 1
                ),
                pay_week = (
                    SELECT p.week_number 
                    FROM job_items j 
                    JOIN payslips p ON j.payslip_id = p.id
                    WHERE j.job_number = run_sheet_jobs.job_number
                    AND j.job_number IS NOT NULL
                    LIMIT 1
                ),
                pay_year = (
                    SELECT p.tax_year 
                    FROM job_items j 
                    JOIN payslips p ON j.payslip_id = p.id
                    WHERE j.job_number = run_sheet_jobs.job_number
                    AND j.job_number IS NOT NULL
                    LIMIT 1
                ),
                pay_updated_at = CURRENT_TIMESTAMP
            WHERE run_sheet_jobs.job_number IS NOT NULL
            AND EXISTS (
                SELECT 1 FROM job_items j 
                WHERE j.job_number = run_sheet_jobs.job_number
            )
        """)
        
        jobs_updated = cursor.rowcount
        
        # Update addresses (only N/A or if payslip has better data)
        cursor.execute("""
            UPDATE run_sheet_jobs 
            SET 
                job_address = CASE 
                    WHEN (run_sheet_jobs.job_address IN ('N/A', '', 'n/a', 'N/a') OR run_sheet_jobs.job_address IS NULL)
                    THEN (
                        SELECT j.location 
                        FROM job_items j 
                        WHERE j.job_number = run_sheet_jobs.job_number
                        AND j.location IS NOT NULL 
                        AND j.location != ''
                        AND j.location NOT IN ('N/A', 'SCS', 'TVS', 'IFM')
                        AND LENGTH(j.location) > 5
                        LIMIT 1
                    )
                    ELSE run_sheet_jobs.job_address
                END
            WHERE run_sheet_jobs.job_number IS NOT NULL
            AND run_sheet_jobs.job_address IN ('N/A', '', 'n/a', 'N/a')
            AND EXISTS (
                SELECT 1 FROM job_items j 
                WHERE j.job_number = run_sheet_jobs.job_number
                AND j.location IS NOT NULL
                AND j.location NOT IN ('N/A', 'SCS', 'TVS', 'IFM')
            )
        """)
        
        conn.commit()
        conn.close()
        
        return jobs_updated
    except Exception as e:
        print(f"Error syncing payslips to runsheets: {e}")
        return 0


def should_send_notification(sync_summary):
    """Determine if email notification should be sent."""
    # Send if anything was downloaded, imported, or if there are errors
    if (sync_summary['runsheets_downloaded'] > 0 or 
        sync_summary['payslips_downloaded'] > 0 or
        sync_summary['runsheets_imported'] > 0 or
        sync_summary['payslips_imported'] > 0 or
        sync_summary['jobs_synced'] > 0 or
        len(sync_summary['errors']) > 0):
        return True
    return False


def format_sync_email(sync_summary):
    """Format sync summary as email HTML with enhanced details."""
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    today_date = datetime.now().strftime('%A, %d %B %Y')
    
    # Determine overall status
    if len(sync_summary['errors']) > 0:
        status = "⚠️ COMPLETED WITH ERRORS"
        status_color = "#ff9800"
    elif (sync_summary['runsheets_downloaded'] > 0 or sync_summary['payslips_downloaded'] > 0):
        status = "✅ SUCCESS"
        status_color = "#4caf50"
    else:
        status = "ℹ️ NO NEW FILES"
        status_color = "#2196f3"
    
    # Get additional context
    total_files = sync_summary.get('runsheets_downloaded', 0) + sync_summary.get('payslips_downloaded', 0)
    sync_duration = sync_summary.get('duration_seconds', 0)
    latest_runsheet_date = sync_summary.get('latest_runsheet_date', 'N/A')
    latest_payslip_week = sync_summary.get('latest_payslip_week', 'N/A')
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: {status_color}; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .section {{ margin: 20px 0; padding: 15px; background-color: #f5f5f5; border-left: 4px solid #2196f3; }}
            .stats {{ display: flex; flex-wrap: wrap; gap: 15px; }}
            .stat-box {{ flex: 1; min-width: 200px; padding: 15px; background-color: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: #2196f3; }}
            .stat-label {{ color: #666; font-size: 14px; }}
            .error {{ color: #f44336; padding: 10px; background-color: #ffebee; border-left: 4px solid #f44336; margin: 10px 0; }}
            .info-box {{ background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 12px; margin: 10px 0; }}
            .success-box {{ background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 12px; margin: 10px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
            .quick-link {{ display: inline-block; background-color: #2196f3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{status}</h1>
            <p>Wages App Auto-Sync Report</p>
            <p><strong>{today_date}</strong></p>
            <p>{now}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📊 Sync Summary</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-number">{sync_summary['runsheets_downloaded']}</div>
                        <div class="stat-label">Runsheets Downloaded</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{sync_summary['runsheets_imported']}</div>
                        <div class="stat-label">Runsheet Jobs Imported</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{sync_summary['payslips_downloaded']}</div>
                        <div class="stat-label">Payslips Downloaded</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{sync_summary['payslips_imported']}</div>
                        <div class="stat-label">Payslips Imported</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{sync_summary['jobs_synced']}</div>
                        <div class="stat-label">Jobs Synced with Pay Data</div>
                    </div>
                </div>
            </div>
    """
    
    # Add latest data info
    if latest_runsheet_date != 'N/A' or latest_payslip_week != 'N/A':
        html += """
            <div class="section">
                <h2>📅 Latest Data</h2>
        """
        if latest_runsheet_date != 'N/A':
            html += f'<div class="info-box"><strong>Latest Runsheet:</strong> {latest_runsheet_date}</div>'
        if latest_payslip_week != 'N/A':
            html += f'<div class="info-box"><strong>Latest Payslip:</strong> {latest_payslip_week}</div>'
        html += "</div>"
    
    # Add sync performance
    if sync_duration > 0:
        html += f"""
            <div class="section">
                <h2>⚡ Performance</h2>
                <div class="info-box">
                    <strong>Sync Duration:</strong> {sync_duration} seconds<br>
                    <strong>Files Processed:</strong> {total_files}<br>
                    <strong>Average Time per File:</strong> {round(sync_duration / total_files, 2) if total_files > 0 else 0} seconds
                </div>
            </div>
        """
    
    # Add errors section if any
    if sync_summary['errors']:
        html += """
            <div class="section">
                <h2>⚠️ Errors</h2>
        """
        for error in sync_summary['errors']:
            html += f'<div class="error">{error}</div>'
        html += "</div>"
    
    # Add success details if files were processed
    if total_files > 0:
        html += """
            <div class="section">
                <h2>✅ What Was Processed</h2>
        """
        if sync_summary['runsheets_downloaded'] > 0:
            html += f"""
                <div class="success-box">
                    <strong>Runsheets:</strong> {sync_summary['runsheets_downloaded']} file(s) downloaded<br>
                    <strong>Jobs Imported:</strong> {sync_summary['runsheets_imported']} job(s)
                </div>
            """
        if sync_summary['payslips_downloaded'] > 0:
            html += f"""
                <div class="success-box">
                    <strong>Payslips:</strong> {sync_summary['payslips_downloaded']} file(s) downloaded<br>
                    <strong>Payslips Imported:</strong> {sync_summary['payslips_imported']}<br>
                    <strong>Jobs Updated with Pay Data:</strong> {sync_summary['jobs_synced']}
                </div>
            """
        html += "</div>"
    
    # Add next steps
    html += """
            <div class="section">
                <h2>📋 What to Do Next</h2>
                <ul>
                    <li>Check the website to verify all data is displaying correctly</li>
                    <li>Review any runsheets that need status updates (DNCO, missed, etc.)</li>
                    <li>Verify payslip totals match your expectations</li>
                </ul>
                <div style="text-align: center; margin-top: 20px;">
                    <a href="http://localhost:5000/wages" class="quick-link">📊 View Wages</a>
                    <a href="http://localhost:5000/runsheets" class="quick-link">📋 View Runsheets</a>
                    <a href="http://localhost:5000/settings" class="quick-link">⚙️ Settings</a>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>This is an automated message from your Wages App sync service.</strong></p>
                <p>Next sync will run automatically based on your schedule.</p>
                <p style="color: #999; font-size: 11px;">Sync completed at {now}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html
