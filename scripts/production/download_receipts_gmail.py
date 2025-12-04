#!/usr/bin/env python3
"""
Download receipts and invoices from Gmail automatically.
Searches for emails with receipt/invoice attachments and downloads them.
Organizes by tax year and month for expense tracking.
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

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly'
]

class GmailReceiptDownloader:
    def __init__(self, download_dir='data/receipts'):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.service = None
        
        # Merchants to search for
        self.merchants = [
            'amazon.co.uk', 'screwfix.com', 'toolstation.com', 'apple.com',
            'halfords.com', 'ee.co.uk', 'o2.co.uk', 'vodafone.co.uk',
            'shell', 'bp.com', 'esso', 'tesco.com', 'asda.com'
        ]
        
    def authenticate(self):
        """Authenticate with Gmail API using existing credentials."""
        creds = None
        token_path = Path('token.json')
        credentials_path = Path('credentials.json')
        
        # Token file stores user's access and refresh tokens
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    print("❌ credentials.json not found!")
                    print("   Please download from Google Cloud Console")
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def get_tax_year_folder(self, date_obj):
        """Get tax year folder name (e.g., '2024-25')."""
        if date_obj.month > 4 or (date_obj.month == 4 and date_obj.day >= 6):
            return f"{date_obj.year}-{str(date_obj.year + 1)[-2:]}"
        else:
            return f"{date_obj.year - 1}-{str(date_obj.year)[-2:]}"
    
    def get_month_folder(self, date_obj):
        """Get month folder name (e.g., '12-December')."""
        return f"{date_obj.month:02d}-{date_obj.strftime('%B')}"
    
    def search_receipts(self, after_date='2024/04/06', merchant=None):
        """Search Gmail for receipt/invoice emails."""
        try:
            # Build search query
            query_parts = []
            
            # Date filter
            query_parts.append(f'after:{after_date}')
            
            # Must have attachment
            query_parts.append('has:attachment')
            
            # Search for receipt/invoice keywords or specific merchant
            if merchant:
                query_parts.append(f'from:{merchant}')
            else:
                # Search for receipt/invoice keywords
                query_parts.append('(receipt OR invoice OR "order confirmation" OR "purchase confirmation")')
            
            # Exclude runsheets, payslips, and non-business documents
            query_parts.append('-subject:runsheet')
            query_parts.append('-subject:payslip')
            query_parts.append('-subject:"payroll for"')
            query_parts.append('-subject:mortgage')
            query_parts.append('-subject:solicitor')
            query_parts.append('-subject:lease')
            query_parts.append('-subject:"credit report"')
            query_parts.append('-subject:conveyancing')
            query_parts.append('-subject:warranty')
            query_parts.append('-subject:reservation')
            query_parts.append('-from:tvsscs.com')
            query_parts.append('-from:sapphireaccounting.co.uk')
            query_parts.append('-from:sapphireorg.co.uk')
            query_parts.append('-from:steelessolicitors.com')
            query_parts.append('-from:lqgroup.org.uk')
            query_parts.append('-from:metrofinance.co.uk')
            query_parts.append('-from:closebrothers.com')
            query_parts.append('-from:docusign.net')
            
            query = ' '.join(query_parts)
            
            print(f"🔍 Searching: {query}")
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print(f"   No emails found")
                return []
            
            print(f"   Found {len(messages)} emails")
            return messages
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def download_attachments(self, message_id):
        """Download all PDF/image attachments from an email."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Get email metadata
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
            
            # Parse date
            try:
                # Gmail date format: "Thu, 5 Dec 2024 10:30:00 +0000"
                date_obj = datetime.strptime(date_str.split(' (')[0], '%a, %d %b %Y %H:%M:%S %z')
                date_obj = date_obj.replace(tzinfo=None)  # Remove timezone
            except:
                date_obj = datetime.now()
            
            # Get merchant from email
            merchant = from_email.split('@')[1].split('>')[0] if '@' in from_email else 'unknown'
            merchant = merchant.replace('.', '_').replace('-', '_')
            
            downloaded = []
            
            # Check for attachments
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part.get('filename'):
                        filename = part['filename']
                        
                        # Only download PDFs and images
                        ext = filename.lower().split('.')[-1]
                        if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'gif']:
                            continue
                        
                        # Skip invoice PDFs, only keep receipts (for Stripe/Windsurf)
                        if 'invoice' in filename.lower() and 'receipt' not in filename.lower():
                            continue
                        
                        # Get attachment data
                        if 'attachmentId' in part['body']:
                            attachment = self.service.users().messages().attachments().get(
                                userId='me',
                                messageId=message_id,
                                id=part['body']['attachmentId']
                            ).execute()
                            
                            data = attachment['data']
                            file_data = base64.urlsafe_b64decode(data)
                            
                            # Organize into tax year/month folders
                            tax_year = self.get_tax_year_folder(date_obj)
                            month_folder = self.get_month_folder(date_obj)
                            
                            save_dir = self.download_dir / tax_year / month_folder
                            save_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Generate filename: DD-MM-YYYY_merchant_original.ext
                            safe_filename = f"{date_obj.strftime('%d-%m-%Y')}_{merchant}_{filename}"
                            save_path = save_dir / safe_filename
                            
                            # Save file
                            with open(save_path, 'wb') as f:
                                f.write(file_data)
                            
                            downloaded.append({
                                'path': str(save_path),
                                'filename': safe_filename,
                                'date': date_obj.strftime('%d/%m/%Y'),
                                'merchant': merchant,
                                'subject': subject
                            })
                            
                            print(f"   ✅ {safe_filename}")
            
            return downloaded
            
        except Exception as e:
            print(f"   ❌ Error downloading: {e}")
            return []
    
    def download_all_receipts(self, after_date='2024/04/06', merchant=None):
        """Download all receipts from Gmail."""
        print("\n📧 Gmail Receipt Downloader")
        print("=" * 50)
        
        if not self.authenticate():
            return []
        
        print("✅ Authenticated with Gmail")
        
        # Search for receipts
        messages = self.search_receipts(after_date, merchant)
        
        if not messages:
            print("\n❌ No receipts found")
            return []
        
        print(f"\n📥 Downloading attachments from {len(messages)} emails...")
        
        all_downloaded = []
        for i, message in enumerate(messages, 1):
            print(f"\n[{i}/{len(messages)}] Processing email...")
            downloaded = self.download_attachments(message['id'])
            all_downloaded.extend(downloaded)
        
        print("\n" + "=" * 50)
        print(f"✅ Downloaded {len(all_downloaded)} receipts")
        print(f"📁 Saved to: {self.download_dir}")
        
        return all_downloaded


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download receipts from Gmail')
    parser.add_argument('--date', default='2024/04/06', help='Download receipts after this date (YYYY/MM/DD)')
    parser.add_argument('--merchant', help='Filter by specific merchant email domain')
    parser.add_argument('--dir', default='data/receipts', help='Download directory')
    
    args = parser.parse_args()
    
    downloader = GmailReceiptDownloader(download_dir=args.dir)
    receipts = downloader.download_all_receipts(
        after_date=args.date,
        merchant=args.merchant
    )
    
    if receipts:
        print("\n📋 Downloaded receipts:")
        for receipt in receipts:
            print(f"   • {receipt['date']} - {receipt['merchant']} - {receipt['filename']}")


if __name__ == '__main__':
    main()
