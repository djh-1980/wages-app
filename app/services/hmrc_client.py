"""
HMRC API Client for Making Tax Digital (MTD) Self-Employment Income & Expenses API.
Handles all API calls with fraud prevention headers and error handling.
"""

import platform
import socket
from datetime import datetime

import requests

from .hmrc_auth import HMRCAuthService
from ..config import Config


class HMRCClient:
    """Client for HMRC MTD Self-Employment API."""
    
    def __init__(self):
        self.config = Config()
        self.auth_service = HMRCAuthService()
        self.base_url = self.config.HMRC_API_BASE_URL
        self.environment = self.config.HMRC_ENVIRONMENT
    
    def _get_fraud_prevention_headers(self):
        """
        Generate fraud prevention headers required by HMRC.
        These headers are mandatory for all API calls.
        
        Returns:
            dict: Fraud prevention headers
        """
        headers = {
            'Gov-Client-Connection-Method': 'WEB_APP_VIA_SERVER',
            'Gov-Client-Public-IP': self._get_public_ip(),
            'Gov-Client-Timezone': self._get_timezone(),
            'Gov-Vendor-Version': f"TVS-Wages={self.config.VERSION}",
            'Gov-Client-User-Agent': self._get_user_agent(),
            'Gov-Client-Device-ID': self._get_device_id(),
            'Gov-Client-Local-IPs': self._get_local_ips(),
            'Gov-Client-Screens': 'width=1920&height=1080&scaling-factor=1&colour-depth=24',
            'Gov-Client-Window-Size': 'width=1920&height=1080',
        }
        return headers
    
    def _get_public_ip(self):
        """Get public IP address."""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json()['ip']
        except:
            return '127.0.0.1'
    
    def _get_timezone(self):
        """Get timezone in UTC offset format."""
        from datetime import timezone
        offset = datetime.now(timezone.utc).astimezone().strftime('%z')
        return f"UTC{offset[:3]}:{offset[3:]}"
    
    def _get_user_agent(self):
        """Get user agent string."""
        return f"os-family={platform.system()}&os-version={platform.release()}&device-manufacturer=Unknown&device-model=Server"
    
    def _get_device_id(self):
        """Get device ID (MAC address hash)."""
        import hashlib
        import uuid
        mac = uuid.getnode()
        return hashlib.sha256(str(mac).encode()).hexdigest()
    
    def _get_local_ips(self):
        """Get local IP addresses."""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except:
            return '127.0.0.1'
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """
        Make authenticated request to HMRC API with fraud prevention headers.
        
        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            dict: Response data or error
        """
        access_token = self.auth_service.get_valid_access_token()
        
        if not access_token:
            return {
                'success': False,
                'error': 'Not authenticated. Please connect to HMRC first.'
            }
        
        # Use different API versions for different endpoints
        api_version = '5.0'  # Default for Self Employment Business API
        if '/individuals/income-received/' in endpoint:
            api_version = '3.0'  # Business Income Source Summary API
        elif '/individuals/business/details/' in endpoint:
            api_version = '3.0'  # Business Details API
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': f'application/vnd.hmrc.{api_version}+json',
            'Content-Type': 'application/json',
            **self._get_fraud_prevention_headers()
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}
            
            # Handle different response codes
            if response.status_code == 200 or response.status_code == 201:
                return {
                    'success': True,
                    'data': response.json() if response.content else {},
                    'status_code': response.status_code
                }
            elif response.status_code == 204:
                return {
                    'success': True,
                    'data': {},
                    'status_code': response.status_code
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    'success': False,
                    'error': error_data.get('message', f'HTTP {response.status_code}'),
                    'status_code': response.status_code,
                    'details': error_data
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_connection(self):
        """
        Test connection to HMRC API.
        
        Returns:
            dict: Connection test result
        """
        # Test with HMRC hello world endpoint
        result = self._make_request('GET', '/hello/world')
        
        if result.get('success'):
            return {
                'success': True,
                'message': 'Successfully connected to HMRC API',
                'environment': self.environment
            }
        else:
            return {
                'success': False,
                'message': f"Connection failed: {result.get('error', 'Unknown error')}",
                'environment': self.environment,
                'details': result.get('details', {})
            }
    
    def get_business_list(self, nino):
        """
        Get list of self-employment businesses for a NINO.
        Uses Business Income Source Summary API v3.0.
        
        Args:
            nino: National Insurance Number
            
        Returns:
            dict: List of businesses with their IDs
        """
        # Business Income Source Summary API v3.0 endpoint
        # This returns all business income sources including self-employment
        endpoint = f"/individuals/income-received/self-employment/{nino}"
        return self._make_request('GET', endpoint)
    
    def get_obligations(self, nino, from_date=None, to_date=None, status=None):
        """
        Get obligations for a business.
        
        Args:
            nino: National Insurance Number
            from_date: Optional from date (YYYY-MM-DD)
            to_date: Optional to date (YYYY-MM-DD)
            status: Optional status filter (O=Open, F=Fulfilled)
            
        Returns:
            dict: Obligations data
        """
        params = {}
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        if status:
            params['status'] = status
        
        endpoint = f"/individuals/business/self-employment/{nino}/obligations"
        return self._make_request('GET', endpoint, params=params)
    
    def get_period_summary(self, nino, business_id, period_id):
        """
        Get summary for a specific period.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            period_id: Period ID
            
        Returns:
            dict: Period summary data
        """
        endpoint = f"/individuals/business/self-employment/{nino}/{business_id}/period/{period_id}"
        return self._make_request('GET', endpoint)
    
    def create_test_business(self, nino):
        """
        Create a test self-employment business for sandbox testing.
        Uses Self Assessment Test Support API.
        
        Args:
            nino: National Insurance Number
            
        Returns:
            dict: Business creation response with business ID
        """
        # Test Support API doesn't require authentication for sandbox
        url = f"{self.base_url}/test-support/self-assessment/ni/{nino}/self-employments"
        
        test_business_data = {
            "tradingName": "Test Self Employment",
            "businessDescription": "Test Business",
            "businessAddressLineOne": "Test Address",
            "businessAddressPostcode": "TE5 7ST",
            "businessStartDate": "2020-01-01",
            "accountingType": "CASH",
            "commencementDate": "2020-01-01"
        }
        
        try:
            response = requests.post(url, json=test_business_data, timeout=30)
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'data': response.json() if response.content else {},
                    'status_code': response.status_code
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    'success': False,
                    'error': error_data.get('message', f'HTTP {response.status_code}'),
                    'status_code': response.status_code,
                    'details': error_data
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_period(self, nino, business_id, period_data):
        """
        Create a new period with income and expenses.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            period_data: Period data including from/to dates and financials
            
        Returns:
            dict: Creation response
        """
        # Self Employment Business API v5.0 endpoint format
        endpoint = f"/individuals/business/self-employment/{business_id}/period"
        return self._make_request('POST', endpoint, data=period_data)
    
    def update_period(self, nino, business_id, period_id, period_data):
        """
        Update an existing period.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            period_id: Period ID to update
            period_data: Updated period data
            
        Returns:
            dict: Update response
        """
        endpoint = f"/individuals/business/self-employment/{nino}/{business_id}/period/{period_id}"
        return self._make_request('PUT', endpoint, data=period_data)
    
    def get_annual_summary(self, nino, business_id, tax_year):
        """
        Get annual summary for a tax year.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            tax_year: Tax year (e.g., '2024-25')
            
        Returns:
            dict: Annual summary data
        """
        endpoint = f"/individuals/business/self-employment/{nino}/{business_id}/annual/{tax_year}"
        return self._make_request('GET', endpoint)
    
    def update_annual_summary(self, nino, business_id, tax_year, annual_data):
        """
        Update annual summary (allowances and adjustments).
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            tax_year: Tax year (e.g., '2024-25')
            annual_data: Annual summary data
            
        Returns:
            dict: Update response
        """
        endpoint = f"/individuals/business/self-employment/{nino}/{business_id}/annual/{tax_year}"
        return self._make_request('PUT', endpoint, data=annual_data)
