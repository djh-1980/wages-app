"""
Application version information
Update this file when making releases
"""

from datetime import datetime
import os

# Version Information
APP_VERSION = "3.0.0"
BUILD_DATE = "2026.04.02"
RELEASE_DATE = datetime(2026, 4, 2)

# Changelog - Add new entries at the top
CHANGELOG = [
    {
        "version": "3.0.0",
        "date": "April 2, 2026",
        "type": "major",  # major, minor, patch
        "changes": [
            "🔄 MAJOR: Rolled back custom mobile drawer to Bootstrap default navbar",
            "🧹 REMOVED: Custom slide-in drawer overlay system (mobile-menu.js)",
            "🧹 REMOVED: 900+ lines of custom mobile navbar CSS",
            "✅ KEPT: Bottom navigation bar for quick mobile access",
            "✅ KEPT: All col-12 responsive grid fixes across pages",
            "📱 SIMPLIFIED: Bootstrap now handles all navbar behavior natively",
            "🎯 IMPROVED: More reliable mobile menu with standard Bootstrap collapse",
            "⚡ OPTIMIZED: Reduced CSS from 900+ lines to 57 lines (mobile-enhancements.css)",
            "🔧 FIXED: Merged requirements.txt and requirements_auth.txt into single file",
            "📦 CLEANED: Removed duplicate authentication dependencies",
            "💷 HMRC Making Tax Digital (MTD) integration fully implemented",
            "🔐 OAuth 2.0 authentication with HMRC API",
            "📊 Quarterly obligation tracking (Q1-Q4 deadlines)",
            "📤 Submit income & expenses directly to HMRC",
            "📋 Submission history with receipt tracking",
            "🧪 Sandbox & production environment support",
            "🛡️ Automatic fraud prevention headers",
            "🔄 Token auto-refresh & secure credential storage"
        ]
    },
    {
        "version": "2.7.0",
        "date": "March 10, 2026",
        "type": "minor",  # major, minor, patch
        "changes": [
            "🔄 FIXED: Runsheet sync missing date detection now works with DD/MM/YYYY format",
            "⚡ OPTIMIZED: Download only emails matching missing dates (no re-downloading)",
            "📅 ENHANCED: Attendance integration - excludes days off from missing dates",
            "🗓️ FIXED: Removed weekend exclusion - now checks all 7 days (user works weekends)",
            "💾 FIXED: Import memory crashes with --recent-minutes argument",
            "📊 NEW: Last Sync Summary card showing key metrics at a glance",
            "🎨 ENHANCED: Color-coded sync log with formatted output",
            "⚠️ NEW: Separate error listing in sync log for better visibility",
            "🧹 REMOVED: Auto-Sync badge from navbar (consolidated in settings)",
            "🔧 FIXED: Missing Runsheets API updated to match download script logic"
        ]
    },
    {
        "version": "2.6.0",
        "date": "February 5, 2026",
        "type": "minor",  # major, minor, patch
        "changes": [
            "🗺️ ENHANCED: Advanced route optimization with nearest-neighbor algorithm",
            "🚫 Fixed route crisscrossing - routes now follow logical geographic flow",
            "📍 Route structure: Home → Depot → Optimized Jobs → Home",
            "🗺️ Interactive map with actual road routes (Google Directions API)",
            "📱 Inline map display - no separate modal needed",
            "🔄 Duplicate job handling for same-location addresses",
            "📊 Job table reorders to match optimized route sequence",
            "💾 All route data persists across devices (database storage)",
            "🔒 Google Maps API key secured in environment variables",
            "💰 HMRC Mileage Allowance calculator with tax comparison",
            "📊 Side-by-side charts: Monthly Mileage + Fuel Cost breakdown",
            "📈 Fuel efficiency tracking (Miles per £ spent)",
            "📋 Monthly breakdown table with sortable columns",
            "💾 CSV export for tax records and accountant submissions",
            "⚠️ Anomaly detection - highlights unusual mileage months",
            "💷 Site-wide thousand separators for all currency amounts",
            "🧹 Removed redundant Missing Mileage Data section",
            "📱 Mobile-optimized map and responsive layouts throughout"
        ]
    },
    {
        "version": "2.5.0",
        "date": "February 4, 2026",
        "type": "minor",  # major, minor, patch
        "changes": [
            "🗺️ NEW: Intelligent route optimization with automatic recalculation",
            "📍 Completed jobs automatically move to top in completion order",
            "🚫 DNCO jobs excluded from route calculations (never visited)",
            "🔄 Status toggle - click action button twice to revert to pending",
            "📊 Batch mileage estimation for historical dates (2025 and earlier)",
            "🎯 Redesigned mileage management page with estimation tools",
            "💾 Persistent route storage in database (survives browser clear)",
            "🔀 Route recalculates when marking jobs as completed, missed, or DNCO",
            "🏠 Routes include home → depot → jobs → home for accurate mileage",
            "⚡ Progress bar and preview table for batch mileage estimation"
        ]
    },
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
