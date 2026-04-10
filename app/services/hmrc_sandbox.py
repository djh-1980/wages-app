"""
HMRC Sandbox Test User Creation Service.
Creates stateful test users and businesses for MTD ITSA sandbox testing.

WARNING: SANDBOX TESTING ONLY - Remove before production deployment.
"""

import os
import logging
import requests
from datetime import datetime, timedelta

from ..database import get_db_connection

logger = logging.getLogger(__name__)


class HMRCSandboxService:
    """Service for creating and managing HMRC sandbox test users."""
    
    def __init__(self):
        self.client_id = os.getenv('HMRC_CLIENT_ID')
        self.client_secret = os.getenv('HMRC_CLIENT_SECRET')
        self.base_url = 'https://test-api.service.hmrc.gov.uk'
        self.token_url = f'{self.base_url}/oauth/token'
        self.create_user_url = f'{self.base_url}/create-test-user/individuals'
        
        if not self.client_id or not self.client_secret:
            logger.warning('HMRC credentials not configured for sandbox testing')
    
    def _get_application_token(self):
        """
        Get application-level OAuth token using client_credentials grant.
        This is different from user-facing OAuth - it's for API-to-API calls.
        
        Note: HMRC sandbox does not accept scope parameter for client_credentials grant.
        
        Returns:
            str: Access token or None if failed
        """
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            logger.info('Requesting application token for test user creation')
            response = requests.post(self.token_url, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                logger.info('Successfully obtained application token')
                return access_token
            else:
                logger.error(f'Failed to get application token: {response.status_code} - {response.text}')
                return None
        
        except Exception as e:
            logger.error(f'Error getting application token: {e}')
            return None
    
    def create_test_individual(self):
        """
        Create a test individual user with MTD ITSA services.
        Uses HMRC Create Test User API.
        
        Returns:
            dict: Test user details or error
        """
        try:
            # Get application token
            token = self._get_application_token()
            if not token:
                return {
                    'success': False,
                    'error': 'Failed to obtain application token'
                }
            
            # Create test user
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            body = {
                'serviceNames': [
                    'mtd-income-tax',
                    'self-assessment',
                    'national-insurance'
                ]
            }
            
            logger.info('Creating test individual user')
            response = requests.post(
                self.create_user_url,
                json=body,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                logger.info(f'Successfully created test user: {user_data.get("userId")}')
                
                return {
                    'success': True,
                    'data': {
                        'userId': user_data.get('userId'),
                        'password': user_data.get('password'),
                        'nino': user_data.get('nino'),
                        'saUtr': user_data.get('saUtr'),
                        'userFullName': user_data.get('userFullName', 'Test User'),
                        'emailAddress': user_data.get('emailAddress', '')
                    }
                }
            else:
                error_msg = f'Failed to create test user: {response.status_code} - {response.text}'
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f'Error creating test individual: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_test_business(self, nino, access_token):
        """
        Retrieve auto-provisioned test business for a test user.
        
        When a test user is created with 'mtd-income-tax' service, HMRC automatically
        provisions a test business. This method retrieves that business using the
        Business Details API.
        
        Args:
            nino: National Insurance Number of test user
            access_token: OAuth access token (user-level, not application-level)
            
        Returns:
            dict: Business details or error
        """
        try:
            endpoint = f'{self.base_url}/individuals/business/details/{nino}/list'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.hmrc.2.0+json'
            }
            
            logger.info(f'Fetching auto-provisioned business for NINO: {nino}')
            logger.info(f'Calling HMRC endpoint: {endpoint}')
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                businesses = data.get('listOfBusinesses', [])
                
                if not businesses:
                    error_msg = 'No businesses found for test user'
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg
                    }
                
                # Get the first business (self-employment)
                business = businesses[0]
                business_id = business.get('businessId')
                logger.info(f'Successfully retrieved test business: {business_id}')
                
                return {
                    'success': True,
                    'data': {
                        'businessId': business_id,
                        'tradingName': business.get('tradingName', 'N/A'),
                        'accountingType': business.get('accountingType', 'N/A'),
                        'commencementDate': business.get('commencementDate', 'N/A'),
                        'typeOfBusiness': business.get('typeOfBusiness', 'self-employment')
                    }
                }
            else:
                error_msg = f'Failed to retrieve business: {response.status_code} - {response.text}'
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f'Error retrieving test business: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def store_test_user(self, user_data, business_data=None):
        """
        Store test user and business details in database.
        
        If business_data is provided and a record for this NINO already exists,
        updates the existing record with business details instead of inserting.
        
        Args:
            user_data: Test user details from create_test_individual
            business_data: Optional business details from create_test_business
            
        Returns:
            dict: Success status
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                nino = user_data.get('nino')
                
                # Check if user with this NINO already exists
                cursor.execute("""
                    SELECT id FROM sandbox_test_users WHERE nino = ?
                """, (nino,))
                existing = cursor.fetchone()
                
                if existing and business_data:
                    # Update existing record with business details
                    cursor.execute("""
                        UPDATE sandbox_test_users
                        SET business_id = ?,
                            trading_name = ?,
                            accounting_type = ?,
                            commencement_date = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE nino = ?
                    """, (
                        business_data.get('businessId'),
                        business_data.get('tradingName'),
                        business_data.get('accountingType'),
                        business_data.get('commencementDate'),
                        nino
                    ))
                    logger.info(f'Updated test user with business details: {nino}')
                elif not existing:
                    # Deactivate any existing test users
                    cursor.execute("""
                        UPDATE sandbox_test_users
                        SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE is_active = 1
                    """)
                    
                    # Insert new test user
                    cursor.execute("""
                        INSERT INTO sandbox_test_users
                        (user_id, password, nino, sa_utr, business_id, trading_name, 
                         accounting_type, commencement_date, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        user_data.get('userId'),
                        user_data.get('password'),
                        nino,
                        user_data.get('saUtr'),
                        business_data.get('businessId') if business_data else None,
                        business_data.get('tradingName') if business_data else None,
                        business_data.get('accountingType') if business_data else None,
                        business_data.get('commencementDate') if business_data else None
                    ))
                    logger.info(f'Stored new test user in database: {nino}')
                
                conn.commit()
                
                # Update .env file with test credentials
                self._update_env_file(
                    nino,
                    business_data.get('businessId') if business_data else None
                )
                
                return {
                    'success': True,
                    'message': 'Test user stored successfully'
                }
        
        except Exception as e:
            logger.error(f'Error storing test user: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_env_file(self, nino, business_id):
        """
        Update .env file with test credentials.
        
        Args:
            nino: Test user NINO
            business_id: Test business ID
        """
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            
            if not os.path.exists(env_path):
                logger.warning('.env file not found, skipping update')
                return
            
            # Read existing .env
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Update or add test credentials
            nino_found = False
            business_found = False
            
            for i, line in enumerate(lines):
                if line.startswith('HMRC_TEST_NINO='):
                    lines[i] = f'HMRC_TEST_NINO={nino}\n'
                    nino_found = True
                elif line.startswith('HMRC_TEST_BUSINESS_ID='):
                    lines[i] = f'HMRC_TEST_BUSINESS_ID={business_id or ""}\n'
                    business_found = True
            
            # Add if not found
            if not nino_found:
                lines.append(f'\nHMRC_TEST_NINO={nino}\n')
            if not business_found:
                lines.append(f'HMRC_TEST_BUSINESS_ID={business_id or ""}\n')
            
            # Write back
            with open(env_path, 'w') as f:
                f.writelines(lines)
            
            logger.info('Updated .env file with test credentials')
        
        except Exception as e:
            logger.error(f'Error updating .env file: {e}')
    
    def get_active_test_user(self):
        """
        Get the currently active test user.
        
        Returns:
            dict: Test user details or None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, password, nino, sa_utr, business_id, 
                           trading_name, accounting_type, commencement_date,
                           created_at
                    FROM sandbox_test_users
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        
        except Exception as e:
            logger.error(f'Error getting active test user: {e}')
            return None
    
    def get_all_test_users(self):
        """
        Get all test users (for history/debugging).
        
        Returns:
            list: List of test user records
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, nino, sa_utr, business_id, 
                           trading_name, is_active, created_at
                    FROM sandbox_test_users
                    ORDER BY created_at DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f'Error getting test users: {e}')
            return []
    
    def delete_test_user(self, user_id):
        """
        Delete a test user record.
        
        Args:
            user_id: ID of test user to delete
            
        Returns:
            dict: Success status
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM sandbox_test_users
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
                
                return {
                    'success': True,
                    'message': 'Test user deleted successfully'
                }
        
        except Exception as e:
            logger.error(f'Error deleting test user: {e}')
            return {
                'success': False,
                'error': str(e)
            }
