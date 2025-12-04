"""
Input validation utilities for the application.
"""

import re
from datetime import datetime
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_date_string(date_str: str, format: str = '%d/%m/%Y') -> Tuple[bool, Optional[str]]:
    """
    Validate a date string.
    
    Args:
        date_str: Date string to validate
        format: Expected date format (default: DD/MM/YYYY)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_str:
        return False, "Date is required"
    
    if not isinstance(date_str, str):
        return False, "Date must be a string"
    
    try:
        datetime.strptime(date_str, format)
        return True, None
    except ValueError as e:
        logger.warning(f"Invalid date format: {date_str} - {e}")
        return False, f"Invalid date format. Expected {format}"


def validate_job_number(job_number: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a job number format.
    
    Args:
        job_number: Job number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not job_number:
        return False, "Job number is required"
    
    if not isinstance(job_number, str):
        return False, "Job number must be a string"
    
    # Job numbers are typically alphanumeric
    if not re.match(r'^[A-Z0-9\-/]+$', job_number, re.IGNORECASE):
        return False, "Job number contains invalid characters"
    
    if len(job_number) > 50:
        return False, "Job number is too long (max 50 characters)"
    
    return True, None


def validate_amount(amount: any) -> Tuple[bool, Optional[str]]:
    """
    Validate a monetary amount.
    
    Args:
        amount: Amount to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if amount is None:
        return True, None  # Null amounts are allowed
    
    try:
        amount_float = float(amount)
        
        if amount_float < 0:
            return False, "Amount cannot be negative"
        
        if amount_float > 999999.99:
            return False, "Amount is too large"
        
        # Check for reasonable decimal places (max 2)
        if round(amount_float, 2) != amount_float:
            return False, "Amount can have maximum 2 decimal places"
        
        return True, None
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid amount: {amount} - {e}")
        return False, "Amount must be a valid number"


def validate_year(year: any) -> Tuple[bool, Optional[str]]:
    """
    Validate a year value.
    
    Args:
        year: Year to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not year:
        return False, "Year is required"
    
    try:
        year_int = int(year)
        
        if year_int < 2020 or year_int > 2050:
            return False, "Year must be between 2020 and 2050"
        
        return True, None
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid year: {year} - {e}")
        return False, "Year must be a valid number"


def validate_week_number(week: any) -> Tuple[bool, Optional[str]]:
    """
    Validate a week number.
    
    Args:
        week: Week number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not week:
        return False, "Week number is required"
    
    try:
        week_int = int(week)
        
        if week_int < 1 or week_int > 53:
            return False, "Week number must be between 1 and 53"
        
        return True, None
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid week number: {week} - {e}")
        return False, "Week number must be a valid number"


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    if not isinstance(email, str):
        return False, "Email must be a string"
    
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 254:  # RFC 5321
        return False, "Email is too long"
    
    return True, None


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitize a string input by removing dangerous characters.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not value:
        return ""
    
    # Convert to string if not already
    value = str(value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Trim whitespace
    value = value.strip()
    
    # Truncate to max length
    if len(value) > max_length:
        value = value[:max_length]
        logger.warning(f"String truncated to {max_length} characters")
    
    return value


def validate_status(status: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a job status value.
    
    Args:
        status: Status to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_statuses = ['completed', 'DNCO', 'pending', 'cancelled']
    
    if not status:
        return False, "Status is required"
    
    if status not in valid_statuses:
        return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
    
    return True, None
