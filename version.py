"""
Application version information
Update this file when making releases
"""

from datetime import datetime
import os

# Version Information
APP_VERSION = "2.4.0"
BUILD_DATE = "2026.01.13"
RELEASE_DATE = datetime(2026, 1, 13)

# Changelog - Add new entries at the top
CHANGELOG = [
    {
        "version": "2.4.0",
        "date": "January 13, 2026",
        "type": "minor",  # major, minor, patch
        "changes": [
            "📧 NEW: Automatic email confirmation system for extra jobs with agreed rates",
            "✉️ Professional HTML email templates sent to manager with user CC'd",
            "📝 Email confirmations include job details, agreed rate, and 24-hour objection period",
            "🔍 NEW: Email Audit Trail in Reports - track all sent confirmation emails",
            "📊 Email audit shows date sent, job details, agreed rate, and recipient",
            "💾 Email audit log database table with full historical tracking",
            "⚙️ Email settings in Profile - configure manager email and auto-send preferences",
            "🔒 Smart edit protection - emails only resend if agreed price changes",
            "📮 Postcode field now properly saves when adding extra jobs",
            "📍 Postcode displays in Extra Jobs report and Email Audit trail",
            "🎯 User name (Daniel Hanson) included in email subject and body",
            "💪 Legal protection - creates written evidence of verbally agreed rates",
            "🔗 Integrated with existing Gmail OAuth setup for seamless sending"
        ]
    },
    {
        "version": "2.3.0",
        "date": "December 10, 2025",
        "type": "minor",  # major, minor, patch
        "changes": [
            "📊 NEW: Comprehensive Earnings Analytics dashboard on Wages page",
            "📈 Added year projection, forecasting, and goal tracking with progress bars",
            "📉 Year-over-year comparison cards showing performance trends",
            "📊 Monthly earnings trends chart with multi-year comparison",
            "👥 Customer and activity breakdown charts with top performers",
            "🏆 Best/worst weeks analysis with detailed metrics",
            "✅ Job completion statistics and regular vs extra jobs breakdown",
            "📊 NEW: Runsheets Analytics with Overview, Customers, and Activities tabs",
            "⚠️ Enhanced DNCO loss calculation using customer + activity type historical averages",
            "🔄 DNCO status normalization (consolidated case variations)",
            "📅 Year filtering on all analytics tabs (2021-2025)",
            "🏢 Customer mapping integration across all analytics for consolidated reporting",
            "💰 Fixed Week 35 earnings discrepancy (removed duplicate job entry)",
            "💵 Added verbal pay difference display in payslips Net Pay column",
            "📱 All new analytics fully mobile-responsive with Bootstrap grid system",
            "🎨 Professional charts and visualizations using Chart.js"
        ]
    },
    {
        "version": "2.2.0",
        "date": "November 27, 2025",
        "type": "minor",  # major, minor, patch
        "changes": [
            "🎨 Complete mobile UI overhaul - standardized responsive layouts across all pages",
            "📱 Fixed Reports page navigation pills to display all options on mobile (no more dropdown)",
            "📊 Enhanced Custom Report Generator with clean 3-line mobile layout",
            "🔧 Fixed Missing Run Sheets attendance API integration and 7-day work schedule support",
            "📋 Standardized all report sections with consistent mobile-friendly controls",
            "🎯 Improved mobile button layouts on Profile, Sync, and Attendance pages",
            "📱 Added mobile table scrolling support across Reports, Paypoint, and Weekly Summary",
            "🚫 Removed all 'swipe to see more' messages for cleaner interface",
            "🔒 Enhanced security by properly handling service account credentials",
            "📊 Added Paypoint report with complete PDF export functionality",
            "🧹 Cleaned barcode prefixes from database (removed C| and D| prefixes)",
            "🎨 Unified UI styling across Reports, Wages, and Runsheets pages",
            "📱 Enhanced backup list mobile styling for better user experience"
        ]
    },
    {
        "version": "2.1.0",
        "date": "November 27, 2025",
        "type": "minor",  # major, minor, patch
        "changes": [
            "Added floating notifications system for better user feedback",
            "Implemented individual backup restore buttons for each backup",
            "Fixed system logs modal display (no more popup blocking)",
            "Added dynamic version system with automatic changelog",
            "Comprehensive codebase cleanup - archived 180MB+ legacy files",
            "Enhanced backup system with proper API endpoint integration"
        ]
    },
    {
        "version": "2.0.0",
        "date": "November 27, 2025",
        "type": "major",  # major, minor, patch
        "changes": [
            "Complete settings page redesign with separate focused pages",
            "Improved mobile responsiveness and touch optimization", 
            "Enhanced sync log display and real-time monitoring",
            "Better error handling and user feedback"
        ]
    },
    {
        "version": "1.9.0", 
        "date": "November 18, 2025",
        "type": "minor",
        "changes": [
            "Implemented comprehensive auto-sync system",
            "Added 12 advanced sync features with health monitoring",
            "Enhanced backup and restore functionality", 
            "Improved attendance tracking with date ranges"
        ]
    },
    {
        "version": "1.8.0",
        "date": "November 12, 2025", 
        "type": "minor",
        "changes": [
            "Unified styling system across all pages",
            "Data folder reorganization and cleanup",
            "Enhanced file management and organization",
            "Improved database performance and optimization"
        ]
    }
]

def get_git_version():
    """Try to get version from git tags"""
    try:
        import subprocess
        # Get the latest git tag
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None

def get_version_info():
    """Get current version information"""
    # Try git tag first, fallback to manual version
    git_version = get_git_version()
    version = git_version if git_version else APP_VERSION
    
    return {
        'version': version,
        'build_date': BUILD_DATE,
        'release_date': RELEASE_DATE,
        'changelog': CHANGELOG,
        'is_git_version': git_version is not None
    }
