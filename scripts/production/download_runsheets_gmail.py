#!/usr/bin/env python3
"""
Download run sheets from Gmail automatically.
Searches for emails with run sheet attachments and downloads them.
Optionally organizes by date and imports to database.
"""

import os
import base64
import re
from datetime import datetime
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import PyPDF2
import sqlite3

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailRunSheetDownloader:
    def __init__(self, download_dir='RunSheets'):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.service = None
        
    def extract_date_from_pdf_filename(self, filename: str) -> str:
        """Extract date from filename like 'Runsheet_11_runs_2025_11_14.pdf' -> '14/11/2025'."""
        import re
        # Try pattern: YYYY_MM_DD
        match = re.search(r'(\d{4})_(\d{2})_(\d{2})', filename)
        if match:
            year, month, day = match.groups()
            return f"{day}/{month}/{year}"
        return None
    
    def extract_date_from_pdf(self, pdf_path: Path) -> str:
        """Extract date from PDF to determine folder structure."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages[:3]:
                    text = page.extract_text()
                    lines = text.split('\n')
                    
                    for line in lines[:10]:
                        # Look for date pattern DD/MM/YYYY
                        date_match = re.search(r'Date\s+(\d{2}/\d{2}/\d{4})', line)
                        if date_match:
                            return date_match.group(1)
                        
                        date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', line)
                        if date_match:
                            return date_match.group(1)
            return None
        except:
            return None
    
    def has_driver_name(self, pdf_path: Path, driver_name: str = "Hanson, Daniel") -> bool:
        """Check if this is a runsheet that should be organized (includes multi-driver sheets)."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text = page.extract_text()
                    # Check for your name in various formats
                    if (driver_name.lower() in text.lower() or
                        "daniel hanson" in text.lower() or
                        "hanson, daniel" in text.lower() or
                        # Also organize if it's a runsheet format (multi-driver sheets)
                        "run sheet" in text.lower() or
                        "runsheet" in text.lower() or
                        "job #" in text.lower()):
                        return True
            return False
        except:
            return False
    
    def organize_pdf(self, pdf_path: Path) -> Path:
        """Move PDF to year/month folder and rename to DH_DD-MM-YYYY.pdf."""
        # Check if file exists (may have been organized already)
        if not pdf_path.exists():
            print(f"  ⚠️  File not found (may be already organized): {pdf_path.name}")
            # Try to find the organized version
            date_str = self.extract_date_from_pdf_filename(pdf_path.name)
            if date_str:
                try:
                    dt = datetime.strptime(date_str, '%d/%m/%Y')
                    month_name = dt.strftime('%B')
                    organized_path = self.download_dir / str(dt.year) / month_name / f"DH_{dt.strftime('%d-%m-%Y')}.pdf"
                    if organized_path.exists():
                        return organized_path
                except:
                    pass
            return pdf_path
        
        # Check if this is your run sheet
        if not self.has_driver_name(pdf_path):
            # Move to manual folder for review
            manual_dir = self.download_dir / "manual"
            manual_dir.mkdir(exist_ok=True)
            target_path = manual_dir / pdf_path.name
            
            if target_path.exists():
                pdf_path.unlink()  # Delete duplicate
                return target_path
            
            pdf_path.rename(target_path)
            print(f"  ⚠️  Not your run sheet - moved to manual: {pdf_path.name}")
            return target_path
        
        date_str = self.extract_date_from_pdf(pdf_path)
        
        if not date_str:
            return pdf_path
        
        try:
            # Parse DD/MM/YYYY
            dt = datetime.strptime(date_str, '%d/%m/%Y')
            
            # Create year/month folder (e.g., 2025/September)
            month_name = dt.strftime('%B')  # Full month name
            target_dir = self.download_dir / str(dt.year) / month_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Rename file to DH_DD-MM-YYYY.pdf
            new_filename = f"DH_{dt.strftime('%d-%m-%Y')}.pdf"
            target_path = target_dir / new_filename
            
            # Handle duplicates
            if target_path.exists():
                pdf_path.unlink()  # Delete duplicate
                return target_path
            
            pdf_path.rename(target_path)
            return target_path
            
        except Exception as e:
            return pdf_path
    
    def authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        token_path = Path('token.json')
        credentials_path = Path('credentials.json')
        
        # The file token.json stores the user's access and refresh tokens
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("🔄 Refreshing expired Gmail token...")
                    creds.refresh(Request())
                    print("✅ Token refreshed successfully")
                    
                    # Save the refreshed credentials
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    
                except Exception as e:
                    print(f"❌ Token refresh failed: {e}")
                    print("🔄 Attempting to re-authenticate...")
                    
                    # Try to re-authenticate automatically
                    if not credentials_path.exists():
                        print("❌ Error: credentials.json not found!")
                        print("Cannot re-authenticate without credentials.json")
                        return False
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(credentials_path), SCOPES)
                        # Use run_console instead of run_local_server for headless environments
                        creds = flow.run_console()
                        
                        # Save the new credentials
                        with open(token_path, 'w') as token:
                            token.write(creds.to_json())
                        
                        print("✅ Re-authentication successful")
                        
                    except Exception as auth_e:
                        print(f"❌ Re-authentication failed: {auth_e}")
                        return False
            else:
                if not credentials_path.exists():
                    print("❌ Error: credentials.json not found!")
                    print()
                    print("To set up Gmail API access:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a new project or select existing one")
                    print("3. Enable Gmail API")
                    print("4. Create OAuth 2.0 credentials (Desktop app)")
                    print("5. Download credentials.json to this directory")
                    print()
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def find_missing_runsheet_dates(self, days_back=30):
        """Find dates in the last N days that don't have run sheets in the database."""
        db_path = Path('data/payslips.db')
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return []
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get all dates from the last N days that have run sheet jobs
            cursor.execute("""
                SELECT DISTINCT date 
                FROM run_sheet_jobs 
                WHERE date IS NOT NULL 
                AND date != ''
                AND date >= date('now', '-{} days')
                ORDER BY date DESC
            """.format(days_back))
            
            existing_dates = {row[0] for row in cursor.fetchall()}
            conn.close()
            
            # Generate all dates in the last N days (excluding weekends)
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            expected_dates = set()
            current_date = start_date
            
            while current_date <= end_date:
                # Skip weekends (Saturday=5, Sunday=6)
                if current_date.weekday() < 5:  # Monday=0 to Friday=4
                    date_str = current_date.strftime('%d/%m/%Y')
                    expected_dates.add(date_str)
                current_date += timedelta(days=1)
            
            # Find missing dates
            missing_dates = expected_dates - existing_dates
            
            return sorted(list(missing_dates), key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            return []
    
    def search_run_sheet_emails(self, after_date='2025/01/01', recent_only=False):
        """Search for emails with run sheet attachments."""
        if not self.service:
            return []
        
        # Search query for run sheets
        # Adjust these search terms based on your email patterns
        # Searches for PDFs with "RUN SHEETS" in subject, "runsheet" in filename, or "Runsheet" (new format)
        
        if recent_only:
            # Search recent emails without date restriction (includes future dates)
            query = f'has:attachment filename:pdf (subject:"RUN SHEETS" OR subject:runsheet OR filename:runsheet) newer_than:7d'
        else:
            # Use original date-based search
            # Gmail filename search is case-insensitive, so just use lowercase
            # Convert date format for Gmail (YYYY/MM/DD to YYYY-MM-DD)
            gmail_date = after_date.replace('/', '-')
            query = f'has:attachment filename:pdf (subject:"RUN SHEETS" OR subject:runsheet OR filename:runsheet) after:{gmail_date}'
        
        print(f"🔍 Gmail search query: {query}")
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            
            # Handle pagination if there are more results
            while 'nextPageToken' in results:
                page_token = results['nextPageToken']
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=500,
                    pageToken=page_token
                ).execute()
                messages.extend(results.get('messages', []))
            
            return messages
        
        except Exception as e:
            print(f"Error searching emails: {e}")
            return []
    
    def search_payslip_emails(self, after_date='2025/01/01'):
        """Search for emails with payslip attachments (Tuesdays at 1300)."""
        if not self.service:
            return []
        
        # Search query for payslips - looking for SASER payroll emails
        # Convert date format for Gmail (YYYY/MM/DD to YYYY-MM-DD)
        gmail_date = after_date.replace('/', '-')
        # Search for SASER emails with date filter
        query = f'SASER after:{gmail_date}'
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            
            # Handle pagination
            while 'nextPageToken' in results:
                page_token = results['nextPageToken']
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=500,
                    pageToken=page_token
                ).execute()
                messages.extend(results.get('messages', []))
            
            # Filter for Tuesdays around 1300 (13:00)
            filtered_messages = []
            for msg in messages:
                try:
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    headers = full_msg['payload']['headers']
                    date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    
                    # Parse email date
                    from email.utils import parsedate_to_datetime
                    email_date = parsedate_to_datetime(date_str)
                    
                    # Check if Tuesday (weekday() == 1) - removed strict time filtering
                    if email_date.weekday() == 1:
                        filtered_messages.append(msg)
                except:
                    # If we can't parse date, include it anyway
                    filtered_messages.append(msg)
            
            return filtered_messages
        
        except Exception as e:
            print(f"Error searching payslip emails: {e}")
            return []
    
    def download_attachments(self, message_id):
        """Download all PDF attachments from a message."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Get email subject and date for context
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            downloaded = []
            
            # Check for attachments
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part.get('filename') and part['filename'].lower().endswith('.pdf'):
                        attachment_id = part['body'].get('attachmentId')
                        
                        if attachment_id:
                            attachment = self.service.users().messages().attachments().get(
                                userId='me',
                                messageId=message_id,
                                id=attachment_id
                            ).execute()
                            
                            file_data = base64.urlsafe_b64decode(attachment['data'])
                            filename = part['filename']
                            filepath = self.download_dir / filename
                            
                            # Download file (overwrite if exists to ensure we have latest)
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                            
                            downloaded.append(filename)
                            print(f"  ✓ Downloaded: {filename}")
            
            return downloaded
        
        except Exception as e:
            print(f"  ✗ Error downloading attachments: {e}")
            return []
    
    def download_all_run_sheets(self, after_date='2025/01/01', organize=True, auto_import=True, recent_only=False):
        """Download all run sheets from Gmail."""
        print("=" * 70)
        print("GMAIL RUN SHEET DOWNLOADER")
        print("=" * 70)
        print()
        
        # Authenticate
        print("🔐 Authenticating with Gmail...")
        if not self.authenticate():
            return
        
        print("✓ Authenticated successfully")
        print()
        
        # Search for emails
        if recent_only:
            print("🔍 Searching for recent run sheet emails (last 7 days, including future dates)...")
        else:
            print(f"🔍 Searching for run sheet emails after {after_date}...")
        messages = self.search_run_sheet_emails(after_date, recent_only=recent_only)
        
        if not messages:
            print("No run sheet emails found")
            return
        
        print(f"✓ Found {len(messages)} emails with run sheets")
        print()
        
        # Download attachments
        print("📥 Downloading attachments...")
        total_downloaded = 0
        downloaded_files = []
        
        for i, message in enumerate(messages, 1):
            print(f"[{i}/{len(messages)}] Processing email...")
            filenames = self.download_attachments(message['id'])
            total_downloaded += len(filenames)
            
            # Track downloaded file paths
            for filename in filenames:
                downloaded_files.append(self.download_dir / filename)
        
        print()
        print("=" * 70)
        print(f"✅ Download complete: {total_downloaded} new run sheets downloaded")
        print("=" * 70)
        print()
        
        # Organize into year/month folders
        if organize and downloaded_files:
            print("🗂️  Organizing by date...")
            organized_files = []
            for pdf_path in downloaded_files:
                organized_path = self.organize_pdf(pdf_path)
                organized_files.append(organized_path)
                if organized_path != pdf_path:
                    print(f"  📁 {organized_path.relative_to(self.download_dir)}")
            
            print()
            print("=" * 70)
            print(f"✅ Organization complete")
            print("=" * 70)
            print()
            
            downloaded_files = organized_files
        
        # Import to database
        if auto_import and downloaded_files:
            print("💾 Importing to database...")
            try:
                from import_run_sheets import RunSheetImporter
                
                importer = RunSheetImporter()
                total_imported = 0
                
                for pdf_path in downloaded_files:
                    count = importer.import_run_sheet(pdf_path, self.download_dir)
                    total_imported += count
                
                importer.close()
                
                print()
                print("=" * 70)
                print(f"✅ Import complete: {total_imported} jobs imported")
                print("=" * 70)
                
            except Exception as e:
                print(f"⚠️  Import failed: {e}")
                print("   Run 'python scripts/production/import_run_sheets.py' manually")
        
        print()
        print(f"📁 Files saved to: {self.download_dir.absolute()}")
    
    def download_missing_runsheets(self, days_back=30):
        """Find and download missing run sheets from the last N days."""
        print("=" * 70)
        print("MISSING RUN SHEETS DOWNLOADER")
        print("=" * 70)
        print(f"Checking for missing run sheets in the last {days_back} days...")
        print()
        
        if not self.authenticate():
            return
        
        # Find missing dates
        missing_dates = self.find_missing_runsheet_dates(days_back)
        
        if not missing_dates:
            print("✅ No missing run sheets found!")
            return
        
        print(f"📋 Found {len(missing_dates)} missing dates:")
        for date in missing_dates:
            print(f"  • {date}")
        print()
        
        # Search for emails in the last N days
        print("🔍 Searching Gmail for run sheet emails...")
        emails = self.search_run_sheet_emails(recent_only=True)
        
        if not emails:
            print("❌ No run sheet emails found in Gmail")
            return
        
        print(f"📧 Found {len(emails)} run sheet emails")
        
        # Download all recent run sheets (they might contain the missing dates)
        downloaded_files = []
        total_downloaded = 0
        
        for i, email in enumerate(emails, 1):
            print(f"\n📧 Processing email {i}/{len(emails)}...")
            
            try:
                # Get email details
                message = self.service.users().messages().get(
                    userId='me', 
                    id=email['id']
                ).execute()
                
                # Get email subject and date
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                date_header = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                print(f"  Subject: {subject}")
                print(f"  Date: {date_header}")
                
                # Download attachments
                email_files = self.download_attachments(email['id'])
                downloaded_files.extend(email_files)
                total_downloaded += len(email_files)
                
            except Exception as e:
                print(f"  ✗ Error processing email: {e}")
        
        print()
        print("=" * 70)
        print("MISSING SHEETS DOWNLOAD COMPLETE")
        print("=" * 70)
        print(f"📥 Downloaded {total_downloaded} files")
        print()
        print("💡 Tip: Run the sync again to import these files into the database")
        print("   and check if the missing dates are now covered.")
        print()
        print(f"📁 Files saved to: {self.download_dir.absolute()}")
    
    def download_all_payslips(self, after_date='2025/01/01', auto_import=True):
        """Download all payslips from Gmail (Tuesdays at 1300 - saser files)."""
        print("=" * 70)
        print("GMAIL PAYSLIP DOWNLOADER")
        print("=" * 70)
        print()
        
        # Authenticate
        print("🔐 Authenticating with Gmail...")
        if not self.authenticate():
            return
        
        print("✓ Authenticated successfully")
        print()
        
        # Search for payslip emails
        print(f"🔍 Searching for payslip emails (saser files) after {after_date}...")
        messages = self.search_payslip_emails(after_date)
        
        if not messages:
            print("No payslip emails found")
            return
        
        print(f"✓ Found {len(messages)} payslip emails (Tuesdays at 1300)")
        print()
        
        # Download attachments to PaySlips folder
        payslip_dir = Path('PaySlips')
        payslip_dir.mkdir(exist_ok=True)
        
        print("📥 Downloading payslips...")
        total_downloaded = 0
        downloaded_files = []
        
        for i, message in enumerate(messages, 1):
            print(f"[{i}/{len(messages)}] Processing email...")
            
            try:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Download attachments
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        filename = part.get('filename', '')
                        if 'saser' in filename.lower() and filename.lower().endswith('.pdf'):
                            attachment_id = part['body'].get('attachmentId')
                            
                            if attachment_id:
                                attachment = self.service.users().messages().attachments().get(
                                    userId='me',
                                    messageId=message['id'],
                                    id=attachment_id
                                ).execute()
                                
                                file_data = base64.urlsafe_b64decode(attachment['data'])
                                
                                # Extract year from filename (e.g., "Week30 2025.pdf" -> "2025")
                                import re
                                year_match = re.search(r'(\d{4})', filename)
                                if filepath.exists():
                                    print(f"  ⏭️  Already exists: {filename}")
                                    # Still add to downloaded list so it gets processed
                                    downloaded_files.append(filepath)
                                    continue
                                
                                with open(filepath, 'wb') as f:
                                    f.write(file_data)
                                
                                downloaded_files.append(filepath)
                                total_downloaded += 1
                                print(f"  ✓ Downloaded: {filename}")
            
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print()
        print("=" * 70)
        print(f"✅ Download complete: {total_downloaded} new payslips downloaded")
        print("=" * 70)
        print()
        
        # Import to database
        if auto_import and downloaded_files:
            print("💾 Importing payslips to database...")
            try:
                import subprocess
                import sys
                
                # Run extract_payslips.py for each file
                total_imported = 0
                for pdf_path in downloaded_files:
                    try:
                        result = subprocess.run(
                            [sys.executable, 'scripts/production/extract_payslips.py', str(pdf_path)],
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        if result.returncode == 0:
                            total_imported += 1
                            print(f"  ✓ Imported: {pdf_path.name}")
                        else:
                            print(f"  ⚠️  Failed to import {pdf_path.name}")
                    except Exception as e:
                        print(f"  ⚠️  Failed to import {pdf_path.name}: {e}")
                
                print()
                print("=" * 70)
                print(f"✅ Import complete: {total_imported} payslips imported")
                print("=" * 70)
                
            except Exception as e:
                print(f"⚠️  Import failed: {e}")
                print("   Run 'python scripts/production/extract_payslips.py' manually")
        
        print()
        print(f"📁 Files saved to: {payslip_dir.absolute()}")
    
    def download_all(self, after_date='2025/01/01'):
        """Download both run sheets and payslips."""
        print("\n" + "=" * 70)
        print("GMAIL AUTO-DOWNLOADER - RUN SHEETS & PAYSLIPS")
        print("=" * 70)
        print()
        
        # Download run sheets
        self.download_all_run_sheets(after_date, organize=True, auto_import=True)
        
        print("\n")
        
        # Download payslips
        self.download_all_payslips(after_date, auto_import=True)
        
        print("\n" + "=" * 70)
        print("✅ ALL DOWNLOADS COMPLETE")
        print("=" * 70)


def main():
    """Run the downloader."""
    import sys
    
    # Parse arguments
    after_date = '2025/01/01'
    mode = 'all'  # all, runsheets, payslips
    recent_only = False
    
    for arg in sys.argv[1:]:
        if arg.startswith('--date='):
            after_date = arg.split('=')[1]
        elif arg == '--runsheets':
            mode = 'runsheets'
        elif arg == '--payslips':
            mode = 'payslips'
        elif arg == '--missing':
            mode = 'missing'
        elif arg == '--recent':
            recent_only = True
        elif arg in ['--help', '-h']:
            print("Usage: python download_runsheets_gmail.py [options]")
            print()
            print("Options:")
            print("  --date=YYYY/MM/DD   Download emails after this date (default: 2025/01/01)")
            print("  --runsheets         Download only run sheets")
            print("  --payslips          Download only payslips")
            print("  --missing           Find and download missing run sheets (last 30 days)")
            print("  --recent            Search recent emails (last 7 days, includes future dates)")
            print("  --help, -h          Show this help")
            print()
            print("Examples:")
            print("  python download_runsheets_gmail.py")
            print("  python download_runsheets_gmail.py --date=2024/01/01")
            print("  python download_runsheets_gmail.py --payslips")
            print("  python download_runsheets_gmail.py --runsheets --recent")
            print("  python download_runsheets_gmail.py --missing")
            return
        else:
            # Assume it's a date
            after_date = arg
    
    downloader = GmailRunSheetDownloader('data/documents/runsheets')
    
    if mode == 'all':
        downloader.download_all(after_date)
    elif mode == 'runsheets':
        downloader.download_all_run_sheets(after_date, recent_only=recent_only)
    elif mode == 'payslips':
        downloader.download_all_payslips(after_date)
    elif mode == 'missing':
        downloader.download_missing_runsheets(30)


if __name__ == "__main__":
    main()
