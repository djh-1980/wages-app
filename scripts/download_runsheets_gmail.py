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

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailRunSheetDownloader:
    def __init__(self, download_dir='RunSheets'):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.service = None
        
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
    
    def organize_pdf(self, pdf_path: Path) -> Path:
        """Move PDF to year/month folder based on date in PDF."""
        date_str = self.extract_date_from_pdf(pdf_path)
        
        if not date_str:
            return pdf_path
        
        try:
            # Parse DD/MM/YYYY
            dt = datetime.strptime(date_str, '%d/%m/%Y')
            
            # Create year/month folder
            target_dir = self.download_dir / str(dt.year) / f"{dt.month:02d}"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Move file
            target_path = target_dir / pdf_path.name
            
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
                creds.refresh(Request())
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
    
    def search_run_sheet_emails(self, after_date='2025/01/01'):
        """Search for emails with run sheet attachments."""
        if not self.service:
            return []
        
        # Search query for run sheets
        # Adjust these search terms based on your email patterns
        # Searches for PDFs with "RUN SHEETS" in subject or "runsheet" in filename
        query = f'has:attachment filename:pdf (subject:"RUN SHEETS" OR filename:runsheet OR subject:runsheet) after:{after_date}'
        
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
                            
                            # Don't overwrite existing files
                            if filepath.exists():
                                print(f"  ⏭️  Skipped (already exists): {filename}")
                                continue
                            
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                            
                            downloaded.append(filename)
                            print(f"  ✓ Downloaded: {filename}")
            
            return downloaded
        
        except Exception as e:
            print(f"  ✗ Error downloading attachments: {e}")
            return []
    
    def download_all_run_sheets(self, after_date='2025/01/01', organize=True, auto_import=True):
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
        print(f"🔍 Searching for run sheet emails after {after_date}...")
        messages = self.search_run_sheet_emails(after_date)
        
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
                print("   Run 'python scripts/import_run_sheets.py' manually")
        
        print()
        print(f"📁 Files saved to: {self.download_dir.absolute()}")


def main():
    """Run the downloader."""
    import sys
    
    # Allow custom date as argument
    after_date = sys.argv[1] if len(sys.argv) > 1 else '2025/01/01'
    
    downloader = GmailRunSheetDownloader()
    downloader.download_all_run_sheets(after_date)


if __name__ == "__main__":
    main()
