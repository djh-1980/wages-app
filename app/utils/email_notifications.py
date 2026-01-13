"""
Email notification service for sending extra job confirmations via Gmail API.
"""
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class EmailNotificationService:
    """Service for sending email notifications via Gmail API."""
    
    def __init__(self):
        self.service = None
        self.authenticated = False
        
    def authenticate(self):
        """Authenticate with Gmail API using existing credentials."""
        try:
            creds = None
            token_path = Path('token.json')
            
            if token_path.exists():
                creds = Credentials.from_authorized_user_file('token.json', 
                    ['https://www.googleapis.com/auth/gmail.send'])
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    return False
            
            self.service = build('gmail', 'v1', credentials=creds)
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"Gmail authentication error: {e}")
            return False
    
    def send_extra_job_confirmation(self, job_data, manager_email, user_email, user_name=None):
        """
        Send extra job rate confirmation email.
        
        Args:
            job_data: Dict with job_number, customer, location, agreed_rate, date
            manager_email: Manager's email address
            user_email: User's email address (for CC)
            user_name: User's name (optional)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.authenticated:
            if not self.authenticate():
                return False
        
        # Get user name from settings if not provided
        if not user_name:
            try:
                from ..database import get_db_connection
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'userName'")
                    row = cursor.fetchone()
                    user_name = row['setting_value'] if row else 'Driver'
            except:
                user_name = 'Driver'
        
        try:
            # Create message
            message = MIMEMultipart()
            message['From'] = 'me'
            message['To'] = manager_email
            message['Cc'] = user_email
            message['Subject'] = f"Extra Job Rate Confirmation - {user_name} - Job #{job_data['job_number']}"
            
            # Create HTML body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px;">
                        Extra Job Rate Confirmation - {user_name}
                    </h2>
                    
                    <p>This email confirms the agreed rate for the following extra job completed by <strong>{user_name}</strong>:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="background-color: #f5f5f5;">
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Job Number:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{job_data['job_number']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Customer:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{job_data['customer']}</td>
                        </tr>
                        <tr style="background-color: #f5f5f5;">
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Location:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{job_data['location']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Date:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{job_data['date']}</td>
                        </tr>
                        <tr style="background-color: #ffffcc;">
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Agreed Rate:</td>
                            <td style="padding: 10px; border: 1px solid #ddd; font-size: 18px; font-weight: bold; color: #0066cc;">
                                £{job_data['agreed_rate']:.2f}
                            </td>
                        </tr>
                    </table>
                    
                    <div style="background-color: #f0f8ff; padding: 15px; border-left: 4px solid #0066cc; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Important:</strong></p>
                        <p style="margin: 5px 0 0 0;">
                            This rate was verbally confirmed on {datetime.now().strftime('%d/%m/%Y at %H:%M')}.
                        </p>
                        <p style="margin: 5px 0 0 0;">
                            <strong>If this rate is incorrect, please respond within 24 hours.</strong>
                        </p>
                        <p style="margin: 5px 0 0 0;">
                            If no objection is received within 24 hours, this rate will be considered confirmed.
                        </p>
                    </div>
                    
                    <p style="color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        This is an automated confirmation email generated by the TVS Wages App.<br>
                        Sent: {datetime.now().strftime('%d/%m/%Y at %H:%M:%S')}
                    </p>
                </div>
            </body>
            </html>
            """
            
            message.attach(MIMEText(html_body, 'html'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = {'raw': raw_message}
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            message_id = result['id']
            print(f"Email sent successfully. Message ID: {message_id}")
            
            # Log to audit trail
            try:
                from ..database import get_db_connection
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO email_audit_log 
                        (job_number, customer, location, agreed_rate, job_date, 
                         sent_to, cc_to, user_name, email_subject, message_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'sent')
                    """, (
                        job_data['job_number'],
                        job_data['customer'],
                        job_data['location'],
                        job_data['agreed_rate'],
                        job_data['date'],
                        manager_email,
                        user_email,
                        user_name,
                        f"Extra Job Rate Confirmation - {user_name} - Job #{job_data['job_number']}",
                        message_id
                    ))
                    conn.commit()
                    print(f"Email logged to audit trail (ID: {cursor.lastrowid})")
            except Exception as log_error:
                print(f"Warning: Failed to log email to audit trail: {log_error}")
                # Don't fail the whole operation if logging fails
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False


# Global instance
email_service = EmailNotificationService()
