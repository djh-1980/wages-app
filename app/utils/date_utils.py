"""
Date and time utility functions.
Centralized date handling, formatting, and validation.
"""

from datetime import datetime, timedelta, date
import re
from typing import Optional, Union, List, Tuple


class DateUtils:
    """Utility class for date operations."""
    
    # Common date formats used in the application
    DD_MM_YYYY = '%d/%m/%Y'
    DD_MM_YY = '%d/%m/%y'
    YYYY_MM_DD = '%Y-%m-%d'
    ISO_FORMAT = '%Y-%m-%dT%H:%M:%S'
    
    @staticmethod
    def parse_date(date_string: str) -> Optional[datetime]:
        """Parse date string in various formats."""
        if not date_string or date_string.strip() == '':
            return None
        
        date_string = date_string.strip()
        
        # Try common formats
        formats = [
            DateUtils.DD_MM_YYYY,
            DateUtils.DD_MM_YY,
            DateUtils.YYYY_MM_DD,
            DateUtils.ISO_FORMAT,
            '%d/%m/%Y %H:%M:%S',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%Y-%m-%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def format_date(date_obj: Union[datetime, date], format_str: str = DD_MM_YYYY) -> str:
        """Format date object to string."""
        if date_obj is None:
            return ''
        
        if isinstance(date_obj, str):
            date_obj = DateUtils.parse_date(date_obj)
            if date_obj is None:
                return ''
        
        return date_obj.strftime(format_str)
    
    @staticmethod
    def convert_date_format(date_string: str, from_format: str, to_format: str) -> str:
        """Convert date from one format to another."""
        try:
            date_obj = datetime.strptime(date_string, from_format)
            return date_obj.strftime(to_format)
        except ValueError:
            return date_string  # Return original if conversion fails
    
    @staticmethod
    def is_valid_date(date_string: str) -> bool:
        """Check if date string is valid."""
        return DateUtils.parse_date(date_string) is not None
    
    @staticmethod
    def get_week_number(date_obj: Union[datetime, date, str]) -> int:
        """Get week number for a date."""
        if isinstance(date_obj, str):
            date_obj = DateUtils.parse_date(date_obj)
        
        if date_obj is None:
            return 0
        
        return date_obj.isocalendar()[1]
    
    @staticmethod
    def get_tax_year(date_obj: Union[datetime, date, str]) -> int:
        """Get tax year for a date (April to March)."""
        if isinstance(date_obj, str):
            date_obj = DateUtils.parse_date(date_obj)
        
        if date_obj is None:
            return datetime.now().year
        
        # Tax year starts in April
        if date_obj.month >= 4:
            return date_obj.year
        else:
            return date_obj.year - 1
    
    @staticmethod
    def get_date_range(start_date: str, end_date: str) -> List[datetime]:
        """Get list of dates between start and end dates."""
        start = DateUtils.parse_date(start_date)
        end = DateUtils.parse_date(end_date)
        
        if start is None or end is None:
            return []
        
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
        
        return dates
    
    @staticmethod
    def days_between(date1: str, date2: str) -> int:
        """Calculate days between two dates."""
        d1 = DateUtils.parse_date(date1)
        d2 = DateUtils.parse_date(date2)
        
        if d1 is None or d2 is None:
            return 0
        
        return abs((d2 - d1).days)
    
    @staticmethod
    def add_business_days(start_date: Union[datetime, str], days: int) -> datetime:
        """Add business days to a date (excluding weekends)."""
        if isinstance(start_date, str):
            start_date = DateUtils.parse_date(start_date)
        
        if start_date is None:
            start_date = datetime.now()
        
        current = start_date
        days_added = 0
        
        while days_added < days:
            current += timedelta(days=1)
            # Monday = 0, Sunday = 6
            if current.weekday() < 5:  # Monday to Friday
                days_added += 1
        
        return current
    
    @staticmethod
    def get_month_boundaries(date_obj: Union[datetime, str]) -> Tuple[datetime, datetime]:
        """Get first and last day of the month for a given date."""
        if isinstance(date_obj, str):
            date_obj = DateUtils.parse_date(date_obj)
        
        if date_obj is None:
            date_obj = datetime.now()
        
        first_day = date_obj.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get last day of month
        if date_obj.month == 12:
            last_day = date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = date_obj.replace(month=date_obj.month + 1, day=1) - timedelta(days=1)
        
        last_day = last_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return first_day, last_day
    
    @staticmethod
    def get_quarter_boundaries(date_obj: Union[datetime, str]) -> Tuple[datetime, datetime]:
        """Get first and last day of the quarter for a given date."""
        if isinstance(date_obj, str):
            date_obj = DateUtils.parse_date(date_obj)
        
        if date_obj is None:
            date_obj = datetime.now()
        
        quarter = (date_obj.month - 1) // 3 + 1
        first_month = (quarter - 1) * 3 + 1
        
        first_day = date_obj.replace(month=first_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if quarter == 4:
            last_day = date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = date_obj.replace(month=first_month + 3, day=1) - timedelta(days=1)
        
        last_day = last_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return first_day, last_day
    
    @staticmethod
    def humanize_date(date_obj: Union[datetime, str]) -> str:
        """Convert date to human-readable format (e.g., '2 days ago', 'yesterday')."""
        if isinstance(date_obj, str):
            date_obj = DateUtils.parse_date(date_obj)
        
        if date_obj is None:
            return 'Unknown date'
        
        now = datetime.now()
        diff = now - date_obj
        
        if diff.days == 0:
            if diff.seconds < 3600:  # Less than 1 hour
                minutes = diff.seconds // 60
                return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
            else:
                hours = diff.seconds // 3600
                return f'{hours} hour{"s" if hours != 1 else ""} ago'
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.days < 7:
            return f'{diff.days} days ago'
        elif diff.days < 30:
            weeks = diff.days // 7
            return f'{weeks} week{"s" if weeks != 1 else ""} ago'
        elif diff.days < 365:
            months = diff.days // 30
            return f'{months} month{"s" if months != 1 else ""} ago'
        else:
            years = diff.days // 365
            return f'{years} year{"s" if years != 1 else ""} ago'
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> dict:
        """Validate a date range."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        start = DateUtils.parse_date(start_date)
        end = DateUtils.parse_date(end_date)
        
        if start is None:
            result['valid'] = False
            result['errors'].append('Invalid start date format')
        
        if end is None:
            result['valid'] = False
            result['errors'].append('Invalid end date format')
        
        if start and end:
            if start > end:
                result['valid'] = False
                result['errors'].append('Start date must be before end date')
            
            # Check for very large date ranges
            days_diff = (end - start).days
            if days_diff > 365 * 2:  # More than 2 years
                result['warnings'].append('Date range spans more than 2 years')
            
            # Check for future dates
            now = datetime.now()
            if end > now:
                result['warnings'].append('End date is in the future')
        
        return result
