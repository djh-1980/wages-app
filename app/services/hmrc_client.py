"""
HMRC API Client for Making Tax Digital (MTD) Self-Employment Income & Expenses API.
Handles all API calls with fraud prevention headers and error handling.
"""

import json
import logging
from datetime import datetime

import requests

from .hmrc_auth import HMRCAuthService
from ..config import Config

logger = logging.getLogger('hmrc')


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

        Implementation lives in `hmrc_fraud_headers.build_fraud_prevention_headers()`
        which builds the full WEB_APP_VIA_SERVER header set from the current
        request + session-captured browser context.
        """
        from .hmrc_fraud_headers import build_fraud_prevention_headers
        return build_fraud_prevention_headers()
    
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
            api_version = '2.0'  # Business Details API v2.0
        elif '/obligations/' in endpoint or '/individuals/business/self-employment/' in endpoint and '/obligations' in endpoint:
            api_version = '3.0'  # Obligations API v3.0
        elif '/individuals/calculations/' in endpoint or '/individuals/declarations/' in endpoint:
            api_version = '8.0'  # Individual Calculations API v8.0
        elif '/individuals/business/property/' in endpoint:
            api_version = '6.0'  # Property Business API v6.0
        elif '/individuals/self-assessment/adjustable-summary/' in endpoint:
            api_version = '7.0'  # Business Source Adjustable Summary (BSAS) API v7.0
        elif '/individuals/losses/' in endpoint:
            api_version = '6.0'  # Individual Losses API v6.0
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': f'application/vnd.hmrc.{api_version}+json',
            'Content-Type': 'application/json',
            **self._get_fraud_prevention_headers()
        }
        
        # For sandbox environment, use STATEFUL test scenario by default
        # BUT exclude obligations endpoints which don't support Gov-Test-Scenario
        is_obligations_endpoint = '/obligations/' in endpoint
        
        if self.environment == 'sandbox' and not is_obligations_endpoint:
            headers['Gov-Test-Scenario'] = 'STATEFUL'
        
        # Allow override of test scenario if explicitly provided (unless it's obligations)
        if test_scenario and not is_obligations_endpoint:
            headers['Gov-Test-Scenario'] = test_scenario
        
        url = f"{self.base_url}{endpoint}"
        
        # Log API call (never log sensitive data like tokens or NINOs)
        safe_endpoint = endpoint.replace(r'/[A-Z]{2}\d{6}[A-D]', '/[NINO]')  # Mask NINOs
        logger.info(f"HMRC API call: {method} {safe_endpoint} (environment: {self.environment})")
        
        # Log request headers (mask Authorization token for security)
        safe_headers = dict(headers)
        if 'Authorization' in safe_headers:
            safe_headers['Authorization'] = 'Bearer [REDACTED]'
        logger.info(f'Request headers: {safe_headers}')
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                # Log the request payload for debugging
                if data:
                    logger.info(f'Period submission payload: {json.dumps(data, indent=2)}')
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'PUT':
                # Log the request payload for debugging
                if data:
                    logger.info(f'Annual submission payload: {json.dumps(data, indent=2)}')
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return {'success': False, 'error': f'Unsupported method: {method}'}
            
            # Log response status
            logger.info(f"HMRC API response: {method} {safe_endpoint} - {response.status_code}")
            
            # Handle different response codes
            if response.status_code == 200 or response.status_code == 201:
                logger.debug(f"HMRC API success: {method} {safe_endpoint}")
                return {
                    'success': True,
                    'data': response.json() if response.content else {},
                    'status_code': response.status_code
                }
            elif response.status_code == 204:
                logger.debug(f"HMRC API success (no content): {method} {safe_endpoint}")
                return {
                    'success': True,
                    'data': {},
                    'status_code': response.status_code
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                logger.warning(f"HMRC API error: {method} {safe_endpoint} - {response.status_code}: {error_msg}")
                
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
                    
                    logger.error(f"HMRC validation errors: {len(validation_errors)} field(s)")
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
            logger.error(f"HMRC API request exception: {method} {safe_endpoint} - {str(e)}")
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
        Get list of businesses for a NINO using Business Details API v2.0.
        This is the recommended endpoint for MTD ITSA.
        
        Args:
            nino: National Insurance Number
            
        Returns:
            dict: List of businesses with their IDs
        """
        endpoint = f"/individuals/business/details/{nino}/list"
        return self._make_request('GET', endpoint)
    
    def get_business_detail(self, nino, business_id):
        """
        Get single business details by ID using Business Details API v2.0.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            
        Returns:
            dict: Business details
        """
        endpoint = f"/individuals/business/details/{nino}/{business_id}"
        return self._make_request('GET', endpoint)
    
    def create_amend_quarterly_period_type(self, nino, business_id, period_type):
        """
        Create or amend quarterly period type for a business.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            period_type: 'standard' or 'calendar'
            
        Returns:
            dict: Response from HMRC
        """
        if period_type not in ['standard', 'calendar']:
            return {
                'success': False,
                'error': 'period_type must be "standard" or "calendar"'
            }
        
        endpoint = f"/individuals/business/details/{nino}/{business_id}/quarterly-period-type"
        data = {'quarterlyPeriodType': period_type}
        return self._make_request('PUT', endpoint, data=data)
    
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
        Get income & expenses obligations for a business using Obligations API v3.0.
        
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
    
    def get_final_declaration_obligations(self, nino, from_date=None, to_date=None, status=None):
        """
        Get final declaration (crystallisation) obligations using Obligations API v3.0.
        
        Args:
            nino: National Insurance Number
            from_date: Optional from date (YYYY-MM-DD)
            to_date: Optional to date (YYYY-MM-DD)
            status: Optional status filter (O=Open, F=Fulfilled)
            
        Returns:
            dict: Final declaration obligations
        """
        params = {}
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        if status:
            params['status'] = status
        
        endpoint = f"/obligations/details/{nino}/crystallisation"
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
    
    def list_periods(self, nino, business_id, tax_year):
        """
        List all periods for a business and tax year.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            tax_year: Tax year (e.g., '2024-25')
            
        Returns:
            dict: List of periods
        """
        endpoint = f"/individuals/business/self-employment/{nino}/{business_id}/period"
        params = {'taxYear': tax_year}
        return self._make_request('GET', endpoint, params=params)
    
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
    
    def create_period(self, nino, business_id, tax_year, period_data):
        """
        Submit period data to HMRC (LEGACY non-cumulative endpoint).

        DEPRECATED: HMRC Self-Employment Business API v5.0 has retired
        per-quarter submissions in favour of cumulative period summaries.
        New code must call :meth:`submit_cumulative_period` instead. This
        method is retained only for backwards compatibility with already
        submitted records.

        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            tax_year: Tax year (not used in URL, kept for compatibility)
            period_data: Period data including dates and financials

        Returns:
            dict: Submission response
        """
        # Self Employment Business API v5.0 period endpoint
        # Tax year is NOT in the URL path
        endpoint = f"/individuals/business/self-employment/{nino}/{business_id}/period"
        return self._make_request('POST', endpoint, data=period_data)

    def submit_cumulative_period(self, nino, business_id, tax_year, period_data):
        """
        POST a cumulative period summary to HMRC.

        Self-Employment Business (MTD) API v5.0 cumulative endpoint:
        ``POST /individuals/business/self-employment/{nino}/{businessId}/period/cumulative/{taxYear}``

        ``period_data`` must contain running totals from the start of the
        tax year (06 April) up to ``periodEndDate``. The payload shape is
        the same as the legacy POST /period:

            {
                'periodDates':    {'periodStartDate', 'periodEndDate'},
                'periodIncome':   {'turnover', 'other'},
                'periodExpenses': {<HMRC expense fields>},
            }

        Args:
            nino: National Insurance Number.
            business_id: Business ID from HMRC.
            tax_year: Tax year in YYYY-YY (e.g. '2025-26') or YYYY/YYYY
                form. The hyphen form is what HMRC expects in the URL;
                the slash form is normalised to it here.
            period_data: Cumulative payload (see above).

        Returns:
            dict: ``_make_request`` result envelope (success/error +
            status_code + data).
        """
        formatted_tax_year = tax_year.replace('/', '-') if tax_year else tax_year
        # If caller passed 'YYYY-YYYY' style ('2025-2026'), collapse the
        # second half down to two digits so the URL matches HMRC's
        # canonical 'YYYY-YY' form.
        if isinstance(formatted_tax_year, str) and formatted_tax_year.count('-') == 1:
            head, tail = formatted_tax_year.split('-')
            if len(tail) == 4:
                formatted_tax_year = f"{head}-{tail[-2:]}"

        endpoint = (
            f"/individuals/business/self-employment/{nino}/{business_id}"
            f"/period/cumulative/{formatted_tax_year}"
        )
        return self._make_request('POST', endpoint, data=period_data)

    def get_cumulative_period(self, nino, business_id, tax_year):
        """
        GET the latest cumulative period summary for a tax year.

        Self-Employment Business (MTD) API v5.0:
        ``GET /individuals/business/self-employment/{nino}/{businessId}/period/cumulative/{taxYear}``

        Args:
            nino: National Insurance Number.
            business_id: Business ID from HMRC.
            tax_year: Tax year in YYYY-YY or YYYY/YYYY form.

        Returns:
            dict: ``_make_request`` result envelope. ``data`` matches
            HMRC's cumulative period summary schema (periodDates,
            periodIncome, periodExpenses).
        """
        formatted_tax_year = tax_year.replace('/', '-') if tax_year else tax_year
        if isinstance(formatted_tax_year, str) and formatted_tax_year.count('-') == 1:
            head, tail = formatted_tax_year.split('-')
            if len(tail) == 4:
                formatted_tax_year = f"{head}-{tail[-2:]}"

        endpoint = (
            f"/individuals/business/self-employment/{nino}/{business_id}"
            f"/period/cumulative/{formatted_tax_year}"
        )
        return self._make_request('GET', endpoint)
    
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
        Get annual summary (allowances & adjustments) for a tax year.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            tax_year: Tax year (e.g., '2024-25')
            
        Returns:
            dict: Annual summary data with allowances and adjustments
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
    
    def list_calculations(self, nino, tax_year):
        """
        List all tax calculations for a tax year using Individual Calculations API v8.0.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year in YYYY/YYYY format (e.g., '2024/2025')
            
        Returns:
            dict: List of calculations with IDs and metadata
        """
        formatted_tax_year = tax_year.replace('/', '-')
        endpoint = f"/individuals/calculations/{nino}/self-assessment"
        params = {'taxYear': formatted_tax_year}
        return self._make_request('GET', endpoint, params=params)
    
    def retrieve_calculation(self, nino, calculation_id):
        """
        Retrieve a specific tax calculation by ID using Individual Calculations API v8.0.
        Returns full tax breakdown including income, expenses, allowances, and tax liability.
        
        Args:
            nino: National Insurance Number
            calculation_id: Calculation ID from HMRC
            
        Returns:
            dict: Complete tax calculation with breakdown
        """
        endpoint = f"/individuals/calculations/{nino}/self-assessment/{calculation_id}"
        return self._make_request('GET', endpoint)
    
    def get_tax_calculation(self, nino, tax_year):
        """
        Get the latest tax calculation for a tax year (legacy method).
        This retrieves the calculation after crystallisation has been triggered.
        Use list_calculations() and retrieve_calculation() for more control.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year in YYYY/YYYY format (e.g., '2024/2025')
            
        Returns:
            dict: Tax calculation data including calculationId and tax liability
        """
        return self.list_calculations(nino, tax_year)
    
    def trigger_crystallisation(self, nino, tax_year, calculation_type='intent-to-finalise'):
        """
        Trigger tax calculation for a tax year using Individual Calculations API v8.0.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year in YYYY/YYYY format (e.g., '2024/2025')
            calculation_type: Type of calculation - 'intent-to-finalise', 'intent-to-amend', or 'in-year'
            
        Returns:
            dict: Response with calculationId
        """
        valid_types = ['intent-to-finalise', 'intent-to-amend', 'in-year']
        if calculation_type not in valid_types:
            return {
                'success': False,
                'error': f'calculation_type must be one of: {", ".join(valid_types)}'
            }
        
        # Convert tax year from YYYY/YYYY to YYYY-YY format (e.g., '2024/2025' -> '2024-25')
        if '/' in tax_year:
            parts = tax_year.split('/')
            formatted_tax_year = f"{parts[0]}-{parts[1][-2:]}"
        else:
            formatted_tax_year = tax_year
        
        # Correct endpoint: POST /individuals/calculations/{nino}/self-assessment
        endpoint = f"/individuals/calculations/{nino}/self-assessment"
        data = {
            'taxYear': formatted_tax_year,
            'calculationType': calculation_type
        }
        return self._make_request('POST', endpoint, data=data)
    
    def submit_final_declaration(self, nino, tax_year, calculation_id, declaration_type='final-declaration'):
        """
        Submit the final declaration for a tax year using Individual Calculations API v8.0.
        This is the point of no return - confirms all information is complete and correct.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year in YYYY/YYYY format (e.g., '2024/2025')
            calculation_id: The calculation ID from trigger_crystallisation
            declaration_type: 'final-declaration' or 'confirm-amendment'
            
        Returns:
            dict: Response with receipt/confirmation
        """
        valid_types = ['final-declaration', 'confirm-amendment']
        if declaration_type not in valid_types:
            return {
                'success': False,
                'error': f'declaration_type must be one of: {", ".join(valid_types)}'
            }
        
        formatted_tax_year = tax_year.replace('/', '-')
        endpoint = f"/individuals/declarations/{nino}/{formatted_tax_year}"
        data = {
            'calculationId': calculation_id,
            'declarationType': declaration_type,
            'finalised': True
        }
        return self._make_request('POST', endpoint, data=data)
    
    def submit_uk_property_period(self, nino, business_id, tax_year, period_data):
        """
        Submit UK property period data to HMRC using Property Business API v6.0.
        
        Args:
            nino: National Insurance Number
            business_id: Property business ID from HMRC
            tax_year: Tax year (e.g., '2024-25')
            period_data: Period data including dates, income, and expenses
            
        Returns:
            dict: Submission response
        """
        endpoint = f"/individuals/business/property/{nino}/uk/{business_id}/period/{tax_year}"
        return self._make_request('POST', endpoint, data=period_data)
    
    def get_uk_property_obligations(self, nino):
        """
        Get UK property obligations using Obligations API v3.0.
        
        Args:
            nino: National Insurance Number
            
        Returns:
            dict: UK property obligations data
        """
        endpoint = f"/obligations/details/{nino}/income-and-expenditure"
        params = {'typeOfBusiness': 'uk-property'}
        return self._make_request('GET', endpoint, params=params)
    
    def trigger_bsas(self, nino, business_id, tax_year, type_of_business='self-employment'):
        """
        Trigger Business Source Adjustable Summary (BSAS) using BSAS API v7.0.
        
        Args:
            nino: National Insurance Number
            business_id: Business ID from HMRC
            tax_year: Tax year (e.g., '2024/2025')
            type_of_business: 'self-employment' or 'uk-property'
            
        Returns:
            dict: Response with calculationId
        """
        # Convert tax year to start/end dates
        # Tax year 2024/2025 runs from 06/04/2024 to 05/04/2025
        if '/' in tax_year:
            start_year = tax_year.split('/')[0]
        else:
            # Handle 2024-25 format
            start_year = tax_year.split('-')[0]
        
        start_date = f"{start_year}-04-06"
        end_year = str(int(start_year) + 1)
        end_date = f"{end_year}-04-05"
        
        endpoint = f"/individuals/self-assessment/adjustable-summary/{nino}/trigger"
        data = {
            'accountingPeriod': {
                'startDate': start_date,
                'endDate': end_date
            },
            'typeOfBusiness': type_of_business,
            'businessId': business_id
        }
        return self._make_request('POST', endpoint, data=data)
    
    def get_bsas_summary(self, nino, bsas_id, tax_year='2024-25', type_of_business='self-employment'):
        """
        Get Business Source Adjustable Summary by calculationId using BSAS API v7.0.
        
        Args:
            nino: National Insurance Number
            bsas_id: calculationId from trigger response
            tax_year: Tax year (optional, not used in v7.0 endpoint)
            type_of_business: 'self-employment' or 'uk-property', defaults to 'self-employment'
            
        Returns:
            dict: BSAS summary data
        """
        # BSAS v7.0 endpoint includes business type in the path
        endpoint = f"/individuals/self-assessment/adjustable-summary/{nino}/{type_of_business}/{bsas_id}"
        
        logger.info(f"BSAS summary request: endpoint={endpoint}, type={type_of_business}")
        
        return self._make_request('GET', endpoint)
    
    def create_loss(self, nino, tax_year, type_of_loss, business_id, loss_amount):
        """
        Create a brought forward loss using Individual Losses API v6.0.
        
        Args:
            nino: National Insurance Number
            tax_year: Tax year brought forward from (e.g., '2023-24')
            type_of_loss: 'self-employment', 'uk-property-fhl', or 'uk-property-non-fhl'
            business_id: Business ID from HMRC
            loss_amount: Loss amount in pounds (e.g., 1000.00)
            
        Returns:
            dict: Response with lossId
        """
        endpoint = f"/individuals/losses/{nino}/brought-forward-losses"
        data = {
            'taxYearBroughtForwardFrom': tax_year,
            'typeOfLoss': type_of_loss,
            'businessId': business_id,
            'lossAmount': float(loss_amount)
        }
        return self._make_request('POST', endpoint, data=data)
    
    def list_losses(self, nino, tax_year=None, type_of_loss=None, business_id=None):
        """
        List brought forward losses using Individual Losses API v6.0.
        
        Args:
            nino: National Insurance Number
            tax_year: Optional tax year filter (e.g., '2023-24')
            type_of_loss: Optional loss type filter
            business_id: Optional business ID filter
            
        Returns:
            dict: List of losses
        """
        endpoint = f"/individuals/losses/{nino}/brought-forward-losses"
        params = {}
        if tax_year:
            params['taxYearBroughtForwardFrom'] = tax_year
        if type_of_loss:
            params['typeOfLoss'] = type_of_loss
        if business_id:
            params['businessId'] = business_id
        
        return self._make_request('GET', endpoint, params=params if params else None)
    
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
