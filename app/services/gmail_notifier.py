"""
Gmail Email Notifier
Uses the same Gmail API authentication as the download service to send notifications.
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Gmail API scopes - need send permission
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]


class GmailNotifier:
    """Send email notifications using Gmail API."""
    
    def __init__(self):
        self.service = None
        
    def authenticate(self):
        """Authenticate with Gmail API (same as download service)."""
        creds = None
        token_path = Path('token.json')
        credentials_path = Path('credentials.json')
        
        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    # Try to re-authenticate
                    if credentials_path.exists():
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(credentials_path), SCOPES)
                        creds = flow.run_local_server(port=0)
                    else:
                        print("Error: credentials.json not found!")
                        return False
            else:
                if not credentials_path.exists():
                    print("Error: credentials.json not found!")
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for next run
            token_path.write_text(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def send_email(self, to_email, subject, html_body, text_body=None):
        """
        Send an email using Gmail API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content of email
            text_body: Plain text fallback (optional)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return False
            
            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = to_email
            message['Subject'] = subject
            
            # Add plain text version if provided
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                message.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_body, 'html')
            message.attach(part2)
            
            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            send_message = {'raw': raw_message}
            
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            print(f"✅ Email sent successfully! Message ID: {result['id']}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def send_sync_notification(self, sync_summary, recipient_email):
        """
        Send a sync notification email.
        
        Args:
            sync_summary: Dictionary with sync results
            recipient_email: Email address to send to
        
        Returns:
            True if sent successfully
        """
        from .sync_helpers import format_sync_email
        from datetime import datetime
        
        # Determine subject based on what was processed
        parts = []
        if sync_summary['runsheets_downloaded'] > 0:
            parts.append(f"{sync_summary['runsheets_downloaded']} Runsheet(s)")
        if sync_summary['payslips_downloaded'] > 0:
            parts.append(f"{sync_summary['payslips_downloaded']} Payslip(s)")
        
        if len(sync_summary['errors']) > 0:
            subject = "⚠️ Wages App Sync - Completed with Errors"
            if parts:
                subject += f" ({', '.join(parts)})"
        elif parts:
            subject = f"✅ Wages App Sync - {', '.join(parts)} Processed"
        else:
            subject = "ℹ️ Wages App Sync - No New Files"
        
        # Add timestamp to subject
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        subject = f"{subject} - {now}"
        
        # Generate HTML body
        html_body = format_sync_email(sync_summary)
        
        # Generate plain text fallback
        text_body = f"""
Wages App Auto-Sync Report
{now}

Summary:
- Runsheets Downloaded: {sync_summary['runsheets_downloaded']}
- Runsheets Imported: {sync_summary['runsheets_imported']} jobs
- Payslips Downloaded: {sync_summary['payslips_downloaded']}
- Payslips Imported: {sync_summary['payslips_imported']}
- Jobs Synced: {sync_summary['jobs_synced']}

"""
        
        if sync_summary['errors']:
            text_body += "Errors:\n"
            for error in sync_summary['errors']:
                text_body += f"- {error}\n"
        
        text_body += "\nCheck the website to verify all data is displaying correctly."
        
        # Send email
        return self.send_email(recipient_email, subject, html_body, text_body)


# Global instance
gmail_notifier = GmailNotifier()
