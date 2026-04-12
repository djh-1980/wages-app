"""
HMRC OAuth 2.0 Authentication Service for Making Tax Digital (MTD).
Handles authorization flow, token management, and refresh logic.
"""

import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests

from ..database import get_db_connection, execute_query
from ..config import Config
from ..utils.encryption import get_encryption


class HMRCAuthService:
    """Handle HMRC OAuth 2.0 authentication and token management."""
    
    def __init__(self):
        self.config = Config()
        self.client_id = self.config.HMRC_CLIENT_ID
        self.client_secret = self.config.HMRC_CLIENT_SECRET
        self.redirect_uri = self.config.HMRC_REDIRECT_URI
        self.environment = self.config.HMRC_ENVIRONMENT
    
    def get_authorization_url(self, state=None):
        """
        Generate HMRC authorization URL for OAuth flow.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            tuple: (authorization_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': 'read:self-assessment write:self-assessment',
            'redirect_uri': self.redirect_uri,
            'state': state
        }
        
        auth_url = f"{self.config.HMRC_AUTH_URL}?{urlencode(params)}"
        return auth_url, state
    
    def exchange_code_for_token(self, authorization_code):
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Code received from HMRC callback
            
        Returns:
            dict: Token response with access_token, refresh_token, expires_in
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri
        }
        
        try:
            response = requests.post(
                self.config.HMRC_TOKEN_URL,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            # Store tokens in database
            self._store_tokens(token_data)
            
            return {
                'success': True,
                'data': token_data
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def refresh_access_token(self, refresh_token=None):
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Optional refresh token. If None, uses stored token.
            
        Returns:
            dict: New token response
        """
        if refresh_token is None:
            # Get stored refresh token
            credentials = self.get_stored_credentials()
            if not credentials:
                return {
                    'success': False,
                    'error': 'No stored credentials found'
                }
            refresh_token = credentials['refresh_token']
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        try:
            response = requests.post(
                self.config.HMRC_TOKEN_URL,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update stored tokens
            self._store_tokens(token_data)
            
            return {
                'success': True,
                'data': token_data
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _store_tokens(self, token_data, nino=None):
        """
        Store or update tokens in database with encryption.

        Args:
            token_data: Token response from HMRC
            nino: Optional NINO to associate with these credentials
        """
        expires_in = token_data.get('expires_in', 14400)  # Default 4 hours
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Encrypt tokens before storage
        encryption = get_encryption()
        encrypted_access_token = encryption.encrypt(token_data.get('access_token'))
        encrypted_refresh_token = encryption.encrypt(token_data.get('refresh_token'))

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Deactivate all existing credentials
            cursor.execute(
                "UPDATE hmrc_credentials SET is_active = 0"
            )

            # Insert new credentials (encrypted)
            cursor.execute("""
                INSERT INTO hmrc_credentials
                (access_token, refresh_token, expires_at, scope, environment, is_active, nino)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (
                encrypted_access_token,
                encrypted_refresh_token,
                expires_at.isoformat(),
                token_data.get('scope', 'read:self-assessment write:self-assessment'),
                self.environment,
                nino
            ))

            conn.commit()
    
    def update_credential_nino(self, nino):
        """
        Set the NINO on the active credential.
        Called after we discover which test user the token belongs to.

        Args:
            nino: National Insurance Number to associate
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE hmrc_credentials SET nino = ? WHERE is_active = 1 AND environment = ?",
                (nino, self.environment)
            )
            conn.commit()

    def get_stored_credentials(self):
        """
        Get active stored credentials from database and decrypt tokens.

        Returns:
            dict: Decrypted credentials or None if not found
        """
        query = """
            SELECT access_token, refresh_token, expires_at, scope, environment, nino
            FROM hmrc_credentials
            WHERE is_active = 1 AND environment = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        row = execute_query(query, (self.environment,), fetch_one=True)
        
        if row:
            credentials = dict(row)
            
            # Decrypt tokens before returning
            encryption = get_encryption()
            credentials['access_token'] = encryption.decrypt(credentials['access_token'])
            credentials['refresh_token'] = encryption.decrypt(credentials['refresh_token'])
            
            return credentials
        return None
    
    def get_valid_access_token(self):
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            str: Valid access token or None
        """
        credentials = self.get_stored_credentials()
        
        if not credentials:
            return None
        
        # Check if token is expired or about to expire (within 5 minutes)
        expires_at = datetime.fromisoformat(credentials['expires_at'])
        if datetime.now() >= expires_at - timedelta(minutes=5):
            # Token expired or about to expire, refresh it
            refresh_result = self.refresh_access_token(credentials['refresh_token'])
            if refresh_result['success']:
                return refresh_result['data']['access_token']
            return None
        
        return credentials['access_token']
    
    def is_authenticated(self):
        """
        Check if user is authenticated with HMRC.
        
        Returns:
            bool: True if authenticated with valid credentials
        """
        credentials = self.get_stored_credentials()
        if not credentials:
            return False
        
        # Check if token is still valid
        expires_at = datetime.fromisoformat(credentials['expires_at'])
        return datetime.now() < expires_at
    
    def revoke_credentials(self):
        """
        Revoke stored credentials (logout).
        
        Returns:
            bool: Success status
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE hmrc_credentials SET is_active = 0 WHERE environment = ?",
                    (self.environment,)
                )
                conn.commit()
            return True
        except Exception:
            return False
    
    def get_connection_status(self):
        """
        Get detailed connection status.
        
        Returns:
            dict: Status information
        """
        credentials = self.get_stored_credentials()
        
        if not credentials:
            return {
                'connected': False,
                'environment': self.environment,
                'message': 'Not connected to HMRC'
            }
        
        expires_at = datetime.fromisoformat(credentials['expires_at'])
        is_valid = datetime.now() < expires_at
        
        return {
            'connected': is_valid,
            'environment': self.environment,
            'expires_at': credentials['expires_at'],
            'scope': credentials['scope'],
            'message': 'Connected to HMRC' if is_valid else 'Token expired'
        }
