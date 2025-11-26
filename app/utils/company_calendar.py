"""
Company Calendar - Central Source of Truth
Handles all company-specific week calculations, payslip dates, and calendar logic.
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional

class CompanyCalendar:
    """
    Central manager for company week structure and date calculations.
    
    Company Year Structure:
    - Year starts: 09/03/2025 (Sunday)
    - Week 1 ends: 22/03/2025 (Saturday)
    - Weeks run: Sunday to Saturday
    - Pay date: ~2 weeks after week ending
    """
    
    # Company year constants
    YEAR_START_2025 = datetime(2025, 3, 9)  # Sunday
    WEEK_1_END_2025 = datetime(2025, 3, 22)  # Saturday
    
    @classmethod
    def get_week_dates(cls, week_number: int, tax_year: int = 2025) -> Tuple[datetime, datetime]:
        """
        Get the start (Sunday) and end (Saturday) dates for a given week number.
        
        Args:
            week_number: Company week number (1-52/53)
            tax_year: Tax year (default 2025)
            
        Returns:
            Tuple of (sunday_start, saturday_end)
        """
        if tax_year == 2025:
            # Calculate from Week 1 ending date
            week_1_saturday = cls.WEEK_1_END_2025
            target_saturday = week_1_saturday + timedelta(weeks=week_number - 1)
            target_sunday = target_saturday - timedelta(days=6)
            
            return target_sunday, target_saturday
        else:
            # For other years, we'd need to define their start dates
            raise ValueError(f"Tax year {tax_year} not implemented yet")
    
    @classmethod
    def get_week_number_from_date(cls, date: datetime, tax_year: int = 2025) -> int:
        """
        Calculate company week number from any date.
        
        Args:
            date: Any date within the week
            tax_year: Tax year (default 2025)
            
        Returns:
            Company week number
        """
        if tax_year == 2025:
            week_1_saturday = cls.WEEK_1_END_2025
            
            # Find the Saturday of the week containing this date
            days_since_saturday = (date.weekday() + 2) % 7  # Convert to days since Saturday
            week_saturday = date - timedelta(days=days_since_saturday)
            
            # Calculate week number
            days_diff = (week_saturday - week_1_saturday).days
            week_number = (days_diff // 7) + 1
            
            return max(1, week_number)
        else:
            raise ValueError(f"Tax year {tax_year} not implemented yet")
    
    @classmethod
    def parse_date_string(cls, date_str: str) -> datetime:
        """
        Parse date string in DD/MM/YYYY format.
        
        Args:
            date_str: Date in DD/MM/YYYY format
            
        Returns:
            datetime object
        """
        return datetime.strptime(date_str, '%d/%m/%Y')
    
    @classmethod
    def format_date_string(cls, date: datetime) -> str:
        """
        Format datetime to DD/MM/YYYY string.
        
        Args:
            date: datetime object
            
        Returns:
            Date string in DD/MM/YYYY format
        """
        return date.strftime('%d/%m/%Y')
    
    @classmethod
    def get_week_label(cls, week_number: int, tax_year: int = 2025) -> str:
        """
        Get formatted week label for display.
        
        Args:
            week_number: Company week number
            tax_year: Tax year
            
        Returns:
            Formatted string like "26 Oct - 01 Nov 2025"
        """
        sunday, saturday = cls.get_week_dates(week_number, tax_year)
        return f"{sunday.strftime('%d %b')} - {saturday.strftime('%d %b %Y')}"
    
    @classmethod
    def get_current_week(cls) -> Tuple[int, int]:
        """
        Get current company week number and tax year.
        
        Returns:
            Tuple of (week_number, tax_year)
        """
        today = datetime.now()
        
        # Determine tax year (simplified - assumes 2025 for now)
        tax_year = 2025
        week_number = cls.get_week_number_from_date(today, tax_year)
        
        return week_number, tax_year
    
    @classmethod
    def get_payslip_week_from_period_end(cls, period_end_str: str) -> Tuple[int, int]:
        """
        Get week number and tax year from payslip period_end date.
        
        Args:
            period_end_str: Period end date in DD/MM/YYYY format (Saturday)
            
        Returns:
            Tuple of (week_number, tax_year)
        """
        period_end = cls.parse_date_string(period_end_str)
        
        # Determine tax year
        if period_end >= cls.YEAR_START_2025:
            tax_year = 2025
        else:
            tax_year = 2024  # Or whatever previous year logic
        
        week_number = cls.get_week_number_from_date(period_end, tax_year)
        return week_number, tax_year
    
    @classmethod
    def validate_week_dates(cls, week_start_str: str, week_end_str: str) -> bool:
        """
        Validate that week start/end dates follow company week structure.
        
        Args:
            week_start_str: Week start in DD/MM/YYYY (should be Sunday)
            week_end_str: Week end in DD/MM/YYYY (should be Saturday)
            
        Returns:
            True if dates are valid company week
        """
        try:
            start_date = cls.parse_date_string(week_start_str)
            end_date = cls.parse_date_string(week_end_str)
            
            # Check if start is Sunday and end is Saturday
            if start_date.weekday() != 6:  # Sunday = 6
                return False
            if end_date.weekday() != 5:  # Saturday = 5
                return False
            
            # Check if they're exactly 6 days apart
            if (end_date - start_date).days != 6:
                return False
            
            return True
        except:
            return False

# Global instance for easy importing
company_calendar = CompanyCalendar()
