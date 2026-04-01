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
    
    def _make_request(self, method, endpoint, data=None, params=None, test_scenario=None):
        """
        Make authenticated request to HMRC API with fraud prevention headers.
        
        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            test_scenario: Optional Gov-Test-Scenario header value for sandbox testing
            
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
        
        if test_scenario:
            headers['Gov-Test-Scenario'] = test_scenario
        
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
                
                # Parse 422 validation errors with field-level details
                if response.status_code == 422 and 'errors' in error_data:
                    validation_errors = []
                    for err in error_data.get('errors', []):
                        field_path = err.get('path', 'unknown')
                        message = err.get('message', 'Validation error')
                        code = err.get('code', '')
                        validation_errors.append({
                            'field': field_path,
                            'message': message,
                            'code': code
                        })
                    
                    return {
                        'success': False,
                        'error': error_data.get('message', 'Validation failed'),
                        'status_code': response.status_code,
                        'validation_errors': validation_errors,
                        'details': error_data
                    }
                
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
    
    def get_business_details(self, nino):
        """
        Get list of businesses for a NINO using Business Details API.
        This is the recommended endpoint for MTD ITSA.
        
        Args:
            nino: National Insurance Number
            
        Returns:
            dict: List of businesses with their IDs
        """
        endpoint = f"/individuals/business/details/{nino}/list"
        return self._make_request('GET', endpoint)
    
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
    
    def get_obligations(self, nino, from_date=None, to_date=None, status=None, test_scenario=None):
        """
        Get obligations for a business.
        
        Args:
            nino: National Insurance Number
            from_date: Optional from date (YYYY-MM-DD)
            to_date: Optional to date (YYYY-MM-DD)
            status: Optional status filter (O=Open, F=Fulfilled)
            test_scenario: Optional Gov-Test-Scenario header for sandbox testing
            
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
        return self._make_request('GET', endpoint, params=params, test_scenario=test_scenario)
    
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
        Requires OAuth Bearer token from authenticated session.
        
        Args:
            nino: National Insurance Number
            
        Returns:
            dict: Business creation response with business ID
        """
        # Correct payload format as per HMRC API documentation
        test_business_data = {
            "annualAccountingRegime": "STANDARD",
            "tradingName": "Test Business",
            "businessAddressLineOne": "1 Test Street",
            "businessAddressLineTwo": "Test Town",
            "businessPostcode": "TE1 1ST"
        }
        
        # Use _make_request for consistency - it handles OAuth headers and fraud prevention
        endpoint = f"/test-support/self-assessment/ni/{nino}/self-employments"
        return self._make_request('POST', endpoint, data=test_business_data)
    
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
    
    def get_tax_calculation(self, nino, tax_year):
        """
        Get the latest tax calculation for a tax year.
        This retrieves the calculation after crystallisation has been triggered.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year in YYYY/YYYY format (e.g., '2024/2025')
            
        Returns:
            dict: Tax calculation data including calculationId and tax liability
        """
        formatted_tax_year = tax_year.replace('/', '-')
        endpoint = f"/individuals/calculations/{nino}/self-assessment"
        params = {'taxYear': formatted_tax_year}
        return self._make_request('GET', endpoint, params=params)
    
    def trigger_crystallisation(self, nino, tax_year):
        """
        Trigger crystallisation (intent to finalise) for a tax year.
        This requests HMRC to calculate the final tax liability.
        Must be called after all 4 quarterly updates are submitted.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year in YYYY/YYYY format (e.g., '2024/2025')
            
        Returns:
            dict: Response with calculationId
        """
        formatted_tax_year = tax_year.replace('/', '-')
        endpoint = f"/individuals/calculations/crystallisation/{nino}/{formatted_tax_year}"
        data = {'taxYear': formatted_tax_year}
        return self._make_request('POST', endpoint, data=data)
    
    def submit_final_declaration(self, nino, tax_year, calculation_id):
        """
        Submit the final declaration for a tax year.
        This is the point of no return - confirms all information is complete and correct.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year in YYYY/YYYY format (e.g., '2024/2025')
            calculation_id: The calculation ID from trigger_crystallisation
            
        Returns:
            dict: Response with receipt/confirmation
        """
        formatted_tax_year = tax_year.replace('/', '-')
        endpoint = f"/individuals/declarations/{nino}/{formatted_tax_year}"
        data = {
            'calculationId': calculation_id,
            'finalised': True
        }
        return self._make_request('POST', endpoint, data=data)
    
    def get_mock_obligations(self):
        """
        Return realistic mock obligations data for sandbox testing.
        Used as fallback when sandbox test data is not available.
        Matches HMRC API response format with nested obligationDetails.
        
        Returns:
            dict: Mock obligations data with 4 quarterly periods
        """
        return {
            'success': True,
            'data': {
                'obligations': [
                    {
                        'typeOfBusiness': 'self-employment',
                        'businessId': 'XAIS12345678901',
                        'obligationDetails': [
                            {
                                'periodKey': 'Q1',
                                'inboundCorrespondenceFromDate': '2024-04-06',
                                'inboundCorrespondenceToDate': '2024-07-05',
                                'inboundCorrespondenceDueDate': '2024-08-05',
                                'status': 'Open'
                            },
                            {
                                'periodKey': 'Q2',
                                'inboundCorrespondenceFromDate': '2024-07-06',
                                'inboundCorrespondenceToDate': '2024-10-05',
                                'inboundCorrespondenceDueDate': '2024-11-05',
                                'status': 'Open'
                            },
                            {
                                'periodKey': 'Q3',
                                'inboundCorrespondenceFromDate': '2024-10-06',
                                'inboundCorrespondenceToDate': '2025-01-05',
                                'inboundCorrespondenceDueDate': '2025-02-05',
                                'status': 'Open'
                            },
                            {
                                'periodKey': 'Q4',
                                'inboundCorrespondenceFromDate': '2025-01-06',
                                'inboundCorrespondenceToDate': '2025-04-05',
                                'inboundCorrespondenceDueDate': '2025-05-05',
                                'status': 'Open'
                            }
                        ]
                    }
                ]
            }
        }
