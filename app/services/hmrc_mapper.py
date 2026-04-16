"""
HMRC Data Mapping Service for MTD Self-Employment.
Maps expense data to HMRC API format and validates submissions.
"""

import logging
from datetime import datetime

from ..models.expense import ExpenseModel
from ..database import execute_query

logger = logging.getLogger(__name__)


class HMRCMapper:
    """Map expense data to HMRC MTD format."""
    
    @staticmethod
    def calculate_quarterly_periods(tax_year):
        """
        Calculate quarterly period dates for a tax year.
        
        Args:
            tax_year: Tax year string (e.g., '2024/2025')
            
        Returns:
            list: List of quarterly periods with start/end dates
        """
        start_year = int(tax_year.split('/')[0])
        
        periods = [
            {
                'period_id': 'Q1',
                'start_date': f'{start_year}-04-06',
                'end_date': f'{start_year}-07-05',
                'due_date': f'{start_year}-08-05'
            },
            {
                'period_id': 'Q2',
                'start_date': f'{start_year}-07-06',
                'end_date': f'{start_year}-10-05',
                'due_date': f'{start_year}-11-05'
            },
            {
                'period_id': 'Q3',
                'start_date': f'{start_year}-10-06',
                'end_date': f'{start_year + 1}-01-05',
                'due_date': f'{start_year + 1}-02-05'
            },
            {
                'period_id': 'Q4',
                'start_date': f'{start_year + 1}-01-06',
                'end_date': f'{start_year + 1}-04-05',
                'due_date': f'{start_year + 1}-05-05'
            }
        ]
        
        return periods
    
    @staticmethod
    def get_period_for_date(date_str, tax_year):
        """
        Determine which quarterly period a date falls into.
        
        Args:
            date_str: Date string (YYYY-MM-DD)
            tax_year: Tax year string (e.g., '2024/2025')
            
        Returns:
            str: Period ID (Q1, Q2, Q3, Q4) or None
        """
        date = datetime.strptime(date_str, '%Y-%m-%d')
        periods = HMRCMapper.calculate_quarterly_periods(tax_year)
        
        for period in periods:
            start = datetime.strptime(period['start_date'], '%Y-%m-%d')
            end = datetime.strptime(period['end_date'], '%Y-%m-%d')
            
            if start <= date <= end:
                return period['period_id']
        
        return None
    
    @staticmethod
    def map_expenses_to_hmrc_format(expenses):
        """
        Map expenses to HMRC API format.
        
        Args:
            expenses: List of expense records
            
        Returns:
            dict: HMRC-formatted expense data
        """
        # Initialize expense categories - Pre-TY 2023-24 format (flat decimal values)
        # HMRC Self Employment Business API v5.0 for TY 2024-25 uses this format
        expense_data = {
            'costOfGoodsBought': 0,
            'cisPaymentsToSubcontractors': 0,
            'staffCosts': 0,
            'travelCosts': 0,
            'premisesRunningCosts': 0,
            'maintenanceCosts': 0,
            'adminCosts': 0,
            'advertisingCosts': 0,
            'interest': 0,
            'financialCharges': 0,
            'badDebt': 0,
            'professionalFees': 0,
            'depreciation': 0,
            'other': 0
        }
        
        # Map each expense to HMRC category
        for expense in expenses:
            amount = float(expense['amount'])
            hmrc_box = expense.get('hmrc_box', 'Other expenses')
            hmrc_box_lower = hmrc_box.lower()  # Case-insensitive matching
            
            # Debug logging to see actual category values
            logger.debug(f'Mapping expense: amount={amount}, hmrc_box="{hmrc_box}", category="{expense.get("category_name", "Unknown")}"')
            
            # Map to HMRC API pre-TY 2023-24 field names (flat decimal values)
            # IMPORTANT: Check 'admin' BEFORE 'advertis' to prevent mismatches
            if 'cost of goods' in hmrc_box_lower or 'materials' in hmrc_box_lower:
                expense_data['costOfGoodsBought'] += amount
            elif 'cis' in hmrc_box_lower and 'payment' in hmrc_box_lower:
                expense_data['cisPaymentsToSubcontractors'] += amount
            elif 'staff' in hmrc_box_lower or 'wages' in hmrc_box_lower:
                expense_data['staffCosts'] += amount
            elif 'motor' in hmrc_box_lower or 'vehicle' in hmrc_box_lower or 'fuel' in hmrc_box_lower or 'travel' in hmrc_box_lower:
                # Motor/vehicle/travel expenses → travelCosts
                expense_data['travelCosts'] += amount
            elif 'premises' in hmrc_box_lower:
                expense_data['premisesRunningCosts'] += amount
            elif 'maintenance' in hmrc_box_lower:
                expense_data['maintenanceCosts'] += amount
            elif 'admin' in hmrc_box_lower:
                # Check admin BEFORE advertising to prevent "Admin" matching "Advertising"
                expense_data['adminCosts'] += amount
            elif 'advertis' in hmrc_box_lower:
                expense_data['advertisingCosts'] += amount
            elif 'interest' in hmrc_box_lower:
                expense_data['interest'] += amount
            elif 'financial' in hmrc_box_lower:
                expense_data['financialCharges'] += amount
            elif 'bad debt' in hmrc_box_lower or 'irrecoverable' in hmrc_box_lower:
                expense_data['badDebt'] += amount
            elif 'professional' in hmrc_box_lower or 'fees' in hmrc_box_lower:
                expense_data['professionalFees'] += amount
            elif 'depreciation' in hmrc_box_lower:
                expense_data['depreciation'] += amount
            else:
                expense_data['other'] += amount
        
        # Round all amounts to 2 decimal places
        for category in expense_data:
            expense_data[category] = round(expense_data[category], 2)
        
        # Only include expense fields with non-zero amounts
        expense_data = {k: v for k, v in expense_data.items() if v > 0}
        
        return expense_data
    
    @staticmethod
    def get_income_for_period(start_date, end_date):
        """
        Get total income for a period from payslips.
        
        Args:
            start_date: Period start date (YYYY-MM-DD)
            end_date: Period end date (YYYY-MM-DD)
            
        Returns:
            float: Total income
        """
        # Convert dates to DD/MM/YYYY format for database query
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        query = """
            SELECT COALESCE(SUM(gross_subcontractor_payment), 0) as total_income
            FROM payslips
            WHERE date(substr(period_end, 7, 4) || '-' || 
                       substr(period_end, 4, 2) || '-' || 
                       substr(period_end, 1, 2)) 
                  BETWEEN ? AND ?
        """
        
        result = execute_query(query, (start_date, end_date), fetch_one=True)
        return round(float(result['total_income'] or 0), 2)
    
    @staticmethod
    def build_period_submission(tax_year, period_id, from_date=None, to_date=None):
        """
        Build complete period submission data for HMRC.
        
        Args:
            tax_year: Tax year string (e.g., '2024/2025')
            period_id: Period ID (Q1, Q2, Q3, Q4)
            from_date: Optional start date (YYYY-MM-DD) - if provided, overrides calculated period
            to_date: Optional end date (YYYY-MM-DD) - if provided, overrides calculated period
            
        Returns:
            dict: Complete submission data
        """
        # Use provided dates if available, otherwise calculate from tax_year and period_id
        if from_date and to_date:
            start_date = from_date
            end_date = to_date
        else:
            periods = HMRCMapper.calculate_quarterly_periods(tax_year)
            period_info = next((p for p in periods if p['period_id'] == period_id), None)
            
            if not period_info:
                return None
            
            start_date = period_info['start_date']
            end_date = period_info['end_date']
        
        # Get expenses for this period
        start_date_display = datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y')
        end_date_display = datetime.strptime(end_date, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        expenses = ExpenseModel.get_expenses(
            start_date=start_date_display,
            end_date=end_date_display
        )
        
        # Get income for this period
        total_income = HMRCMapper.get_income_for_period(
            start_date,
            end_date
        )
        
        # Map expenses to HMRC format
        expense_data = HMRCMapper.map_expenses_to_hmrc_format(expenses)
        
        # Build submission - HMRC Self Employment Business API v5.0 format
        # TY 2024-25: nested structure with periodDates/periodIncome/periodExpenses
        # TY 2025-26+: flat structure with fromDate/toDate/income/expenses
        submission = {
            'periodDates': {
                'periodStartDate': start_date,
                'periodEndDate': end_date
            },
            'periodIncome': {
                'turnover': total_income,
                'other': 0
            },
            'periodExpenses': expense_data
        }
        
        return submission
    
    @staticmethod
    def validate_submission(submission_data):
        """
        Validate submission data meets HMRC requirements.
        
        Args:
            submission_data: Submission data to validate
            
        Returns:
            dict: Validation result with success status and errors
        """
        errors = []
        
        # Check required fields - HMRC Self Employment Business API v5.0
        # TY 2024-25: nested structure
        if 'periodDates' not in submission_data:
            errors.append('Missing periodDates object')
        elif 'periodStartDate' not in submission_data['periodDates'] or 'periodEndDate' not in submission_data['periodDates']:
            errors.append('Missing period dates in periodDates object')
        
        # Check income
        if 'periodIncome' not in submission_data:
            errors.append('Missing periodIncome object')
        elif 'turnover' not in submission_data['periodIncome']:
            errors.append('Missing turnover in periodIncome')
        
        # Check expenses
        if 'periodExpenses' not in submission_data:
            errors.append('Missing periodExpenses object')
        elif not submission_data['periodExpenses']:
            errors.append('No expenses provided in periodExpenses')
        
        # Validate amounts are positive
        if 'periodIncome' in submission_data and 'turnover' in submission_data['periodIncome']:
            turnover = submission_data['periodIncome']['turnover']
            if turnover < 0:
                errors.append('Turnover amount cannot be negative')
        
        if 'periodExpenses' in submission_data:
            for category, amount in submission_data['periodExpenses'].items():
                # Pre-TY 2023-24 format uses flat decimal values
                if not isinstance(amount, (int, float)):
                    errors.append(f'Expense {category} must be a number, not {type(amount).__name__}')
                elif amount < 0:
                    errors.append(f'Expense amount for {category} cannot be negative')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def format_tax_year_for_hmrc(tax_year):
        """
        Convert tax year format from '2024/2025' to '2024-25'.
        
        Args:
            tax_year: Tax year in format '2024/2025'
            
        Returns:
            str: Tax year in HMRC format '2024-25'
        """
        years = tax_year.split('/')
        return f"{years[0]}-{years[1][-2:]}"
