"""
Gmail Service Account Authentication
Replaces OAuth token authentication with service account for automated access.
"""

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

class GmailServiceAccount:
    def __init__(self, service_account_file=None, user_email=None):
        """
        Initialize Gmail service with service account.
        
        Args:
            service_account_file: Path to service account JSON file
            user_email: Email address to impersonate (for domain-wide delegation)
        """
        self.service_account_file = service_account_file or 'service-account.json'
        self.user_email = user_email
        self.service = None
        
    def authenticate(self):
        """Authenticate using service account."""
        try:
            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            
            # If user email provided, delegate to that user
            if self.user_email:
                credentials = credentials.with_subject(self.user_email)
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=credentials)
            
            # Test the connection
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"✅ Authenticated as: {profile.get('emailAddress')}")
            
            return self.service
            
        except Exception as e:
            print(f"❌ Service account authentication failed: {e}")
            return None
    
    def get_service(self):
        """Get authenticated Gmail service."""
        if not self.service:
            return self.authenticate()
        return self.service

# Example usage
if __name__ == "__main__":
    # Test service account authentication
    gmail_sa = GmailServiceAccount()
    service = gmail_sa.authenticate()
    
    if service:
        print("🎉 Service account authentication successful!")
    else:
        print("❌ Service account authentication failed!")
