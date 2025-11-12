"""
Path Constants for TVS Wages Application
Centralized path definitions for the organized data folder structure.
"""

from pathlib import Path

# Base paths
BASE_DATA_DIR = Path("data")
DATABASE_DIR = BASE_DATA_DIR / "database"
DOCUMENTS_DIR = BASE_DATA_DIR / "documents"
EXPORTS_DIR = BASE_DATA_DIR / "exports"
PROCESSING_DIR = BASE_DATA_DIR / "processing"
REPORTS_DIR = BASE_DATA_DIR / "reports"
UPLOADS_DIR = BASE_DATA_DIR / "uploads"

# Database paths
DATABASE_FILE = DATABASE_DIR / "payslips.db"
DATABASE_BACKUPS_DIR = DATABASE_DIR / "backups"

# Document paths
RUNSHEETS_DIR = DOCUMENTS_DIR / "runsheets"
PAYSLIPS_DIR = DOCUMENTS_DIR / "payslips"

# Export paths
CSV_EXPORTS_DIR = EXPORTS_DIR / "csv"
SUMMARY_EXPORTS_DIR = EXPORTS_DIR / "summaries"

# Processing workflow paths
PROCESSING_QUEUE_DIR = PROCESSING_DIR / "queue"
PROCESSING_TEMP_DIR = PROCESSING_DIR / "temp"
PROCESSING_FAILED_DIR = PROCESSING_DIR / "failed"
PROCESSING_MANUAL_DIR = PROCESSING_DIR / "manual"
PROCESSING_PROCESSED_DIR = PROCESSING_DIR / "processed"

# Upload paths
UPLOADS_PENDING_DIR = UPLOADS_DIR / "pending"
UPLOADS_PROCESSED_DIR = UPLOADS_DIR / "processed"

# Legacy compatibility - these should be gradually phased out
LEGACY_PATHS = {
    "payslips_db": str(DATABASE_FILE),
    "manual_uploads": str(PROCESSING_MANUAL_DIR),
    "temp_processing": str(PROCESSING_TEMP_DIR),
    "failed_processing": str(PROCESSING_FAILED_DIR)
}

# Notification files
NEW_RUNSHEETS_NOTIFICATION = BASE_DATA_DIR / "new_runsheets.json"

def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        DATABASE_DIR, DATABASE_BACKUPS_DIR,
        RUNSHEETS_DIR, PAYSLIPS_DIR,
        CSV_EXPORTS_DIR, SUMMARY_EXPORTS_DIR,
        PROCESSING_QUEUE_DIR, PROCESSING_TEMP_DIR, PROCESSING_FAILED_DIR,
        PROCESSING_MANUAL_DIR, PROCESSING_PROCESSED_DIR,
        UPLOADS_PENDING_DIR, UPLOADS_PROCESSED_DIR,
        REPORTS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def get_archive_path(document_type: str, year: int, month: int) -> Path:
    """Get archive path for a specific document type, year, and month."""
    month_names = [
        "01-January", "02-February", "03-March", "04-April",
        "05-May", "06-June", "07-July", "08-August",
        "09-September", "10-October", "11-November", "12-December"
    ]
    
    if document_type == "runsheets":
        return RUNSHEETS_DIR / str(year) / month_names[month - 1]
    elif document_type == "payslips":
        return PAYSLIPS_DIR / str(year) / month_names[month - 1]
    else:
        raise ValueError(f"Unknown document type: {document_type}")

def get_report_path(year: int, month: int) -> Path:
    """Get report path for a specific year and month."""
    month_names = [
        "01-January", "02-February", "03-March", "04-April",
        "05-May", "06-June", "07-July", "08-August",
        "09-September", "10-October", "11-November", "12-December"
    ]
    
    return REPORTS_DIR / str(year) / month_names[month - 1]
