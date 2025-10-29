"""
Input validation utilities.
Centralized validation functions for data integrity and security.
"""

import re
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from .date_utils import DateUtils


class ValidationUtils:
    """Utility class for input validation."""
    
    # Common regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?[\d\s\-\(\)]{10,}$')
    POSTCODE_UK_PATTERN = re.compile(r'^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$', re.IGNORECASE)
    JOB_NUMBER_PATTERN = re.compile(r'^\d{3,}$')
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> Dict[str, Any]:
        """Validate that a field is not empty."""
        result = {'valid': True, 'errors': []}
        
        if value is None or (isinstance(value, str) and value.strip() == ''):
            result['valid'] = False
            result['errors'].append(f'{field_name} is required')
        
        return result
    
    @staticmethod
    def validate_string(value: str, field_name: str, min_length: int = 0, 
                       max_length: int = None, pattern: str = None) -> Dict[str, Any]:
        """Validate string field."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not isinstance(value, str):
            result['valid'] = False
            result['errors'].append(f'{field_name} must be a string')
            return result
        
        # Length validation
        if len(value) < min_length:
            result['valid'] = False
            result['errors'].append(f'{field_name} must be at least {min_length} characters')
        
        if max_length and len(value) > max_length:
            result['valid'] = False
            result['errors'].append(f'{field_name} must not exceed {max_length} characters')
        
        # Pattern validation
        if pattern and not re.match(pattern, value):
            result['valid'] = False
            result['errors'].append(f'{field_name} format is invalid')
        
        # Check for potentially dangerous content
        dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=']
        if any(pattern.lower() in value.lower() for pattern in dangerous_patterns):
            result['warnings'].append(f'{field_name} contains potentially unsafe content')
        
        return result
    
    @staticmethod
    def validate_number(value: Union[int, float, str], field_name: str, 
                       min_value: float = None, max_value: float = None,
                       allow_decimal: bool = True) -> Dict[str, Any]:
        """Validate numeric field."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Convert to number if string
        if isinstance(value, str):
            try:
                if allow_decimal:
                    value = float(value)
                else:
                    value = int(value)
            except (ValueError, TypeError):
                result['valid'] = False
                result['errors'].append(f'{field_name} must be a valid number')
                return result
        
        # Type validation
        if not isinstance(value, (int, float)):
            result['valid'] = False
            result['errors'].append(f'{field_name} must be a number')
            return result
        
        # Range validation
        if min_value is not None and value < min_value:
            result['valid'] = False
            result['errors'].append(f'{field_name} must be at least {min_value}')
        
        if max_value is not None and value > max_value:
            result['valid'] = False
            result['errors'].append(f'{field_name} must not exceed {max_value}')
        
        # Check for suspicious values
        if value < 0 and field_name.lower() in ['amount', 'payment', 'salary', 'wage']:
            result['warnings'].append(f'{field_name} is negative, which may be unusual')
        
        return result
    
    @staticmethod
    def validate_currency(value: Union[str, float, int], field_name: str) -> Dict[str, Any]:
        """Validate currency amount."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Handle string input (remove currency symbols)
        if isinstance(value, str):
            # Remove common currency symbols and whitespace
            cleaned = re.sub(r'[£$€,\s]', '', value)
            try:
                value = Decimal(cleaned)
            except InvalidOperation:
                result['valid'] = False
                result['errors'].append(f'{field_name} must be a valid currency amount')
                return result
        
        # Convert to Decimal for precise currency handling
        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation:
            result['valid'] = False
            result['errors'].append(f'{field_name} must be a valid currency amount')
            return result
        
        # Check decimal places (max 2 for currency)
        if decimal_value.as_tuple().exponent < -2:
            result['warnings'].append(f'{field_name} has more than 2 decimal places')
        
        # Range validation for reasonable currency amounts
        if decimal_value < 0:
            result['warnings'].append(f'{field_name} is negative')
        
        if decimal_value > 100000:  # £100,000
            result['warnings'].append(f'{field_name} is unusually large')
        
        return result
    
    @staticmethod
    def validate_email(email: str, field_name: str = 'Email') -> Dict[str, Any]:
        """Validate email address."""
        result = {'valid': True, 'errors': []}
        
        if not isinstance(email, str):
            result['valid'] = False
            result['errors'].append(f'{field_name} must be a string')
            return result
        
        if not ValidationUtils.EMAIL_PATTERN.match(email):
            result['valid'] = False
            result['errors'].append(f'{field_name} format is invalid')
        
        return result
    
    @staticmethod
    def validate_postcode(postcode: str, field_name: str = 'Postcode') -> Dict[str, Any]:
        """Validate UK postcode."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not isinstance(postcode, str):
            result['valid'] = False
            result['errors'].append(f'{field_name} must be a string')
            return result
        
        # Clean postcode (remove extra spaces)
        cleaned_postcode = re.sub(r'\s+', ' ', postcode.strip().upper())
        
        if not ValidationUtils.POSTCODE_UK_PATTERN.match(cleaned_postcode):
            result['warnings'].append(f'{field_name} format may be invalid for UK postcodes')
        
        return result
    
    @staticmethod
    def validate_job_number(job_number: Union[str, int], field_name: str = 'Job Number') -> Dict[str, Any]:
        """Validate job number format."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Convert to string for validation
        job_str = str(job_number).strip()
        
        if not ValidationUtils.JOB_NUMBER_PATTERN.match(job_str):
            result['warnings'].append(f'{field_name} should be a numeric value with at least 3 digits')
        
        # Check for reasonable range
        try:
            job_int = int(job_str)
            if job_int < 100:
                result['warnings'].append(f'{field_name} seems unusually low')
            elif job_int > 999999:
                result['warnings'].append(f'{field_name} seems unusually high')
        except ValueError:
            result['valid'] = False
            result['errors'].append(f'{field_name} must be numeric')
        
        return result
    
    @staticmethod
    def validate_date(date_value: str, field_name: str = 'Date') -> Dict[str, Any]:
        """Validate date field."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not isinstance(date_value, str):
            result['valid'] = False
            result['errors'].append(f'{field_name} must be a string')
            return result
        
        parsed_date = DateUtils.parse_date(date_value)
        if parsed_date is None:
            result['valid'] = False
            result['errors'].append(f'{field_name} format is invalid')
            return result
        
        # Check for reasonable date ranges
        from datetime import datetime, timedelta
        now = datetime.now()
        
        # Check if date is too far in the past (more than 10 years)
        if parsed_date < now - timedelta(days=365 * 10):
            result['warnings'].append(f'{field_name} is more than 10 years in the past')
        
        # Check if date is in the future
        if parsed_date > now + timedelta(days=30):
            result['warnings'].append(f'{field_name} is more than 30 days in the future')
        
        return result
    
    @staticmethod
    def validate_payslip_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive payslip data validation."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Required fields
        required_fields = ['tax_year', 'week_number', 'net_payment']
        for field in required_fields:
            field_result = ValidationUtils.validate_required(data.get(field), field)
            if not field_result['valid']:
                result['valid'] = False
                result['errors'].extend(field_result['errors'])
        
        # Tax year validation
        if 'tax_year' in data:
            tax_year_result = ValidationUtils.validate_number(
                data['tax_year'], 'Tax Year', min_value=2020, max_value=2030, allow_decimal=False
            )
            if not tax_year_result['valid']:
                result['valid'] = False
                result['errors'].extend(tax_year_result['errors'])
            result['warnings'].extend(tax_year_result['warnings'])
        
        # Week number validation
        if 'week_number' in data:
            week_result = ValidationUtils.validate_number(
                data['week_number'], 'Week Number', min_value=1, max_value=53, allow_decimal=False
            )
            if not week_result['valid']:
                result['valid'] = False
                result['errors'].extend(week_result['errors'])
        
        # Currency fields validation
        currency_fields = ['net_payment', 'gross_pay', 'tax', 'ni', 'pension']
        for field in currency_fields:
            if field in data and data[field] is not None:
                currency_result = ValidationUtils.validate_currency(data[field], field.replace('_', ' ').title())
                if not currency_result['valid']:
                    result['valid'] = False
                    result['errors'].extend(currency_result['errors'])
                result['warnings'].extend(currency_result['warnings'])
        
        # Business logic validation
        if all(field in data and data[field] is not None for field in ['gross_pay', 'tax', 'ni', 'net_payment']):
            try:
                gross = float(data['gross_pay'])
                tax = float(data['tax'])
                ni = float(data['ni'])
                net = float(data['net_payment'])
                pension = float(data.get('pension', 0))
                
                calculated_net = gross - tax - ni - pension
                if abs(calculated_net - net) > 0.01:
                    result['warnings'].append('Net payment doesn\'t match gross minus deductions')
            except (ValueError, TypeError):
                pass  # Already handled by individual field validation
        
        return result
    
    @staticmethod
    def validate_runsheet_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive runsheet data validation."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Required fields
        required_fields = ['date', 'job_number', 'customer']
        for field in required_fields:
            field_result = ValidationUtils.validate_required(data.get(field), field.replace('_', ' ').title())
            if not field_result['valid']:
                result['valid'] = False
                result['errors'].extend(field_result['errors'])
        
        # Date validation
        if 'date' in data:
            date_result = ValidationUtils.validate_date(data['date'])
            if not date_result['valid']:
                result['valid'] = False
                result['errors'].extend(date_result['errors'])
            result['warnings'].extend(date_result['warnings'])
        
        # Job number validation
        if 'job_number' in data:
            job_result = ValidationUtils.validate_job_number(data['job_number'])
            result['warnings'].extend(job_result['warnings'])
        
        # Customer name validation
        if 'customer' in data:
            customer_result = ValidationUtils.validate_string(
                data['customer'], 'Customer', min_length=2, max_length=100
            )
            if not customer_result['valid']:
                result['valid'] = False
                result['errors'].extend(customer_result['errors'])
            result['warnings'].extend(customer_result['warnings'])
        
        # Status validation
        if 'status' in data:
            valid_statuses = ['pending', 'completed', 'missed', 'dnco', 'extra']
            if data['status'] not in valid_statuses:
                result['valid'] = False
                result['errors'].append(f'Status must be one of: {", ".join(valid_statuses)}')
        
        # Postcode validation
        if 'postcode' in data and data['postcode']:
            postcode_result = ValidationUtils.validate_postcode(data['postcode'])
            result['warnings'].extend(postcode_result['warnings'])
        
        return result
    
    @staticmethod
    def sanitize_input(value: str, max_length: int = 1000) -> str:
        """Sanitize input string to prevent XSS and other attacks."""
        if not isinstance(value, str):
            return str(value)
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', value)
        
        # Limit length
        sanitized = sanitized[:max_length]
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
